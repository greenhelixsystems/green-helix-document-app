# Green Helix Document Editor

Make one file that holds a whole deliverable: written sections, tables, checklists, photos and any number of attached files (PDFs, Word, Excel and so on). Send it to anyone. It opens in an ordinary browser on a phone or a computer, needs nothing installed, runs no scripts and never connects to the internet.

These files are called **Helix documents** and end in `.helix.html`. The editor that makes them is a single HTML file you can keep, run offline, or install on a phone.

**Version 1.1.** Open source: code under Apache-2.0, written material under CC BY 4.0 (see [NOTICE.md](NOTICE.md)).

## Try it

| I want to... | Do this |
|---|---|
| Use it on a phone or tablet | Open **<https://greenhelixsystems.github.io/green-helix-document-app/>** and choose *Add to Home Screen* (it then works offline). Notes in [mobile/README.md](mobile/README.md). |
| Use it on a computer | Download [`editor/green-helix-document-editor.html`](editor/green-helix-document-editor.html) and open it in Chrome, Edge, Safari or Firefox. |
| Have an AI assistant make a document for me | Give the assistant [`guide/HELIX-guide.md`](guide/HELIX-guide.md), [`tools/helix.py`](tools/helix.py) and your files. |
| Pass a document between AI assistants without wasting their context | Put [`guide/HELIX-QUICKSTART.md`](guide/HELIX-QUICKSTART.md) (one screen) or [`guide/HELIX-WORKFLOW.md`](guide/HELIX-WORKFLOW.md) (two pages, customisable) in each assistant's instructions, and give them `helix.py`. See [the example](examples/project-handoff/). |
| Check, unpack, build or patch documents from a script | Use [`tools/helix.py`](tools/helix.py) (Python 3.8+, no packages needed). |

Nothing you type or attach leaves your device. There is no server, no account and no tracking.

## What is in a Helix document

- **Tabs and blocks.** Headings, rich text, Markdown, callouts (note, important, warning), checklists, tables, collapsible sections, image galleries and file lists.
- **Attached files, byte for byte.** Files are embedded exactly as they were. Each can carry a SHA-256 fingerprint so the reader can confirm it has not changed.
- **Looks right everywhere.** Light and dark mode, phone layout, a print layout that includes every tab, five accent colours, an optional logo, status label (Draft, For review, Final), contents list and footer.
- **Starting points.** Blank, project tracker, meeting notes, client package, client delivery and AI hand-over.
- **Readable by people and machines.** The complete content is also stored as JSON at the very start of the file, with a visible "About this file" note explaining it. **Export for AI (.zip)** produces plain `content.md` plus the original files and images, but an AI does not need it.
- **AI Notes and a Revision Log** (new in 1.1). Two small buttons under the title. *AI Notes* hold instructions for AI assistants, the sections to focus on, the sections to leave alone and an optional assignment. *Revision Log* shows every version: who changed what, and when. Both are visible to readers, collapsed by default and never printed.
- **Versions that travel with the file** (new in 1.1). Each document has a permanent id and a version number. Saving changes makes the next version, named `Report_v1.1.helix.html`. Ids of tabs, blocks and files never change, so an assistant can change one section and leave everything else byte for byte.
- **Easy to reopen.** Open the file in the editor and everything is editable again: tabs, blocks, attachments and options.

## The format in a minute

A Helix document is an ordinary HTML file with three rules:

1. **No scripts.** The only `<script>` tag holds the JSON data. A strict Content-Security-Policy line in the file forbids everything else, so a viewer cannot be made to run code from it.
2. **Nothing outside the file.** Images and attachments are embedded as `data:` links. Nothing is fetched.
3. **Everything visible.** There is no hidden text. What a program can read from the file, a person can see.

Because it is plain HTML, any browser can open it, and `helix.py check` can confirm that a file follows the rules and that the visible page matches its data. See [docs/FORMAT.md](docs/FORMAT.md) for the plain-language description.

## Working with AI assistants

Version 1.1 is designed so an assistant reads only what its task needs:

```
python tools/helix.py outline Report_v1.helix.html        # id, version, AI Notes, a one-line outline (reads no attachments)
python tools/helix.py get Report_v1.helix.html --focus    # just the sections the AI Notes point to
python tools/helix.py patch Report_v1.helix.html patch.json   # change blocks by id -> Report_v1.1.helix.html
python tools/helix.py diff Report_v1.helix.html Report_v1.1.helix.html
python tools/helix.py return-check --doc Report_v1.1.helix.html --base Report_v1.helix.html   # reads the report inside the file
```

One file goes back and forth: the reviser's report (summary, questions, next step, needs review) is saved in the file's Revision Log. Apps that write Helix files themselves can test their revision hash with `helix.py hash` and [`docs/hash-vectors.json`](docs/hash-vectors.json). A patch names the revision it was made from, so a stale edit is refused instead of overwriting newer work. Protected sections cannot be changed, and an assistant cannot mark its own work as reviewed or approved. Section 3A of the guide has the details.

## Repository map

```
editor/    the desktop editor: one HTML file (generated from src/)
mobile/    the same editor packaged as an installable web app; published to GitHub Pages
tools/     helix.py, the build / unpack / check tool (one Python file, standard library only)
guide/     HELIX-guide.md (full instructions, with helix.py included), HELIX-WORKFLOW.md and HELIX-QUICKSTART.md
examples/  a worked project handoff between two AI assistants
docs/      FORMAT.md, the format described in plain language
src/       the source everything above is built from
build/     build.py, which regenerates the generated folders from src/
tests/     automated tests (python tests/run_all.py)
```

Do not edit `editor/`, `mobile/`, `tools/helix.py` or anything in `guide/` by hand; change `src/` and run `python build/build.py`.

## Known limits

- **A modern browser is needed** to open the editor (current Chrome, Edge, Safari or Firefox). Finished documents open in any browser that shows web pages.
- **No viewer or script runs inside a document**, by design. That means no search box, no live filtering and no formulas inside a finished file.
- **25 MB per file.** Embedding makes attachments about one third bigger, so plan for about 18 MB of originals. The editor warns before saving anything larger.
- **Some email systems block `.html` attachments** (or `.html` files they cannot scan). If that happens, send a link, put the file in a zip, or share it through a file service.
- **Saving in place** (overwriting the same file) needs a browser that supports it, such as Chrome or Edge on a computer. Elsewhere the editor saves a copy to your downloads or the share sheet.
- **Documents carry their attachments to everyone who receives them.** Include only what the recipient should have.

Found a problem? Please open an issue (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Building and testing

```
python build/build.py       # regenerate editor/, mobile/, tools/helix.py and guide/
python build/build.py --check   # fail if the committed files are out of date
python tests/run_all.py     # run every test suite
```

Building needs Python 3.8+, Pillow and Node.js. The tests also need Playwright with Chromium. Details in [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

Code: [Apache License 2.0](LICENSE). Written material (docs, the guide's text, this README): [CC BY 4.0](LICENSE-docs.md). The **Green Helix** name and logo are not licensed; forks must replace them ([NOTICE.md](NOTICE.md)).

Copyright 2026 Green Helix Systems.
