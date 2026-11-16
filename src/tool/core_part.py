# ---------------------------------------------------------------------------
# Rendering: a port of the editor's buildDocument.
# ---------------------------------------------------------------------------
import base64
import datetime
import hashlib
import json

_MONTHS = "January February March April May June July August September October November December".split()


def _tab_name(t, i):
    return trim(t["title"]) or "Tab %d" % (i + 1)


def _is_num(s):
    s = trim(s)
    s = re.sub(r"^[-+]?\$", "", s).replace(",", "")
    return s != "" and re.fullmatch(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)%?", s) is not None


def _paras(text):
    return [p for p in re.split(r"\n+", text) if trim(p)]


def fingerprint(a):
    if not a.get("sha"):
        a["sha"] = hashlib.sha256(base64.b64decode(a["b64"])).hexdigest()
    return a["sha"]


def _section(b, inner):
    return '<section id="s-' + b["id"] + '">' + ("<h2>" + esc(trim(b["title"])) + "</h2>" if trim(b["title"]) else "") + inner + "</section>"


def _render_block(b, doc, assets):
    t = b["type"]
    if t == "heading":
        return '<h2 class="group" id="s-' + b["id"] + '">' + esc(trim(b["text"])) + "</h2>" if trim(b["text"]) else ""
    if t == "text":
        c = sanitize(b["html"])
        return _section(b, '<div class="rich">' + c + "</div>") if (c or trim(b["title"])) else ""
    if t == "markdown":
        c = md_render(b["md"])
        return _section(b, '<div class="rich md">' + c + "</div>") if (c or trim(b["title"])) else ""
    if t == "images":
        figs = []
        for it in b["items"]:
            a = assets.get(it["asset"])
            if not a:
                continue
            cap = trim(it["caption"])
            figs.append('<figure><details class="zoom"><summary title="Enlarge or shrink this image"><img id="asset-' + it["asset"] + '" alt="' + esc(cap or a["name"])
                        + '" src="data:' + a["type"] + ";base64," + a["b64"] + '"></summary></details>' + ("<figcaption>" + esc(cap) + "</figcaption>" if cap else "") + "</figure>")
        return _section(b, '<div class="gallery' + (" one" if len(b["items"]) == 1 else "") + '">' + "".join(figs) + "</div>") if figs else ""
    if t == "table":
        rows = b["rows"]
        cols = len(rows[0])
        num = []
        for c in range(cols):
            any_ = False
            all_ = True
            for r in range(1, len(rows)):
                v = trim(rows[r][c] if c < len(rows[r]) else "")
                if v:
                    any_ = True
                    if not _is_num(v):
                        all_ = False
            num.append(any_ and all_)
        head = "<tr>" + "".join("<th" + (' class="num"' if num[i] else "") + ' scope="col">' + esc(x) + "</th>" for i, x in enumerate(rows[0])) + "</tr>"
        body = "".join("<tr>" + "".join("<td" + (' class="num"' if num[i] else "") + ">" + esc(x) + "</td>" for i, x in enumerate(row)) + "</tr>"
                       for row in rows[1:] if any(trim(x) for x in row))
        if not body:
            return ""
        return _section(b, '<div class="scroll"><table><thead>' + head + "</thead><tbody>" + body + "</tbody></table></div>")
    if t == "collapsible":
        d = "".join("<details><summary>" + esc(trim(it["summary"]) or "Details") + "</summary>" + "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(it["body"])) + "</details>"
                    for it in b["items"] if trim(it["summary"]) or trim(it["body"]))
        return _section(b, d) if (d or trim(b["title"])) else ""
    if t == "callout":
        tone = b["tone"] if b["tone"] in TONES else "note"
        ps = "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(b["text"]))
        if not ps and not trim(b["title"]):
            return ""
        return ('<section class="callout c-' + tone + '" id="s-' + b["id"] + '"><p class="ctag">' + TONES[tone] + "</p>"
                + ("<h2>" + esc(trim(b["title"])) + "</h2>" if trim(b["title"]) else "") + ps + "</section>")
    if t == "checklist":
        li = "".join("<li" + (' class="done"><span class="vh">Done: </span>' if it["done"] else ">") + esc(trim(it["text"])) + "</li>" for it in b["items"] if trim(it["text"]))
        return _section(b, '<ul class="checks">' + li + "</ul>") if (li or trim(b["title"])) else ""
    if t == "files":
        rows = []
        for id_ in b["items"]:
            a = assets.get(id_)
            if not a:
                continue
            note = trim(b["notes"][id_]) if b["desc"] and b["notes"] and id_ in b["notes"] and b["notes"][id_] else ""
            rows.append('<tr><td class="fname">' + esc(a["name"]) + ('<div class="fdesc">' + esc(note) + "</div>" if note else "")
                        + ('<div class="fdesc fp">SHA-256 <code>' + fingerprint(a) + "</code></div>" if doc["options"]["fingerprints"] else "")
                        + '</td><td class="num">' + fmt_size(a["bytes"]) + '</td><td class="act"><a class="dl" id="asset-' + id_ + '" download="' + esc(a["name"])
                        + '" href="data:' + a["type"] + ";base64," + a["b64"] + '">Download</a></td></tr>')
        return (_section(b, '<div class="scroll"><table class="ft"><thead><tr><th scope="col">File</th><th class="num" scope="col">Size</th><th scope="col"><span aria-hidden="true"></span></th></tr></thead><tbody>'
                         + "".join(rows) + "</tbody></table></div>") if rows else "")
    return ""


