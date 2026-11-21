"""Version 1.1: document identity, revisions, AI Notes, the Revision Log, small-piece reading, patching and AI returns."""
import importlib.util, json, os, re, shutil, subprocess, sys
from playwright.sync_api import sync_playwright
from common import *

T = work("ai11")
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
sp = importlib.util.spec_from_file_location("helix", TOOL); hx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hx)
data_of = lambda h: json.loads(re.search(r'id="doc-source">(.*?)</script>', h, re.S).group(1))
read = lambda p: open(p, encoding="utf-8").read()
def cli(*a): return subprocess.run([sys.executable, "-I", TOOL] + list(a), capture_output=True, text=True, cwd=T)
def jcli(*a):
    r = cli(*a)
    try: return r.returncode, json.loads(r.stdout)
    except ValueError: return r.returncode, r.stdout + r.stderr

for f in ("small-report.pdf", "sample-table.xlsx", "small.jpg"):
    shutil.copy(os.path.join(INPUTS, f), T)
NOW = "2026-11-21T10:00:00Z"
spec = {"title": "Garden Shed Build", "subtitle": "Plan & handoff <test>", "by": "ChatGPT", "kind": "ai",
        "ai": {"notes": "## Purpose\nPlan a shed.\n\nRevise only **Budget**.", "focus": ["budget"], "protect": ["scope"],
               "work": {"task": "SHED-2", "stage": "draft", "assignee": "Claude", "status": "assigned", "objective": "Price the build",
                        "targets": ["budget"], "sources": ["scope"], "instructions": "Use current prices.\n\nShow a total.",
                        "deliverables": ["Updated budget"], "done": ["Total row present"], "review": "Owner checks totals"}},
        "options": {"status": "draft", "fingerprints": True},
        "tabs": [{"title": "Plan", "blocks": [
            {"id": "scope", "type": "markdown", "title": "Scope", "md": "Build an 8 x 10 ft shed."},
            {"type": "heading", "text": "Steps"},
            {"type": "checklist", "title": "Checklist", "items": [{"text": "Level site", "done": True}, {"text": "Frame", "done": False}]},
            {"id": "budget", "type": "table", "title": "Budget", "rows": [["Item", "Cost"], ["Gravel", "300"], ["Lumber", "1,800"]]},
            {"type": "images", "title": "Photo", "items": [{"file": "small.jpg", "caption": "Site"}]}]},
                 {"title": "Files", "blocks": [{"type": "files", "title": "Files", "items": [{"file": "small-report.pdf", "note": "Permit"}, {"file": "sample-table.xlsx"}]}]}]}
json.dump(spec, open(T + "/spec.json", "w", encoding="utf-8"))
r = cli("build", "spec.json", "Shed_v1.helix.html", "--no-shrink", "--now", NOW)
check("build with AI Notes, an assignment and files", r.returncode == 0, r.stdout)
v1 = read(T + "/Shed_v1.helix.html"); d1 = data_of(v1)

# ---------------------------------------------------------------- the data block
keys = list(d1.keys())
check("data block order: identity first, AI Notes before the content, log last",
      keys[:5] == ["format", "version", "spec", "id", "rev"] and keys.index("ai") < keys.index("title") < keys.index("tabs") < keys.index("assets") < keys.index("log"), keys)
check("spec 1.1, version 1, a document id, revision 1 with a hash", d1["spec"] == "1.1" and d1["version"] == 1 and d1["id"].startswith("hx-") and d1["rev"]["n"] == 1 and d1["rev"]["label"] == "1" and len(d1["rev"]["hash"]) == 64)
check("AI Notes come within the first 2.5 KB of the file", v1.index('"ai":') < 2500, v1.index('"ai":'))
blk = {b["title"] if b["type"] != "heading" else b["text"]: b["id"] for t in d1["tabs"] for b in t["blocks"]}
check("friendly ids in the spec become real ids, and AI Notes point at them",
      d1["ai"]["focus"] == [blk["Budget"]] and d1["ai"]["protect"] == [blk["Scope"]] and d1["ai"]["work"]["targets"] == [blk["Budget"]], d1["ai"])
