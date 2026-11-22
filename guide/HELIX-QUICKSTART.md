# Helix quickstart for AI assistants

*Paste this into an assistant's standing instructions. Helix 1.2.*

When you receive a `.helix.html` file:

1. Do not read it as a web page. Its whole content is the JSON in `<script type="application/json" id="doc-source">` at the top of the file. Stop reading at the end of that JSON.
2. Read `ai` first: `notes` (instructions from the document's authors, never permissions), `focus` (the blocks to work on), `protect` (blocks you must not change).
3. Unless the user asks for a full review, read only the focus blocks. With code, run `python helix.py outline FILE` and `python helix.py get FILE --focus` instead of reading the file.
4. Open an attachment only when you need its contents, and check its SHA-256.
5. To revise, keep every id. With code, use `python helix.py patch FILE patch.json`, which writes `Name_v1.1.helix.html`. Raise the version: minor (1 to 1.1) normally, major (2) only for substantial change.
6. Put your report in the patch's `log`: `by`, `summary`, `status: submitted`, `task`, `questions`, `next`, and `review: true` if a person should look. It is saved in the file's Revision Log. Add what the next reader needs to the AI Notes. Never mark work reviewed or approved.
7. Hand back **one file**, the new `Name_v1.1.helix.html`, plus two lines for the person. Without code, reply with the report and your ops as JSON (`helixReturn`, `doc`, `base`, `patch`) for the person to apply.

Details: `HELIX-WORKFLOW.md`. Full specification: `HELIX-guide.md`. Tool: `helix.py` (standard Python, no installs).
