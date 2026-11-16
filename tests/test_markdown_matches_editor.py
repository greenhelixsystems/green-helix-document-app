"""Differential test: Python md_render must equal the editor's JavaScript mdRender, byte for byte."""
import json, random, sys
from playwright.sync_api import sync_playwright
from common import *
sys.setrecursionlimit(30000)
src = "import re\n" + open(SRC_TOOL + "/md_part.py", encoding="utf-8").read()
ns = {}; exec(src, ns); py = ns["md_render"]
random.seed(20261115)

TOK = ["# ", "## ", "###### ", "####### ", "- ", "* ", "+ ", "1. ", "2) ", "10. ", "007. ", "> ", ">", "```", "~~~", "````", "---", "***", "___", "- - -",
       "|", " | ", "|---|", "| --- | :-: |", ":--", "--:", "**", "*", "_", "__", "~~", "~", "`", "``", "\\", "\\|", "\\*", "[", "]", "(", ")", "![", "](", "<", ">", "&", '"', "'",
       "http://a.com/x", "https://b.org/y(z)", "www.x.com", "mailto:a@b.c", "javascript:alert(1)", "<https://c.com>", "[t](https://d.com)", "[t](x.com)", "[t](/p)", "[t](#a)", "![i](https://e.com/i.png)",
       "<script>x</script>", "<img src=x onerror=y>", "&amp;", "[ ]", "[x]", "[X] ", "- [ ] ", "- [x] ",
       "word", "Word", "snake_case_word", "a", "b", "1", "2.5", "$3,400", "-7%", ".5", "foo bar", "é", "日本", "😀", "a😀b", " ", " ", "﻿", "　", "\x1f", "\x0b", "ſ", "K",
       " ", "  ", "    ", "\t", "\n", "\n", "\n\n", "\n\n", "\r\n", "\r", "   ", "H", "HTTP://UP.com", "hTtPs://m.com/a.", "ſ"]

def rnd_doc(maxn):
    return "".join(random.choice(TOK) for _ in range(random.randint(1, maxn)))

seeds = [
 "# Title\n\nSome *emphasis*, **strong**, ~~gone~~ and `code`.\n\n- one\n- two\n  - nested\n  - nested two\n- three\n\n1. a\n2. b\n\n> quote\n> more\n\n```py\nprint('x')\n```\n\n| a | b | c |\n|:--|:-:|--:|\n| 1 | 2 | 3 |\n| x | y | z |\n\nSee https://example.com/a_b_c). Done.",
 "- [ ] todo\n- [x] done\n\n* [X] big X\n\n1. one\n\n   para in item\n\n2. two\n",
 "Hard  \nbreak\\\nnext line\n\n***bold italic*** _x_ __y__ snake_case_here a*b*c",
 "| a | b |\n|---|---|\n| 1 |\n| 2 | 3 | 4 |\n\n|a|b|\n|-|-|\n|$1,000|50%|\n|-3|.5|",
]
cases = list(seeds)
for _ in range(9000): cases.append(rnd_doc(14))
for _ in range(5000): cases.append(rnd_doc(45))
for _ in range(1500): cases.append(rnd_doc(160))
# mutations of seeds
for s in seeds:
    for _ in range(600):
        L = list(s)
        for _ in range(random.randint(1, 5)):
            op = random.random(); i = random.randrange(len(L) + 1)
            if op < .4 and L: L.pop(min(i, len(L) - 1))
            elif op < .8: L.insert(i, random.choice(TOK))
            elif L: L[min(i, len(L) - 1)] = random.choice(TOK)
        cases.append("".join(L))
# nesting and limits
cases += ["> " * 14 + "deep", "- " * 14 + "deep", "  - x\n" * 3 + "    - y", "\n".join("  " * i + "- n%d" % i for i in range(14)),
          "*" * 60, "**" * 60 + "x" + "**" * 60, "*a " * 400 + "*", "_a_ " * 900, "[" * 100 + "x" + "]" * 100 + "(u)", "(" * 3000, "`" * 5000, "`a" * 4000,
          "*" + "a " * 2600 + "*", "*" + "a" * 5100 + "*", "**" + "a" * 4990 + "**", "**" + "a " * 2495 + "**", "x*" + "**" * 1300 + "y",
          "[" + "a" * 4990 + "](http://x.com)", "[a](" + "b" * 4990 + ")", "http://" + "a" * 2090, "http://" + "a" * 2100 + ".", "<http://" + "a" * 2085 + ">", "<http://" + "a" * 2090 + ">",
          "😀" * 2600 + "*a*", "*" + "😀" * 2490 + "*", "a" * 4999 + "*" + "b*", "**" + "😀" * 2495 + "**",
          ">" * 40 + "x", "|a|b|\n|-|-|\n" + "|1|2|\n" * 300, "\n".join("%d. i" % i for i in range(1, 300))]

# boundary sweeps: every length limit, in ASCII and in emoji (2 UTF-16 units each)
for unit, lo, hi in (("a", 4985, 5015), ("😀", 2488, 2512), ("é😀", 1655, 1680)):
    for n in range(lo, hi):
        body = unit * n
        for w in ("*", "**", "_", "~~", "`", "``"):
            cases.append(w + body + w)
            cases.append("x " + w + body + w + " y")
        cases.append("[" + body + "](http://x.com)")
        cases.append("[x](" + body + ")")
        cases.append("![" + body + "](http://x.com/i)")
        cases.append("*" + body + "* **" + body + "**")
        cases.append("a*" + body + "*b _" + body + "_c")
        cases.append("**a *" + body + "* b**")
for unit, lo, hi in (("a", 2085, 2112), ("😀", 1040, 1060), ("é", 2085, 2112)):
    for n in range(lo, hi):
        cases.append("http://" + unit * n)
        cases.append("http://" + unit * n + ").")
        cases.append("<http://" + unit * n + ">")
        cases.append("<mailto:" + unit * n + ">")
        cases.append("see https://x.com/" + unit * n + " ok")

with sync_playwright() as p:
    b = launch(p)
    pg = b.new_page(); pg.goto("file://" + ED)
    js = []
    for i in range(0, len(cases), 2000):
        js += pg.evaluate("a=>a.map(x=>{try{return window.__pde.md(x)}catch(e){return 'JSERROR '+e}})", cases[i:i + 2000])
    b.close()
bad = []; errs = 0
for c, j in zip(cases, js):
    try: r = py(c)
    except Exception as e: r = "PYERROR %r" % e
    if r != j:
        bad.append((c, j, r))
    if j.startswith("JSERROR"): errs += 1
print("cases:", len(cases), "| js errors:", errs, "| differences:", len(bad))
for c, j, r in bad[:5]:
    print("INPUT ", repr(c)[:300]); print("JS    ", repr(j)[:300]); print("PY    ", repr(r)[:300]); print()
raise SystemExit(0 if not bad and not errs else 1)
