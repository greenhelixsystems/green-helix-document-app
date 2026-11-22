"""Version 1.2: report-style blocks and options, compatibility with 1.1 files, and the preview fix for issue #2."""
import importlib.util, json, os, re, shutil, subprocess, sys
from playwright.sync_api import sync_playwright
from common import *

T = work("v12")
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
sp = importlib.util.spec_from_file_location("helix", TOOL); hx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hx)
data_of = lambda h: json.loads(re.search(r'id="doc-source">(.*?)</script>', h, re.S).group(1))
read = lambda p: open(p, encoding="utf-8").read()
def cli(*a): return subprocess.run([sys.executable, "-I", TOOL] + list(a), capture_output=True, text=True, cwd=T)
for f in ("small.jpg", "small-report.pdf"):
    shutil.copy(os.path.join(INPUTS, f), T)
# a small PNG logo (1x1) and the large photo as an oversized logo
open(T + "/logo.png", "wb").write(bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                                                "1f15c4890000000d49444154789c6360f8cfc0f01f0005fe02fea3a3d0e90000000049454e44ae426082"))

spec = {"title": "Promotion options", "subtitle": "What to do first", "id": "hx-00000000000000aa",
        "options": {"eyebrow": "Research • 21 November 2026", "facts": ["Nothing was posted", "No prices quoted"], "titleSize": "large", "nav": True, "logo": "logo.png"},
        "tabs": [{"title": "Report", "blocks": [
            {"type": "stats", "title": "At a glance", "items": [{"value": "11 + 11", "label": "Ranked options", "note": "Financial / Designs"}, {"value": "#1 gap", "label": "No business profile"}]},
            {"type": "heading", "text": "Options"},
            {"id": "opts", "type": "cards", "title": "Ranked options", "items": [
                {"title": "Event listings", "body": "Submit each seminar.\n\n**You provide:** approved copy.", "tags": [{"text": "High impact", "tone": "good"}, {"text": "Low effort", "tone": "neutral"}]},
                {"title": "Paid ads", "body": "Not now.", "tags": [{"text": "Uncertain", "tone": "caution"}, {"text": "Paid", "tone": "bad"}]}]},
            {"type": "table", "title": "Proof projects", "rows": [["Project", "Status"], ["Farm building", "[[Built • First proof|good]]"], ["Eco House", "[[Not yet built|caution]]"], ["Demo unit", "[[Planned]]"], ["Plain", "[[broken]"]]},
            {"type": "callout", "tone": "danger", "title": "Hard limit", "text": "Never publish a rate."},
            {"type": "callout", "tone": "success", "title": "Done", "text": "Site verified."},
            {"type": "heading", "text": "Sources"},
            {"id": "src", "type": "sources", "title": "Sources", "items": [
                {"title": "CIRO publication", "url": "https://www.ciro.ca/x", "accessed": "2026-11-21", "group": "Compliance"},
                {"title": "Bad link", "url": "javascript:alert(1)", "group": "Compliance", "note": "kept as text"},
                {"title": "Site", "url": "example.org", "accessed": "2026-11-21", "group": "Website"}]}]},
            {"title": "Appendix", "blocks": [{"type": "cards", "numbered": False, "items": [{"title": "Unnumbered", "body": "x"}]}]}]}
json.dump(spec, open(T + "/spec.json", "w", encoding="utf-8"))
r = cli("build", "spec.json", "report.helix.html", "--no-shrink", "--now", "2026-11-21T20:00:00Z")
check("a 1.2 report builds", r.returncode == 0, r.stdout)
h = read(T + "/report.helix.html"); d = data_of(h)
check("check passes", hx.check_document(h)[0] == [], hx.check_document(h))
check("hash is canonical", json.loads(cli("hash", "report.helix.html").stdout)["canonical"])

