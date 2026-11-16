import base64, hashlib, json, os, random, re, time, zipfile
from playwright.sync_api import sync_playwright

# Checkpoint 3 after the viewer was removed: fingerprints, integrity warnings, checksum list, downloads.
from common import *
T = work("v9")
os.makedirs(T, exist_ok=True)
ok = []
sha = lambda data: hashlib.sha256(data).hexdigest()
shaf = lambda p: sha(open(p, "rb").read())


def check(name, cond, extra=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:200]) if extra != "" else ""))


open(T + "/notes.txt", "w", encoding="utf-8").write("Plain notes, with an accent: é\n<script>alert(1)</script>\n")
open(T + "/evil.html", "w").write("<html><body><script>document.title='pwned'</script>hello</body></html>")
FILES = [SRC + "/small-report.pdf", INPUTS + "/small.jpg", T + "/notes.txt", SRC + "/sample-notes.docx", T + "/evil.html"]
random.seed(7)

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

    # SHA-256 correctness
    bad = []
    for n in [0, 1, 3, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 129, 1000, 65536, 100003]:
        data = bytes(random.getrandbits(8) for _ in range(n))
        if page.evaluate("b=>window.__pde.sha(window.__pde.bytes(b))", base64.b64encode(data).decode()) != sha(data): bad.append(n)
    check("JS SHA-256 matches hashlib at 17 boundary sizes", not bad, bad)
    big = open(SRC + "/medium-report.pdf", "rb").read(); t0 = time.time()
    check("JS SHA-256 of a 1.2 MB pdf matches, and is quick", page.evaluate("b=>window.__pde.sha(window.__pde.bytes(b))", base64.b64encode(big).decode()) == sha(big) and time.time() - t0 < 3)

    # two-tab document with files and fingerprints shown
    page.fill("#doc-title", "Fingerprint test")
    page.click('[data-add="files"]'); blk = page.locator(".block.files").first
    blk.locator(".bhead input").fill("Documents")
    with page.expect_file_chooser() as fc:
        blk.locator('button:has-text("Add files")').click()
    fc.value.set_files(FILES); page.wait_for_selector(".flist li >> nth=4")
    page.click("#btn-options"); page.check("#opt-fp"); page.click("#btn-options")
    page.click(".tabadd"); page.fill("#tab-name", "More")
    page.click('[data-add="files"]'); b2 = page.locator(".block.files")
    with page.expect_file_chooser() as fc:
        b2.locator('button:has-text("Add files")').click()
    fc.value.set_files(SRC + "/medium-report.pdf"); page.wait_for_selector(".flist li")
    page.click('.tabbtn >> nth=0'); page.fill("#tab-name", "Main")
    with page.expect_download() as d:
        page.click("#btn-copy")
    path = T + "/" + d.value.suggested_filename; d.value.save_as(path)
    html = open(path, encoding="utf-8").read()
    src = json.loads(re.search(r'id="doc-source">(.*?)</script>', html, re.S).group(1))
    meta = src["assets"]; names = {v["name"]: v for v in meta.values()}
    allfiles = FILES + [SRC + "/medium-report.pdf"]
    check("every asset has a fingerprint equal to hashlib's", all(v.get("sha256") == shaf(next(f for f in allfiles if os.path.basename(f) == v["name"])) for v in meta.values()), len(meta))
    check("fingerprint shown in file lists, and it is the right one", html.count('class="fdesc fp"') == 6 and ("<code>" + names["small.jpg"]["sha256"] + "</code>") in html)
    check("no viewer, no frames, no Open buttons, no frame permission", 'class="viewer"' not in html and "<iframe" not in html and "frame-src" not in html and 'class="op"' not in html and '"view"' not in html)

    page.evaluate("t=>window.__pde.load(t)", html)
    check("no fingerprint warnings on a clean file", page.evaluate("window.__pde.bad()") == [])
    with page.expect_download() as d:
        page.click("#btn-copy")
    d.value.save_as(T + "/second.helix.html")
    check("re-open and re-save is byte-identical", html == open(T + "/second.helix.html", encoding="utf-8").read())

    # tamper detection through the real open path
    m = re.search(r'(id="asset-\w+" download="small\.jpg" href="data:image/jpeg;base64,)(.{300})', html, re.S)
    chunk = m.group(2); flip = chunk[:100] + ("B" if chunk[100] != "B" else "C") + chunk[101:]
    tampered = html.replace(m.group(1) + chunk, m.group(1) + flip, 1)
    check("tamper test file differs", tampered != html)
    open(T + "/tampered.helix.html", "w", encoding="utf-8").write(tampered)
    page.set_input_files("#open-input", T + "/tampered.helix.html"); page.wait_for_timeout(1200)
    check("editor warns that small.jpg changed", "Warning" in notice() and "small.jpg" in notice() and page.evaluate("window.__pde.bad()") == ["small.jpg"], notice()[:160])
    page.set_input_files("#open-input", path); page.wait_for_timeout(1200)
    check("clean file opens without a warning", "Warning" not in notice() and page.evaluate("window.__pde.bad()") == [])

    # zip checksum list
    page.click("#btn-options")
    with page.expect_download() as d:
        page.click("#btn-zip")
    zp = T + "/" + d.value.suggested_filename; d.value.save_as(zp); z = zipfile.ZipFile(zp)
    sums = z.read("SHA256SUMS.txt").decode().strip().split("\n")
    check("zip has SHA256SUMS.txt that matches every file", all(sha(z.read(l.split("  ", 1)[1])) == l.split("  ", 1)[0] for l in sums) and len(sums) == len(z.namelist()) - 1)
    check("export notice counts files, not the checksum list", "Exported 6 items" in notice(), notice())
    page.click("#btn-options")

    # the document in a browser: downloads byte-identical, scripts blocked, attachment text not executed
    v = b.new_context(accept_downloads=True, viewport={"width": 1100, "height": 800}).new_page()
    v.goto("file://" + path)
    try:
        v.add_script_tag(content="window.__ran=1"); refused = False
    except Exception as e:
        refused = "Content Security Policy" in str(e)
    check("an injected script is refused by the document's policy", refused and v.evaluate("window.__ran") is None)
    okd = []
    for f in FILES:
        n = os.path.basename(f)
        with v.expect_download() as dd:
            v.locator("tr:has-text('%s') a.dl" % n).first.click()
        pth = T + "/dl-" + n; dd.value.save_as(pth); okd.append(shaf(pth) == shaf(f))
    check("all 5 downloads identical to the originals", all(okd), okd)
    check("every file has only a Download button", v.locator("td.act a").count() == 6 and v.locator("td.act a.dl").count() == 6)
    v.screenshot(path=T + "/doc-files.png")

    # frozen older documents
    for name, expect_assets in [("v7.hlx.html", 2), ("v8.hlx.html", 2)]:
        t = open(FIX + "/" + name, encoding="utf-8").read()
        miss = page.evaluate("t=>window.__pde.load(t)", t)
        r = page.evaluate("window.__pde.build()")
        s_ = json.loads(re.search(r'id="doc-source">(.*?)</script>', r, re.S).group(1))
        check("frozen " + name + " opens, files intact and fingerprinted", miss == 0 and page.evaluate("window.__pde.bad()") == [] and len(s_["assets"]) == expect_assets and all("sha256" in a for a in s_["assets"].values()))

    check("no console errors", not errs, errs[:2])

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
