# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [1.1.0] - unreleased

AI-native documents: identity, revisions, AI Notes and work handoffs. The format stays version 1 (every 1.0 file is a valid 1.1 file); the data block now says `"spec": "1.1"`.

### Format
- **Document identity and revisions.** `id` (permanent), `rev` (`n`, the visible `label` such as `1.1`, a content `hash` and the `parent` hash), `created`, `modified` and an optional `source`.
- **AI Notes** (`ai`): `notes` (Markdown), `focus` and `protect` (block or tab ids), and an optional assignment `work` (task, stage, role, assignee, status, objective, instructions, targets, sources, deliverables, definition of done, review, base). Placed near the top of the data block so readers meet it first.
- **Revision Log** (`log`): who changed what and when, which blocks, the status they claim and the checks run. Each entry can also carry the reviser's handback (`task`, `questions`, `next`, `review`), so a returned file is its own report: one file passes between assistants with nothing beside it. Statuses separate claims (`submitted`, `validated`) from review and approval, which a patch or return can never record.
- The visible page shows **AI Notes** and **Revision Log** as collapsed buttons under the title, never printed. Documents without them look as before (apart from a Revision Log button once a version is recorded).
- The "About this file" note now tells AI assistants to read the AI Notes first, read only the focus unless asked for a full review, and how to record a revision.
- A file whose data changed without a new revision fails `check`.
- Files with a newer `version` are refused by the editor and cannot be patched (they can still be read).

### Editor
- AI Notes box under the title: notes, plus a Focus / Do-not-change tick for every section. Assignments from other apps are kept and shown.
- Revision Log box: the history, a note for the next save, a major-version option and *Start a new version on the next save*.
- Saving changed content records one revision per editing session and names the file `Title_v1.1.helix.html`. Saving unchanged content keeps the revision. When the version changes, the editor asks where to save rather than overwriting the previous version.

### helix.py
- New commands: `outline` and `get` (read only the data block, never attachments; `get --focus` returns just the focus with the base hash), `asset`, `patch` (set, insert, delete, move, ai, title, attach; conflict detection, protected sections, automatic version and log entry), `diff`, `check --json` and `return-check` (from a returned file alone, or from a separate return for assistants without code).
- `unpack` keeps every id and the revision record; `build` of an unchanged unpacked spec gives an identical file, and a changed one becomes the next revision.
- Specs may give blocks friendly ids (`"budget"`) for AI Notes to point at; `build` maps them to real ids. `by` and `kind` record who created the document; `--now` makes builds reproducible.

### Guides and examples
- `HELIX-WORKFLOW.md` (a two-page customisable template for AI workflows) and `HELIX-QUICKSTART.md` (one screen).
- The guide gains section 3A (revising with AI Notes, focus and patches), 3B (the return envelope), a mapping for project and workflow data, and how other apps can write Helix files.
- `examples/project-handoff/`: a project built by one AI, revised by another and handed back.

### Compatibility
- 1.0 files open, check and save normally; the first save that changes content gives them an id and version 1.1. Pre-1.0 `.hlx.html` files still open.
- Software older than 1.1 does not know the new fields and drops them if it saves a 1.1 file.

## [1.0.0] - 2026-11-16

First public release.

### Changed in the move to 1.0
- The format now has its public name, **Helix**, and its own extension, **`.helix.html`**.
- The format's public version is **1**. The numbers used during development (5 to 9) were pre-release.
- The command-line tool is now `helix.py`, and the guide is `HELIX-guide.md`.
- Opening an old file in the editor and choosing *Download copy* suggests the new `.helix.html` name.

### Compatibility
- Files made before 1.0 (`.hlx.html`, `"format":"hlx"`) are still opened by the editor and read by `helix.py`, and saving one writes the current format. This is tested against three saved development-era files.

### Editor
- Tabs and blocks: heading, text (rich), Markdown, callout (note / important / warning), checklist, table, collapsible, images and files; blocks can sit side by side.
- Attach any files, stored byte for byte, with optional SHA-256 fingerprints and per-file notes. Photos in image blocks can be scaled down; attached files never are.
- Paste Markdown or a spreadsheet range and get a Markdown block or table. HTML pasted into text blocks is sanitised.
- Options: contents list, five accent colours, logo, status (Draft / For review / Final), footer (author, version, date), fingerprints, and the "About this file" note.
- Six starting points: blank, project tracker, meeting notes, client package, client delivery, AI hand-over.
- Export for AI (.zip) and Export all images and files (.zip); print or save as PDF with every tab included.
- Light and dark mode, phone layout with tap-sized controls, undo and redo.
- Warns before saving files over 25 MB and when an attachment no longer matches its fingerprint.
- Mobile: installable web app that works offline (published through GitHub Pages).
- Save in place where the browser allows it (File System Access API); download or the share sheet elsewhere.

### Format
- One self-contained HTML file; the only script is the JSON data block, which comes first in the file, before the stylesheet.
- A Content-Security-Policy line forbids scripts, network access, frames and forms.
- A visible "About this file" section explains the file to humans and machines; the same words are stored as `about` in the data block.
- Tabs work with CSS only (`:target`), so they need no script.

### Tool and guide
- `helix.py`: `build` (from a JSON spec), `unpack` (content.md, spec.json, SHA256SUMS.txt, files/, images/), `check` and `md`. Standard library only. Its output is byte-identical to the editor's.
- `HELIX-guide.md`: instructions for AI assistants to make, read and check documents, with `helix.py` included so no other file is needed.

### Quality
- Automated tests cover the editor, the Python tool against the editor (including a randomised comparison of 700 specs), the Markdown converter against the editor (19,726 generated cases, no differences), fingerprints and integrity warnings, exports, templates, the guide followed literally, naming and old-file compatibility.

### Development history (pre-release)
The editor was built and tested over six checkpoints (internal versions 1 to 10). Two things worth knowing: a built-in viewer script was added and later removed, so that finished documents contain no script at all; and a client-copy variant planned for checkpoint 4 was not built.