# ---------------------------------------------------------------- rendering
check("eyebrow above a large title, key facts under the subtitle",
      h.index('<p class="eyebrow">Research') < h.index('<h1 class="lg">Promotion options</h1>') < h.index('<p class="sub">') < h.index('<ul class="facts"><li>Nothing was posted</li>'))
check("stat tiles", '<div class="stats"><div class="stat"><b>11 + 11</b><span>Ranked options</span><small>Financial / Designs</small></div>' in h)
check("numbered cards with toned tags and a Markdown body", '<ol class="cards"><li><span class="cn" aria-hidden="true">1</span><div><h3>Event listings</h3><div class="rich md">' in h
      and "<strong>You provide:</strong>" in h and '<span class="chip t-good">High impact</span>' in h and '<span class="chip t-bad">Paid</span>' in h)
check("unnumbered cards", '<ol class="cards plain"><li><div><h3>Unnumbered</h3>' in h)
check("status chips in table cells; broken syntax stays text", '<td><span class="chip t-good">Built • First proof</span></td>' in h and '<td><span class="chip t-neutral">Planned</span></td>' in h and "<td>[[broken]</td>" in h)
check("Danger and Success callouts", '<section class="callout c-danger"' in h and '<p class="ctag">Danger</p>' in h and '<section class="callout c-success"' in h)
check("sources grouped, with dates; unsafe links become text, bare addresses get https",
      '<h3 class="srcg">Compliance</h3><ul class="srcs"><li><a href="https://www.ciro.ca/x">CIRO publication</a> <span class="acc">accessed 2026-11-21</span></li><li>Bad link <span class="acc">· kept as text</span></li>' in h
      and '<a href="https://example.org">Site</a>' in h and "javascript:" not in h.split("</script>", 1)[1])
check("sticky section bar per tab, listing top-level sections", '<nav class="secbar" aria-label="Sections"><a href="#s-' in h and h.count('class="secbar"') == 1)
check("small logo becomes the browser-tab icon", '<link rel="icon" href="data:image/png;base64,' in h.split("<body>")[0])

# ---------------------------------------------------------------- reading in pieces
rc = cli("get", "report.helix.html", d["tabs"][0]["blocks"][2]["id"], "--md")
check("get --md renders cards as Markdown", "**1. Event listings** *High impact · Low effort*" in rc.stdout and "**You provide:** approved copy." in rc.stdout, rc.stdout[:400])
rc = cli("get", "report.helix.html", [b["id"] for b in d["tabs"][0]["blocks"] if b["type"] == "sources"][0], "--md")
check("get --md lists sources with group and date", "**Compliance**" in rc.stdout and "- [CIRO publication](https://www.ciro.ca/x) (accessed 2026-11-21)" in rc.stdout, rc.stdout[:400])
o = json.loads(cli("outline", "report.helix.html").stdout)
check("outline previews the new blocks", any("11 + 11" in b.get("preview", "") for b in o["tabs"][0]["blocks"]) and any("CIRO" in b.get("preview", "") for b in o["tabs"][0]["blocks"]))
rc = subprocess.run([sys.executable, "-I", TOOL, "unpack", "report.helix.html", "un"], capture_output=True, text=True, cwd=T)
r2 = cli("build", "un/spec.json", "rebuilt.helix.html", "--no-shrink")
check("unpack then build of a 1.2 document is byte-identical", rc.returncode == 0 and r2.returncode == 0 and read(T + "/rebuilt.helix.html") == h, r2.stdout)
pf = {"base": hx.content_hash(*hx.light_load(d)), "ops": [{"op": "set", "id": d["tabs"][0]["blocks"][2]["id"], "items": [{"title": "Only one", "body": "x", "tags": [{"text": "New", "tone": "good"}]}]}], "log": {"by": "T"}}
json.dump(pf, open(T + "/p.json", "w"))
r = cli("patch", "report.helix.html", "p.json", "-o", "patched.helix.html")
check("patch edits a cards block", r.returncode == 0 and data_of(read(T + "/patched.helix.html"))["tabs"][0]["blocks"][2]["items"][0]["tags"] == [{"text": "New", "tone": "good"}], r.stdout)