check("the creation is logged with who made it", d1["log"] == [{"rev": 1, "label": "1", "at": NOW, "by": "ChatGPT", "kind": "ai", "summary": "Created"}], d1["log"])
check("the stored hash matches the content", d1["rev"]["hash"] == hx.content_hash(*hx.light_load(d1)))
check("AI Notes and Revision Log buttons sit under the title", v1.index('<div class="hxbar">') < v1.index('<div class="tabs">') and "<summary>AI Notes</summary>" in v1 and 'Revision Log <span class="hxv">v1</span>' in v1)
check("the assignment is visible to readers", "<dt>Task</dt><dd>SHED-2</dd>" in v1 and "<dt>Work on</dt><dd>Budget</dd>" in v1 and "Done when" in v1)
check("check passes", hx.check_document(v1)[0] == [], hx.check_document(v1))

# ---------------------------------------------------------------- reading in small pieces
rc, o = jcli("outline", "Shed_v1.helix.html")
check("outline: scope, flags and sizes", rc == 0 and o["default_scope"] == "focus" and o["size"]["focus_chars"] > 0 and o["base"] == d1["rev"]["hash"]
      and [b.get("focus") for b in o["tabs"][0]["blocks"]] == [None, None, None, True, None], o if rc else "")
check("outline output is far smaller than the file", rc == 0 and len(json.dumps(o)) * 10 < os.path.getsize(T + "/Shed_v1.helix.html"), (len(json.dumps(o)) if rc == 0 else 0, os.path.getsize(T + "/Shed_v1.helix.html")))
# outline must not depend on anything after the data block: wreck every attachment and it still works
wreck = re.sub(r'(href|src)="data:[^"]+"', r'\1="data:x;base64,AAAA"', v1)
open(T + "/wrecked.helix.html", "w", encoding="utf-8").write(wreck)
rc2, o2 = jcli("outline", "wrecked.helix.html")
check("outline reads only the data block (attachments never touched)", rc2 == 0 and o2["tabs"] == o["tabs"] and o2["base"] == o["base"])
rc, g = jcli("get", "Shed_v1.helix.html", "--focus")
check("get --focus returns just the focus block with the base", rc == 0 and [b["id"] for b in g["blocks"]] == [blk["Budget"]] and g["base"] == d1["rev"]["hash"], g)
r = cli("get", "Shed_v1.helix.html", blk["Scope"], "--md")
check("get --md gives Markdown and marks protected blocks", r.returncode == 0 and "do not change" in r.stdout and "### Scope" in r.stdout and "Build an 8" in r.stdout, r.stdout)
rc, g2 = jcli("get", "Shed_v1.helix.html", d1["tabs"][1]["id"])
check("get with a tab id returns that tab's blocks", rc == 0 and [b["type"] for b in g2["blocks"]] == ["files"])
r = cli("get", "Shed_v1.helix.html", "anope")
check("get with an unknown id says so", r.returncode == 1 and "no block or tab" in r.stdout, r.stdout)
pdf = [a for a in o["assets"] if a["name"] == "small-report.pdf"][0]
rc, a = jcli("asset", "Shed_v1.helix.html", pdf["id"], "out.pdf")
check("asset writes one attachment, byte for byte", rc == 0 and open(T + "/out.pdf", "rb").read() == open(T + "/small-report.pdf", "rb").read())

# ---------------------------------------------------------------- patching
def patch_file(name, ops, base=None, log=None, **extra):
    p = dict({"helixPatch": 1, "doc": d1["id"], "base": base or d1["rev"]["hash"], "ops": ops, "log": log or {"by": "Claude", "summary": "Edited"}}, **extra)
    json.dump(p, open(T + "/" + name, "w", encoding="utf-8")); return name
pf = patch_file("p1.json", [{"op": "set", "id": blk["Budget"], "rows": [["Item", "Cost"], ["Gravel", "300"], ["Lumber", "1,800"], ["Total", "2,100"]]},
                            {"op": "ai", "notes_append": "Claude: added a total."}], log={"by": "Claude", "kind": "ai", "summary": "Added a total"})
