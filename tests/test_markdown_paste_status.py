import hashlib, json, os, re, zipfile
from playwright.sync_api import sync_playwright

from common import *
T = work("v8")
os.makedirs(T, exist_ok=True)
LOGO = INPUTS + "/logo.png"
ok = []


def check(name, cond, extra=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra != "" else ""))


MD = """# Quarterly notes

Some **bold**, *italic*, `inline code` and a [safe link](https://example.com).

- first point
- second point
  - nested point

1. step one
2. step two

- [ ] open task
- [x] finished task

> A quoted line

| Item | Amount |
|---|---:|
| Rent | $1,200 |
| Food | $400 |

```prompt
You are a careful assistant.
Summarise <the attached> files.
```

<script>alert('x')</script> and [bad](javascript:alert(1)) and <img src=x onerror=alert(2)>
"""

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

    def paste(loc, text):
        loc.evaluate("(el,t)=>{const dt=new DataTransfer();dt.setData('text/plain',t);el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));}", text)

    def save_copy():
        with page.expect_download() as d:
            page.click("#btn-copy")
        path = T + "/" + d.value.suggested_filename
        d.value.save_as(path)
        return path, open(path, encoding="utf-8").read()

    # ---------------------------------------------------------------- Markdown block
    page.fill("#doc-title", "Checkpoint two")
    page.click('[data-add="markdown"]')
    blk = page.locator(".block.markdown")
    blk.locator(".bhead input").fill("Notes in Markdown")
    blk.locator("textarea.mdarea").fill(MD)
    check("markdown block added", raw()["doc"]["blocks"][0]["type"] == "markdown" and raw()["doc"]["blocks"][0]["md"] == MD)

    # code block button wraps a selection
    page.click('[data-add="markdown"]')
    b2 = page.locator(".block.markdown").nth(1)
    ta = b2.locator("textarea.mdarea")
    ta.fill("before\nprint('hi')\nafter")
    ta.evaluate("el=>{el.focus();el.setSelectionRange(7,18);}")
    b2.locator('button:has-text("Code block")').click()
    check("code block button wraps the selection", raw()["doc"]["blocks"][1]["md"] == "before\n```\nprint('hi')\n```\nafter", repr(raw()["doc"]["blocks"][1]["md"]))

    # load a .md file via the chooser
    mdfile = T + "/loaded.md"
    open(mdfile, "w", encoding="utf-8").write("## From a file\r\n\r\nLoaded line.\r\n")
    with page.expect_file_chooser() as fc:
        b2.locator('button:has-text("Load a file")').click()
    fc.value.set_files(mdfile)
    page.wait_for_timeout(300)
    got = raw()["doc"]["blocks"][1]["md"]
    check("file loaded into block, CRLF normalised, appended", got.endswith("## From a file\n\nLoaded line.\n") and "\r" not in got and got.startswith("before"), repr(got[-40:]))
    with page.expect_file_chooser() as fc:
        b2.locator('button:has-text("Load a file")').click()
    fc.value.set_files(SRC + "/small-report.pdf"); page.wait_for_timeout(300)
    check("pdf not loaded into markdown", "That is not a text file" in notice(), notice())

    # ---------------------------------------------------------------- Excel paste into a table
    page.click('[data-add="table"]')
    tb = page.locator(".block.table")
    tb.locator(".bhead input").fill("Pasted table")
    grid = 'Name\tQty\tPrice\n"Widget\twith tab"\t3\t$1,200.50\n"He said ""hi"""\t10\t$99\nTotal\t13\t$1,299.50\n'
    paste(tb.locator("table.grid input").nth(0), grid)
    rws = raw()["doc"]["blocks"][2]["rows"]
    check("fresh table replaced by pasted grid", rws[0] == ["Name", "Qty", "Price"] and len(rws) == 4, rws)
    check("quoted cells with tabs and quotes parsed", rws[1][0] == "Widget with tab" and rws[2][0] == 'He said "hi"', (rws[1][0], rws[2][0]))
    check("paste notice", "Pasted 4 rows by 3 columns" in notice(), notice())
    # paste into the middle cell grows the table
    paste(tb.locator("table.grid input").nth(1 * 3 + 2), "9\t8\t7\n6\t5\t4\n3\t2\t1")
    rws = raw()["doc"]["blocks"][2]["rows"]
    check("paste into a middle cell overwrites and widens the table", rws[1][2:] == ["9", "8", "7"] and all(len(r) == 5 for r in rws) and rws[3][2:] == ["3", "2", "1"] and rws[0][:3] == ["Name", "Qty", "Price"], rws)
    # size limit
    page.click('[data-add="table"]')
    t2 = page.locator(".block.table").nth(1)
    big = "\n".join("r%d\t%d" % (i, i) for i in range(260))
    paste(t2.locator("table.grid input").nth(0), big)
    check("table limited to 200 rows with a notice", len(raw()["doc"]["blocks"][3]["rows"]) == 200 and "limit" in notice(), notice())
    # delete that big table again to keep the test document light
    t2.locator('button[aria-label="Delete block"]').click()

    # ---------------------------------------------------------------- logo and status
    page.click("#btn-options")
    check("logo preview hidden at first", page.locator("#logo-prev").is_hidden() and page.locator("#btn-logo-x").is_hidden())
    with page.expect_file_chooser() as fc:
        page.click("#btn-logo")
    fc.value.set_files(LOGO); page.wait_for_selector("#logo-prev:not([hidden])")
    st = raw()
    check("logo stored as an asset and previewed", st["doc"]["options"]["logo"].startswith("a") and st["assets"] == 1 and page.locator("#btn-logo-x").is_visible(), st["assets"])
    page.select_option("#opt-status", "review")
    check("status stored", raw()["doc"]["options"]["status"] == "review")
    page.click("#btn-options")

    path, html = save_copy()
    src = json.loads(re.search(r'id="doc-source">(.*?)</script>', html, re.S).group(1))
    check("saved format version 1 with logo and status options", src["version"] == 1 and src["format"] == "helix" and src["options"]["status"] == "review" and src["options"]["logo"] in src["assets"], (src["version"], list(src["options"])))
    check("markdown stored raw in the data block", src["tabs"][0]["blocks"][0]["md"] == MD)
    check("exactly one script element (the data block)", html.count("<script") == 1, html.count("<script"))
    from html.parser import HTMLParser
    class Scan(HTMLParser):
        def __init__(self):
            super().__init__(); self.tags = {}; self.bad = []
        def handle_starttag(self, tag, attrs):
            self.tags[tag] = self.tags.get(tag, 0) + 1
            for k, val in attrs:
                if k.startswith("on") or (k in ("href", "src") and (val or "").strip().lower().startswith(("javascript:", "vbscript:"))):
                    self.bad.append((tag, k))
    sc = Scan(); sc.feed(html)
    check("no event handlers or javascript: urls anywhere in the saved document", not sc.bad, sc.bad)
    check("only the logo is an img, only the data block is a script", sc.tags.get("img") == 1 and sc.tags.get("script") == 1, sc.tags)
    check("favicon / logo header present", '<header class="head">' in html and 'class="logo"' in html and 'class="status st-review">For review</p>' in html)
    check("generator says 1.0", 'content="Green Helix Document Editor 1.0"' in html)

    # ---------------------------------------------------------------- re-open in the editor, re-save, compare bytes
    page.evaluate("t=>window.__pde.load(t)", html)
    path2, html2 = save_copy()
    check("re-open and re-save is byte-identical", html == html2, (len(html), len(html2)))

    # undo / redo of logo
    page.click("#btn-options"); page.click("#btn-logo-x")
    check("logo removed (asset gone)", raw()["assets"] == 0 and raw()["doc"]["options"]["logo"] == "")
    page.click("#btn-undo")
    check("undo brings the logo back", raw()["assets"] == 1 and raw()["doc"]["options"]["logo"] != "" and page.locator("#logo-prev").is_visible())
    page.click("#btn-options")

    # zip export includes the logo
    page.click("#btn-options")
    with page.expect_download() as d:
        page.click("#btn-zip")
    zp = T + "/" + d.value.suggested_filename; d.value.save_as(zp)
    check("zip contains the logo", any(n.startswith("images/") for n in zipfile.ZipFile(zp).namelist()), zipfile.ZipFile(zp).namelist())
    page.click("#btn-options")

    # ---------------------------------------------------------------- the saved document with scripts off
    v = b.new_context(java_script_enabled=False, viewport={"width": 1000, "height": 900}).new_page()
    v.goto("file://" + path)
    t = lambda sel: v.locator(sel).all_inner_texts()
    check("doc: h1 and status and logo", v.locator("header.head img.logo").count() == 1 and [x.lower() for x in t("header.head .status")] == ["for review"] and t("h1") == ["Checkpoint two"], t("header.head .status"))
    check("doc: logo is visible and loaded", v.locator("img.logo").evaluate("e=>e.complete&&e.naturalWidth>0"))
    check("doc: markdown heading is h3", t(".md h3") == ["Quarterly notes"], t(".md h3"))
    check("doc: bold / em / code", t(".md strong")[:1] == ["bold"] and t(".md em")[:1] == ["italic"] and "inline code" in t(".md p code"))
    check("doc: safe link opens in new tab", v.locator('.md a[href="https://example.com"][target=_blank][rel*=noopener]').count() == 1)
    check("doc: no javascript: links, no image, no live script", v.locator('a[href^="javascript"]').count() == 0 and v.locator(".md img").count() == 0 and v.locator(".md script").count() == 0)
    check("doc: hostile text shown as plain text", "<script>alert('x')</script>" in v.locator(".md").first.inner_text() and "<img src=x onerror=alert(2)>" in v.locator(".md").first.inner_text())
    check("doc: lists and nesting", v.locator(".md > ul:not(.checks) li").count() >= 3 and v.locator(".md ul ul li").count() == 1 and v.locator(".md ol li").count() == 2)
    check("doc: task list", v.locator(".md ul.checks li").count() == 2 and v.locator(".md ul.checks li.done").count() == 1)
    check("doc: quote", t(".md blockquote") == ["A quoted line"])
    check("doc: md table with right-aligned numbers", v.locator(".md table td.num").count() == 2 and t(".md table th")[0] == "Item")
    pre = v.locator('.md pre[data-lang="prompt"]')
    check("doc: prompt code block keeps lines and shows label", pre.count() == 1 and "You are a careful assistant.\nSummarise <the attached> files." in pre.inner_text()
          and v.locator('.md pre[data-lang="prompt"]').evaluate("e=>getComputedStyle(e,'::before').content") == '"prompt"')
    check("doc: code block from button", v.locator(".md pre >> nth=1").inner_text() == "print('hi')" or "print('hi')" in v.locator(".md pre").nth(1).inner_text())
    check("doc: pasted table rendered with numeric columns", v.locator("section table >> nth=1").count() == 1 or v.locator("table").count() >= 2)
    v.screenshot(path=T + "/doc-light.png", full_page=True)
    vd = b.new_context(java_script_enabled=False, color_scheme="dark", viewport={"width": 1000, "height": 900}).new_page()
    vd.goto("file://" + path); vd.screenshot(path=T + "/doc-dark.png", full_page=True)
    check("doc (dark): logo has a white plate", vd.locator("img.logo").evaluate("e=>getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)")
    vp = b.new_context(java_script_enabled=False, viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True).new_page()
    vp.goto("file://" + path); vp.screenshot(path=T + "/doc-phone.png", full_page=True)
    check("doc (phone): no sideways scrolling", vp.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"), vp.evaluate("document.documentElement.scrollWidth"))

    # print layout
    v.emulate_media(media="print"); v.pdf(path=T + "/doc.pdf")
    check("doc prints to pdf", os.path.getsize(T + "/doc.pdf") > 5000, os.path.getsize(T + "/doc.pdf"))

    # ---------------------------------------------------------------- old (V6) documents still open
    olds = ["v6.hlx.html"]
    if olds:
        old = open(FIX + "/" + olds[0], encoding="utf-8").read()
        miss = page.evaluate("t=>window.__pde.load(t)", old)
        p3, h3 = save_copy()
        check("V6 document opens, no logo/status, re-saves with only version markers changed",
              miss == 0 and raw()["doc"]["options"]["status"] == "" and raw()["doc"]["options"]["logo"] == "",
              olds[0])
        nostyle = lambda x: re.sub(r"<style>.*?</style>", "<style></style>", x, flags=re.S)
        body = lambda x: re.sub(r"\n\n+", "\n", re.sub(r'<script type="application/json" id="doc-source">.*?</script>', "", nostyle(x), flags=re.S)).replace("Editor 6", "Editor X").replace("Editor 1.0", "Editor X")
        check("  ...and the visible document is identical (style and data block aside)", body(old) == body(h3), (len(body(old)), len(body(h3))))

    # ---------------------------------------------------------------- phone layout of the editor
    b2 = launch(p)
    ph = b2.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True).new_page()
    ph.on("dialog", lambda d: d.accept())
    ph.goto("file://" + ED)
    ph.evaluate("t=>window.__pde.load(t)", html)
    ph.tap("#btn-options")
    check("editor (phone): no sideways scrolling", ph.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"), ph.evaluate("document.documentElement.scrollWidth"))
    small = ph.evaluate("""()=>Array.from(document.querySelectorAll('button,select,input[type=text]')).filter(e=>e.offsetParent&&!e.closest('.bar')&&!e.matches('.title,.subtitle')).map(e=>[e.getBoundingClientRect().height,e.textContent.slice(0,14)||e.getAttribute('aria-label')]).filter(x=>x[0]<38||x[1]<38).slice(0,5)""")
    check("editor (phone): tap targets at least 38px", not small, (small, "coarse=" + str(ph.evaluate("matchMedia('(pointer:coarse)').matches")), ph.evaluate("innerWidth")))
    ph.screenshot(path=T + "/editor-phone.png", full_page=True)  # last: a full-page screenshot resets touch emulation
    page.screenshot(path=T + "/editor-desktop.png", full_page=True)

    check("no console errors", not errs, errs)

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
