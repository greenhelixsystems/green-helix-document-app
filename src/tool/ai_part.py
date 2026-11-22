# ---------------------------------------------------------------------------
# Working with a document in small pieces: outline, get, asset, patch, diff and
# return-check. These read only what a task needs, so an AI assistant can revise
# one section without loading every section or any attachment.
# ---------------------------------------------------------------------------
import copy
import difflib

_SOURCE_RX = re.compile(r'<script\b[^>]*\bid="doc-source"[^>]*>(.*?)</script', re.S | re.I)
RETURN_STATUS = ("started", "submitted", "validated", "blocked", "changes")
HUMAN_STATUS = ("reviewed", "approved")


def read_data_block(path):
    """Read a file only as far as the end of its data block. Attachments after it are never read."""
    buf = ""
    with open(path, encoding="utf-8") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            buf += chunk
            i = buf.find('id="doc-source"')
            if i >= 0 and buf.find("</script", i) >= 0:
                break
    m = _SOURCE_RX.search(buf)
    if not m:
        raise ValueError("This file has no editing data (an element with id doc-source), so it is not a Helix document.")
    try:
        data = json.loads(m.group(1))
    except ValueError:
        raise ValueError("The data block in this file is damaged.")
    if not isinstance(data, dict):
        raise ValueError("The data block in this file is not in a format this tool knows.")
    return data, len(m.group(1))


def light_load(data):
    """Load a document from its data block alone. Attachments carry their name, size and fingerprint but no bytes."""
    info = data.get("assets") if isinstance(data.get("assets"), dict) else {}

    def find(id_):
        m = info.get(id_)
        if not isinstance(m, dict):
            return None
        sha = m.get("sha256") if isinstance(m.get("sha256"), str) else ""
        return {"b64": "", "type": _s(m.get("type")), "hint": _s(m.get("name")), "sha": sha, "bytes": _int(m.get("bytes"))}
    doc, assets, _missing, _bad = load_data(data, find)
    return doc, assets


def block_text(b, assets):
    """The readable text of a block, for sizes, previews and diffs."""
    t = b["type"]
    if t == "heading":
        return b["text"]
    if t == "text":
        return re.sub(r"<[^>]+>", " ", b["html"]).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    if t in ("markdown",):
        return b["md"]
    if t == "callout":
        return b["text"]
    if t == "checklist":
        return "\n".join(("[x] " if it["done"] else "[ ] ") + it["text"] for it in b["items"])
    if t == "collapsible":
        return "\n".join(it["summary"] + "\n" + it["body"] for it in b["items"])
    if t == "table":
        return "\n".join(" | ".join(r) for r in b["rows"])
    if t == "images":
        return "\n".join((assets[it["asset"]]["name"] if it["asset"] in assets else "") + (": " + it["caption"] if it["caption"] else "") for it in b["items"])
    if t == "files":
        return "\n".join((assets[i]["name"] if i in assets else "") + (": " + b["notes"][i] if i in b["notes"] else "") for i in b["items"])
    if t == "stats":
        return "\n".join(" ".join(x for x in (it["value"], it["label"], it["note"]) if trim(x)) for it in b["items"])
    if t == "cards":
        return "\n".join(it["title"] + (" [" + ", ".join(g["text"] for g in it["tags"]) + "]" if it["tags"] else "") + ("\n" + it["body"] if trim(it["body"]) else "") for it in b["items"])
    if t == "sources":
        return "\n".join(" ".join(x for x in (it["group"], it["title"], it["url"], it["accessed"], it["note"]) if trim(x)) for it in b["items"])
    return ""


def _each_block(doc):
    for t in doc["tabs"]:
        for i, b in enumerate(t["blocks"]):
            yield t, i, b


def _expand(doc, ids):
    """Block ids for a list of block and tab ids, in document order."""
    want = set(ids)
    tabs = set(t["id"] for t in doc["tabs"] if t["id"] in want)
    return [b["id"] for t, _i, b in _each_block(doc) if b["id"] in want or t["id"] in tabs]


def _ai(doc):
    return doc.get("ai") or {}


