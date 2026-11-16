#!/usr/bin/env python3
"""Run every suite and print one line each. Exit code 0 only if all pass.

    python tests/run_all.py

Needs: Python 3.8+, Playwright with a Chromium (pip install playwright pillow; playwright install chromium),
Node.js (the build check) and Pillow. Set HELIX_CHROME to use a browser you already have.
"""
import glob, os, re, subprocess, sys, time

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
suites = [("build is up to date", [sys.executable, os.path.join(root, "build", "build.py"), "--check"])]
suites += [(os.path.basename(f)[5:-3].replace("_", " "), [sys.executable, f]) for f in sorted(glob.glob(os.path.join(here, "test_*.py")))]
only = sys.argv[1:]
failed = 0
for name, cmd in suites:
    if only and not any(o in name or o in cmd[-1] for o in only):
        continue
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=here)
    out = r.stdout + r.stderr
    m = re.findall(r"(\d+/\d+ checks passed|cases: .*differences: \d+|OK: .*)", out)
    ok = r.returncode == 0
    failed += not ok
    print("%-4s %-38s %5.1fs  %s" % ("PASS" if ok else "FAIL", name, time.time() - t0, m[-1] if m else ""))
    if not ok:
        print("\n".join("     " + l for l in out.strip().split("\n")[-15:]))
print("\nAll suites passed." if not failed else "\n%d suite(s) failed." % failed)
sys.exit(1 if failed else 0)
