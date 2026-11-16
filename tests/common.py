"""Shared paths and helpers for the test suites. Nothing here depends on where the repo is checked out."""
import os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ED = str(ROOT / "editor" / "green-helix-document-editor.html")
WEB = str(ROOT / "mobile")
TOOL = str(ROOT / "tools" / "helix.py")
GUIDE = str(ROOT / "guide" / "HELIX-guide.md")
SRC_TOOL = str(ROOT / "src" / "tool")
FIX = str(ROOT / "tests" / "fixtures")
WORK_ROOT = ROOT / "tests" / ".work"
INPUTS = str(WORK_ROOT / "inputs")
SRC = INPUTS


def work(name):
    """A scratch folder for one suite (ignored by git)."""
    p = WORK_ROOT / name
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def make_inputs():
    """Committed small files plus generated larger ones, all in one folder the suites read from."""
    os.makedirs(INPUTS, exist_ok=True)
    for f in os.listdir(FIX + "/inputs"):
        shutil.copy(FIX + "/inputs/" + f, INPUTS + "/" + f)
    big = INPUTS + "/medium-report.pdf"
    if not os.path.exists(big):
        import random
        rng = random.Random(1250845)
        body = bytes(rng.getrandbits(8) for _ in range(1250000))
        pdf = (b"%PDF-1.3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
               b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n"
               b"4 0 obj<</Length " + str(len(body)).encode() + b">>stream\n" + body + b"\nendstream\nendobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
        open(big, "wb").write(pdf)


make_inputs()


def launch(p):
    """Start Chromium. Set HELIX_CHROME to a browser binary to use your own; otherwise Playwright's Chromium, then Chrome."""
    exe = os.environ.get("HELIX_CHROME")
    if exe:
        return p.chromium.launch(executable_path=exe, headless=True)
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        for name in ("google-chrome", "chromium", "chromium-browser"):
            path = shutil.which(name)
            if path:
                return p.chromium.launch(executable_path=path, headless=True)
        raise
