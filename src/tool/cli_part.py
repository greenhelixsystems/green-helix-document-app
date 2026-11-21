# ---------------------------------------------------------------------------
# Reading a document file.
# ---------------------------------------------------------------------------
import mimetypes
import os
import sys


class _Reader(HTMLParser):
    """Finds the data block and every element that carries an embedded file."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.source = None
        self.els = {}
        self.scripts = []
        self._in_source = False
        self._buf = []
        self.bad_attrs = []
        self.csp = None
        self.generator = None
        self.external = []

    def handle_starttag(self, tag, attrs):
        a = dict((k, "" if v is None else v) for k, v in attrs)
        if tag == "script":
            self.scripts.append(a)
            if a.get("id") == "doc-source" and self.source is None:
                self._in_source = True
                self._buf = []
        for k in a:
            if k.startswith("on"):
                self.bad_attrs.append(tag + "[" + k + "]")
        if tag == "meta":
            if a.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = a.get("content")
            if a.get("name") == "generator":
                self.generator = a.get("content")
        if a.get("id") and a["id"] not in self.els:
            self.els[a["id"]] = (tag, a)
        for k in ("src", "href"):
            v = a.get(k)
            if v is not None and tag != "a" and not v.startswith("data:") and not v.startswith("#"):
                self.external.append(tag + " " + k + "=" + v[:60])
            if v is not None and tag == "a" and k == "href" and v.lower().startswith("javascript:"):
                self.external.append("a javascript: link")

    def handle_endtag(self, tag):
        if tag == "script" and self._in_source:
            self._in_source = False
            self.source = "".join(self._buf)

    def handle_data(self, data):
        if self._in_source:
            self._buf.append(data)


def read_document(text):
    """Parse a Helix file. Returns (doc, assets, missing, bad, reader)."""
    r = _Reader()
    r.feed(text)
    r.close()
    if r.source is None:
        raise ValueError("This file has no editing data (an element with id doc-source), so it is not a Helix document.")
    try:
        data = json.loads(r.source)
    except ValueError:
        raise ValueError("The data block in this file is damaged.")
    if not isinstance(data, dict):
        raise ValueError("The data block in this file is not in a format this tool knows.")

    def find(id_):
        e = r.els.get("asset-" + id_) or r.els.get(id_)
        if not e:
            return None
        tag, a = e
        url = a.get("src") or a.get("href") or ""
        i = url.find(",")
        head = url[:i]
        if i < 0 or url[:5] != "data:" or not re.search(r";base64$", head, re.I):
            return None
        return {"b64": url[i + 1:], "type": head[5:].split(";")[0], "hint": a.get("download")}
    doc, assets, missing, bad = load_data(data, find)
    return doc, assets, missing, bad, r, data


# ---------------------------------------------------------------------------
# Unpacking: the document as Markdown plus the original files.
# ---------------------------------------------------------------------------
def _ex_plain(t):
    return re.sub(r"([\\*_`\[\]])", r"\\\1", t)


def _ex_inl(n):
    if isinstance(n, str):
        return _ex_plain(n)
    t = n.tag
    inner = "".join(_ex_inl(c) for c in n.kids)
    if t == "br":
        return "  \n"
    if t == "strong":
        return "**" + trim(inner) + "**" if trim(inner) else inner
    if t == "em":
        return "*" + trim(inner) + "*" if trim(inner) else inner
    if t == "a":
        hr = n.attrs.get("href") or ""
        return "[" + inner + "](" + hr.replace(")", "%29") + ")" if hr else inner
    return inner


def _ex_list(l, d):
    ordered = l.tag == "ol"
    k = 0
    lines = []
    pad = " " * (d * 3)
    for li in l.kids:
        if isinstance(li, str) or li.tag != "li":
            continue
        k += 1
        text = ""
        nested = []
        for c in li.kids:
            if not isinstance(c, str) and c.tag in ("ul", "ol"):
                nested.append(_ex_list(c, d + 1))
            else:
                text += _ex_inl(c)
        lines.append(pad + (("%d. " % k) if ordered else "- ") + trim(text).replace("\n", "\n" + pad + "   "))
        lines.extend(nested)
    return "\n".join(lines)


def _ex_html(html):
    root = parse_fragment(html)
    out = []
    buf = [""]

    def flush():
        if trim(buf[0]):
            out.append(trim(buf[0]))
        buf[0] = ""
    for c in root.kids:
        if not isinstance(c, str) and c.tag == "p":
            flush()
            out.append(trim(_ex_inl(c)))
        elif not isinstance(c, str) and c.tag in ("ul", "ol"):
            flush()
            out.append(_ex_list(c, 0))
        else:
            buf[0] += _ex_inl(c)
    flush()
    return "\n\n".join(x for x in out if x)


def _ex_cell(v):
    return trim(re.sub(r"\s*\n\s*", " ", v.replace("|", "\\|")))


def _ex_path(p):
    from urllib.parse import quote
    return quote(p or "", safe=";,/?:@&=+$-_.!~*'()#").replace("(", "%28").replace(")", "%29")


def _ex_paras(t):
    return [_ex_plain(trim(p)) for p in re.split(r"\n+", t) if trim(p)]


def _ex_body(b, assets, paths):
    t = b["type"]
    if t == "text":
        return _ex_html(sanitize(b["html"]))
    if t == "markdown":
        return trim(b["md"])
    if t == "callout":
        tone = TONES.get(b["tone"], "Note")
        return "\n>\n".join("> " + ("**" + tone + ":** " if i == 0 else "") + p for i, p in enumerate(_ex_paras(b["text"])))
    if t == "checklist":
        return "\n".join("- [" + ("x" if it["done"] else " ") + "] " + _ex_plain(trim(it["text"])) for it in b["items"] if trim(it["text"]))
    if t == "collapsible":
        out = []
        for it in b["items"]:
            if not (trim(it["summary"]) or trim(it["body"])):
                continue
            body = "\n\n".join(_ex_paras(it["body"]))
            out.append("**" + _ex_plain(trim(it["summary"]) or "Details") + "**" + ("\n\n" + body if body else ""))
        return "\n\n".join(out)
    if t == "table":
        rows = [r for r in b["rows"][1:] if any(trim(x) for x in r)]
        if not rows:
            return ""
        return "\n".join(["| " + " | ".join(_ex_cell(x) for x in b["rows"][0]) + " |", "| " + " | ".join("---" for _ in b["rows"][0]) + " |"]
                         + ["| " + " | ".join(_ex_cell(x) for x in r) + " |" for r in rows])
    if t == "images":
        out = []
        for it in b["items"]:
            a = assets.get(it["asset"])
            if not a:
                continue
            cap = trim(it["caption"])
            out.append("![" + _ex_plain(cap or a["name"]) + "](" + _ex_path(paths.get(it["asset"])) + ")" + ("\n*" + _ex_plain(cap) + "*" if cap else ""))
        return "\n\n".join(out)
    if t == "files":
        out = []
        for id_ in b["items"]:
            a = assets.get(id_)
            if not a:
                continue
            note = trim(b["notes"][id_]) if b["desc"] and b["notes"] and b["notes"].get(id_) else ""
            out.append("- [" + _ex_plain(a["name"]) + "](" + _ex_path(paths.get(id_)) + ") (" + fmt_size(a["bytes"]) + ")" + (" - " + _ex_plain(note) if note else "") + "\n  SHA-256: `" + fingerprint(a) + "`")
        return "\n".join(out)
    return ""


def gather_files(doc, assets):
    """Plan the folder layout for unpacked files: [(path, id)] in document order."""
    used = {}
    paths = {}
    order = []

    def add(folder, id_):
        a = assets.get(id_)
        if not a:
            return
        base = folder + "/" + (re.sub(r'[\\/:*?"<>|\u0000-\u001f]', "_", a["name"]) or "file")
        name = base
        k = 2
        dot = base.rfind(".")
        while name.lower() in used:
            name = (base[:dot] + " (%d)" % k + base[dot:]) if dot > len(folder) + 1 else base + " (%d)" % k
            k += 1
        used[name.lower()] = 1
        paths[id_] = name
        order.append((name, id_))
    if doc["options"]["logo"]:
        add("images", doc["options"]["logo"])
    for t in doc["tabs"]:
        for b in t["blocks"]:
            if b["type"] == "images":
                for it in b["items"]:
                    add("images", it["asset"])
            if b["type"] == "files":
                for id_ in b["items"]:
                    add("files", id_)
    return order, paths


def doc_to_markdown(doc, assets, paths):
    L = []
    multi = len(doc["tabs"]) > 1
    base = 2 if multi else 1
    st = STATUS.get(doc["options"]["status"])

    def hd(n, t):
        return "#" * min(6, n) + " " + t
    L.append(hd(1, trim(doc["title"]) or "Untitled document"))
    if st:
        L.append("**Status:** " + st)
    if trim(doc["subtitle"]):
        L.append(trim(doc["subtitle"]))
    L.append("> Exported from a Helix document. Images and attached files are in the folders next to this file, and the paths below are relative to it. SHA256SUMS.txt lists the SHA-256 fingerprint of each file.")
    for ti, t in enumerate(doc["tabs"]):
        seen = False
        if multi:
            L.append(hd(2, _tab_name(t, ti)))
        for b in t["blocks"]:
            if b["type"] == "heading":
                if trim(b["text"]):
                    L.append(hd(base + 1, trim(b["text"])))
                    seen = True
                continue
            body = _ex_body(b, assets, paths)
            title = hd(base + (2 if seen else 1), trim(b["title"])) if trim(b.get("title", "")) else ""
            if title:
                L.append(title)
            if body:
                L.append(body)
    return "\n\n".join(L) + "\n"


def spec_from_document(doc, assets, paths):
    """A spec that rebuilds this document from the unpacked files (see the guide)."""
    def named(entry, id_):
        # keep the display name when the file on disk had to be renamed (clashes, characters not allowed in file names)
        if assets[id_]["name"] != paths[id_].split("/")[-1]:
            entry["name"] = assets[id_]["name"]
        return entry

    def bk(b):
        o = {"id": b["id"], "type": b["type"]}
        if b["type"] == "heading":
            o["text"] = b["text"]
            return o
        o["title"] = b["title"]
        if b["half"]:
            o["half"] = True
        t = b["type"]
        if t == "text":
            o["html"] = b["html"]
        elif t == "markdown":
            o["md"] = b["md"]
        elif t == "images":
            o["items"] = [named({"id": i["asset"], "file": paths[i["asset"]], "caption": i["caption"]}, i["asset"]) for i in b["items"]]
        elif t == "files":
            o["desc"] = b["desc"]
            o["items"] = [named({"id": i, "file": paths[i], "note": b["notes"].get(i, "")}, i) for i in b["items"]]
        elif t == "callout":
            o["tone"] = b["tone"]
            o["text"] = b["text"]
        elif t in ("collapsible", "checklist"):
            o["items"] = b["items"]
        elif t == "table":
            o["rows"] = b["rows"]
        return o
    op = dict(doc["options"])
    if op["logo"]:
        op["logo_id"] = op["logo"]
    op["logo"] = paths.get(op["logo"], "")
    m = doc["meta"]
    out = {"id": m["id"], "rev": prune(m["rev"])}
    for k in ("created", "modified", "source"):
        if m.get(k):
            out[k] = m[k]
    if doc.get("ai"):
        out["ai"] = doc["ai"]
    out.update({"title": doc["title"], "subtitle": doc["subtitle"], "options": op,
                "tabs": [{"id": t["id"], "title": t["title"], "blocks": [bk(b) for b in t["blocks"]]} for t in doc["tabs"]]})
    if m["log"]:
        out["log"] = m["log"]
    return out


def unpack(path, outdir):
    text = open(path, encoding="utf-8").read()
    doc, assets, missing, bad, _r, _d = read_document(text)
    order, paths = gather_files(doc, assets)
    os.makedirs(outdir, exist_ok=True)
    sums = []
    for name, id_ in order:
        full = os.path.join(outdir, *name.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        data = base64.b64decode(assets[id_]["b64"])
        with open(full, "wb") as fh:
            fh.write(data)
        sums.append(hashlib.sha256(data).hexdigest() + "  " + name + "\n")
    with open(os.path.join(outdir, "content.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(doc_to_markdown(doc, assets, paths))
    if sums:
        with open(os.path.join(outdir, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(sums))
    with open(os.path.join(outdir, "spec.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(spec_from_document(doc, assets, paths), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return {"files": len(order), "missing": missing, "bad": bad}


# ---------------------------------------------------------------------------
# Building from a spec.
# ---------------------------------------------------------------------------
_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
          ".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv", ".json": "application/json", ".html": "text/html", ".htm": "text/html", ".zip": "application/zip",
          ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".doc": "application/msword", ".xls": "application/vnd.ms-excel", ".ppt": "application/vnd.ms-powerpoint",
          ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".mov": "video/quicktime", ".wav": "audio/wav", ".eml": "message/rfc822", ".rtf": "application/rtf", ".xml": "application/xml"}
LIMIT = 25 * 1048576
MAX_PIXELS = 1600


def _guess_type(name):
    ext = os.path.splitext(name)[1].lower()
    return _TYPES.get(ext) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def _shrink(data, mime):
    """Scale a large photo down (only when Pillow is installed, and only if it gets smaller)."""
    if mime not in ("image/jpeg", "image/png"):
        return data
    try:
        import io
        from PIL import Image, ImageOps
    except ImportError:
        return data
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if max(im.size) <= MAX_PIXELS:
            return data
        im.thumbnail((MAX_PIXELS, MAX_PIXELS))
        out = io.BytesIO()
        if mime == "image/jpeg":
            im.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
        else:
            im.save(out, "PNG", optimize=True)
        return out.getvalue() if len(out.getvalue()) < len(data) else data
    except Exception:
        return data


def build_from_spec(spec, base_dir=".", shrink=True, today=None, now=None):
    """Turn a spec into (html, problems).

    The revision record follows one rule: a spec without rev.hash is a new document (revision 1, or the rev it names);
    a spec whose content still matches rev.hash is rebuilt unchanged; otherwise it becomes the next revision."""
    html, problems, _doc = build_doc_from_spec(spec, base_dir, shrink, today, now)
    return html, problems


def build_doc_from_spec(spec, base_dir=".", shrink=True, today=None, now=None):
    problems = []
    files = {}
    order = []
    taken = set()

    def reg(path, for_images, name=None, want=None):
        if not isinstance(path, str) or not path:
            problems.append("a file reference is empty")
            return None
        full = path if os.path.isabs(path) else os.path.join(base_dir, path)
        key = (full, for_images, name, want)
        if key in files:
            return files[key]
        if not os.path.isfile(full):
            problems.append("file not found: " + path)
            return None
        data = open(full, "rb").read()
        mime = _guess_type(full)
        if for_images and shrink:
            data = _shrink(data, mime)
        id_ = want if isinstance(want, str) and re.fullmatch(r"a[a-z0-9]{6,24}", want) and want not in taken else "spec%d" % len(order)
        taken.add(id_)
        files[key] = id_
        order.append((id_, {"name": name or os.path.basename(full), "type": mime, "b64": base64.b64encode(data).decode("ascii"), "bytes": len(data), "hint": name or os.path.basename(full)}))
        return id_
    spec = json.loads(json.dumps(spec))
    op = spec.get("options") if isinstance(spec.get("options"), dict) else {}
    op.setdefault("about", True)
    spec["options"] = op
    if "tabs" not in spec and isinstance(spec.get("blocks"), list):
        spec["tabs"] = [{"title": "", "blocks": spec["blocks"]}]
    for t in spec.get("tabs") or []:
        for b in (t.get("blocks") or []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and "html" not in b and isinstance(b.get("text"), str):
                b["html"] = "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(b["text"]))
                b.pop("text", None)
            if b.get("type") == "images":
                items = []
                for it in b.get("items") or []:
                    it = {"file": it} if isinstance(it, str) else dict(it)
                    items.append({"asset": reg(it.get("file"), True, it.get("name"), it.get("id")), "caption": it.get("caption", "")})
                b["items"] = items
            if b.get("type") == "files":
                items = []
                notes = {}
                for it in b.get("items") or []:
                    it = {"file": it} if isinstance(it, str) else dict(it)
                    id_ = reg(it.get("file"), False, it.get("name"), it.get("id"))
                    if id_:
                        items.append(id_)
                        if it.get("note"):
                            notes[id_] = it["note"]
                b["items"] = items
                b["notes"] = notes
                if notes:
                    b.setdefault("desc", True)
    if isinstance(op.get("logo"), str) and op["logo"]:
        op["logo"] = reg(op["logo"], True, None, op.get("logo_id"))
    op.pop("logo_id", None)
    by_id = dict(order)
    spec["assets"] = {}
    if spec.get("format") == "helix" and isinstance(spec.get("version"), (int, float)) and not isinstance(spec.get("version"), bool) and spec["version"] > FORMAT_VERSION:
        raise ValueError("this spec says format version %s, newer than this tool (version %d)" % (spec["version"], FORMAT_VERSION))
    ids = IdMaker(_s(spec.get("title")))
    # Specs may name blocks and tabs with friendly ids ("budget"). Give them real ids and point AI Notes at those.
    ref, used = {}, set()

    def fix(obj):
        i = obj.get("id")
        if isinstance(i, str) and re.fullmatch(r"a[a-z0-9]{6,24}", i) and i not in used:
            used.add(i)
            return
        n = ids.next()
        while n in used:
            n = ids.next()
        if isinstance(i, str) and i and i not in ref:
            ref[i] = n
        obj["id"] = n
        used.add(n)
    for t in spec.get("tabs") or []:
        if isinstance(t, dict):
            fix(t)
            for b in (t.get("blocks") if isinstance(t.get("blocks"), list) else []):
                if isinstance(b, dict):
                    fix(b)
    remap = lambda v: [ref.get(x, x) if isinstance(x, str) else x for x in v] if isinstance(v, list) else v
    if isinstance(spec.get("ai"), dict):
        ai = dict(spec["ai"])
        for k in ("focus", "protect"):
            ai[k] = remap(ai.get(k))
        if isinstance(ai.get("work"), dict):
            ai["work"] = dict(ai["work"], targets=remap(ai["work"].get("targets")), sources=remap(ai["work"].get("sources")))
        spec["ai"] = ai
    raw_rev = spec.get("rev") if isinstance(spec.get("rev"), dict) else {}
    had = _match(_HASH, raw_rev.get("hash"))
    doc, assets, missing, _bad = load_data(spec, lambda i: by_id.get(i), ids)
    m = doc["meta"]
    fresh = content_hash(doc, assets)
    stamp = now or now_iso()
    by = trim(_s(spec.get("by"))) or "helix.py"
    kind = spec.get("kind") if _has(KINDS, spec.get("kind")) else ("tool" if by == "helix.py" else "")
    if not had:
        m["rev"]["hash"] = fresh
        m["rev"]["parent"] = m["rev"]["parent"] if m["rev"]["n"] > 1 else ""
        m["created"] = m["created"] or stamp
        m["modified"] = m["modified"] or m["created"]
        if not m["log"]:
            m["log"] = [norm_entry({"rev": m["rev"]["n"], "label": m["rev"]["label"], "at": m["created"], "by": by, "kind": kind,
                                    "summary": _s(spec.get("summary")) or ("Created" if m["rev"]["n"] == 1 else ""), "status": spec.get("status"),
                                    "task": spec.get("task"), "questions": spec.get("questions"), "next": spec.get("next"), "review": spec.get("review")})]
    elif fresh != had:
        n = m["rev"]["n"] + 1
        label = bump_label(m["rev"]["label"], bool(spec.get("major")))
        m["rev"] = {"n": n, "label": label, "hash": fresh, "parent": had}
        m["modified"] = stamp
        m["log"].append(prune({"rev": n, "label": label, "at": stamp, "by": by, "kind": kind, "summary": _s(spec.get("summary")) or "Rebuilt from spec"}))
    html = render(doc, assets, today)
    size = len(html.encode("utf-8"))
    if size > LIMIT:
        problems.append("the finished file is %s, over the 25 MB limit" % fmt_size(size))
    return html, problems, doc


# ---------------------------------------------------------------------------
# Checking a document.
# ---------------------------------------------------------------------------
def _outside_data(html):
    return re.sub(r'<script type="application/json" id="doc-source">.*?</script>', "<script/>", html, count=1, flags=re.S)


def check_document(text):
    """Returns (problems, notes)."""
    problems = []
    notes = []
    try:
        doc, assets, missing, bad, r, data = read_document(text)
    except ValueError as e:
        return [str(e)], notes
    others = [s for s in r.scripts if s.get("id") != "doc-source"]
    if others or len(r.scripts) != 1:
        problems.append("the file contains %d script element(s); only the data block is allowed" % len(r.scripts))
    if r.scripts and (r.scripts[0].get("type") != "application/json"):
        problems.append("the data block is not type application/json")
    if r.bad_attrs:
        problems.append("event-handler attributes found: " + ", ".join(sorted(set(r.bad_attrs))[:5]))
    if r.csp != DOC_CSP:
        problems.append("the security policy line is missing or changed")
    if r.external:
        problems.append("references to things outside the file: " + "; ".join(r.external[:3]))
    if data.get("format") not in ("helix", "hlx"):
        notes.append("the data block does not say format helix")
    elif data.get("format") == "hlx":
        notes.append("made before version 1.0 (format hlx); opening and saving it in the editor upgrades it")
    if missing:
        problems.append("%d embedded file(s) could not be read" % missing)
    if bad:
        problems.append("file(s) do not match their saved fingerprint: " + ", ".join(bad[:5]))
    for id_, a in assets.items():
        info = (data.get("assets") or {}).get(id_)
        if not info or not info.get("sha256"):
            notes.append("no fingerprint saved for " + a["name"])
    size = len(text.encode("utf-8"))
    if size > LIMIT:
        problems.append("the file is %s, over the 25 MB limit" % fmt_size(size))
    if data.get("format") == "helix" and isinstance(data.get("version"), (int, float)) and not isinstance(data.get("version"), bool) and data["version"] > FORMAT_VERSION:
        notes.append("format version %s is newer than this tool, so only the safety checks apply; it can be read but not patched" % data["version"])
    if data.get("format") == "helix" and data.get("spec"):
        stored = data.get("rev").get("hash") if isinstance(data.get("rev"), dict) else None
        try:
            normalised = json.loads(_js_json(data_block(doc, assets))) != data
        except Exception:
            normalised = True
        if not (isinstance(stored, str) and re.fullmatch(_HASH, stored)):
            notes.append("no revision hash saved; tools add one when they next write the file")
        elif stored != content_hash(doc, assets):
            msg = "the content does not match its revision hash: it was changed by hand or by software that does not record revisions"
            (notes if normalised else problems).append(msg + (" (the data block was also normalised when read)" if normalised else ""))
    if r.generator == GENERATOR:
        date = doc["options"]["footer"]["date"]
        try:
            again = render(doc, assets, None if date else _guess_today(text))
        except Exception as e:
            again = ""
            problems.append("could not rebuild the page: %r" % e)
        if again and _outside_data(again) != _outside_data(text):
            problems.append("the visible page does not match the data block (it was edited by hand, or made by something else)")
        try:
            if json.loads(_js_json(data_block(doc, assets))) != data:
                notes.append("the data block was normalised when read (older or unusual layout)")
        except Exception:
            pass
    else:
        notes.append("made by a different version (%s), so the page layout was not compared" % (r.generator or "unknown"))
    return problems, notes


def _guess_today(text):
    m = re.search(r"Updated ((?:%s) \d{1,2}, \d{4})" % "|".join(_MONTHS), text)
    if m:
        mo, d, y = re.match(r"(\w+) (\d+), (\d+)", m.group(1)).groups()
        return datetime.date(int(y), _MONTHS.index(mo) + 1, int(d))
    return datetime.date.today()


# ---------------------------------------------------------------------------
# Command line.
# ---------------------------------------------------------------------------
USAGE = """helix.py - build, unpack and check Helix documents (single-file, script-free HTML documents)

  python helix.py build spec.json output.helix.html [--no-shrink]
      Build a document from a JSON spec. File paths in the spec are relative to the spec's folder.
  python helix.py unpack document.helix.html outfolder
      Write content.md, spec.json, SHA256SUMS.txt and the original files (files/, images/).
  python helix.py check document.helix.html
      Verify the document: no scripts, security policy intact, files match their fingerprints, page matches data.
  python helix.py md notes.md
      Print the HTML that a Markdown block would produce for this file.