# ---------------------------------------------------------------- compatibility with 1.1
old_spec = {"title": "Old", "id": "hx-00000000000000bb", "options": {"toc": True}, "blocks": [{"type": "markdown", "title": "A", "md": "x"}, {"type": "table", "title": "T", "rows": [["a"], ["b"]]}]}
json.dump(old_spec, open(T + "/old.json", "w"))
cli("build", "old.json", "old.helix.html", "--now", "2026-11-01T00:00:00Z")
oh = read(T + "/old.helix.html"); od = data_of(oh)
check("documents that use no 1.2 settings have exactly the 1.1 options", list(od["options"].keys()) == ["toc", "accent", "footer", "logo", "status", "fingerprints", "about"], list(od["options"].keys()))
v11 = str(ROOT / "tests" / "fixtures" / "v1.1-report.helix.html")
if os.path.exists(v11):
    t11 = read(v11)
    check("a file made by 1.1 passes the 1.2 check with its hash unchanged", hx.check_document(t11)[0] == [] and json.loads(cli("hash", v11).stdout)["match"], hx.check_document(t11))

# ---------------------------------------------------------------- the editor
with sync_playwright() as p:
    b = launch(p)
    page = b.new_context(accept_downloads=True, viewport={"width": 1280, "height": 1000}).new_page(); errs = []
    page.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None); page.on("pageerror", lambda e: errs.append(str(e)[:200])); page.on("dialog", lambda dl: dl.accept())
    page.goto("file://" + ED); page.evaluate("()=>{delete window.showSaveFilePicker;}")
    for name, html in (("report", h), ("old", oh), ("patched", read(T + "/patched.helix.html"))):
        page.evaluate("t=>window.__pde.load(t)", html)
        check("editor reopens the %s file and writes it back byte for byte" % name, page.evaluate("()=>window.__pde.build()") == html)
    if os.path.exists(v11):
        page.evaluate("t=>window.__pde.load(t)", t11)
        check("editor reopens a 1.1 file without changing its content hash", page.evaluate("()=>JSON.parse(window.__pde.build().match(/doc-source\">(.*?)<\\/script>/s)[1]).rev.hash") == data_of(t11)["rev"]["hash"]
              and "next save" not in page.inner_text("#log-sum"), page.inner_text("#log-sum"))
    # issue #2: tabs in the preview
    page.evaluate("t=>window.__pde.load(t)", h); page.click("#btn-preview"); page.wait_for_timeout(400)
    fr = page.frame_locator("#preview"); fr.locator(".tabbar a").nth(1).click(); page.wait_for_timeout(500)
    f = [x for x in page.frames if x != page.main_frame][0]
    check("issue #2: switching tabs in the preview stays in the preview", f.url.startswith("about:srcdoc#t-") and f.evaluate("()=>getComputedStyle(document.querySelectorAll('.panel')[1]).display") != "none", f.url)
    fr.locator(".tabbar a").nth(0).click(); page.wait_for_timeout(300)
    check("issue #2: and back to the first tab", f.evaluate("()=>getComputedStyle(document.querySelectorAll('.panel')[0]).display") != "none")
    fr.locator(".secbar a").nth(1).click(); page.wait_for_timeout(300)
    check("issue #2: section bar links work in the preview", f.url.startswith("about:srcdoc#s-"), f.url)
    page.click("#btn-preview")
    # options panel: turn settings on and off again; nothing is left behind
    page.evaluate("t=>window.__pde.load(t)", oh); page.click("#btn-options")
    page.check("#opt-nav"); page.fill("#opt-eyebrow", "Brief"); page.fill("#opt-facts", "One\nTwo"); page.select_option("#opt-tsize", "large")
    on = data_of(page.evaluate("()=>window.__pde.build()"))["options"]
    check("editor writes the title area and sticky bar settings", on.get("nav") is True and on.get("eyebrow") == "Brief" and on.get("facts") == ["One", "Two"] and on.get("titleSize") == "large", on)
    page.uncheck("#opt-nav"); page.fill("#opt-eyebrow", ""); page.fill("#opt-facts", ""); page.select_option("#opt-tsize", "")
    off = data_of(page.evaluate("()=>window.__pde.build()"))
    check("turning them off leaves no trace: same options and hash as before", off["options"] == od["options"] and off["rev"]["hash"] == od["rev"]["hash"], off["options"])
    check("the table of contents option is still there", page.is_checked("#opt-toc"))
    page.click("#btn-options")
    # build the three new blocks through the editor's forms
    page.click("#btn-new"); page.click('[data-tpl="blank"]'); page.fill("#doc-title", "Made in the editor")
    page.click('[data-add="stats"]'); blk = page.locator(".block.stats")
    blk.locator(".erow input").nth(0).fill("42"); blk.locator(".erow input").nth(1).fill("Things counted")
    page.click('[data-add="cards"]'); cb = page.locator(".block.cards")
    cb.locator(".cardedit .row input").first.fill("First option"); cb.locator(".cardedit textarea").first.fill("**Bold** detail")
    cb.locator("button", has_text="+ Tag").click(); cb.locator(".tg input").first.fill("High impact"); cb.locator(".tg select").first.select_option("good")
    cb.locator("button", has_text="Add card").click(); cb.locator(".cardedit .row input").nth(1).fill("Second option")
    cb.locator('[aria-label="Move card 2 up"]').click()
    page.click('[data-add="sources"]'); sb = page.locator(".block.sources")
    sb.locator('[aria-label="Source 1 title"]').fill("A source"); sb.locator('[aria-label="Source 1 address"]').fill("https://example.org/a")
    sb.locator('[aria-label="Source 1 date accessed"]').fill("2026-11-21"); sb.locator('[aria-label="Source 1 group"]').fill("Web")
    with page.expect_download() as dl: page.click("#btn-copy")
    dl.value.save_as(T + "/editor-made.helix.html"); em = read(T + "/editor-made.helix.html"); ed = data_of(em)
    blocks = {x["type"]: x for x in ed["tabs"][0]["blocks"]}
    check("editor forms: stat tile saved", blocks["stats"]["items"][0] == {"value": "42", "label": "Things counted", "note": ""}, blocks["stats"]["items"][:1])
    check("editor forms: cards saved, reordered, with a tag", [c["title"] for c in blocks["cards"]["items"]] == ["Second option", "First option"] and blocks["cards"]["items"][1]["tags"] == [{"text": "High impact", "tone": "good"}], blocks["cards"]["items"])
    check("editor forms: source saved with its date and group", blocks["sources"]["items"][0] == {"title": "A source", "url": "https://example.org/a", "accessed": "2026-11-21", "group": "Web", "note": ""}, blocks["sources"]["items"])
    check("the editor's file passes the Python check and matches helix.py's rendering", hx.check_document(em)[0] == [], hx.check_document(em))
    check("Export for AI is gone", page.locator("#btn-ai").count() == 0)
    # print and phone
    pv = b.new_page(viewport={"width": 1100, "height": 900}); pv.goto("file://" + T + "/report.helix.html")
    pv.emulate_media(media="print")
    check("the sticky bar and AI panels are not printed", pv.evaluate("()=>getComputedStyle(document.querySelector('.secbar')).display") == "none")
    pv.emulate_media(media="screen"); pv.evaluate("()=>window.scrollTo(0,1400)")
    check("the section bar sticks to the top while scrolling", abs(pv.evaluate("()=>document.querySelector('.secbar').getBoundingClientRect().top")) < 2)
    ph = b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True).new_page(); ph.goto("file://" + T + "/report.helix.html")
    check("phone: no sideways scrolling with cards, stats and the section bar", ph.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    check("no editor errors", not errs, errs)
    b.close()

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