def _render_tab(t, doc, assets):
    parts = []
    toc = []
    seen = False
    for b in t["blocks"]:
        out = _render_block(b, doc, assets)
        if not out:
            continue
        if b["type"] == "heading":
            seen = True
            toc.append((b["id"], trim(b["text"]), False))
        elif trim(b.get("title", "")):
            toc.append((b["id"], trim(b["title"]), seen))
        parts.append((out, bool(b.get("half")) and b["type"] != "heading"))
    body = ""
    i = 0
    while i < len(parts):
        if parts[i][1] and i + 1 < len(parts) and parts[i + 1][1]:
            body += '<div class="row2">' + parts[i][0] + parts[i + 1][0] + "</div>\n"
            i += 2
        else:
            body += parts[i][0] + "\n"
            i += 1
    nav = ""
    if doc["options"]["toc"] and len(toc) > 1:
        nav = ('<nav class="toc" aria-label="Contents"><section><h2>Contents</h2><ul>'
               + "".join("<li" + (' class="sub"' if sub else "") + '><a href="#s-' + id_ + '">' + esc(tx) + "</a></li>" for id_, tx, sub in toc) + "</ul></section></nav>\n")
    return nav + body


def about_html(has_files):
    return ('<details class="about"><summary>About this file</summary>\n<p>This is a Helix document: a single web page that opens in any browser. It contains no scripts and never connects to the internet. '
            + ("Its images and attached files are stored inside this file, so it can be emailed, saved or archived on its own. Use the Download buttons to save attachments." if has_files
               else "Everything it shows is stored inside this file, so it can be emailed, saved or archived on its own.") + "</p>\n"
            + "<p><strong>For AI assistants and other software</strong></p>\n<ul>" + "".join("<li>" + esc(x) + "</li>" for x in ABOUT_AI) + "</ul>\n</details>\n")


