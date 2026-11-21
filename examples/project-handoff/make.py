#!/usr/bin/env python3
"""Rebuild this example: a project exported as a readable Helix document, revised by a second AI, and handed back.

    python examples/project-handoff/make.py

Writes Community-Garden-Launch_v1.helix.html, patch.json and Community-Garden-Launch_v1.1.helix.html.
The revised file is the whole handback: its newest Revision Log entry is the reviewer's report.
Everything here is invented example data. The id and times are fixed so the files are reproducible.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "tools", "helix.py")
V1, V11 = "Community-Garden-Launch_v1.helix.html", "Community-Garden-Launch_v1.1.helix.html"


def run(*args):
    r = subprocess.run([sys.executable, "-I", TOOL] + list(args), capture_output=True, text=True, cwd=HERE)
    if r.returncode:
        sys.exit("helix.py %s failed:\n%s%s" % (args[0], r.stdout, r.stderr))
    return r.stdout


def data_of(name):
    import re
    return json.loads(re.search(r'id="doc-source">(.*?)</script>', open(os.path.join(HERE, name), encoding="utf-8").read(), re.S).group(1))


# 1. The app's project data, mapped to a conventional document (see section 5 of HELIX-guide.md).
spec = json.load(open(os.path.join(HERE, "spec.json"), encoding="utf-8"))
run("build", "spec.json", V1, "--now", "2026-11-21T15:00:00Z")

# 2. A second AI reads only its focus (outline, get --focus) and writes a patch against the base it read.
focus = json.loads(run("get", V1, "--focus"))
budget = focus["blocks"][0]
patch = {
    "helixPatch": 1, "doc": focus["id"], "base": focus["base"],
    "ops": [
        {"op": "set", "id": budget["id"], "rows": budget["rows"] + [["Contingency (10%)", "172"], ["Total", "1,892"]]},
        {"op": "ai", "notes_append": "## From the reviewer AI (v1.1)\n\nAdded a 10% contingency and a total to the budget. "
                                     "Open question: does the water line estimate include the 40 ft run in the site notes?"},
    ],
    "log": {"by": "Reviewer AI", "kind": "ai", "summary": "Added a 10% contingency and a total to the budget.", "status": "submitted",
            "questions": ["Does the water line estimate include the 40 ft run in the site notes?"],
            "next": "The project lead confirms the water line estimate.", "review": True},
}
json.dump(patch, open(os.path.join(HERE, "patch.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
out = json.loads(run("patch", V1, "patch.json", "--now", "2026-11-21T16:30:00Z"))

# 3. The receiver reads the report from the returned file itself.
print(run("return-check", "--doc", V11, "--base", V1))
