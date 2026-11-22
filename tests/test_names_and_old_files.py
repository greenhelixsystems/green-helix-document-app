"""Version 1.0 names (.helix.html, format "helix") and the promise to keep reading files made before 1.0 (.hlx.html, format "hlx")."""
import importlib.util, json, os, re, subprocess, sys, zipfile
from playwright.sync_api import sync_playwright
from common import *

T = work("names")
os.makedirs(T, exist_ok=True)
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:240]) if extra != "" else ""))
sp = importlib.util.spec_from_file_location("helix", TOOL); helix = importlib.util.module_from_spec(sp); sp.loader.exec_module(helix)
data_of = lambda h: json.loads(re.search(r'id="doc-source">(.*?)</script>', h, re.S).group(1))

with sync_playwright() as p:
    b = launch(p)
    page = b.new_context(accept_downloads=True, viewport={"width": 1100, "height": 900}).new_page(); errs = []
    page.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None); page.on("pageerror", lambda e: errs.append(str(e)[:200])); page.on("dialog", lambda d: d.accept())
    page.goto("file://" + ED)

    # a new document is saved as name.helix.html with the current format words
    page.click("#btn-new"); page.click('[data-tpl="blank"]')
    page.fill(".title", "Naming check")
    with page.expect_download() as d: page.click("#btn-copy")
    name = d.value.suggested_filename; d.value.save_as(T + "/new.helix.html"); html = open(T + "/new.helix.html", encoding="utf-8").read()
    check("a new document downloads as name.helix.html", name == "Naming-check.helix.html" or name.endswith(".helix.html"), name)
    check("the data block says format helix, version 1", data_of(html)["format"] == "helix" and data_of(html)["version"] == 1)
    check("the visible note and the stored note say Helix document", "This is a Helix document" in html and data_of(html)["about"].startswith("This is a Helix document"))
    check("no old name appears anywhere in a new file", not re.search(r"hlx|HLX", html), re.findall(r".{20}(?:hlx|HLX).{20}", html)[:2])
    check("the Python tool accepts it without notes about age", helix.check_document(html)[0] == [] and not any("before version 1.0" in n for n in helix.check_document(html)[1]), helix.check_document(html))

    # files made before 1.0 still open, and saving them writes the new format and name
    for v in ("v6", "v7", "v8"):
        old_path = FIX + "/%s.hlx.html" % v
        page.click("#btn-new"); page.click('[data-tpl="blank"]')
        page.set_input_files("#open-input", old_path); page.wait_for_timeout(900)
        with page.expect_download() as d: page.click("#btn-copy")
        nm = d.value.suggested_filename; d.value.save_as(T + "/up-%s.helix.html" % v); h = open(T + "/up-%s.helix.html" % v, encoding="utf-8").read()
        check("%s (.hlx.html, format hlx) opens and re-saves as format helix" % v, data_of(h)["format"] == "helix" and data_of(h)["version"] == 1, nm)
        check("%s: the saved name is .helix.html, not .hlx.helix.html" % v, nm.endswith(".helix.html") and ".hlx" not in nm, nm)
        check("%s: the upgraded file passes the Python check" % v, helix.check_document(h)[0] == [], helix.check_document(h))
    check("no console errors", not errs, errs)
    b.close()

# the tool reads old files, says why they are notes, and unpacks them
r = subprocess.run([sys.executable, "-I", TOOL, "check", FIX + "/v6.hlx.html"], capture_output=True, text=True)
check("tool check on a pre-1.0 file passes with a note", r.returncode == 0 and "made before version 1.0" in r.stdout and r.stdout.strip().endswith("OK"), r.stdout)
r = subprocess.run([sys.executable, "-I", TOOL, "unpack", FIX + "/v6.hlx.html", T + "/unpack-old"], capture_output=True, text=True)
check("tool unpack reads a pre-1.0 file", r.returncode == 0 and os.path.exists(T + "/unpack-old/content.md"), r.stdout + r.stderr)
spec = {"title": "From spec", "tabs": [{"name": "A", "blocks": [{"type": "text", "text": "hello"}]}]}
json.dump(spec, open(T + "/spec.json", "w"))
r = subprocess.run([sys.executable, "-I", TOOL, "build", "spec.json", "out.helix.html"], capture_output=True, text=True, cwd=T)
check("tool build writes format helix", r.returncode == 0 and data_of(open(T + "/out.helix.html", encoding="utf-8").read())["format"] == "helix", r.stdout + r.stderr)

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