def _js_json(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def data_block(doc, assets):
    meta = {}
    for id_, a in assets.items():
        meta[id_] = {"name": a["name"], "type": a["type"], "bytes": a["bytes"], "sha256": fingerprint(a)}
    head = {"format": "helix", "version": FORMAT_VERSION}
    if doc["options"]["about"]:
        head["about"] = ABOUT_JSON
    head.update({"title": doc["title"], "subtitle": doc["subtitle"], "options": doc["options"], "tabs": doc["tabs"], "assets": meta})
    return head


def render(doc, assets, today=None):
    """The complete HTML of a document, identical to what the editor saves."""
    source = _js_json(data_block(doc, assets))
    title = trim(doc["title"]) or "Untitled document"
    tabcss = ""
    if len(doc["tabs"]) < 2:
        body = _render_tab(doc["tabs"][0], doc, assets)
    else:
        body = ('<div class="tabs">\n<nav class="tabbar" aria-label="Tabs">' + "".join('<a href="#t-' + t["id"] + '">' + esc(_tab_name(t, i)) + "</a>" for i, t in enumerate(doc["tabs"])) + "</nav>\n"
                + "".join('<div class="panel" id="t-' + t["id"] + '">\n<h2 class="ptitle">' + esc(_tab_name(t, i)) + "</h2>\n" + _render_tab(t, doc, assets) + "</div>\n" for i, t in enumerate(doc["tabs"]))
                + "</div>\n")
        tabcss = (".tabs:not(:has(.panel:target,.panel :target)) .tabbar a:first-child,"
                  + ",".join(".tabs:has(#t-" + t["id"] + ":target,#t-" + t["id"] + ' :target) .tabbar a[href="#t-' + t["id"] + '"]' for t in doc["tabs"])
                  + "{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}")
    f = doc["options"]["footer"]
    foot = ""
    if f and f["on"]:
        if f["date"]:
            d = datetime.date(int(f["date"][:4]), int(f["date"][5:7]), int(f["date"][8:10]))
        else:
            d = today or datetime.date.today()
        bits = []
        if trim(f["author"]):
            bits.append(esc(trim(f["author"])))
        if trim(f["version"]):
            bits.append("Version " + esc(trim(f["version"])))
        bits.append("Updated " + esc("%s %d, %d" % (_MONTHS[d.month - 1], d.day, d.year)))
        foot = '<footer class="meta">' + ' <span aria-hidden="true">\u00b7</span> '.join(bits) + "</footer>\n"
    lg = assets.get(doc["options"]["logo"])
    st = doc["options"]["status"] if doc["options"]["status"] in STATUS else ""
    h1 = "<h1>" + esc(title) + "</h1>\n" + ('<p class="sub">' + esc(trim(doc["subtitle"])) + "</p>\n" if trim(doc["subtitle"]) else "")
    if lg or st:
        h1 = ('<header class="head">\n' + ('<img class="logo" id="asset-' + doc["options"]["logo"] + '" alt="Logo" src="data:' + lg["type"] + ";base64," + lg["b64"] + '">\n' if lg else "")
              + '<div class="ht">\n' + ('<p class="status st-' + st + '">' + STATUS[st] + "</p>\n" if st else "") + h1 + "</div>\n</header>\n")
    ac = ACCENTS.get(doc["options"]["accent"])
    tint = ""
    if ac and doc["options"]["accent"] != "green":
        tint = (":root{--accent:" + ac[1] + ";--accent-ink:" + ac[2] + ";--accent-text:" + ac[5] + "}"
                + "@media (prefers-color-scheme:dark){:root{--accent:" + ac[3] + ";--accent-ink:" + ac[4] + ";--accent-text:" + ac[3] + "}}")
    n_files = len(assets) - (1 if doc["options"]["logo"] in assets else 0)
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            + '<meta http-equiv="Content-Security-Policy" content="' + DOC_CSP + '">\n<meta name="generator" content="' + GENERATOR + '">\n'
            + "<title>" + esc(title) + '</title>\n<script type="application/json" id="doc-source">' + source + "</script>\n<style>" + DOC_CSS + tint + tabcss + "</style>\n</head>\n<body>\n<main>\n"
            + h1 + body + foot + (about_html(n_files > 0) if doc["options"]["about"] else "") + "</main>\n</body>\n</html>\n")


# ---------------------------------------------------------------------------
# Loading: a port of the editor's loader. It accepts the JSON stored in a document
# (and the older layouts) and returns a clean document plus its attachments.
# ---------------------------------------------------------------------------
_BLOCK_TYPES = ("heading", "text", "markdown", "images", "table", "collapsible", "checklist", "callout", "files")


