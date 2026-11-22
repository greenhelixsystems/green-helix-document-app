#!/usr/bin/env python3
"""Rebuild this example: a research report in the Helix 1.2 report style.

    python examples/research-report/make.py

Writes Riverside-Garden-Outreach-Options_v1.helix.html. All content is invented; the id and time are fixed for reproducible output.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "..", "tools", "helix.py")
r = subprocess.run([sys.executable, "-I", TOOL, "build", "spec.json", "Riverside-Garden-Outreach-Options_v1.helix.html", "--now", "2026-11-21T18:00:00Z"],
                   capture_output=True, text=True, cwd=HERE)
print(r.stdout + r.stderr, end="")
sys.exit(r.returncode)
