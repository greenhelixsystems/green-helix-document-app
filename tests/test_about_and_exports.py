import base64, hashlib, html as htmllib, json, os, re, urllib.parse, zipfile
from playwright.sync_api import sync_playwright

from common import *
short_ver = ".".join(open(os.path.join(str(ROOT), "VERSION")).read().strip().split(".")[:2])
T = work("v10")
os.makedirs(T, exist_ok=True)
ok = []
sha = lambda data: hashlib.sha256(data).hexdigest()
b64 = lambda p: base64.b64encode(open(p, "rb").read()).decode()


def check(name, cond, extra=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:200]) if extra != "" else ""))


# ---------------------------------------------------------------- a hand-made document with one of everything, two tabs
IMG, PDF = INPUTS + "/small.jpg", SRC + "/small-report.pdf"
doc = {
    "format": "helix", "version": 1, "title": "Export test", "subtitle": "A subtitle",
    "options": {"toc": False, "accent": "green", "footer": {"on": False, "author": "", "version": "", "date": ""}, "logo": "", "status": "final", "fingerprints": False, "about": True},
    "tabs": [
        {"id": "atabmain1", "title": "Main", "blocks": [
            {"id": "ablkhead1", "type": "heading", "text": "Overview"},
            {"id": "ablktext1", "type": "text", "title": "Summary", "half": False,
             "html": '<p>Hello <strong>bold</strong> and <em>em</em> with a <a href="https://example.com/a">link</a>.</p><ul><li>one</li><li>two<ul><li>nested</li></ul></li></ul><ol><li>first</li><li>second</li></ol>'},
            {"id": "ablkmd001", "type": "markdown", "title": "", "half": False, "md": "## From markdown\n\n- x\n\n```prompt\nDo it\n```"},
            {"id": "ablkcall1", "type": "callout", "title": "", "half": False, "tone": "important", "text": "First line * with star\nSecond para"},
            {"id": "ablkchk01", "type": "checklist", "title": "Tasks", "half": False, "items": [{"text": "Open task", "done": False}, {"text": "Done task", "done": True}]},
            {"id": "ablktab01", "type": "table", "title": "Budget", "half": False, "rows": [["Item", "Cost | USD"], ["Rent", "1,200"], ["", ""]]},
            {"id": "ablkimg01", "type": "images", "title": "Photos", "half": False, "items": [{"asset": "aimgasset1", "caption": "A *nice* [photo]"}]},
            {"id": "ablkfile1", "type": "files", "title": "Docs", "half": False, "items": ["afileasset1"], "desc": True, "notes": {"afileasset1": "The report"}},
        ]},
        {"id": "atabmore1", "title": "More", "blocks": [
            {"id": "ablkcoll1", "type": "collapsible", "title": "FAQ", "half": False, "items": [{"summary": "Why?", "body": "Because.\nTwo."}]}]},
    ],
    "assets": {"aimgasset1": {"name": "small.jpg", "type": "image/jpeg", "bytes": os.path.getsize(IMG)},
               "afileasset1": {"name": "report (final).pdf", "type": "application/pdf", "bytes": os.path.getsize(PDF)}},
}
crafted = ('<!DOCTYPE html><html><head><script type="application/json" id="doc-source">' + json.dumps(doc).replace("<", "\\u003c") + '</script></head><body>'
           '<img id="asset-aimgasset1" src="data:image/jpeg;base64,' + b64(IMG) + '"><a id="asset-afileasset1" download="report (final).pdf" href="data:application/pdf;base64,' + b64(PDF) + '">x</a></body></html>')
open(T + "/crafted.html", "w", encoding="utf-8").write(crafted)

