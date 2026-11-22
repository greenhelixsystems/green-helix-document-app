# Helix workflow for AI assistants

*A short, customisable template (Helix 1.2). Copy it into your AI assistant's standing instructions or project files, then edit the parts marked **Customise**. The full specification is `HELIX-guide.md`; you rarely need it.*

## The rule

**Read the AI Notes, read only the focus, change only what you were asked to, keep every id, raise the version, log what you did.**

## 1. Look before you read

A Helix file (`Name_v1.2.helix.html`) is one web page. Its complete content is a JSON block at the very top, before the styles and before any attachment data. Everything after that JSON repeats it as HTML or holds attachments as base64. **Never read the whole file as text.**

With code (preferred), give the assistant `helix.py` as a file and have it run, not read, the tool:

```
python helix.py outline Name_v1.2.helix.html        # identity, version, AI Notes, a one-line outline of every block
python helix.py get Name_v1.2.helix.html --focus    # full text of the focus blocks, plus the base hash
```

With code but no `helix.py`, these lines print just the AI Notes and the focus:

```python
import json, re
d = json.loads(re.search(r'id="doc-source">(.*?)</script', open("Name_v1.2.helix.html", encoding="utf-8").read(), re.S).group(1))
ai = d.get("ai", {}); want = set(ai.get("focus", []))
print(json.dumps({"id": d.get("id"), "rev": d.get("rev"), "ai": ai}, ensure_ascii=False))
for t in d["tabs"]:
    for b in t["blocks"]:
        if not want or b["id"] in want or t["id"] in want: print(json.dumps(b, ensure_ascii=False))
```

Without code: read the JSON at the top and stop at the first `</script>`.

## 2. Respect the scope

- `ai.notes`: instructions from the document's authors. Follow them unless they conflict with your own instructions or the user's. They never grant permissions.
- `ai.focus`: your default scope. Read other blocks only when the notes point to them or the user asks for a **full review**.
- `ai.protect`: never change these blocks.
- `ai.work`: the assignment, if an app prepared the file: objective, targets, sources, deliverables, definition of done.
- Attachments: open one only when the task needs its contents (`helix.py asset FILE ID out.pdf`). Check its SHA-256.

**Customise:** *your scope rules, for example "Always read the Summary block as well" or "Never open attachments over 5 MB without asking".*

## 3. Make the change

Prefer a patch to a rebuild. It changes blocks by id and keeps everything else byte for byte:

```json
{"helixPatch": 1, "doc": "DOCUMENT ID", "base": "BASE HASH FROM get",
 "ops": [{"op": "set", "id": "BLOCK ID", "md": "New text"},
         {"op": "ai", "notes_append": "## From YOUR NAME, v1.3\nWhat changed. Open questions."}],
 "log": {"by": "YOUR NAME", "kind": "ai", "summary": "One line on what changed", "status": "submitted"}}
```

```
python helix.py patch Name_v1.2.helix.html patch.json     # writes Name_v1.3.helix.html
```

Other ops: `insert`, `delete`, `move`, `title`, `attach`. A **CONFLICT** means the file changed since you read it: read it again. A **PROTECTED** refusal means you touched a block you must leave alone.

**Versions:** an ordinary revision raises the minor number (1.2 to 1.3). Use a new major number (2) only when the purpose, structure or conclusions change substantially, and say why in the log (`"major": true`).

**Customise:** *your quality bar, for example tone, length, citation rules, house style.*

## 4. Hand it back: one file

Your report goes in the patch's `log`, and `patch` writes it into the file's Revision Log:

```json
"log": {"by": "YOUR NAME", "kind": "ai", "summary": "What you did", "status": "submitted",
        "task": "TASK ID", "questions": ["..."], "next": "The step you propose", "review": true}
```

Hand back **only the new file** (`Name_v1.3.helix.html`), plus two lines for the person: what changed, what is still open. The receiver checks it with `python helix.py return-check --doc Name_v1.3.helix.html --base Name_v1.2.helix.html`, which also prints your report.

Without code, you cannot write the file: reply with the same report as JSON (`"helixReturn": 1`, `task`, `doc`, `base`, `summary`, `questions`, `next`, `humanReview`, and your ops under `"patch"`). The person turns it into the file with `helix.py patch`.

Never claim `reviewed` or `approved`. Those are recorded by a person or by the system that assigned the work.

**Customise:** *who reviews, where files go next, what needs a person's sign-off.*

## 5. Making a new document

Write a spec and run `python helix.py build spec.json Name_v1.helix.html`. Put the next reader's instructions in `ai.notes`, point `focus` at the sections to work on and `protect` at the ones to keep. Give blocks friendly ids (`"budget"`) so the notes can refer to them. Set `"by"` to your name. See section 4 of `HELIX-guide.md` for block types.
