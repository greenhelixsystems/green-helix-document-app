"""The guide must work when followed literally: extraction, the example spec, the Markdown table, shrink, round trip."""
import hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from common import *
T = work("guidetest"); shutil.rmtree(T, ignore_errors=True); os.makedirs(T + "/inputs")
ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
guide = open(GUIDE, encoding="utf-8").read()

# 1. extraction snippet, copied from the guide and run as written
snip = re.search(r"```python\n(import re\nguide = open\(\"HELIX-guide.md\".*?)\n```", guide, re.S).group(1)
shutil.copy(GUIDE, T + "/HELIX-guide.md")
subprocess.run([sys.executable, "-I", "-c", snip], cwd=T, check=True)
check("extraction snippet reproduces helix.py exactly", open(T + "/helix.py", encoding="utf-8").read() == open(TOOL, encoding="utf-8").read())
HELIX = T + "/helix.py"
sp = importlib.util.spec_from_file_location("hlx", HELIX); hlx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hlx)
run = lambda *a: subprocess.run([sys.executable, "-I", HELIX] + list(a), capture_output=True, text=True, cwd=T)

# 2. the spec example in section 4 builds as written
spec_text = re.search(r"## 4\. The spec.*?```json\n(.*?)\n```", guide, re.S).group(1)
open(T + "/spec.json", "w", encoding="utf-8").write(spec_text)
shutil.copy(INPUTS + "/small.jpg", T + "/inputs/kitchen-before.jpg"); shutil.copy(INPUTS + "/small-report.pdf", T + "/inputs/quote-north-build.pdf"); shutil.copy(INPUTS + "/sample-notes.docx", T + "/inputs/budget.xlsx")
r = run("build", "spec.json", "example.helix.html"); check("the section 4 example builds and prints OK", r.returncode == 0 and r.stdout.startswith("OK"), r.stdout)
html = open(T + "/example.helix.html", encoding="utf-8").read(); d = hlx.read_document(html)[0]
check("example: two tabs, status, fingerprints and About as the guide describes", len(d["tabs"]) == 2 and d["options"]["status"] == "review" and "SHA-256 <code>" in html and 'class="about"' in html)
check("example: download name override and the note are applied", 'download="Renovation budget.xlsx"' in html and "Working budget" in html)
check("example: data block comes first in the file, before the stylesheet", html.index('id="doc-source"') < html.index("<style>") and html.index('id="doc-source"') < 4000, html.index('id="doc-source"'))
check("example: the data block says format helix, version %d" % hlx.FORMAT_VERSION, json.loads(re.search(r'id="doc-source">(.*?)</script>', html, re.S).group(1))["version"] == hlx.FORMAT_VERSION)

# 3. unpack gives what section 3 lists, and unpack -> build keeps the document
r = run("unpack", "example.helix.html", "un"); names = sorted(os.listdir(T + "/un"))
check("unpack writes exactly the files section 3 lists", names == ["SHA256SUMS.txt", "content.md", "files", "images", "spec.json"], names)
sums = open(T + "/un/SHA256SUMS.txt").read().strip().split("\n")
check("SHA256SUMS.txt lines are '<hash>  <path>' and verify", all(re.fullmatch(r"[0-9a-f]{64}  \S.*", l) and hashlib.sha256(open(T + "/un/" + l.split("  ", 1)[1], "rb").read()).hexdigest() == l[:64] for l in sums), sums)
r = run("build", "un/spec.json", "again.helix.html"); r2 = run("unpack", "again.helix.html", "un2")
check("edit-and-rebuild round trip keeps content.md", r.returncode == 0 and open(T + "/un/content.md", encoding="utf-8").read() == open(T + "/un2/content.md", encoding="utf-8").read(), r.stdout)
check("check passes on both files", run("check", "example.helix.html").returncode == 0 and run("check", "again.helix.html").returncode == 0)