def _s(x):
    """JavaScript's String(x) for values that come out of JSON."""
    if isinstance(x, str):
        return x
    if x is None:
        return ""
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, float) and x == int(x) and abs(x) < 1e21:
        return str(int(x))
    if isinstance(x, list):
        return ",".join(_s(i) for i in x)
    if isinstance(x, dict):
        return "[object Object]"
    return str(x)


def _b(x):
    """JavaScript truthiness (an empty list or object is true, unlike Python)."""
    if x is None or x is False:
        return False
    if isinstance(x, (int, float)):
        return x != 0 and x == x
    if isinstance(x, str):
        return x != ""
    return True


def _or(a, b):
    return a if _b(a) else b


def _has(d, k):
    return isinstance(k, str) and k in d


class IdMaker(object):
    """Deterministic ids, so the same input always produces the same file."""

    def __init__(self, seed=""):
        self.n = 0
        self.seed = seed

    def next(self):
        self.n += 1
        return "a" + hashlib.sha1(("%s/%d" % (self.seed, self.n)).encode("utf-8")).hexdigest()[:12]


def load_data(data, find, ids=None):
    """data: parsed JSON. find(id) -> dict(name, type, b64, hint) or None.
    Returns (doc, assets, missing, bad)."""
    ids = ids or IdMaker()
    if isinstance(data.get("tabs"), list):
        tabs_in = data["tabs"]
    elif isinstance(data.get("blocks"), list):
        tabs_in = [{"title": "", "blocks": data["blocks"]}]
    else:
        raise ValueError("The data in this file is not in a format this tool knows.")
    op = data.get("options") if isinstance(data.get("options"), dict) else {}
    fo = op.get("footer") if isinstance(op.get("footer"), dict) else {}
    info = data.get("assets") if isinstance(data.get("assets"), dict) else {}
    nd = {"title": _s(data.get("title")), "subtitle": _s(data.get("subtitle")),
          "options": {"toc": _b(op.get("toc")), "accent": op.get("accent") if _has(ACCENTS, op.get("accent")) else "green",
                      "footer": {"on": _b(fo.get("on")), "author": _s(fo.get("author")), "version": _s(fo.get("version")),
                                 "date": fo.get("date") if isinstance(fo.get("date"), str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fo.get("date")) else ""},
                      "logo": "", "status": op.get("status") if _has(STATUS, op.get("status")) else "", "fingerprints": _b(op.get("fingerprints")), "about": _b(op.get("about"))},
          "tabs": []}
    assets = {}
    state = {"missing": 0, "bad": [], "seen": set()}

    def keep(id_):
        id_ = _s(id_)
        if re.fullmatch(r"a[a-z0-9]{6,24}", id_) and id_ not in state["seen"]:
            state["seen"].add(id_)
            return id_
        while True:
            n = ids.next()
            if n not in state["seen"]:
                break
        state["seen"].add(n)
        return n

    def take(id_):
        id_ = _s(id_)
        el = find(id_)
        if not el:
            state["missing"] += 1
            return None
        m = info.get(id_) if isinstance(info.get(id_), dict) else {}
        nid = keep(id_)
        b64 = el["b64"]
        pad = 2 if b64[-2:] == "==" else 1 if b64[-1:] == "=" else 0
        a = {"name": _s(m.get("name")) or el.get("hint") or "file", "type": clean_type(el["type"]), "b64": b64, "bytes": len(b64) * 3 // 4 - pad}
        assets[nid] = a
        if m.get("sha256") and fingerprint(a) != m.get("sha256"):
            state["bad"].append(a["name"])
        return nid

    for tin in tabs_in:
        tin = tin if isinstance(tin, dict) else {}
        tab = {"id": keep(tin.get("id")), "title": _s(tin.get("title")), "blocks": []}
        nd["tabs"].append(tab)
        for s in (tin.get("blocks") if isinstance(tin.get("blocks"), list) else []):
            if not isinstance(s, dict):
                continue
            t = s.get("type")
            t = {"gallery": "images", "attachments": "files"}.get(t, t) if isinstance(t, str) else None
            if t == "keyvalues":
                items = s.get("items") if isinstance(s.get("items"), list) else []
                s = dict(s)
                s["rows"] = [["Detail", "Value"]] + [[_s(it.get("label")), _s(it.get("value"))] for it in items if isinstance(it, dict) and (trim(_s(it.get("label"))) or trim(_s(it.get("value"))))]
                t = "table"
            if t not in _BLOCK_TYPES:
                continue
            b = {"id": keep(s.get("id")), "type": t}
            if t == "heading":
                b["text"] = _s(s.get("text"))
            else:
                b["title"] = _s(s.get("title"))
                b["half"] = _b(s.get("half"))
                if t == "text":
                    h = s.get("html") if s.get("html") is not None else ("<p>" + esc(_s(s.get("text"))) + "</p>" if _b(s.get("text")) else "")
                    b["html"] = sanitize(_s(h))
                if t == "markdown":
                    b["md"] = _s(s.get("md") if s.get("md") is not None else s.get("text")).replace("\r\n", "\n").replace("\r", "\n")
                if t == "images":
                    raw = s.get("items") if _b(s.get("items")) else [{"asset": a} for a in (_or(s.get("assets"), []))]
                    items = []
                    for it in raw:
                        it = it if isinstance(it, dict) else {}
                        id_ = take(it.get("asset"))
                        if id_:
                            items.append({"asset": id_, "caption": _s(it.get("caption"))})
                    b["items"] = items
                if t == "files":
                    b["items"] = []
                    b["desc"] = _b(s.get("desc"))
                    b["notes"] = {}
                    notes = s.get("notes") if isinstance(s.get("notes"), dict) else {}
                    for old in _or(s.get("items"), _or(s.get("assets"), [])):
                        id_ = take(old)
                        n = notes.get(_s(old))
                        if id_:
                            b["items"].append(id_)
                            if _b(n):
                                b["notes"][id_] = _s(n)
                if t == "callout":
                    b["tone"] = s.get("tone") if _has(TONES, s.get("tone")) else "note"
                    b["text"] = _s(s.get("text"))
                if t == "collapsible":
                    its = s.get("items") if isinstance(s.get("items"), list) else []
                    b["items"] = [{"summary": _s(i.get("summary") if isinstance(i, dict) else None), "body": _s(i.get("body") if isinstance(i, dict) else None)} for i in its]
                    if not b["items"]:
                        b["items"] = [{"summary": "", "body": ""}]
                if t == "checklist":
                    its = s.get("items") if isinstance(s.get("items"), list) else []
                    b["items"] = [{"text": _s(i.get("text") if isinstance(i, dict) else None), "done": isinstance(i, dict) and _b(i.get("done"))} for i in its]
                    if not b["items"]:
                        b["items"] = [{"text": "", "done": False}]
                if t == "table":
                    rows = list(s.get("rows")) if isinstance(s.get("rows"), list) else []
                    if isinstance(s.get("columns"), list):
                        rows.insert(0, s["columns"])
                    rows = [r for r in rows if isinstance(r, list)]
                    w = max([len(r) for r in rows] + [1])
                    b["rows"] = [[_s(r[k]) if k < len(r) else "" for k in range(w)] for r in rows]
                    if not b["rows"]:
                        b["rows"] = [["Column 1"], [""]]
                    if len(b["rows"]) < 2:
                        b["rows"].append(["" for _ in b["rows"][0]])
            tab["blocks"].append(b)
    if not nd["tabs"]:
        nd["tabs"].append({"id": keep(""), "title": "", "blocks": []})
    if op.get("logo"):
        lg = take(op["logo"])
        if lg:
            nd["options"]["logo"] = lg
    return nd, assets, state["missing"], state["bad"]
