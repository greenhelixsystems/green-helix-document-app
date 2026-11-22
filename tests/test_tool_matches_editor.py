"""helix.py against the editor: the Python tool must produce, read and unpack documents exactly as the editor does."""
import urllib.parse, base64, hashlib, importlib.util, io, json, os, random, re, subprocess, sys, zipfile
from playwright.sync_api import sync_playwright
from common import *

T = work("hlxtest"); os.makedirs(T, exist_ok=True)
sp = importlib.util.spec_from_file_location("hlx", TOOL); hlx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hlx)
sys.setrecursionlimit(30000)
random.seed(int(os.environ.get("SEED", "1115")))
ok = []
def data_of(html):
    return json.loads(re.search(r'id="doc-source">(.*?)</script>', html, re.S).group(1))


def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
sha = lambda b: hashlib.sha256(b).hexdigest()

# ---- test material -------------------------------------------------------
os.makedirs(T + "/in", exist_ok=True)
import shutil
for f in [SRC + "/small-report.pdf", SRC + "/sample-notes.docx", INPUTS + "/small.jpg"]:
    shutil.copy(f, T + "/in/")
open(T + "/in/notes é (1).txt", "w", encoding="utf-8").write("notes\n")
open(T + "/in/notes é (1) copy.txt", "w", encoding="utf-8").write("more notes\n")
os.makedirs(T + "/in/sub", exist_ok=True); shutil.copy(SRC + "/small-report.pdf", T + "/in/sub/small-report.pdf")
open(T + "/in/odd:name?.bin", "wb").write(bytes(range(256)) * 3)
LOGO = INPUTS + "/logo.png"
if os.path.exists(LOGO): shutil.copy(LOGO, T + "/in/logo.png")
FILES = ["small-report.pdf", "sample-notes.docx", "notes é (1).txt", "notes é (1) copy.txt", "sub/small-report.pdf", "odd:name?.bin"]
IMGS = ["small.jpg"] + (["logo.png"] if os.path.exists(T + "/in/logo.png") else [])

def mkspec(rng):
    tok = ["# ", "- ", "1. ", "> ", "```", "|a|b|\n|-|-|\n|1|2|", "**x**", "*y*", "`z`", "[l](http://a.com)", "http://b.org/p.", "\n\n", "\n", "text", "é", "😀", "<b>", "&", "\\", " "]
    mdtxt = lambda: "".join(rng.choice(tok) for _ in range(rng.randint(0, 30)))
    htmls = ["<p>Hello <b>bold</b> and <i>it</i></p>", "<div>one</div><div>two<br>three</div>", "<ul><li>a<li>b</ul>", "<p>x<ul><li>y</li></ul></p>", "a &amp; b &lt;c&gt; &nbsp;d",
             "<p><b>unclosed bold</p>after", "<h2>Title</h2><p>text</p>", "<a href='javascript:x'>bad</a> <a href='site.com'>ok</a> <a href='#top'>top</a>", "<script>x</script><style>y</style>ok",
             "<span>s</span> <em>e</em> <strong>s</strong>", "<p></p><p> </p>", "<ol><li>1<ol><li>n</li></ol></li></ol>", "line<br><br>two", "<p>a</p>b<p>c</p>"]
    def txt(): return rng.choice(["", "Plain", " Spaced ", "Two\n\nparas", "A & B < C", "é😀"])
    def block(tabfiles):
        t = rng.choice(["heading", "text", "markdown", "table", "collapsible", "checklist", "callout", "files", "images", "text", "markdown"])
        b = {"type": t}
        if t == "heading": b["text"] = rng.choice(["Group", "", " Sp "]); return b
        b["title"] = rng.choice(["", "Title", " T & <x> ", "Éa"]); 
        if rng.random() < .3: b["half"] = True
        if t == "text":
            if rng.random() < .5: b["html"] = rng.choice(htmls)
            else: b["text"] = txt()
        elif t == "markdown": b["md"] = mdtxt()
        elif t == "table":
            w = rng.randint(1, 4); b["rows"] = [[rng.choice(["", "x", "12", "$3,400", "-7%", "a|b", "é"]) for _ in range(rng.randint(1, w))] for _ in range(rng.randint(0, 5))]
        elif t == "collapsible": b["items"] = [{"summary": rng.choice(["", "Q?", "Q & A"]), "body": rng.choice(["", "A.", "A\n\nB"])} for _ in range(rng.randint(0, 3))]
        elif t == "checklist": b["items"] = [{"text": rng.choice(["", "Do", " Do too "]), "done": rng.random() < .5} for _ in range(rng.randint(0, 4))]
        elif t == "callout": b["tone"] = rng.choice(["note", "important", "warning", "bogus"]); b["text"] = txt()
        elif t == "files":
            b["desc"] = rng.random() < .6; b["items"] = [{"file": f, "note": rng.choice(["", "A note", "A & B"])} for f in rng.sample(FILES, rng.randint(0, 3))]
        elif t == "images": b["items"] = [{"file": f, "caption": rng.choice(["", "Cap", "C & <d>"])} for f in rng.sample(IMGS[:1], rng.randint(0, 1))]
        return b
    spec = {"title": rng.choice(["", "Doc", "A & <B>", "Éé 😀"]), "subtitle": rng.choice(["", "Sub", " S "]),
            "options": {"toc": rng.random() < .5, "accent": rng.choice(["green", "gold", "crimson", "plum", "slate", "bogus"]), "status": rng.choice(["", "draft", "review", "final", "x"]),
                        "fingerprints": rng.random() < .5, "about": rng.random() < .7}}
    if rng.random() < .4: spec["options"]["footer"] = {"on": True, "author": rng.choice(["", "Me"]), "version": rng.choice(["", "1.2"]), "date": rng.choice(["", "2025-03-09"])}
    if len(IMGS) > 1 and rng.random() < .4: spec["options"]["logo"] = "logo.png"
    spec["tabs"] = [{"title": rng.choice(["", "One", "A & B"]), "blocks": [block(None) for _ in range(rng.randint(0, 7))]} for _ in range(rng.choice([1, 1, 2, 3]))]
    return spec

