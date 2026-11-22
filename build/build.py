#!/usr/bin/env python3
"""Build everything from src/ into the folders people download from.

    python build/build.py          write editor/, mobile/, tools/helix.py and guide/HELIX-guide.md
    python build/build.py --check  rebuild into memory and fail if the committed files differ
    python build/build.py --dist   also write dist/ (the files attached to a GitHub release)

Needs: Python 3.8+, Pillow (draws the home-screen icons) and Node.js (reads constants out of the editor source).
"""
import base64, hashlib, io, json, os, re, subprocess, sys, tempfile, zipfile
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
VERSION = open(P("VERSION")).read().strip()
SHORT = ".".join(VERSION.split(".")[:2])
rd = lambda p: open(p, encoding="utf-8").read()
OUTPUTS = {}  # path (relative to ROOT, with /) -> bytes


def emit(rel, data):
    OUTPUTS[rel] = data.encode("utf-8") if isinstance(data, str) else data


# ---------------------------------------------------------------- editor
src = rd(P("src", "editor.src.html")).replace("__VERSION__", SHORT)
m = re.search(r"<script>(.*)</script>", src, re.S)
digest = base64.b64encode(hashlib.sha256(m.group(1).encode("utf-8")).digest()).decode()
logo = "data:image/png;base64," + base64.b64encode(open(P("src", "assets", "logo.png"), "rb").read()).decode()
assert src.count("__LOGO__") == 2
standalone = src.replace("'__HASH__'", "'sha256-%s'" % digest).replace("__LOGO__", logo)
assert standalone.count("sha256-") == 1
emit("editor/green-helix-document-editor.html", standalone)