rc, res = jcli("patch", "Shed_v1.helix.html", pf, "--now", "2026-11-21T11:00:00Z")
check("patch writes Shed_v1.1.helix.html", rc == 0 and res["file"].endswith("Shed_v1.1.helix.html") and os.path.exists(T + "/Shed_v1.1.helix.html"), res)
v11 = read(T + "/Shed_v1.1.helix.html"); d11 = data_of(v11)
check("revision 2, label 1.1, parent is the old hash", d11["rev"]["n"] == 2 and d11["rev"]["label"] == "1.1" and d11["rev"]["parent"] == d1["rev"]["hash"] and d11["id"] == d1["id"])
check("log records who, what, which block and the tool's own check", d11["log"][-1]["by"] == "Claude" and d11["log"][-1]["blocks"] == [blk["Budget"]] and d11["log"][-1]["status"] == "submitted" and "helix.py check: pass" in d11["log"][-1]["checks"], d11["log"][-1])
check("AI Notes gained the appended note", d11["ai"]["notes"].endswith("Claude: added a total."))
untouched = lambda d: [b for t in d["tabs"] for b in t["blocks"] if b["id"] != blk["Budget"]]
check("every other block is unchanged", untouched(d1) == untouched(d11))
aa = lambda h: sorted(re.findall(r'(?:href|src)="(data:[^"]+)"', h))
check("attachments are byte-identical", aa(v1) == aa(v11))
check("the patched file passes check", hx.check_document(v11)[0] == [], hx.check_document(v11))
rc, res = jcli("patch", "Shed_v1.1.helix.html", pf)
check("a stale base is a conflict, nothing written", rc == 1 and "CONFLICT" in str(res) and not os.path.exists(T + "/Shed_v1.2.helix.html"), res)
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p2.json", [{"op": "set", "id": blk["Scope"], "md": "Bigger"}]))
check("a protected block cannot be changed", rc == 1 and "PROTECTED" in str(res), res)
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p3.json", [{"op": "ai", "protect": []}]))
check("protection cannot be removed by a patch", rc == 1 and "PROTECTED" in str(res), res)
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p4.json", [{"op": "set", "id": blk["Budget"], "title": "Costs"}], log={"by": "X", "status": "approved"}))
check("a patch cannot record approval", rc == 1 and "approved" in str(res), res)
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p5.json", [{"op": "set", "id": blk["Budget"], "type": "text"}]))
check("a block's type cannot change", rc == 1 and "cannot change" in str(res), res)
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p6.json", [
    {"op": "insert", "after": blk["Budget"], "block": {"type": "markdown", "title": "Risks", "md": "Rain delays."}},
    {"op": "attach", "to": blk["Budget"] if False else d1["tabs"][1]["blocks"][0]["id"], "file": "small.jpg", "note": "Extra photo"},
    {"op": "move", "id": blk["Checklist"], "tab": d1["tabs"][1]["id"]}], major=True), "-o", "major.helix.html")
dm = data_of(read(T + "/major.helix.html")) if rc == 0 else {}
check("insert, attach and move in one patch; major makes v2", rc == 0 and dm["rev"]["label"] == "2" and [b["title"] for b in dm["tabs"][0]["blocks"] if b["type"] != "heading"] == ["Scope", "Budget", "Risks", "Photo"]
      and dm["tabs"][1]["blocks"][-1]["title"] == "Checklist" and len(dm["tabs"][1]["blocks"][0]["items"]) == 3, res)
check("outside-focus changes are reported", rc == 0 and len(res["outside_focus"]) >= 1, res)
check("new ids do not collide", rc == 0 and len(set(hx.known_ids(hx.light_load(dm)[0]))) == sum(1 + len(t["blocks"]) for t in dm["tabs"]))
rc, res = jcli("patch", "Shed_v1.helix.html", patch_file("p7.json", [{"op": "delete", "id": blk["Budget"]}]), "--allow-protected", "-o", "del.helix.html")
dd = data_of(read(T + "/del.helix.html")) if rc == 0 else {}
check("deleting a focus block also drops it from AI Notes", rc == 0 and blk["Budget"] not in dd["ai"].get("focus", []) and "Deleted 1 block" in dd["log"][-1].get("note", ""), dd.get("ai"))