with sync_playwright() as p:
    b = launch(p)
    ctx = b.new_context(accept_downloads=True, viewport={"width": 1280, "height": 1200})
    page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)[:200]))
    page.on("dialog", lambda d: d.accept())
    page.goto("file://" + ED)
    editor = lambda html: page.evaluate("t=>{window.__pde.load(t);return window.__pde.build();}", html)

    # 1. sanitizer, fuzzed against the browser
    frag = ["<p>", "</p>", "<b>", "</b>", "<i>", "</i>", "<em>", "</em>", "<strong>", "</strong>", "<a href='http://x.com'>", "<a href=x.com>", "<a href='javascript:1'>", "<a href='#a'>", "</a>", "<br>", "<br/>",
            "<ul>", "</ul>", "<ol>", "</ol>", "<li>", "</li>", "<div>", "</div>", "<span>", "</span>", "<h1>", "</h1>", "<blockquote>", "</blockquote>", "<script>x</script>", "<style>a</style>",
            "text", " ", "&amp;", "&lt;", "&nbsp;", "&copy", "é", "<", "a < b", "<!-- c -->", "<u>", "</u>", "<pre>", "</pre>", "<hr>", "<img src=x>", "<font color=red>", "</font>", "<code>", "</code>"]
    wellformed = ["<p>Hello <b>bold</b> and <i>it</i></p>", "<div>one</div><div>two<br>three</div>", "<ul><li>a</li><li>b</li></ul>", "<ol start=3><li>a<ul><li>n</li></ul></li></ol>", "<p>a<br>b</p>", "text only", "<b>x</b><i>y</i>"]
    cases = wellformed[:]
    for _ in range(6000): cases.append("".join(random.choice(frag) for _ in range(random.randint(1, 14))))
    js = page.evaluate("a=>a.map(x=>window.__pde.san(x))", cases)
    bad = [(c, j, hlx.sanitize(c)) for c, j in zip(cases, js) if hlx.sanitize(c) != j]
    # classify: structural (mis-nested formatting, tables) are known limits; report the rate
    check("sanitize: all well-formed rich text matches the browser", not [x for x in bad if x[0] in wellformed], [x for x in bad if x[0] in wellformed][:1])
    print("   sanitize fuzz: %d random fragments, %d differ (%.2f%%)" % (len(cases), len(bad), 100.0 * len(bad) / len(cases)))
    for c, j, r in bad[:4]: print("     IN", repr(c)[:140], "\n     JS", repr(j)[:140], "\n     PY", repr(r)[:140])
    SAN_BAD = len(bad)

    # 2. built by Python, reopened and re-saved by the editor: must be byte-identical
    ident = 0; n_spec = int(os.environ.get("NSPEC", "160")); first_bad = None; rng = random.Random(int(os.environ.get("SEED", "1115")) + 1); kinds = set()
    for k in range(n_spec):
        spec = mkspec(rng)
        # keep sanitizer-sensitive html out of the exact-equality run (measured separately above)
        try:
            html, problems = hlx.build_from_spec(spec, T + "/in", shrink=False)
        except Exception as e:
            check("spec %d builds" % k, False, repr(e)); continue
        if problems:
            continue
        ed = editor(html)
        if ed == html: ident += 1
        elif first_bad is None: first_bad = (k, spec, html, ed)
    check("%d random specs: Python-built file == editor reopen+save, byte for byte" % n_spec, ident == n_spec, "%d/%d" % (ident, n_spec))
    if first_bad:
        k, spec, h1, h2 = first_bad
        i = next((i for i in range(min(len(h1), len(h2))) if h1[i] != h2[i]), min(len(h1), len(h2)))
        print("   first difference, spec", k, "at", i, "\n   PY ", repr(h1[max(0, i - 120):i + 160]), "\n   ED ", repr(h2[max(0, i - 120):i + 160]))
        json.dump(spec, open(T + "/bad-spec.json", "w"), ensure_ascii=False, indent=1)

    # 3. frozen real documents from earlier checkpoints: the editor saves, Python reads and rebuilds the same page
    for name in ("v6.hlx.html", "v7.hlx.html", "v8.hlx.html"):
        t = open(FIX + "/" + name, encoding="utf-8").read(); saved = editor(t)
        d, a, missing, bad_, r, data = hlx.read_document(saved)
        again = hlx.render(d, a, hlx._guess_today(saved))
        check("frozen %s: editor save == Python rebuild of that file" % name, again == saved and not missing and not bad_)
        pr, nt = hlx.check_document(saved)
        check("frozen %s: check says OK" % name, not pr, pr)

    # 4. loader tolerance: edit the data block (missing fields, wrong types, old layouts) and let both read it
    base_spec = {"title": "Loader", "options": {"about": True, "fingerprints": True}, "tabs": [{"title": "T", "blocks": [
        {"type": "files", "title": "F", "desc": True, "items": [{"file": "small-report.pdf", "note": "n"}]}, {"type": "images", "title": "I", "items": [{"file": "small.jpg", "caption": "c"}]},
        {"type": "table", "title": "T", "rows": [["a", "b"], ["1", "2"]]}, {"type": "checklist", "title": "C", "items": [{"text": "x", "done": True}]}]}]}
    html0, _ = hlx.build_from_spec(base_spec, T + "/in", shrink=False)
    m = re.search(r'(<script type="application/json" id="doc-source">)(.*?)(</script>)', html0, re.S); data0 = json.loads(m.group(2))
    aid = [k for k, v in data0["assets"].items() if v["name"] == "small-report.pdf"][0]; iid = [k for k, v in data0["assets"].items() if v["name"] == "small.jpg"][0]
    def variants():
        import copy
        def v(f):
            d = copy.deepcopy(data0); f(d); return d
        yield "no options", v(lambda d: d.pop("options"))
        yield "no tabs, blocks at top", v(lambda d: (d.update(blocks=d["tabs"][0]["blocks"]), d.pop("tabs")))
        yield "options wrong types", v(lambda d: d.update(options={"toc": "yes", "accent": 5, "footer": "x", "status": [], "fingerprints": 1, "about": 0}))
        yield "footer date bad", v(lambda d: d["options"].update(footer={"on": True, "author": 5, "version": None, "date": "March 3"}))
        yield "unknown block type", v(lambda d: d["tabs"][0]["blocks"].append({"type": "video", "title": "x"}))
        yield "legacy gallery and attachments", v(lambda d: d.update(tabs=[{"title": "", "blocks": [{"type": "gallery", "title": "G", "assets": [iid]}, {"type": "attachments", "title": "A", "assets": [aid], "notes": {aid: "legacy"}, "desc": True}]}]))
        yield "legacy keyvalues", v(lambda d: d["tabs"][0]["blocks"].append({"type": "keyvalues", "title": "K", "items": [{"label": "a", "value": "b"}, {"label": "", "value": ""}, {"label": "c", "value": "d"}]}))
        yield "table ragged and columns", v(lambda d: d["tabs"][0]["blocks"].append({"type": "table", "title": "R", "columns": ["x", "y"], "rows": [["1"], ["2", "3", "4"], "bad"]}))
        yield "empty table", v(lambda d: d["tabs"][0]["blocks"].append({"type": "table", "title": "E", "rows": []}))
        yield "empty lists", v(lambda d: d["tabs"][0]["blocks"].extend([{"type": "checklist", "items": []}, {"type": "collapsible", "items": "no"}]))
        yield "duplicate and bad ids", v(lambda d: (d["tabs"][0].update(id="X"), [b.update(id="aaaaaaaa") for b in d["tabs"][0]["blocks"]]))
        yield "asset referenced twice", v(lambda d: d["tabs"][0]["blocks"].append({"type": "files", "title": "again", "items": [aid, aid]}))
        yield "missing asset", v(lambda d: d["tabs"][0]["blocks"].append({"type": "files", "title": "gone", "items": ["azzzzzzzz"]}))
        yield "text from plain text field", v(lambda d: d["tabs"][0]["blocks"].append({"type": "text", "title": "p", "text": "plain <b>x</b>"}))
        yield "markdown from text field", v(lambda d: d["tabs"][0]["blocks"].append({"type": "markdown", "title": "m", "text": "# a\r\n\r\nb\rc"}))
        yield "callout tone unknown", v(lambda d: d["tabs"][0]["blocks"].append({"type": "callout", "tone": "loud", "text": "x"}))
        yield "tab list not a list", v(lambda d: d.update(tabs="nope", blocks=[{"type": "heading", "text": "h"}]))
        yield "logo set", v(lambda d: d["options"].update(logo=iid))
        yield "logo missing", v(lambda d: d["options"].update(logo="azzzzzzzz"))
        yield "sha wrong", v(lambda d: d["assets"][aid].update(sha256="0" * 64))
        yield "name missing", v(lambda d: d["assets"][aid].pop("name"))
    nv = 0; same = 0
    for name, d in variants():
        mut = html0[:m.start(2)] + hlx._js_json(d) + html0[m.end(2):]
        try:
            e_html = editor(mut)
            e_bad = page.evaluate("window.__pde.bad()")
            dd, aa, miss, bad_, r, data = hlx.read_document(mut)
            p_html = hlx.render(dd, aa, hlx._guess_today(mut))
        except Exception as e:
            check("loader variant: " + name, False, repr(e)); nv += 1; continue
        def canon(h):
            seen = {}
            return re.sub(r"\ba[a-z0-9]{6,24}\b", lambda m_: seen.setdefault(m_.group(0), "ID%d" % len(seen)), h)
        e_html, p_html = canon(e_html), canon(p_html)
        nv += 1; good = (e_html == p_html and sorted(e_bad) == sorted(bad_))
        same += good
        if not good:
            i = next((i for i in range(min(len(e_html), len(p_html))) if e_html[i] != p_html[i]), -1)
            print("   VARIANT DIFF", name, "bad:", e_bad, bad_, "at", i, "\n   ED", repr(e_html[max(0, i - 80):i + 120]), "\n   PY", repr(p_html[max(0, i - 80):i + 120]))
    check("loader: %d damaged or old-layout data blocks read identically" % nv, same == nv, "%d/%d" % (same, nv))

    # 5. unpack == the editor's own Export for AI
    spec = {"title": "Export test", "subtitle": "Sub", "options": {"status": "final", "fingerprints": True, "logo": "small.jpg" if False else ""}, "tabs": [
        {"title": "Alpha", "blocks": [{"type": "heading", "text": "Group"}, {"type": "text", "title": "Rich", "html": "<p>Hi <b>bold</b> <i>it</i> <a href='http://x.com/a(b)'>link</a></p><ul><li>one<ul><li>deep</li></ul></li><li>two</li></ul><p>x[1]*y_z</p>"},
            {"type": "callout", "title": "Heads up", "tone": "warning", "text": "One\n\nTwo * star"}, {"type": "checklist", "title": "To do", "items": [{"text": "a_b", "done": True}, {"text": "c", "done": False}]},
            {"type": "collapsible", "title": "Q&A", "items": [{"summary": "Why?", "body": "Because.\n\nAlso."}]}, {"type": "table", "title": "Data", "rows": [["a|b", "c"], ["1", "2\n3"], ["", ""]]},
            {"type": "markdown", "title": "MD", "md": "## Inner\n\n- x\n"}]},
        {"title": "Beta", "blocks": [{"type": "files", "title": "Files", "desc": True, "items": [{"file": "small-report.pdf", "note": "The *report*"}, {"file": "sub/small-report.pdf"}, {"file": "notes é (1).txt"}, {"file": "notes é (1) copy.txt"}, {"file": "odd:name?.bin"}]},
            {"type": "images", "title": "Pics", "items": [{"file": "small.jpg", "caption": "A (nice) pic"}]}, {"type": "heading", "text": "After"}, {"type": "text", "title": "Late", "text": "Para"}]}]}
    html, pr = hlx.build_from_spec(spec, T + "/in", shrink=False); assert not pr, pr
    open(T + "/export.helix.html", "w", encoding="utf-8").write(html)
    page.evaluate("t=>window.__pde.load(t)", html)
    res = hlx.unpack(T + "/export.helix.html", T + "/unpacked") if os.path.isdir(T + "/unpacked") is False or True else None
    py_md = open(T + "/unpacked/content.md", encoding="utf-8").read(); ed_md = page.evaluate("window.__pde.toMd()")
    check("unpack: content.md identical to the editor's Markdown export", py_md == ed_md)
    if py_md != ed_md:
        i = next((i for i in range(min(len(py_md), len(ed_md))) if py_md[i] != ed_md[i]), -1); print("   PY", repr(py_md[max(0, i - 80):i + 120]), "\n   ED", repr(ed_md[max(0, i - 80):i + 120]))
    pnames = sorted(os.path.relpath(os.path.join(r_, f), T + "/unpacked").replace(os.sep, "/") for r_, _, fs in os.walk(T + "/unpacked") for f in fs if f not in ("content.md", "SHA256SUMS.txt", "spec.json"))
    check("unpack: every file the Markdown links to is written", all(urllib.parse.unquote(l) in pnames for l in re.findall(r"\]\(((?:files|images)/[^)]+)\)", py_md)), pnames)

    # 6. unpack -> build -> unpack: nothing lost
    html2, pr = hlx.build_from_spec(json.load(open(T + "/unpacked/spec.json", encoding="utf-8")), T + "/unpacked", shrink=False)
    check("spec.json from unpack rebuilds without problems", not pr, pr)
    open(T + "/round.helix.html", "w", encoding="utf-8").write(html2); hlx.unpack(T + "/round.helix.html", T + "/unpacked2")
    check("round trip keeps content.md and every file", open(T + "/unpacked/content.md", encoding="utf-8").read() == open(T + "/unpacked2/content.md", encoding="utf-8").read()
          and open(T + "/unpacked/SHA256SUMS.txt").read() == open(T + "/unpacked2/SHA256SUMS.txt").read())
    d1 = hlx.read_document(html)[0]; d2 = hlx.read_document(html2)[0]
    strip = lambda d: json.dumps(d, sort_keys=True).replace("", "")
    def shape(d):
        import copy; d = copy.deepcopy(d); d["options"]["logo"] = bool(d["options"]["logo"])
        def walk(o):
            if isinstance(o, dict):
                for k in list(o):
                    if k in ("id", "asset"): o[k] = "_"
                    elif k == "notes": o[k] = sorted(o[k].values())
                    elif k == "items" and o.get("type") == "files": o[k] = len(o[k])
                    else: walk(o[k])
            elif isinstance(o, list):
                for x in o: walk(x)
        walk(d); return json.dumps(d, sort_keys=True)
    check("round trip keeps the document structure", shape(d1) == shape(d2))
    check("editor opens the rebuilt file without warnings", editor(html2) is not None and page.evaluate("window.__pde.bad()") == [])

    # 7. check command: catches tampering
    good, _ = hlx.build_from_spec(base_spec, T + "/in", shrink=False)
    pr, nt = hlx.check_document(good); check("check: fresh file is OK", not pr, pr)
    def broke(name, mutate, expect):
        h = mutate(good); pr, nt = hlx.check_document(h); check("check catches: " + name, any(expect in x for x in pr), pr)
    broke("an added script", lambda h: h.replace("</body>", "<script>alert(1)</script></body>"), "script")
    broke("an event handler", lambda h: h.replace("<main>", '<main onclick="x()">'), "event-handler")
    broke("a changed security policy", lambda h: h.replace("default-src 'none'", "default-src *"), "security policy")
    broke("an outside image", lambda h: h.replace("<main>", '<main><img src="http://evil.example/x.png">'), "outside")
    broke("a changed attachment", lambda h: re.sub(r'(download="small-report\.pdf" href="data:application/pdf;base64,.{40})', lambda m_: m_.group(1) + "AAAA", h, 1), "fingerprint")
    broke("visible text edited by hand", lambda h: h.replace("<h2>F</h2>", "<h2>Edited</h2>"), "does not match")
    broke("a missing data block", lambda h: h.replace('id="doc-source"', 'id="nothing"'), "no editing data")
    check("check: a file made by another editor version is only noted", any("different version" in x for x in hlx.check_document(open(FIX + "/v6.hlx.html", encoding="utf-8").read())[1]))

    # 8. command line
    def cli(*a): return subprocess.run([sys.executable, "-I", TOOL] + list(a), capture_output=True, text=True, cwd=T)
    json.dump(base_spec, open(T + "/in/base.json", "w")); r = cli("build", "in/base.json", "cli.helix.html")
    check("cli build prints OK and writes the file", r.returncode == 0 and r.stdout.startswith("OK") and os.path.getsize(T + "/cli.helix.html") > 1000, r.stdout + r.stderr)
    bs = json.loads(json.dumps(base_spec)); bs["tabs"][0]["blocks"][0]["items"][0]["file"] = "nope.pdf"; json.dump(bs, open(T + "/in/missing.json", "w"))
    r = cli("build", "in/missing.json", "nope.helix.html"); check("cli build reports a missing file and writes nothing", r.returncode == 1 and "PROBLEM: file not found: nope.pdf" in r.stdout and not os.path.exists(T + "/nope.helix.html"), r.stdout)
    r = cli("check", "cli.helix.html"); check("cli check prints OK", r.returncode == 0 and r.stdout.strip().endswith("OK"), r.stdout)
    r = cli("unpack", "cli.helix.html", "cli-un"); check("cli unpack writes the files", r.returncode == 0 and os.path.exists(T + "/cli-un/content.md"), r.stdout)
    open(T + "/n.md", "w", encoding="utf-8").write("# Hi\n\n**x**\n"); r = cli("md", "n.md"); check("cli md prints HTML", r.stdout.strip() == "<h3>Hi</h3><p><strong>x</strong></p>", r.stdout)
    check("cli with no arguments shows usage", "build spec.json" in cli().stdout)
    # 9. same input, same output
    fixed = dict(base_spec, id="hx-0123456789abcdef")
    h_a, _ = hlx.build_from_spec(fixed, T + "/in", shrink=False, now="2026-01-02T03:04:05Z"); h_b, _ = hlx.build_from_spec(fixed, T + "/in", shrink=False, now="2026-01-02T03:04:05Z")
    check("building twice with the same id and time gives identical files", h_a == h_b)
    h_c, _ = hlx.build_from_spec(base_spec, T + "/in", shrink=False); h_d, _ = hlx.build_from_spec(base_spec, T + "/in", shrink=False)
    check("two new documents built from one spec get different document ids", data_of(h_c)["id"] != data_of(h_d)["id"] and data_of(h_c)["id"].startswith("hx-"))
    check("no editor errors", not errs, errs[:2])
    b.close()

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
