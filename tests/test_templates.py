import importlib.util, json, os, re
from playwright.sync_api import sync_playwright
from common import *
T = work("v11"); os.makedirs(T, exist_ok=True)
sp = importlib.util.spec_from_file_location("hlx", TOOL); hlx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hlx)
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:240]) if extra != "" else ""))
with sync_playwright() as p:
    b = launch(p)
    ctx = b.new_context(accept_downloads=True, viewport={"width": 1100, "height": 1000}); page = ctx.new_page(); errs = []
    page.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None); page.on("pageerror", lambda e: errs.append(str(e)[:200])); page.on("dialog", lambda d: d.accept())
    page.goto("file://" + ED)
    state = lambda: json.loads(page.evaluate("JSON.stringify(window.__pde.state())"))
    check("six starting points are offered", [x.strip() for x in page.locator("#templates button").all_inner_texts()] == ["Blank", "Project tracker", "Meeting notes", "Client package", "Client delivery", "AI hand-over"], page.locator("#templates button").all_inner_texts())
    def save(name):
        with page.expect_download() as d: page.click("#btn-copy")
        pth = T + "/" + name; d.value.save_as(pth); return open(pth, encoding="utf-8").read()

    # existing single-tab templates still work and still produce one tab
    for key in ("project", "meeting", "client"):
        page.click("#btn-new"); page.click('[data-tpl="%s"]' % key)
        check("%s template still starts a one-tab document with About on" % key, page.locator(".tabbtn").count() <= 1 and page.evaluate("window.__pde.state().doc.options.about") is True)

    # Client delivery
    page.click("#btn-new"); page.click('[data-tpl="delivery"]')
    check("delivery: notice names it", "Client delivery template" in page.inner_text("#notice"), page.inner_text("#notice"))
    check("delivery: three named tabs", page.locator(".tabbtn").all_inner_texts()[:3] == ["Overview", "Documents", "Questions"] or [t.strip() for t in page.locator(".tabbtn").all_inner_texts()][:3] == ["Overview", "Documents", "Questions"], page.locator(".tabbtn").all_inner_texts())
    h = save("delivery.helix.html"); d, a, miss, bad, r, data = hlx.read_document(h)
    check("delivery: saved structure (3 tabs, status final, About on, no fingerprints)", [t["title"] for t in d["tabs"]] == ["Overview", "Documents", "Questions"] and d["options"]["status"] == "final" and d["options"]["about"] and not d["options"]["fingerprints"])
    check("delivery: Python check says OK", not hlx.check_document(h)[0], hlx.check_document(h)[0])
    check("delivery: files and photos blocks are on the Documents tab", [b_["type"] for b_ in d["tabs"][1]["blocks"]] == ["files", "images"] and [b_["type"] for b_ in d["tabs"][2]["blocks"]] == ["collapsible", "text"])
    check("delivery: tab bar and 3 panels in the document", h.count('class="panel"') == 3 and 'class="tabbar"' in h)

    # AI hand-over
    page.click("#btn-new"); page.click('[data-tpl="handover"]')
    h = save("handover.helix.html"); d, a, miss, bad, r, data = hlx.read_document(h)
    check("hand-over: tabs Brief, Data, Instructions", [t["title"] for t in d["tabs"]] == ["Brief", "Data", "Instructions"])
    check("hand-over: draft status, fingerprints on, About on", d["options"]["status"] == "draft" and d["options"]["fingerprints"] and d["options"]["about"])
    check("hand-over: two Markdown blocks with real Markdown", [b_["type"] for t in d["tabs"] for b_ in t["blocks"]].count("markdown") == 2 and "## Context" in h and "## Task" in h)
    check("hand-over: Python check says OK, data block in the first 4 KB", not hlx.check_document(h)[0] and h.index('id="doc-source"') < 4000)
    check("hand-over: the About note is in the data block and on the page", data.get("about", "").startswith("This is a Helix document") and 'class="about"' in h)
    page.click("#btn-options"); check("hand-over: the Options panel shows fingerprints ticked", page.is_checked("#opt-fp") and page.is_checked("#opt-about") if page.locator("#opt-about").count() else page.is_checked("#opt-fp"))
    page.click("#btn-options")
    # the Markdown export works on a template
    md = page.evaluate("window.__pde.toMd()"); check("hand-over: the Markdown export has tabs as ## headings", "## Brief" in md and "## Data" in md and "## Instructions" in md and "**Status:** Draft" in md)

    # reopen the saved files: identical re-save and editor/Python agree
    for name in ("delivery.helix.html", "handover.helix.html"):
        t = open(T + "/" + name, encoding="utf-8").read(); page.evaluate("t=>window.__pde.load(t)", t); again = page.evaluate("window.__pde.build()")
        check("%s reopens and re-saves identically" % name, again == t)
        dd_, aa_, *_ = hlx.read_document(t); check("%s: Python rebuild equals the editor's file" % name, hlx.render(dd_, aa_, hlx._guess_today(t)) == t)

    # undo goes back to the previous document, templates can be started over a saved one
    page.click("#btn-new"); page.click('[data-tpl="blank"]'); check("blank after a template gives an empty one-tab document", len(state()["doc"]["tabs"]) == 1 and state()["doc"]["blocks"] == [])
    # look at them
    for key, label in (("delivery", "Client delivery"), ("handover", "AI hand-over")):
        page.click("#btn-new"); page.click('[data-tpl="%s"]' % key); page.wait_for_timeout(200); page.screenshot(path=T + "/editor-%s.png" % key, full_page=False)
        page.click("#btn-preview") if page.locator("#btn-preview").count() else None; page.wait_for_timeout(300); page.screenshot(path=T + "/preview-%s.png" % key, full_page=False)
        page.click("#btn-preview") if page.locator("#btn-preview").count() else None
    ph = b.new_context(viewport={"width": 390, "height": 800}, device_scale_factor=2, is_mobile=True, has_touch=True).new_page(); ph.goto("file://" + T + "/handover.helix.html"); ph.wait_for_timeout(200)
    check("phone: no horizontal overflow on the hand-over document", ph.evaluate("document.documentElement.scrollWidth") <= 390, ph.evaluate("document.documentElement.scrollWidth"))
    ph.screenshot(path=T + "/phone-handover.png")
    check("no console errors", not errs, errs[:2])
    b.close()
print("\n%d/%d checks passed" % (sum(ok), len(ok))); raise SystemExit(0 if all(ok) else 1)