# 4. every claim in the Markdown table of section 6
md = hlx.md_render
claims = [
 ("# T / ## T", md("# A\n\n## B"), "<h3>A</h3><h4>B</h4>"), ("heading cap", md("###### A"), "<h6>A</h6>"), ("single newline kept", md("a\nb"), "<p>a<br>b</p>"),
 ("emphasis forms", md("*a* _b_ **c** ~~d~~ `e`"), "<p><em>a</em> <em>b</em> <strong>c</strong> <del>d</del> <code>e</code></p>"),
 ("task list", md("- [ ] a\n- [x] b"), '<ul class="checks"><li>a</li><li class="done"><span class="vh">Done: </span>b</li></ul>'),
 ("numbered 1)", md("1) a\n2) b"), "<ol><li>a</li><li>b</li></ol>"), ("quote", md("> q"), "<blockquote><p>q</p></blockquote>"),
 ("fence with language", md("```py\nx<1\n```"), '<pre data-lang="py"><code>x&lt;1</code></pre>'), ("divider", md("---"), "<hr>"),
 ("table alignment", md("|a|b|\n|:-|--:|\n|x|y|"), '<div class="scroll"><table><thead><tr><th scope="col">a</th><th class="num" scope="col">b</th></tr></thead><tbody><tr><td>x</td><td class="num">y</td></tr></tbody></table></div>'),
 ("raw html shown as text", md("<b>x</b>"), "<p>&lt;b>x&lt;/b></p>".replace("&lt;/b>", "&lt;/b&gt;").replace("&lt;b>", "&lt;b&gt;")),
 ("image syntax becomes plain text without a link scheme", md("![alt](javascript:x)"), "<p>alt</p>"),
 ("image syntax with https becomes a link", md("![alt](https://e.com/i.png)"), '<p><a href="https://e.com/i.png" target="_blank" rel="noopener noreferrer">alt</a></p>'),
 ("schemeless link target gets https", md("[s](example.org)"), '<p><a href="https://example.org" target="_blank" rel="noopener noreferrer">s</a></p>'),
 ("javascript and relative links lose the link", md("[a](javascript:x) [b](/p) [c](./p)"), "<p>a b c</p>"), ("anchor and mailto kept", md("[a](#x) [b](mailto:a@b.c)"), None),
 ("bare domain is not linked", md("see example.org"), "<p>see example.org</p>"), ("bare https is linked", md("see https://e.com"), '<p>see <a href="https://e.com" target="_blank" rel="noopener noreferrer">https://e.com</a></p>'),
 ("escapes", md("\\*x\\*"), "<p>*x*</p>"), ("setext is not a heading", md("Title\n====="), "<p>Title<br>=====</p>"), ("indented code is not code", md("    code"), "<p>code</p>"),
]
for name, got, want in claims:
    if want is None: check("claim: " + name, 'href="#x"' in got and 'href="mailto:a@b.c"' in got, got)
    else: check("claim: " + name, got == want, got)
# text block html rules from section 7
claims7 = [("b/i/div", hlx.sanitize("<b>x</b><i>y</i><div>z</div>"), "<strong>x</strong><em>y</em><p>z</p>"), ("script dropped, other tags unwrapped", hlx.sanitize("<script>a</script><h1>t</h1><span>s</span>"), "ts"),
           ("bare link target gets https", hlx.sanitize("<a href='example.org'>x</a>"), '<a href="https://example.org" target="_blank" rel="noopener noreferrer">x</a>')]
for name, got, want in claims7: check("section 7: " + name, got == want, got)

# 5. photo shrink: scaled in Images blocks, never in Files blocks, and --no-shrink keeps bytes
from PIL import Image
import random
random.seed(1); im = Image.new("RGB", (3200, 2400)); px = im.load()
for x in range(0, 3200, 4):
    for y in range(0, 2400, 4): px[x, y] = (random.randint(0, 255),) * 3
im = im.resize((3200, 2400)); im.save(T + "/inputs/big.jpg", quality=92); big = open(T + "/inputs/big.jpg", "rb").read()
json.dump({"title": "Shrink", "blocks": [{"type": "images", "title": "I", "items": ["inputs/big.jpg"]}, {"type": "files", "title": "F", "items": ["inputs/big.jpg"]}]}, open(T + "/shrink.json", "w"))
run("build", "shrink.json", "shrunk.helix.html"); d, a, *_ = hlx.read_document(open(T + "/shrunk.helix.html", encoding="utf-8").read())
import base64, io
imgb = [base64.b64decode(v["b64"]) for k, v in a.items() if k in [it["asset"] for it in d["tabs"][0]["blocks"][0]["items"]]][0]
filb = [base64.b64decode(v["b64"]) for k, v in a.items() if k in d["tabs"][0]["blocks"][1]["items"]][0]
check("photo in an Images block is scaled to 1600 px", max(Image.open(io.BytesIO(imgb)).size) == 1600 and len(imgb) < len(big), len(imgb))
check("the same file in a Files block is untouched", filb == big)
run("build", "shrink.json", "full.helix.html", "--no-shrink"); d, a, *_ = hlx.read_document(open(T + "/full.helix.html", encoding="utf-8").read())
check("--no-shrink keeps the photo byte for byte", all(base64.b64decode(v["b64"]) == big for v in a.values()))
print("\n%d/%d checks passed" % (sum(ok), len(ok))); raise SystemExit(0 if all(ok) else 1)