# ---------------------------------------------------------------- mobile (hosted copy)
csp_old = "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'sha256-%s'; base-uri 'none'; form-action 'none'" % digest
csp_new = "default-src 'none'; img-src 'self' data: blob:; style-src 'unsafe-inline'; script-src 'sha256-%s'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'" % digest
assert standalone.count(csp_old) == 1
head = """<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1f2226" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Helix Docs">
<link rel="apple-touch-icon" href="apple-touch-icon.png">"""
vp = '<meta name="viewport" content="width=device-width, initial-scale=1">'
assert standalone.index(vp) < standalone.index("<title>Green Helix Document Editor</title>")
hosted = standalone.replace(csp_old, csp_new).replace(vp, head, 1)
emit("mobile/index.html", hosted)
emit("mobile/manifest.json", json.dumps({
    "name": "Green Helix Document Editor", "short_name": "Helix Docs",
    "description": "Create single-file documents with text, images and attached files. Works offline; nothing is uploaded.",
    "start_url": "./", "scope": "./", "display": "standalone",
    "background_color": "#f6f5f1", "theme_color": "#4B8747",
    "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
              {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
}, indent=2) + "\n")
emit("mobile/sw.js", """// Offline cache for the editor. Online: always fetch the newest copy. Offline: use the saved copy.
const CACHE = 'green-helix-document-editor';
const FILES = ['./', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }).then((r) => r || caches.match('index.html')))
  );
});
""")


def icon(size):
    S = size * 4
    im = Image.new("RGB", (S, S), "#4B8747")
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = S * 0.27, S * 0.20, S * 0.73, S * 0.80
    d.rounded_rectangle([x0, y0, x1, y1], radius=S * 0.05, fill="#ffffff")
    pad = S * 0.055
    bx0, bx1 = x0 + pad, x1 - pad
    d.rounded_rectangle([bx0, y0 + pad, bx1, y0 + pad + S * 0.13], radius=S * 0.022, fill="#9fd09b")
    d.rounded_rectangle([bx0, y0 + pad + S * 0.165, bx0 + (bx1 - bx0) * 0.46, y0 + pad + S * 0.30], radius=S * 0.022, fill="#dcecd9")
    d.rounded_rectangle([bx0 + (bx1 - bx0) * 0.54, y0 + pad + S * 0.165, bx1, y0 + pad + S * 0.30], radius=S * 0.022, fill="#dcecd9")
    d.rounded_rectangle([bx0, y0 + pad + S * 0.335, bx1, y0 + pad + S * 0.375], radius=S * 0.014, fill="#D1A33A")
    d.rounded_rectangle([bx0, y0 + pad + S * 0.41, bx0 + (bx1 - bx0) * 0.62, y0 + pad + S * 0.45], radius=S * 0.014, fill="#dcecd9")
    out = io.BytesIO()
    im.resize((size, size), Image.LANCZOS).save(out, "PNG")
    return out.getvalue()


emit("mobile/icon-512.png", icon(512))
emit("mobile/icon-192.png", icon(192))
emit("mobile/apple-touch-icon.png", icon(180))

# ---------------------------------------------------------------- tool: constants come straight from the editor source
ed = src


def between(a, b):
    i = ed.index(a)
    return ed[i:ed.index(b, i)]


js = ";\n".join([between("var ACCENTS=", "var DUP_ICON="), between("var LABEL=", "var STATUS="), between("var STATUS=", "var DOC_CSS="), between("var DOC_CSS=", "var DOC_CSP="),
                 between("var DOC_CSP=", "\n\nvar mdTarget"), between("var ABOUT_AI=[", "function aboutHtml")]).replace(";;", ";")
js += "\nprocess.stdout.write(JSON.stringify({ACCENTS:ACCENTS,STATUS:STATUS,TONES:TONES,CHIP:CHIP,ICON_MAX:ICON_MAX,LABEL:LABEL,SPEC:SPEC,WORK:WORK,KINDS:KINDS,DOC_CSS:DOC_CSS,DOC_CSP:DOC_CSP,ABOUT_AI:ABOUT_AI,ABOUT_JSON:ABOUT_JSON}));"
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
    fh.write(js)
r = subprocess.run(["node", fh.name], capture_output=True, text=True)
os.unlink(fh.name)
if r.returncode:
    sys.exit("node failed: " + r.stderr)
C = json.loads(r.stdout)
gen = re.search(r'content="(Green Helix Document Editor [0-9.]+)"', ed).group(1)
ver = int(re.search(r"\{format:'helix',version:(\d+),spec:SPEC", ed).group(1))
lit = lambda x: json.dumps(x, ensure_ascii=True)
tool_head = '''#!/usr/bin/env python3
"""helix.py - build, unpack and check Helix documents.

A Helix document is one self-contained .helix.html file: it opens in any browser, runs no scripts,
embeds its images and attachments, and carries its own editing data so the Green Helix Document
Editor can reopen it. This tool makes and reads those files without the editor.

    python helix.py build spec.json output.helix.html
    python helix.py unpack document.helix.html outfolder
    python helix.py check document.helix.html
    python helix.py md notes.md
    python helix.py outline | get | asset | patch | diff | return-check ...   (run with no arguments for details)

Format version %d (Helix %s). Standard library only (Pillow is optional, for scaling large photos).
Licensed under the Apache License 2.0. "Green Helix" and its logo are not licensed; see NOTICE.md.
"""
import re

FORMAT_VERSION = %d
GENERATOR = %s
DOC_CSP = %s
ACCENTS = %s
STATUS = %s
TONES = %s
CHIP = %s
ICON_MAX = %s
SPEC = %s
LABEL = %s
WORK = %s
KINDS = %s
ABOUT_AI = %s
ABOUT_JSON = %s
DOC_CSS = %s

''' % (ver, C["SPEC"], ver, lit(gen), lit(C["DOC_CSP"]), lit(C["ACCENTS"]), lit(C["STATUS"]), lit(C["TONES"]), lit(C["CHIP"]), lit(C["ICON_MAX"]), lit(C["SPEC"]), lit(C["LABEL"]), lit(C["WORK"]), lit(C["KINDS"]), lit(C["ABOUT_AI"]), lit(C["ABOUT_JSON"]), lit(C["DOC_CSS"]))
parts = [rd(P("src", "tool", "%s_part.py" % n)) for n in ("md", "html", "core", "ai", "cli")]
tool = (tool_head + "\n\n".join(parts)).replace("\n\n\n\n", "\n\n\n")
assert all(ord(c) < 128 for c in tool)
emit("tools/helix.py", tool)

# ---------------------------------------------------------------- guide
names = {"green": "white", "gold": "dark", "crimson": "white", "plum": "white", "slate": "white"}
rows = "\n".join("| %s | `%s` | %s | `%s` |" % (k, v[1], names[k], v[3]) for k, v in C["ACCENTS"].items())
g = rd(P("src", "guide.tpl.md")).replace("__VERSION__", str(ver)).replace("__SPEC__", C["SPEC"]).replace("__EDITOR__", SHORT).replace("__GENERATOR__", gen).replace("__ACCENT_ROWS__", rows).replace("__SCRIPT__", tool.rstrip("\n"))
emit("guide/HELIX-guide.md", g)
for src_name, out_name in (("workflow.tpl.md", "HELIX-WORKFLOW.md"), ("quickstart.tpl.md", "HELIX-QUICKSTART.md")):
    emit("guide/" + out_name, rd(P("src", src_name)).replace("__SPEC__", C["SPEC"]))

# ---------------------------------------------------------------- release files
dist = {}
dist["dist/green-helix-document-editor-%s.html" % VERSION] = OUTPUTS["editor/green-helix-document-editor.html"]
dist["dist/helix.py"] = OUTPUTS["tools/helix.py"]
dist["dist/HELIX-guide.md"] = OUTPUTS["guide/HELIX-guide.md"]
dist["dist/HELIX-WORKFLOW.md"] = OUTPUTS["guide/HELIX-WORKFLOW.md"]
dist["dist/HELIX-QUICKSTART.md"] = OUTPUTS["guide/HELIX-QUICKSTART.md"]
zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(k for k in OUTPUTS if k.startswith("mobile/")):
        zi = zipfile.ZipInfo("green-helix-document-editor-web/" + rel[len("mobile/"):], date_time=(2026, 11, 16, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, OUTPUTS[rel])
dist["dist/green-helix-document-editor-web-%s.zip" % VERSION] = zbuf.getvalue()

if __name__ == "__main__":
    if "--check" in sys.argv:
        bad = [k for k, v in OUTPUTS.items() if not os.path.exists(P(k)) or open(P(k), "rb").read() != v]
        print("OK: committed files match src/" if not bad else "OUT OF DATE (run python build/build.py): " + ", ".join(bad))
        sys.exit(1 if bad else 0)
    todo = dict(OUTPUTS)
    if "--dist" in sys.argv:
        todo.update(dist)
    for k, v in todo.items():
        os.makedirs(os.path.dirname(P(k)), exist_ok=True)
        open(P(k), "wb").write(v)
    print("built %s: editor %d bytes, mobile %d files, helix.py %d bytes, guide %d bytes%s" % (
        VERSION, len(OUTPUTS["editor/green-helix-document-editor.html"]), sum(1 for k in OUTPUTS if k.startswith("mobile/")),
        len(OUTPUTS["tools/helix.py"]), len(OUTPUTS["guide/HELIX-guide.md"]), " + dist/" if "--dist" in sys.argv else ""))