Working in small pieces (for AI assistants; output is JSON):
  python helix.py outline document.helix.html
      Id, revision, AI Notes, recent log and an outline of every block. Reads only the data block, never attachments.
  python helix.py get document.helix.html ID [ID...] [--focus] [--md]
      The full content of the blocks or tabs named (or the AI Notes focus), with the base hash a patch needs.
  python helix.py asset document.helix.html ID output-file
      Write one attachment to a file after checking its fingerprint.
  python helix.py patch document.helix.html patch.json [-o out.helix.html] [--allow-protected] [--force] [--as-human]
      Apply targeted changes by id. Refuses stale bases and protected sections; writes Name_vX.Y.helix.html.
  python helix.py diff old.helix.html new.helix.html [--brief]
      What changed between two revisions, block by block.
  python helix.py check document.helix.html --json
      The checks above as JSON.
  python helix.py return-check --doc returned.helix.html [--base original.helix.html]
      Read and check the report an AI left in a returned file (its newest Revision Log entry).
  python helix.py return-check return.json [--doc returned.helix.html] [--base original.helix.html]
      The same for a separate return (for assistants that could only send a patch).

Standard library only. Photos in Images blocks are scaled to 1600 px if Pillow is installed (--no-shrink to keep them).
"""


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    cmd = argv[1]
    rest = argv[2:]
    opts = {}
    for k in ("-o", "--doc", "--base", "--now"):
        if k in rest:
            i = rest.index(k)
            if i + 1 >= len(rest):
                print("PROBLEM: %s needs a value" % k)
                return 2
            opts[k] = rest[i + 1]
            del rest[i:i + 2]
    args = [a for a in rest if not a.startswith("--")]
    flags = [a for a in rest if a.startswith("--")]

    def emit(obj):
        sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    try:
        if cmd == "build" and len(args) == 2:
            spec = json.load(open(args[0], encoding="utf-8"))
            html, problems = build_from_spec(spec, os.path.dirname(os.path.abspath(args[0])), "--no-shrink" not in flags, None, opts.get("--now"))
            for p in problems:
                print("PROBLEM: " + p)
            if problems:
                return 1
            with open(args[1], "w", encoding="utf-8", newline="") as fh:
                fh.write(html)
            problems, notes = check_document(html)
            for p in problems:
                print("PROBLEM: " + p)
            if problems:
                return 1
            print("OK: wrote %s (%s)" % (args[1], fmt_size(len(html.encode("utf-8")))))
            return 0
        if cmd == "unpack" and len(args) == 2:
            res = unpack(args[0], args[1])
            for b in res["bad"]:
                print("WARNING: %s does not match its saved fingerprint" % b)
            print("OK: wrote content.md, spec.json and %d file(s) to %s" % (res["files"], args[1]))
            return 1 if res["bad"] or res["missing"] else 0
        if cmd == "check" and len(args) == 1 and "--json" in flags:
            problems, notes = check_document(open(args[0], encoding="utf-8").read())
            emit({"ok": not problems, "problems": problems, "notes": notes})
            return 1 if problems else 0
        if cmd == "outline" and len(args) == 1:
            emit(outline(args[0]))
            return 0
        if cmd == "get" and len(args) >= 1:
            res = get_blocks(args[0], args[1:], "--focus" in flags, "--md" in flags)
            if isinstance(res, str):
                sys.stdout.write(res)
            else:
                emit(res)
            return 0
        if cmd == "asset" and len(args) == 3:
            emit(extract_asset(args[0], args[1], args[2]))
            return 0
        if cmd == "patch" and len(args) == 2:
            patch = json.load(open(args[1], encoding="utf-8"))
            if not isinstance(patch, dict):
                raise ValueError("the patch file must hold a JSON object")
            emit(patch_document(args[0], patch, os.path.dirname(os.path.abspath(args[1])), opts.get("-o"),
                                "--allow-protected" in flags, "--force" in flags, "--as-human" in flags, opts.get("--now")))
            return 0
        if cmd == "diff" and len(args) == 2:
            emit(diff_documents(args[0], args[1], "--brief" in flags))
            return 0
        if cmd == "return-check" and len(args) == 0 and opts.get("--doc"):
            res = handback(opts["--doc"], opts.get("--base"))
            emit(res)
            return 0 if res["ok"] else 1
        if cmd == "return-check" and len(args) == 1:
            env = json.load(open(args[0], encoding="utf-8"))
            res = check_return(env, opts.get("--doc"), opts.get("--base"), os.path.dirname(os.path.abspath(args[0])))
            emit(res)
            return 0 if res["ok"] else 1
        if cmd == "check" and len(args) == 1:
            problems, notes = check_document(open(args[0], encoding="utf-8").read())
            for p in problems:
                print("PROBLEM: " + p)
            for n in notes:
                print("NOTE: " + n)
            if not problems:
                print("OK")
            return 1 if problems else 0
        if cmd == "md" and len(args) == 1:
            sys.stdout.write(md_render(open(args[0], encoding="utf-8").read()) + "\n")
            return 0
    except (ValueError, OSError) as e:
        print("PROBLEM: %s" % e)
        return 1
    sys.stdout.write(USAGE)
    return 2


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    sys.exit(main(sys.argv))