with sync_playwright() as p:
    b = launch(p)
    ctx = b.new_context(accept_downloads=True, viewport={"width": 1280, "height": 1300})
    page = ctx.new_page(); errs = []
    page.on("console", lambda m: errs.append(m.text[:300]) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)[:300]))
    page.on("dialog", lambda d: d.accept())
    page.goto("file://" + ED)
    raw = lambda: json.loads(page.evaluate("JSON.stringify(window.__pde.state())"))
    notice = lambda: page.inner_text("#notice")

    def save_copy(name=None):
        with page.expect_download() as d:
            page.click("#btn-copy")
        path = T + "/" + (name or d.value.suggested_filename); d.value.save_as(path)
        return path, open(path, encoding="utf-8").read()

    # ---------------------------------------------------------------- removals and wording
    labels = page.locator(".adder button").all_inner_texts()
    check("Key details is gone from the Add row", "Key details" not in labels and page.locator('[data-add="keyvalues"]').count() == 0, labels)
    tops = page.locator(".adder button").evaluate_all("els=>[...new Set(els.map(e=>Math.round(e.getBoundingClientRect().top)))]")
    check("the Add row wraps onto at most two lines (twelve block types since 1.2)", 1 <= len(tops) <= 2 and len(labels) == 12, (tops, len(labels)))
    check("footer says A free tool from Green Helix Systems", page.locator(".promo-head strong").inner_text() == "A free tool from Green Helix Systems", page.locator(".promo-head strong").inner_text())
    check("footer still has exactly the two buttons", page.locator(".promo a").all_inner_texts() == ["Try the Free Financial Simplicity Assessment →", "Explore Financial Planning →"])
    page.click('[data-add="files"]')
    check("Files block no longer offers the in-document viewer", page.locator("text=Let readers open").count() == 0 and "view" not in raw()["doc"]["blocks"][0])
    check("new documents have the About section on by default", raw()["doc"]["options"]["about"] is True)
    page.screenshot(path=T + "/editor-top.png")

    # ---------------------------------------------------------------- load the crafted document and save it as a real one
    miss = page.evaluate("t=>window.__pde.load(t)", crafted)
    check("crafted document opens with all files", miss == 0 and raw()["assets"] == 2 and page.evaluate("window.__pde.bad()") == [])
    path, html = save_copy("export-test.helix.html")
    src = json.loads(re.search(r'id="doc-source">(.*?)</script>', html, re.S).group(1))

    # ---------------------------------------------------------------- data first
    js_end = html.index("</script>") + len("</script>")
    first_b64 = html.index("base64,")
    check("data block comes first: before the stylesheet", html.index('id="doc-source"') < html.index("<style>"))
    check("data block ends before the first embedded file", js_end < first_b64, (js_end, first_b64))
    check("only 1 script element in the whole file", html.count("<script") == 1 and html.count("</script>") == 1)
    check("everything an AI needs sits in the first 40 KB", js_end < 40000, js_end)
    check("format helix version 1, spec 1.2, generator " + short_ver, src["format"] == "helix" and src["version"] == 1 and src["spec"] == "1.2" and ('Document Editor %s"' % short_ver) in html)
    check("data lists every attachment with a fingerprint", all(v.get("sha256") for v in src["assets"].values()) and len(src["assets"]) == 2)
    check("data block has no file bytes in it", "base64," not in html[:js_end] and "data:image" not in html[:js_end] and "data:application" not in html[:js_end])

    # ---------------------------------------------------------------- the About section
    about_html = re.search(r'<details class="about">.*?</details>', html, re.S)
    check("About section exists, after the content, collapsed", about_html is not None and html.index('<details class="about">') > html.index("report (final).pdf") and "open" not in about_html.group(0)[:30])
    lis = [htmllib.unescape(x) for x in re.findall(r"<li>(.*?)</li>", about_html.group(0), re.S)]
    check("it has the five instructions for AI and software (data block, AI Notes, focus first, attachments, revising)", len(lis) == 5 and "doc-source" in lis[0] and "focus" in lis[1] and "full review" in lis[2] and "SHA-256" in lis[3] and "rev" in lis[4], len(lis))
    check("the data block carries the same words", src["about"] == "This is a Helix document (a single self-contained HTML file with no scripts). " + " ".join(lis))
    check("the section is plain visible text, no hidden elements or comments", "<!--" not in html and 'aria-hidden' not in about_html.group(0) and "display:none" not in about_html.group(0) and 'hidden' not in about_html.group(0))
    check("it says what the file is, in plain language", "single web page that opens in any browser" in about_html.group(0) and "contains no scripts" in about_html.group(0))

    # re-open + re-save identical
    page.evaluate("t=>window.__pde.load(t)", html)
    p2, h2 = save_copy("second.helix.html")
    check("re-open and re-save is byte-identical", html == h2, (len(html), len(h2)))

    # toggle off
    page.click("#btn-options"); page.uncheck("#opt-about")
    p3, h3 = save_copy("no-about.helix.html")
    s3 = json.loads(re.search(r'id="doc-source">(.*?)</script>', h3, re.S).group(1))
    check("About off: no section and no about field in the data", 'class="about"' not in h3 and "about" not in s3 and s3["options"]["about"] is False)
    check("About off: still data-first", h3.index('id="doc-source"') < h3.index("<style>"))
    page.evaluate("t=>window.__pde.load(t)", h3)
    check("About stays off after reopening", raw()["doc"]["options"]["about"] is False)
    page.check("#opt-about"); page.click("#btn-options")

    # ---------------------------------------------------------------- the document, no scripts in the browser, About works by click alone
    v = b.new_context(java_script_enabled=False, viewport={"width": 1000, "height": 900}).new_page()
    v.goto("file://" + path)
    det = v.locator("details.about")
    check("About is collapsed until opened", det.count() == 1 and not det.evaluate("e=>e.open") and det.locator("summary").inner_text() == "About this file")
    det.locator("summary").click()
    check("About opens with a plain click and shows the text", det.evaluate("e=>e.open") and "doc-source" in det.inner_text() and det.locator("li").count() == 5)
    v.screenshot(path=T + "/doc-about-open.png", full_page=True)
    v.emulate_media(media="print")
    check("About is not printed", det.evaluate("e=>getComputedStyle(e).display") == "none")
    v.emulate_media(media="screen")
    nj = b.new_context(java_script_enabled=False, viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True).new_page()
    nj.goto("file://" + path)
    check("phone: no sideways scrolling", nj.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))

    # ---------------------------------------------------------------- Markdown export (the same Markdown as helix.py unpack and get --md)
    page.evaluate("t=>window.__pde.load(t)", html)
    md = page.evaluate("window.__pde.toMd()")
    open(T + "/content.md", "w", encoding="utf-8").write(md)
    has = lambda s_: s_ in md
    check("md: title, status, subtitle, note", md.startswith("# Export test\n\n**Status:** Final\n\nA subtitle\n\n> Exported from a Helix document."))
    check("md: tab, heading and block title levels", has("\n## Main\n") and has("\n### Overview\n") and has("\n#### Summary\n") and has("\n## More\n") and has("\n### FAQ\n"))
    check("md: text with bold, italic, link", has("Hello **bold** and *em* with a [link](https://example.com/a)."))
    check("md: bullet, nested bullet and numbered lists", has("- one\n- two\n   - nested") and has("1. first\n2. second"))
    check("md: markdown block kept as written", has("## From markdown\n\n- x\n\n```prompt\nDo it\n```"))
    check("md: callout with its type and escaping", has("> **Important:** First line \\* with star\n>\n> Second para"))
    check("md: checklist", has("- [ ] Open task\n- [x] Done task"))
    check("md: table with escaped pipe and no blank row", has("| Item | Cost \\| USD |\n| --- | --- |\n| Rent | 1,200 |") and not has("|  |  |"))
    check("md: image link and caption", has("![A \\*nice\\* \\[photo\\]](images/small.jpg)\n*A \\*nice\\* \\[photo\\]*"))
    fp = src["assets"]["afileasset1"]["sha256"]
    check("md: file link with encoded path, size, note and SHA-256", has("- [report (final).pdf](files/report%20%28final%29.pdf) (412 KB) - The report\n  SHA-256: `" + fp + "`"), [l for l in md.split("\n") if "report" in l][:2])
    check("md: collapsible", has("**Why?**\n\nBecause.\n\nTwo."))
    check("md: no file bytes", "base64" not in md and len(md) < 4000, len(md))
    rendered = page.evaluate("m=>window.__pde.md(m)", md)
    check("md renders through the editor's own Markdown converter", "<h3>Export test</h3>" in rendered and "<h4>Main</h4>" in rendered and "<table>" in rendered and "<strong>bold</strong>" in rendered)

    page.click("#btn-options")
    check("Export for AI is gone: the file itself is the AI format (helix.py unpack still makes loose files)", page.locator("#btn-ai").count() == 0 and page.locator("#btn-zip").count() == 1)
    page.click("#btn-options")

    # ---------------------------------------------------------------- frozen older documents
    def load_fixture(name):
        t = open(FIX + "/" + name, encoding="utf-8").read()
        m = page.evaluate("t=>window.__pde.load(t)", t)
        return m, page.evaluate("window.__pde.build()")

    m6, r6 = load_fixture("v6.hlx.html")
    check("V6 document opens, About stays off, gets fingerprints", m6 == 0 and 'class="about"' not in r6 and page.evaluate("window.__pde.bad()") == [])
    m7, r7 = load_fixture("v7.hlx.html")
    st7 = raw()["doc"]; tabs7 = json.loads(re.search(r'id="doc-source">(.*?)</script>', r7, re.S).group(1))["tabs"]
    types7 = [[x["type"] for x in t_["blocks"]] for t_ in tabs7]
    check("V7 document: its Key details block became a plain table", m7 == 0 and types7 == [["text", "files"], ["checklist", "markdown", "table"]], types7)
    check("  ...with the details kept as two columns", tabs7[1]["blocks"][2]["rows"] == [["Detail", "Value"], ["Client", "Jane"]], tabs7[1]["blocks"][2]["rows"])
    check("  ...and its status, markdown and files survived", json.loads(re.search(r'id="doc-source">(.*?)</script>', r7, re.S).group(1))["options"]["status"] == "final" and "<h4>Hello</h4>" in r7)
    m8, r8 = load_fixture("v8.hlx.html")
    s8 = json.loads(re.search(r'id="doc-source">(.*?)</script>', r8, re.S).group(1))
    check("V8 document (with viewer) opens cleanly, both files intact and verified", m8 == 0 and page.evaluate("window.__pde.bad()") == [] and len(s8["assets"]) == 2)
    check("  ...re-saved with no viewer, no frames, no view setting", 'class="viewer"' not in r8 and "frame-src" not in r8 and '"view"' not in r8 and 'href="#v-' not in r8 and "<iframe" not in r8)
    check("  ...downloads still byte-identical", sorted(v_["sha256"] for v_ in s8["assets"].values()) == sorted([sha(open(PDF, "rb").read()), sha(open(IMG, "rb").read())]))

    # ---------------------------------------------------------------- phone: editor options panel
    b2 = launch(p)
    ph = b2.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True).new_page()
    ph.goto("file://" + ED); ph.tap("#btn-options")
    check("phone editor: no sideways scrolling", ph.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    small = ph.evaluate("""()=>Array.from(document.querySelectorAll('#options button,#options select,#options input')).filter(e=>e.offsetParent&&e.type!=='checkbox'&&e.type!=='radio').map(e=>[Math.round(e.getBoundingClientRect().height),e.id||e.textContent.slice(0,12)]).filter(x=>x[0]<38)""")
    check("phone editor: options controls are tap-sized", not small, small)
    ph.screenshot(path=T + "/editor-phone-options.png", full_page=True)
    page.screenshot(path=T + "/editor-final.png")
    check("no console errors", not errs, errs[:2])

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
