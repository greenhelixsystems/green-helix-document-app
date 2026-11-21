"""The example in examples/project-handoff and the snippets in HELIX-WORKFLOW.md do what they say."""
import json, os, re, shutil, subprocess, sys, importlib.util
from common import *

T = work("examples")
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
sp = importlib.util.spec_from_file_location("helix", TOOL); hx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hx)
EX = str(ROOT / "examples" / "project-handoff")
V1, V11 = "Community-Garden-Launch_v1.helix.html", "Community-Garden-Launch_v1.1.helix.html"
read = lambda p: open(p, encoding="utf-8").read()

# the committed example is exactly what make.py produces
copy = os.path.join(T, "ex")
shutil.rmtree(copy, ignore_errors=True)
shutil.copytree(EX, copy)
os.makedirs(os.path.join(T, "tools"), exist_ok=True)
shutil.copy(TOOL, os.path.join(T, "tools", "helix.py"))
os.makedirs(os.path.join(T, "examples"), exist_ok=True)
shutil.rmtree(os.path.join(T, "examples", "project-handoff"), ignore_errors=True)
shutil.move(copy, os.path.join(T, "examples", "project-handoff"))
gen = os.path.join(T, "examples", "project-handoff")
r = subprocess.run([sys.executable, os.path.join(gen, "make.py")], capture_output=True, text=True)
check("make.py runs and its return passes return-check", r.returncode == 0 and '"ok": true' in r.stdout, r.stdout + r.stderr)
for f in (V1, V11, "patch.json", "return.json"):
    check("the committed %s matches make.py's output" % f, read(os.path.join(gen, f)) == read(os.path.join(EX, f)))
for f in (V1, V11):
    check("%s passes check" % f, hx.check_document(read(os.path.join(EX, f)))[0] == [])
d1 = json.loads(re.search(r'id="doc-source">(.*?)</script>', read(os.path.join(EX, V1)), re.S).group(1))
check("the example maps project data to readable blocks, not collapsibles", "collapsible" not in [b["type"] for t in d1["tabs"] for b in t["blocks"]]
      and [b["type"] for t in d1["tabs"] for b in t["blocks"]].count("heading") == 2)
check("the example has AI Notes, focus, protect and an assignment", all(k in d1["ai"] for k in ("notes", "focus", "protect", "work")))

# the no-helix.py snippet in HELIX-WORKFLOW.md prints the AI Notes and only the focus block
wf = read(str(ROOT / "guide" / "HELIX-WORKFLOW.md"))
snippet = re.search(r"```python\n(.*?)```", wf, re.S).group(1).replace("Name_v1.2.helix.html", os.path.join(EX, V1).replace("\\", "/"))
r = subprocess.run([sys.executable, "-I", "-c", snippet], capture_output=True, text=True)
lines = r.stdout.strip().split("\n")
check("the workflow snippet prints the AI Notes, then only the focus block", r.returncode == 0 and len(lines) == 2 and json.loads(lines[1])["title"] == "Budget" and '"focus"' in lines[0], r.stdout[:300] + r.stderr)
check("the workflow guide and quickstart are short", len(wf) < 6000 and len(read(str(ROOT / "guide" / "HELIX-QUICKSTART.md"))) < 2000, (len(wf),))
check("no Green Helix business names in the public workflow template", not re.search(r"Dashboard|Command Cent|financial|Green Helix Financial", wf))

print("\n%d/%d checks passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
