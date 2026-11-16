# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [1.0.0] - 2026-11-16

First public release.

### Changed in the move to 1.0
- The format now has its public name, **Helix**, and its own extension, **`.helix.html`**. Files made during development used `.hlx.html` and `"format":"hlx"`.
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