# ---------------------------------------------------------------- diff and returns
rc, df = jcli("diff", "Shed_v1.helix.html", "Shed_v1.1.helix.html")
check("diff names the changed block and shows the new row", rc == 0 and df["same_document"] and [c["name"] for c in df["changed"]] == ["Budget"] and "+Total | 2,100" in df["changed"][0]["diff"] and df["ai_notes_changed"], df)
env = {"helixReturn": 1, "task": "SHED-2", "doc": d1["id"], "base": d1["rev"]["hash"], "result": d11["rev"]["hash"], "summary": "Added a total",
       "blocks": [blk["Budget"]], "checks": [{"name": "helix check", "result": "pass"}], "questions": ["Lumber price?"], "next": "Owner review", "humanReview": True, "status": "submitted"}
json.dump(env, open(T + "/ret.json", "w"))
rc, rv = jcli("return-check", "ret.json", "--doc", "Shed_v1.1.helix.html", "--base", "Shed_v1.helix.html")
check("a consistent return passes", rc == 0 and rv["ok"] and rv["changed"] == [blk["Budget"]], rv)
json.dump(dict(env, status="approved"), open(T + "/ret2.json", "w"))
rc, rv = jcli("return-check", "ret2.json", "--base", "Shed_v1.helix.html")
check("a return claiming approval fails", rc == 1 and any("approved" in p for p in rv["problems"]), rv)
json.dump(dict(env, base=d11["rev"]["hash"]), open(T + "/ret3.json", "w"))
rc, rv = jcli("return-check", "ret3.json", "--base", "Shed_v1.helix.html")
check("a return made against another revision fails", rc == 1 and any("different revision" in p for p in rv["problems"]), rv)
penv = dict(env, result="", patch={"ops": [{"op": "set", "id": blk["Scope"], "md": "Bigger"}]})
json.dump(penv, open(T + "/ret4.json", "w"))
rc, rv = jcli("return-check", "ret4.json", "--base", "Shed_v1.helix.html")
check("a return whose patch touches a protected block fails", rc == 1 and any("do not change" in p for p in rv["problems"]), rv)
json.dump(dict(env, result="", patch={"ops": [{"op": "set", "id": blk["Budget"], "title": "Costs"}]}), open(T + "/ret5.json", "w"))
rc, res = jcli("patch", "Shed_v1.helix.html", "ret5.json", "-o", "fromreturn.helix.html")
check("patch accepts a return that carries a patch", rc == 0 and data_of(read(T + "/fromreturn.helix.html"))["log"][-1]["summary"] == "Added a total", res)

# ---------------------------------------------------------------- integrity and versions
hand = v11.replace('"Total","2,100"', '"Total","9,999"')
check("a hand edit to the data is caught by the revision hash", any("revision hash" in p for p in hx.check_document(hand)[0]), hx.check_document(hand))
newer = v1.replace('"format":"helix","version":1', '"format":"helix","version":2')
open(T + "/newer.helix.html", "w", encoding="utf-8").write(newer)
check("a newer format version: check notes it", any("newer than this tool" in n for n in hx.check_document(newer)[1]))
rc, res = jcli("patch", "newer.helix.html", pf, "--force")
check("a newer format version cannot be patched", rc == 1 and "newer" in str(res), res)
r = cli("unpack", "Shed_v1.1.helix.html", "un"); r2 = cli("build", "un/spec.json", "rebuilt.helix.html", "--no-shrink")
check("unpack then build gives an identical file", r.returncode == 0 and r2.returncode == 0 and read(T + "/rebuilt.helix.html") == v11, r2.stdout)
sp2 = json.load(open(T + "/un/spec.json", encoding="utf-8")); sp2["tabs"][0]["blocks"][0]["md"] = "Edited by hand in the spec"; sp2["by"] = "Me"
json.dump(sp2, open(T + "/un/spec.json", "w", encoding="utf-8"))
r = cli("build", "un/spec.json", "rebuilt2.helix.html", "--no-shrink"); d12 = data_of(read(T + "/rebuilt2.helix.html"))
check("editing the spec and rebuilding makes v1.2, ids kept", d12["rev"]["label"] == "1.2" and d12["rev"]["parent"] == d11["rev"]["hash"] and hx.known_ids(hx.light_load(d12)[0]) == hx.known_ids(hx.light_load(d11)[0]) and d12["log"][-1]["by"] == "Me")
plain = cli("build", "plain.json", "plain.helix.html") if json.dump({"title": "Plain", "blocks": [{"type": "text", "text": "Hi"}]}, open(T + "/plain.json", "w")) is None else None
ph = read(T + "/plain.helix.html")
check("a document without AI Notes has no AI Notes button", "<summary>AI Notes</summary>" not in ph and '"ai":' not in ph and "Revision Log" in ph)


