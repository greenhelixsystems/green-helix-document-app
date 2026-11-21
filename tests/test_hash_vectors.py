"""Revision-hash test vectors (docs/hash-vectors.json): helix.py and the editor compute the same canonical JSON and SHA-256.

    python tests/test_hash_vectors.py           check the committed vectors
    python tests/test_hash_vectors.py --write   regenerate them

Other writers (for example a TypeScript exporter) should reproduce every "canonical" string and "sha256" exactly.
"""
import importlib.util, json, os, sys
from playwright.sync_api import sync_playwright
from common import *

ok = []
def check(name, cond, extra=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)[:300]) if extra != "" else ""))
sp = importlib.util.spec_from_file_location("helix", TOOL); hx = importlib.util.module_from_spec(sp); sp.loader.exec_module(hx)
OUT = str(ROOT / "docs" / "hash-vectors.json")
SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
OPT = {"toc": False, "accent": "green", "footer": {"on": False, "author": "", "version": "", "date": ""}, "logo": "", "status": "", "fingerprints": False, "about": True}

# Keys are deliberately out of order: the canonical form sorts them.
cases = [
    ("empty document", "One tab, no blocks, default options.",
     {"title": "", "subtitle": "", "options": OPT, "tabs": [{"id": "a1b2c3d4e5f6g", "title": "", "blocks": []}], "assets": {}}),
    ("typical project", "Heading, Markdown, checklist, table and a files block with an attachment.",
     {"tabs": [{"title": "Plan", "id": "a1b2c3d4e5f6g", "blocks": [
         {"type": "heading", "id": "a2b3c4d5e6f7h", "text": "Phase 1"},
         {"id": "a3b4c5d6e7f8i", "type": "markdown", "title": "1. Site", "half": False, "md": "Level the ground.\n\n- Gravel"},
         {"id": "a4b5c6d7e8f9j", "type": "checklist", "title": "Checklist", "half": False, "items": [{"text": "Lease", "done": True}, {"text": "Mark beds", "done": False}]},
         {"id": "a5b6c7d8e9f0k", "type": "table", "title": "Budget", "half": True, "rows": [["Item", "Cost"], ["Gravel", "300"]]},
         {"id": "a6b7c8d9e0f1l", "type": "files", "title": "Files", "half": False, "items": ["a9z8y7x6w5v4u"], "desc": True, "notes": {"a9z8y7x6w5v4u": "Quote"}}]}],
      "title": "Garden", "subtitle": "Plan", "options": dict(OPT, toc=True, status="draft", fingerprints=True), "assets": {"a9z8y7x6w5v4u": SHA}}),
    ("text that needs escaping", "Quotes, backslashes, control characters, <, U+2028, DEL, accents and emoji.",
     {"title": "Café ☕ \U0001F600 \"q\" \\ <script>", "subtitle": "tab\there\nnew line \u0001 \u007f   end",
      "options": OPT, "tabs": [{"id": "a1b2c3d4e5f6g", "title": "éè", "blocks": [{"id": "a2b3c4d5e6f7h", "type": "callout", "title": "", "half": False, "tone": "warning", "text": "a\r\nb"}]}], "assets": {}}),
    ("with AI Notes", "ai is included only when it has content; work fields are pruned of empty values.",
     {"ai": {"notes": "## For the next AI\nRevise **Budget** only.", "focus": ["a2b3c4d5e6f7h"], "protect": ["a1b2c3d4e5f6g"],
             "work": {"task": "T-1", "assignee": "Reviewer AI", "status": "assigned", "targets": ["a2b3c4d5e6f7h"], "done": ["Total row present"]}},
      "title": "Notes", "subtitle": "", "options": OPT, "assets": {},
      "tabs": [{"id": "a0a0a0a0a0a0a", "title": "", "blocks": [
          {"id": "a1b2c3d4e5f6g", "type": "markdown", "title": "Goal", "half": False, "md": "Fixed."},
          {"id": "a2b3c4d5e6f7h", "type": "table", "title": "Budget", "half": False, "rows": [["Item", "Cost"], ["", ""]]}]}]}),
]

vectors = []
for name, note, content in cases:
    canon = hx._canon(content)
    vectors.append({"name": name, "note": note, "content": content, "canonical": canon, "sha256": hx.hash_of(content)})
doc = {"about": "Test vectors for the Helix revision hash (rev.hash). For each entry, the canonical JSON of 'content' "
                "(object keys sorted by UTF-16 code unit, no whitespace, strings escaped as JavaScript's JSON.stringify does, "
                "non-ASCII written as UTF-8) must equal 'canonical', and its SHA-256 must equal 'sha256'. 'content' is "
                "{title, subtitle, options, tabs, assets: {asset id: sha256}, ai (only when not empty)} of the document in "
                "canonical form; 'helix.py hash FILE' shows whether a file's data block is in that form.",
       "vectors": vectors}
text = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
if "--write" in sys.argv:
    open(OUT, "w", encoding="utf-8", newline="").write(text); print("wrote " + OUT); sys.exit(0)

check("docs/hash-vectors.json is up to date (run with --write after changing the hash)", os.path.exists(OUT) and open(OUT, encoding="utf-8").read() == text)
committed = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else doc
check("key order in the input does not change the hash", hx.hash_of(dict(reversed(list(cases[1][2].items())))) == vectors[1]["sha256"])
with sync_playwright() as p:
    b = launch(p); page = b.new_page(); page.goto("file://" + ED)
    for v in committed["vectors"]:
        js = page.evaluate("v=>{var c=window.__pde.canon(v.content);return [c, window.__pde.sha(new TextEncoder().encode(c))];}", v)
        check("editor reproduces '%s'" % v["name"], js[0] == v["canonical"] and js[1] == v["sha256"], js[1])
        check("helix.py reproduces '%s'" % v["name"], hx._canon(v["content"]) == v["canonical"] and hx.hash_of(v["content"]) == v["sha256"])
    b.close()
print("\n%d/%d checks passed" % (sum(ok), len(ok)))
sys.exit(0 if all(ok) else 1)