def outline(path):
    data, n_json = read_data_block(path)
    doc, assets = light_load(data)
    m = doc["meta"]
    ai = _ai(doc)
    focus = set(_expand(doc, ai.get("focus", [])))
    protect = set(_expand(doc, ai.get("protect", [])))
    fresh = content_hash(doc, assets)
    used = {}
    for _t, _i, b in _each_block(doc):
        for it in (b["items"] if b["type"] in ("images", "files") else []):
            used[it["asset"] if b["type"] == "images" else it] = b["id"]
    tabs = []
    focus_chars = 0
    for t in doc["tabs"]:
        bl = []
        for b in t["blocks"]:
            text = block_text(b, assets)
            e = {"id": b["id"], "type": b["type"], "title": trim(b["text"] if b["type"] == "heading" else b["title"]), "chars": len(text)}
            pre = re.sub(r"\s+", " ", trim(text))
            if b["type"] != "heading" and pre:
                e["preview"] = pre[:100] + ("\u2026" if len(pre) > 100 else "")
            if b["id"] in focus:
                e["focus"] = True
                focus_chars += len(text)
            if b["id"] in protect:
                e["protect"] = True
            bl.append(e)
        tabs.append({"id": t["id"], "title": t["title"], "blocks": bl})
    out = {"file": os.path.basename(path), "helix": data.get("spec") or "1.0", "id": m["id"], "rev": prune(m["rev"]),
           "base": fresh, "title": doc["title"], "subtitle": doc["subtitle"]}
    if data.get("format") == "helix" and isinstance(data.get("version"), (int, float)) and data["version"] > FORMAT_VERSION:
        out["warning"] = "format version %s is newer than this tool: read only" % data["version"]
    elif m["rev"]["hash"] != fresh:
        out["warning"] = "the content no longer matches its revision hash (changed by hand or by software that does not record revisions)"
    for k in ("created", "modified", "source"):
        if m.get(k):
            out[k] = m[k]
    out["ai"] = ai or None
    out["default_scope"] = "focus" if focus else "whole document"
    out["log"] = m["log"][-3:]
    out["log_entries"] = len(m["log"])
    out["tabs"] = tabs
    out["assets"] = [prune({"id": k, "name": a["name"], "type": a["type"], "bytes": a["bytes"], "sha256": a["sha"], "in": used.get(k, "")}) for k, a in assets.items()]
    out["size"] = {"file_bytes": os.path.getsize(path), "data_block_chars": n_json, "focus_chars": focus_chars}
    return out