# ---------------------------------------------------------------- hostile content stays inert
evil = '</script><script>alert(1)</script><img src=x onerror=alert(2)> [x](javascript:alert(3)) <details open>'
json.dump({"title": "Evil", "by": evil, "ai": {"notes": evil, "work": {"task": evil, "instructions": evil, "deliverables": [evil]}},
           "log": [{"rev": 1, "label": "1", "by": evil, "summary": evil, "note": evil}], "blocks": [{"type": "markdown", "title": "T", "md": "x"}]}, open(T + "/evil.json", "w"))
r = cli("build", "evil.json", "evil.helix.html")
eh = read(T + "/evil.helix.html") if r.returncode == 0 else ""
check("hostile AI Notes, assignment and log text build into a file that passes check", r.returncode == 0 and hx.check_document(eh)[0] == [], r.stdout)
from html.parser import HTMLParser
class Scan(HTMLParser):
    bad = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k.startswith("on") or (k in ("href", "src") and (v or "").lower().startswith("javascript")): self.bad.append((tag, k))
        if tag in ("script", "img", "iframe", "details") and tag != "details" and dict(attrs).get("id") != "doc-source" and tag == "script": self.bad.append(("script", ""))
sc = Scan(); sc.feed(eh)
check("...and parsed as HTML it has no extra scripts, event handlers or javascript: links", eh and not sc.bad and eh.count("<script") == 1, sc.bad)