def _differences(a, b, path="", out=None):
    """JSON paths where a (as written) differs from b (canonical form)."""
    out = [] if out is None else out
    if len(out) >= 12:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a.keys()) + [k for k in b if k not in a]:
            if k not in b:
                out.append("%s.%s: not part of the format (remove it)" % (path, k))
            elif k not in a:
                out.append("%s.%s: missing (canonical value %s)" % (path, k, json.dumps(b[k], ensure_ascii=False)[:60]))
            else:
                _differences(a[k], b[k], "%s.%s" % (path, k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s: %d item(s) written, %d in canonical form" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            _differences(x, y, "%s[%d]" % (path, i), out)
    elif a != b or type(a) != type(b):
        out.append("%s: written %s, canonical %s" % (path, json.dumps(a, ensure_ascii=False)[:60], json.dumps(b, ensure_ascii=False)[:60]))
    return out


def hash_report(path, show=False):
    """For writers other than this tool: is the stored rev.hash right, and is the data block in canonical form?"""
    data, _ = read_data_block(path)
    doc, assets = light_load(data)
    rev = data.get("rev") if isinstance(data.get("rev"), dict) else {}
    stored = rev.get("hash") if isinstance(rev.get("hash"), str) else None
    computed = content_hash(doc, assets)
    canon_block = json.loads(_js_json(data_block(doc, assets)))
    diffs = [] if canon_block == data else _differences(data, canon_block)
    out = {"stored": stored, "computed": computed, "match": stored == computed, "canonical": not diffs}
    if diffs:
        out["differences"] = diffs
    if show:
        out["canonical_json"] = _canon(content_of(doc, assets))
    return out


def get_blocks(path, ids, focus=False, as_md=False):
    data, _n = read_data_block(path)
    doc, assets = light_load(data)
    ai = _ai(doc)
    want = list(ids) + (ai.get("focus", []) if focus else [])
    if not want:
        raise ValueError("name one or more block or tab ids, or use --focus")
    known = known_ids(doc)
    unknown = [x for x in want if x not in known]
    if unknown:
        raise ValueError("no block or tab with id: " + ", ".join(unknown))
    pick = set(_expand(doc, want))
    protect = set(_expand(doc, ai.get("protect", [])))
    _order, paths = gather_files(doc, assets)
    blocks = []
    for t, i, b in _each_block(doc):
        if b["id"] in pick:
            if as_md:
                title = trim(b["text"] if b["type"] == "heading" else b["title"])
                body = "" if b["type"] == "heading" else _ex_body(b, assets, paths)
                blocks.append("<!-- block %s (%s)%s -->\n" % (b["id"], b["type"], ", do not change" if b["id"] in protect else "")
                              + (("## " if b["type"] == "heading" else "### ") + title + "\n\n" if title else "") + body)
            else:
                e = {"tab": t["id"], "index": i}
                e.update(b)
                if b["id"] in protect:
                    e["protect"] = True
                blocks.append(e)
    head = {"id": doc["meta"]["id"], "rev": doc["meta"]["rev"]["label"], "base": content_hash(doc, assets)}
    if as_md:
        return "<!-- helix %s v%s base %s -->\n\n" % (head["id"], head["rev"], head["base"]) + "\n\n".join(blocks) + "\n"
    head["blocks"] = blocks
    return head


def extract_asset(path, id_, out):
    doc, assets, _m, _b, _r, _d = read_document(open(path, encoding="utf-8").read())
    if id_ not in assets:
        raise ValueError("no attachment with id " + id_)
    a = assets[id_]
    raw = base64.b64decode(a["b64"])
    sha = hashlib.sha256(raw).hexdigest()
    info = (_d.get("assets") or {}).get(id_) or {}
    if info.get("sha256") and info["sha256"] != sha:
        raise ValueError("%s does not match its saved fingerprint; not written" % a["name"])
    with open(out, "wb") as fh:
        fh.write(raw)
    return {"ok": True, "id": id_, "name": a["name"], "type": a["type"], "bytes": len(raw), "sha256": sha, "written": out}


# ---------------------------------------------------------------- patching
def versioned_name(path, label):
    """Report_v1.helix.html -> Report_v1.1.helix.html (adds _vN when the name has none)."""
    d, base = os.path.split(path)
    base = re.sub(r"\.(helix|hlx)\.html?$", "", base, flags=re.I)
    base = re.sub(r"\.html?$", "", base, flags=re.I)
    base = re.sub(r"_v[0-9]+(\.[0-9]+)*$", "", base) or "document"
    return os.path.join(d, base + "_v" + label + ".helix.html")


def _find_block(doc, id_):
    for t, i, b in _each_block(doc):
        if b["id"] == id_:
            return t, i, b
    raise ValueError("no block with id " + _s(id_))


def _find_tab(doc, id_):
    for t in doc["tabs"]:
        if t["id"] == id_:
            return t
    raise ValueError("no tab with id " + _s(id_))


def _place(doc, op, block):
    """Put a block where an insert or move op says: after, before, or at the end (or start) of a tab."""
    if op.get("after") is not None:
        t, i, _b = _find_block(doc, op["after"])
        t["blocks"].insert(i + 1, block)
    elif op.get("before") is not None:
        t, i, _b = _find_block(doc, op["before"])
        t["blocks"].insert(i, block)
    elif op.get("start") is not None:
        _find_tab(doc, op["start"])["blocks"].insert(0, block)
    else:
        tab = _find_tab(doc, op["tab"]) if op.get("tab") is not None else doc["tabs"][-1]
        tab["blocks"].append(block)


def _block_map(doc):
    return dict((b["id"], json.dumps(b, sort_keys=True)) for _t, _i, b in _each_block(doc))


def apply_patch(doc, assets, patch, base_dir=".", ids=None):
    """Apply a patch's ops to a copy of the document. Returns (doc, assets) normalised exactly as a saved file would be."""
    d = copy.deepcopy(doc)
    a = dict(assets)
    ids = ids or IdMaker(doc["meta"]["id"] + "/" + str(doc["meta"]["rev"]["n"]))
    ops = patch.get("ops")
    if not isinstance(ops, list) or not ops:
        raise ValueError("the patch has no ops")
    for k, op in enumerate(ops):
        if not isinstance(op, dict):
            raise ValueError("op %d is not an object" % (k + 1))
        kind = op.get("op")
        if kind == "set":
            _t, _i, b = _find_block(d, op.get("id"))
            fields = op.get("fields") if isinstance(op.get("fields"), dict) else dict((x, y) for x, y in op.items() if x not in ("op", "id"))
            for x, y in fields.items():
                if x in ("id", "type"):
                    raise ValueError("op %d: a block's id and type cannot change (delete it and insert a new one)" % (k + 1))
                b[x] = y
        elif kind == "insert":
            nb = op.get("block")
            if not isinstance(nb, dict) or nb.get("type") not in _BLOCK_TYPES:
                raise ValueError("op %d: insert needs a block with a type (%s)" % (k + 1, ", ".join(_BLOCK_TYPES)))
            nb = dict(nb)
            if not (isinstance(nb.get("id"), str) and re.fullmatch(r"a[a-z0-9]{6,24}", nb["id"]) and nb["id"] not in known_ids(d)):
                nb["id"] = ids.next()
            if nb["type"] in ("images", "files"):
                nb.setdefault("items", [])
            _place(d, op, nb)
        elif kind == "delete":
            t, i, _b = _find_block(d, op.get("id"))
            del t["blocks"][i]
        elif kind == "move":
            t, i, b = _find_block(d, op.get("id"))
            del t["blocks"][i]
            _place(d, op, b)
        elif kind == "ai":
            ai = dict(d.get("ai") or {})
            for x in ("notes", "focus", "protect", "work"):
                if x in op:
                    ai[x] = op[x]
            if isinstance(op.get("notes_append"), str) and trim(op["notes_append"]):
                ai["notes"] = (trim(_s(ai.get("notes"))) + "\n\n" if trim(_s(ai.get("notes"))) else "") + op["notes_append"].strip("\n")
            d["ai"] = ai
        elif kind == "title":
            for x in ("title", "subtitle"):
                if x in op:
                    d[x] = _s(op[x])
        elif kind == "attach":
            p = op.get("file")
            if not isinstance(p, str) or not p:
                raise ValueError("op %d: attach needs a file path" % (k + 1))
            full = p if os.path.isabs(p) else os.path.join(base_dir, p)
            if not os.path.isfile(full):
                raise ValueError("op %d: file not found: %s" % (k + 1, p))
            raw = open(full, "rb").read()
            nid = ids.next()
            while nid in a:
                nid = ids.next()
            name = _s(op.get("name")) or os.path.basename(full)
            a[nid] = {"name": name, "type": _guess_type(full), "b64": base64.b64encode(raw).decode("ascii"), "bytes": len(raw)}
            _t, _i, b = _find_block(d, op.get("to"))
            if b["type"] == "images":
                b["items"].append({"asset": nid, "caption": _s(op.get("caption"))})
            elif b["type"] == "files":
                b["items"].append(nid)
                if trim(_s(op.get("note"))):
                    b["notes"][nid] = _s(op["note"])
                    b["desc"] = True
            else:
                raise ValueError("op %d: attach goes into an Images or Files block" % (k + 1))
        else:
            raise ValueError("op %d: unknown op %r (set, insert, delete, move, ai, title, attach)" % (k + 1, kind))
    # Normalise through the loader, exactly as reopening the saved file would.
    meta_info = dict((k, {"name": x["name"], "type": x["type"], "bytes": x["bytes"], "sha256": fingerprint(x)}) for k, x in a.items())
    raw = {"format": "helix", "version": FORMAT_VERSION, "title": d["title"], "subtitle": d["subtitle"], "options": d["options"],
           "tabs": d["tabs"], "assets": meta_info, "ai": d.get("ai")}
    raw.update(dict((k, v) for k, v in data_block(d, a).items() if k in ("id", "rev", "created", "modified", "source", "log")))

    def find(id_):
        x = a.get(id_)
        return {"b64": x["b64"], "type": x["type"], "hint": x["name"]} if x else None
    nd, na, _missing, _bad = load_data(raw, find, ids)
    nd["meta"] = d["meta"]
    return nd, na


def patch_document(path, patch, base_dir=".", out=None, allow_protected=False, force=False, as_human=False, now=None):
    text = open(path, encoding="utf-8").read()
    doc, assets, missing, bad, _r, data = read_document(text)
    if data.get("format") == "helix" and isinstance(data.get("version"), (int, float)) and data["version"] > FORMAT_VERSION:
        raise ValueError("this file uses format version %s, newer than this tool; it can be read but not patched" % data["version"])
    if missing or bad:
        raise ValueError("the file's attachments are damaged or do not match their fingerprints; run check first")
    if isinstance(patch.get("patch"), dict):  # a return envelope that carries its changes
        env = patch
        patch = dict(env["patch"])
        patch.setdefault("base", env.get("base"))
        patch.setdefault("doc", env.get("doc"))
        lg = dict(patch.get("log") or {})
        for k in ("summary", "status", "task", "questions", "next"):
            lg.setdefault(k, env.get(k))
        if isinstance(env.get("humanReview"), bool):
            lg.setdefault("review", env["humanReview"])
        patch["log"] = lg
    m = doc["meta"]
    base = content_hash(doc, assets)
    if patch.get("doc") and patch["doc"] != m["id"]:
        raise ValueError("this patch is for document %s, but the file is %s" % (patch["doc"], m["id"]))
    if not force:
        if not patch.get("base"):
            raise ValueError("the patch has no base hash; get it from outline or get (or use --force)")
        if patch["base"] != base:
            raise ValueError("CONFLICT: the file has changed since this patch was made (patch base %s..., file %s...). "
                             "Read the current version and make the patch again." % (_s(patch["base"])[:12], base[:12]))
    nd, na = apply_patch(doc, assets, patch, base_dir)
    before, after = _block_map(doc), _block_map(nd)
    changed = [k for k in after if before.get(k) != after[k]]
    deleted = [k for k in before if k not in after]
    old_ai, new_ai = _ai(doc), _ai(nd)
    protect = set(_expand(doc, old_ai.get("protect", [])))
    touched = [k for k in changed + deleted if k in protect]
    if not allow_protected:
        if touched:
            raise ValueError("PROTECTED: the patch changes section(s) marked do not change: " + ", ".join(_name_of(doc, assets, k) for k in touched))
        if old_ai.get("protect", []) != new_ai.get("protect", []):
            raise ValueError("PROTECTED: only a person can change which sections are protected (use --allow-protected)")
    fresh = content_hash(nd, na)
    if fresh == base:
        raise ValueError("the patch changes nothing")
    lg = patch.get("log") if isinstance(patch.get("log"), dict) else {}
    status = lg.get("status") or "submitted"
    if status in HUMAN_STATUS and not as_human:
        raise ValueError("a patch cannot record '%s'; review and approval are recorded by a person (use --as-human) or by the system that assigned the work" % status)
    if not _has(WORK, status):
        raise ValueError("unknown status %r" % status)
    focus = set(_expand(doc, old_ai.get("focus", [])))
    outside = [k for k in changed + deleted if focus and k not in focus and k in before]
    label = lg.get("label") if isinstance(lg.get("label"), str) and re.fullmatch(_LABEL, lg["label"]) else bump_label(m["rev"]["label"], bool(patch.get("major") or lg.get("major")))
    stamp = now or now_iso()
    nm = copy.deepcopy(m)
    nm["rev"] = {"n": m["rev"]["n"] + 1, "label": label, "hash": fresh, "parent": base}
    nm["modified"] = stamp
    nd["meta"] = nm
    html0 = render(nd, na)
    problems, _notes = check_document(html0)
    checks = trim(_s(lg.get("checks")))
    checks = (checks + "; " if checks else "") + "helix.py check: " + ("pass" if not problems else "FAILED")
    entry = norm_entry({"rev": nm["rev"]["n"], "label": label, "at": stamp, "by": trim(_s(lg.get("by"))) or "unknown",
                        "kind": lg.get("kind") if _has(KINDS, lg.get("kind")) else "ai", "summary": trim(_s(lg.get("summary"))) or "Revised",
                        "blocks": changed, "status": status, "checks": checks,
                        "note": _s(lg.get("note")) + ((" " if trim(_s(lg.get("note"))) else "") + "Deleted %d block(s)." % len(deleted) if deleted else ""),
                        "task": _s(lg.get("task")) or (new_ai.get("work") or {}).get("task", ""), "questions": lg.get("questions"), "next": lg.get("next"),
                        "review": lg.get("review")})
    nm["log"].append(entry)
    html = render(nd, na)
    problems, _notes = check_document(html)
    if problems:
        raise ValueError("the patched document failed its checks: " + "; ".join(problems))
    out = out or versioned_name(path, label)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    return {"ok": True, "file": out, "id": nm["id"], "from": m["rev"]["label"], "to": label, "base": base, "hash": fresh,
            "changed": changed, "deleted": deleted, "outside_focus": outside, "log": entry}


# ---------------------------------------------------------------- comparing
def diff_documents(path_a, path_b, brief=False):
    da, _ = read_data_block(path_a)
    db, _ = read_data_block(path_b)
    a, aa = light_load(da)
    b, ab = light_load(db)
    ma, mb = _block_map(a), _block_map(b)
    order_a = [x["id"] for _t, _i, x in _each_block(a)]
    order_b = [x["id"] for _t, _i, x in _each_block(b)]
    common = [x for x in order_a if x in mb]
    common_b = [x for x in order_b if x in ma]
    changed = []
    for _t, _i, x in _each_block(b):
        if x["id"] in ma and ma[x["id"]] != mb[x["id"]]:
            e = {"id": x["id"], "name": _name_of(b, ab, x["id"])}
            if not brief:
                old = block_text(_find_block(a, x["id"])[2], aa).splitlines()
                new = block_text(x, ab).splitlines()
                lines = [l for l in difflib.unified_diff(old, new, lineterm="", n=1)][2:]
                e["diff"] = lines[:80] + (["... %d more line(s)" % (len(lines) - 80)] if len(lines) > 80 else [])
            changed.append(e)
    out = {"same_document": a["meta"]["id"] == b["meta"]["id"],
           "from": {"id": a["meta"]["id"], "rev": a["meta"]["rev"]["label"], "base": content_hash(a, aa)},
           "to": {"id": b["meta"]["id"], "rev": b["meta"]["rev"]["label"], "base": content_hash(b, ab)},
           "added": [{"id": k, "name": _name_of(b, ab, k)} for k in order_b if k not in ma],
           "removed": [{"id": k, "name": _name_of(a, aa, k)} for k in order_a if k not in mb],
           "changed": changed,
           "moved": common != common_b}
    if a["title"] != b["title"] or a["subtitle"] != b["subtitle"]:
        out["title_changed"] = True
    if _ai(a) != _ai(b):
        out["ai_notes_changed"] = True
    sa = dict((k, x["sha"]) for k, x in aa.items())
    sb = dict((k, x["sha"]) for k, x in ab.items())
    out["attachments"] = {"added": [ab[k]["name"] for k in sb if k not in sa], "removed": [aa[k]["name"] for k in sa if k not in sb],
                          "changed": [ab[k]["name"] for k in sb if k in sa and sa[k] != sb[k]]}
    out["log_added"] = b["meta"]["log"][len(a["meta"]["log"]):] if b["meta"]["log"][:len(a["meta"]["log"])] == a["meta"]["log"] else b["meta"]["log"][-1:]
    return out


# ---------------------------------------------------------------- AI returns
def handback(doc_path, base_path=None):
    """Read the report an AI left in a returned file (its newest Revision Log entry) and check it.
    One file carries everything: the content, the revision, and the report."""
    d, _ = read_data_block(doc_path)
    doc, assets = light_load(d)
    m = doc["meta"]
    if not m["log"]:
        return {"ok": False, "problems": ["the file has no Revision Log entry to report from"], "notes": []}
    e = m["log"][-1]
    env = {"helixReturn": 1, "task": e.get("task") or ((doc.get("ai") or {}).get("work") or {}).get("task", ""), "doc": m["id"],
           "base": m["rev"]["parent"], "result": m["rev"]["hash"], "summary": e.get("summary", ""), "blocks": e.get("blocks", []),
           "status": e.get("status") or "submitted", "humanReview": bool(e.get("review")), "questions": e.get("questions", []), "next": e.get("next", "")}
    out = check_return(env, doc_path, base_path, from_file=True)
    out["report"] = prune({"by": e.get("by", ""), "kind": e.get("kind", ""), "at": e.get("at", ""), "from": e.get("label") and _prev_label(m), "to": m["rev"]["label"],
                           "summary": env["summary"], "questions": env["questions"], "next": env["next"], "needs_review": env["humanReview"],
                           "checks": e.get("checks", ""), "file": os.path.basename(doc_path)})
    return out


def _prev_label(m):
    for e in reversed(m["log"][:-1]):
        if e.get("label") and e.get("label") != m["rev"]["label"]:
            return e["label"]
    return ""


def check_return(env, doc_path=None, base_path=None, base_dir=".", from_file=False):
    """Validate an AI's return envelope. A return is a claim: this checks it is consistent, never that work was approved."""
    problems, notes = [], []
    if not isinstance(env, dict) or env.get("helixReturn") != 1:
        return {"ok": False, "problems": ["not a Helix return (it needs \"helixReturn\": 1)"], "notes": []}
    for k in ("task", "doc", "base", "summary"):
        if not trim(_s(env.get(k))):
            (notes if from_file and k in ("task", "summary") else problems).append(("no " if from_file else "missing ") + k + (" in the newest log entry" if from_file else ""))
    if env.get("base") and not re.fullmatch(_HASH, _s(env.get("base"))):
        problems.append("base is not a revision hash")
    st = env.get("status") or "submitted"
    if st in HUMAN_STATUS:
        problems.append("a return cannot claim '%s'; review and approval are recorded by a person or by the system that assigned the work" % st)
    elif st not in RETURN_STATUS:
        problems.append("unknown status %r (use %s)" % (st, ", ".join(RETURN_STATUS)))
    for c in env.get("checks") or []:
        if isinstance(c, dict) and c.get("result") not in ("pass", "fail", "skipped"):
            notes.append("check %r has no pass/fail/skipped result" % c.get("name"))
    if not isinstance(env.get("humanReview"), bool):
        notes.append("humanReview is not true or false; treat it as true")
    out = {"task": env.get("task"), "status": st, "claimed": True}
    base_doc = None
    if base_path:
        bd, _ = read_data_block(base_path)
        base_doc, base_assets = light_load(bd)
        if base_doc["meta"]["id"] != env.get("doc"):
            problems.append("the return is for document %s, but the base file is %s" % (env.get("doc"), base_doc["meta"]["id"]))
        if content_hash(base_doc, base_assets) != env.get("base"):
            problems.append("the return was made against a different revision than the base file")
    result = None
    if doc_path:
        text = open(doc_path, encoding="utf-8").read()
        p2, _n2 = check_document(text)
        problems += ["returned file: " + p for p in p2]
        if not p2:
            rd_, _ = read_data_block(doc_path)
            result, result_assets = light_load(rd_)
            if result["meta"]["id"] != env.get("doc"):
                problems.append("the returned file is document %s, not %s" % (result["meta"]["id"], env.get("doc")))
            if env.get("result") and env["result"] != content_hash(result, result_assets):
                problems.append("the result hash does not match the returned file")
            if result["meta"]["rev"]["parent"] and env.get("base") and result["meta"]["rev"]["parent"] != env["base"]:
                problems.append("the returned file's revision does not follow the base revision")
    elif isinstance(env.get("patch"), dict) and base_path:
        full = open(base_path, encoding="utf-8").read()
        d0, a0, _m0, _b0, _r0, _x0 = read_document(full)
        try:
            result, result_assets = apply_patch(d0, a0, env["patch"], base_dir)
        except ValueError as e:
            problems.append("the patch does not apply: %s" % e)
    if base_doc is not None and result is not None:
        before, after = _block_map(base_doc), _block_map(result)
        changed = [k for k in after if before.get(k) != after[k]] + [k for k in before if k not in after]
        ai = _ai(base_doc)
        protect = set(_expand(base_doc, ai.get("protect", [])))
        allowed = set(_expand(base_doc, (ai.get("work") or {}).get("targets", []) or ai.get("focus", [])))
        touched = [k for k in changed if k in protect]
        if touched:
            problems.append("changed section(s) marked do not change: " + ", ".join(touched))
        outside = [k for k in changed if allowed and k not in allowed and k in before]
        if outside:
            notes.append("changed section(s) outside the assigned scope: " + ", ".join(outside))
        claimed = set(_ids(env.get("blocks")))
        if claimed and claimed != set(k for k in changed if k in after):
            notes.append("the blocks the return lists differ from the blocks that actually changed")
        out["changed"] = changed
    out["ok"] = not problems
    out["problems"] = problems
    out["notes"] = notes
    return out