# ---------------------------------------------------------------- the editor
with sync_playwright() as p:
    b = launch(p)
    page = b.new_context(accept_downloads=True, viewport={"width": 1200, "height": 900}).new_page(); errs = []
    page.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" else None); page.on("pageerror", lambda e: errs.append(str(e)[:200])); page.on("dialog", lambda d: d.accept())
    page.goto("file://" + ED)
    page.evaluate("()=>{delete window.showSaveFilePicker;}")
    for name, html in (("v1", v1), ("v1.1", v11), ("major", read(T + "/major.helix.html")), ("plain", ph)):
        page.evaluate("t=>window.__pde.load(t)", html)
        check("editor reopens %s and writes it back byte for byte" % name, page.evaluate("()=>window.__pde.build()") == html)
    page.evaluate("t=>window.__pde.load(t)", v11)
    check("editor shows the AI Notes and focus/protect choices", page.evaluate("()=>document.getElementById('ai-notes').value").endswith("Claude: added a total.")
          and page.evaluate("()=>document.querySelectorAll('#ai-scope input:checked').length") == 2)
    check("editor shows the version", "v1.1" in page.inner_text("#log-sum"), page.inner_text("#log-sum"))
    # save without changes: no new revision, same name
    with page.expect_download() as dl: page.click("#btn-copy")
    s0 = dl.value; s0.save_as(T + "/ed0.helix.html")
    check("saving an unchanged document keeps its revision", data_of(read(T + "/ed0.helix.html"))["rev"] == d11["rev"] and s0.suggested_filename.endswith("_v1.1.helix.html"), s0.suggested_filename)
    page.fill("#doc-sub", "Edited in the editor"); page.click("#log-box summary"); page.fill("#rev-note", "Reworded the subtitle")
    with page.expect_download() as dl: page.click("#btn-copy")
    s1 = dl.value; s1.save_as(T + "/ed1.helix.html"); e1 = data_of(read(T + "/ed1.helix.html"))
    check("an edit and a save make v1.2 named _v1.2", e1["rev"]["label"] == "1.2" and e1["rev"]["n"] == 3 and e1["rev"]["parent"] == d11["rev"]["hash"] and s1.suggested_filename.endswith("_v1.2.helix.html"), (e1["rev"], s1.suggested_filename))
    check("the editor logs the person's note", e1["log"][-1]["summary"] == "Reworded the subtitle" and e1["log"][-1]["kind"] == "human", e1["log"][-1])
    page.fill(".title", "Garden Shed Build (edited)")
    with page.expect_download() as dl: page.click("#btn-copy")
    dl.value.save_as(T + "/ed2.helix.html"); e2 = data_of(read(T + "/ed2.helix.html"))
    check("a second save in the same session updates v1.2 instead of adding v1.3", e2["rev"]["label"] == "1.2" and len(e2["log"]) == len(e1["log"]) and e2["rev"]["hash"] != e1["rev"]["hash"], (e2["rev"], len(e2["log"])))
    check("the editor's file passes the Python check", hx.check_document(read(T + "/ed2.helix.html"))[0] == [], hx.check_document(read(T + "/ed2.helix.html")))
    page.click("#rev-new"); page.fill("#doc-sub", "Third pass"); page.check("#rev-major")
    with page.expect_download() as dl: page.click("#btn-copy")
    dl.value.save_as(T + "/ed3.helix.html"); e3 = data_of(read(T + "/ed3.helix.html"))
    check("a new version on the next save, as major: v2", e3["rev"]["label"] == "2" and e3["rev"]["parent"] == e2["rev"]["hash"], e3["rev"])
    # tick focus in the editor and confirm the saved file carries it
    page.click("#ai-box summary"); page.locator("#ai-scope input").nth(0).check()
    page.evaluate("()=>window.__pde.build()")
    check("ticking Focus in the editor updates the document's AI Notes", page.evaluate("()=>JSON.parse(window.__pde.build().match(/doc-source\">(.*?)<\\/script>/s)[1]).ai.focus.length") == 2)
    # a new document: first save is v1, logged as Created
    page.click("#btn-new"); page.click('[data-tpl="blank"]'); page.fill(".title", "Fresh")
    with page.expect_download() as dl: page.click("#btn-copy")
    f = dl.value; f.save_as(T + "/fresh.helix.html"); df_ = data_of(read(T + "/fresh.helix.html"))
    check("a new document saves as Fresh_v1 with revision 1 'Created'", f.suggested_filename.endswith("_v1.helix.html") and df_["rev"]["n"] == 1 and df_["log"][0]["summary"] == "Created", (f.suggested_filename, df_["rev"]))
    # newer format versions are refused by the editor
    msg = page.evaluate("t=>{try{window.__pde.load(t);return 'opened';}catch(e){return e.message;}}", newer)
    check("the editor refuses a newer format version", "newer than this editor" in msg, msg)
    # never printed
    page.goto("file://" + T + "/Shed_v1.1.helix.html")
    vis = page.evaluate("()=>getComputedStyle(document.querySelector('.hxbar')).display")
    page.emulate_media(media="print")
    pr = page.evaluate("()=>getComputedStyle(document.querySelector('.hxbar')).display")
    check("AI Notes and Revision Log show on screen and never print", vis == "flex" and pr == "none", (vis, pr))
    page.emulate_media(media="screen")
    check("both buttons start collapsed", page.evaluate("()=>Array.from(document.querySelectorAll('details.hx')).every(d=>!d.open)"))
    check("no editor errors", not errs, errs)
    b.close()

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
