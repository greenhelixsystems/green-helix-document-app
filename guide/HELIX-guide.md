# Helix documents: guide for AI assistants

Format version 1, for Green Helix Document Editor 1.0.

A **Helix document** is one `.helix.html` file that holds a complete deliverable: text, tables, checklists, images and any number of attached files (PDFs, Word and Excel files, and so on). It opens in any browser, runs no scripts, never connects to the internet, and carries its own editing data so the Green Helix Document Editor can reopen it.

This guide has two jobs:

- **Make** a Helix document from a user's inputs (sections 2 to 8).
- **Read** one you have been given, and take it apart again (section 3).

You do not write the HTML by hand. You write a small JSON **spec** and run `helix.py`, which is included at the end of this guide (section 13). Its output is byte-for-byte what the editor itself would save.

## 1. Rules that must hold

1. The result is **one `.helix.html` file**. Nothing else is needed to view it.
2. **No scripts.** The only `<script>` tag is the JSON data block. No event handlers, no `javascript:` links.
3. **Nothing loads from outside the file.** Images and attachments are embedded as base64. No remote images, fonts or stylesheets.
4. **Do not edit the stylesheet, the security policy line or the About section.** The script writes them.
5. **Attachments are stored byte for byte.** Never re-encode, convert or "fix" a file you attach. Photos in an Images block may be scaled down; files in a Files block never are.
6. **Keep the finished file under 25 MB.** Embedding adds about one third, so inputs should total under roughly 18 MB.
7. **Only include what the user asked for.** Anyone who receives the document can download every attachment in full.
8. **Do not invent content.** Summaries must come from the inputs. If you summarise, say so in the section title ("Summary of the contract").
9. **Do not add branding, promotional footers or credits.** Those belong to the editor, not to documents.
10. **Do not hide anything.** There is no hidden text, no hidden instructions and no invisible elements. Everything a machine can read from the file, a person can also see.

## 2. Making a document

1. Read every input file. Note what each is and what the document must do for its reader.
2. Plan tabs and blocks using sections 4 and 5.
3. Put the input files in a working folder and write `spec.json` beside them.
4. Extract the script (section 11), then run:

   ```
   python helix.py build spec.json output.helix.html
   ```

5. Confirm it printed `OK`. If it printed any `PROBLEM:` line, fix the spec and run it again.
6. Give the user the `.helix.html` file with one line on what is inside and its size.

If the request is ambiguous about which files to attach or how much to summarise, ask once before building.

## 3. Reading and unpacking a document

If you are given an `.helix.html` file, **do not read it as a web page.** Most of it is base64 data. Read it in this order:

1. **The data block.** The JSON in `<script type="application/json" id="doc-source">` sits at the very start of the file, before the stylesheet and before any attachment. It has the title, subtitle, options, every tab and block in order (Markdown blocks keep their original Markdown) and a list of attachments with name, type, size and SHA-256 fingerprint. **This is the whole document. Read it and stop**, unless you need the contents of an attachment.
2. **An attachment, when you need it.** Its bytes are a base64 `data:` link on the element whose id is `asset-` plus the asset's id from the JSON. Decode it with code, never by eye, and compare its SHA-256 with the fingerprint in the JSON before relying on it.
3. **The "About this file" section** at the bottom says the same things in plain words. It is collapsed on screen and hidden when printed.

To take a document apart with code:

```
python helix.py unpack document.helix.html outfolder
```

This writes:

| File | What it is |
|---|---|
| `content.md` | The whole document as Markdown. Tabs are `##` headings. Links to attachments point into the folders below, each with its SHA-256. |
| `files/` and `images/` | Every attachment, byte for byte, plus the logo if there is one. |
| `SHA256SUMS.txt` | A fingerprint for each of those files, in the format `sha256sum -c` reads. |
| `spec.json` | A spec that rebuilds the document (section 4) from these same files. |

To change a document: unpack it, edit `spec.json` (or the files), then run `build` on the edited spec. Display names survive the round trip. Block ids are not kept; they are regenerated.

To verify a document without changing it:

```
python helix.py check document.helix.html
```

It reports `OK` or one `PROBLEM:` line per fault (section 8).

## 4. The spec

`spec.json` is one JSON object. File paths are relative to the folder that holds `spec.json`. Spec fields are the same fields that appear in the data block, with file paths where the data block has asset ids.

```json
{
  "title": "Kitchen renovation",
  "subtitle": "Quotes, schedule and documents",
  "options": {
    "toc": true,
    "accent": "green",
    "status": "review",
    "fingerprints": true,
    "about": true,
    "footer": {"on": true, "author": "Jordan Lee", "version": "1.0", "date": "2026-11-14"}
  },
  "tabs": [
    {"title": "Overview", "blocks": [
      {"type": "callout", "title": "Decision needed", "tone": "important", "text": "Choose a contractor by 28 November."},
      {"type": "markdown", "title": "Summary", "md": "Three quotes received. The **lowest** excludes electrical work.\n\n- Permit needed for wiring\n- Cabinets: 6 week lead time"},
      {"type": "checklist", "title": "Next steps", "half": true, "items": [
        {"text": "Confirm start date", "done": true},
        {"text": "Order cabinets", "done": false}
      ]},
      {"type": "table", "title": "Quotes", "half": true, "rows": [
        ["Contractor", "Price"],
        ["North Build", "$18,400"],
        ["Lakeshore Renos", "$21,950"]
      ]}
    ]},
    {"title": "Documents", "blocks": [
      {"type": "images", "title": "Photos", "items": [
        {"file": "inputs/kitchen-before.jpg", "caption": "Before, facing the window"}
      ]},
      {"type": "files", "title": "Quotes and budget", "desc": true, "items": [
        {"file": "inputs/quote-north-build.pdf", "note": "Quote dated 3 November"},
        {"file": "inputs/budget.xlsx", "name": "Renovation budget.xlsx", "note": "Working budget"}
      ]}
    ]}
  ]
}
```

A document with one tab may use `"blocks": [...]` at the top level instead of `"tabs"`.

### Top level and options

| Field | Meaning |
|---|---|
| `title`, `subtitle` | The main heading and the optional line under it. |
| `options.toc` | `true` adds a clickable contents box to each tab that has at least two entries. |
| `options.accent` | `green` (default), `gold`, `crimson`, `plum` or `slate`. Anything else becomes `green`. |
| `options.status` | `draft`, `review` (shown as "For review") or `final`. Shown as a small label above the title. Empty for none. |
| `options.logo` | Path to a logo image, shown beside the title. Optional. |
| `options.fingerprints` | `true` shows each file's SHA-256 in the file lists. The fingerprints are always saved in the data block either way. |
| `options.about` | `true` (the default when you build) adds the collapsed "About this file" section and the matching `about` note in the data block. Leave it on unless the user says otherwise. |
| `options.footer` | `on` shows a details line at the bottom. `author` and `version` are optional. `date` is `YYYY-MM-DD`; empty means today. |

### Tabs

Tabs are one level only. Use them when the document has clearly separate parts (for example Overview, Documents, Questions). Each tab has a `title` and its own `blocks`. A single-tab document shows no tab bar. In print, all tabs follow one another.

### Blocks

Every block except `heading` accepts `title` (optional section title) and `half` (optional, default `false`).

| `type` | Fields | Notes |
|---|---|---|
| `heading` | `text` | A group heading between sections. |
| `text` | `text` or `html` | `text` is plain: blank lines separate paragraphs. `html` uses the limited tags in section 7. |
| `markdown` | `md` | Markdown in the fixed subset in section 6. Best for anything with structure: lists, tables, emphasis, code. |
| `callout` | `tone`, `text` | `tone` is `note`, `important` or `warning`. `text` is plain; each line is a paragraph. |
| `checklist` | `items`: `{"text", "done"}` | `done` defaults to `false`. Mark items done only if the input says so. |
| `table` | `rows`: list of rows of strings | The first row is the header. Needs at least one data row. Columns of only numbers are right-aligned automatically. |
| `collapsible` | `items`: `{"summary", "body"}` | `summary` is the clickable label; `body` is plain text. |
| `images` | `items`: `{"file", "caption"}` (or just a path) | Optional `name`. Files must be images. |
| `files` | `items`: `{"file", "note"}` (or just a path), plus `desc` | Optional `name` sets the download name. `desc` shows the notes; it defaults to `true` when any item has a note. |

The same file listed twice is embedded twice. List it once.

## 5. Choosing blocks for the inputs

| Input | What to do |
|---|---|
| PDF, Word, PowerPoint, other documents | Attach the original in a **files** block. Add a short **markdown** summary only if the user wants one. |
| Spreadsheet or CSV | Attach the original. If a small part is worth reading on the page (about 8 columns and 40 rows at most), also reproduce it as a **table**. |
| Photos, screenshots, scans | **images** block, with a caption when you know what the picture shows. |
| Notes, emails, transcripts | **markdown** or **text** blocks. Keep the user's wording where it matters. |
| Tasks and action items | **checklist**. |
| Deadlines, decisions, things the reader must do | **callout** with tone `important`. |
| Risks and cautions | **callout** with tone `warning`. |
| Background, questions and answers | **collapsible**. |

Layout guidance:

- Start with what the reader most needs: usually a callout or a short summary.
- Use **heading** blocks to group sections once a tab has more than about five blocks, and turn on `toc` with four or more titled sections.
- Give every files block a note for each file, so the reader knows what they are downloading.
- Set `"half": true` on two neighbouring short blocks to put them side by side. A half block without a half-width neighbour is shown full width.
- Empty blocks are left out automatically, so do not add placeholders.
- For a hand-over to another person or another AI, put the goal and constraints first, the data and files next, and the instructions last, in separate tabs.

## 6. Markdown in a Markdown block

The converter supports a fixed subset and renders it the same way everywhere. It never produces anything but the tags listed here.

| You write | You get |
|---|---|
| `# Title` to `###### Title` | Headings, pushed down two levels so they sit under the block title: `#` becomes a third-level heading, `##` a fourth, and so on, never deeper than sixth. |
| Text, blank line, text | Paragraphs. A single line break inside a paragraph is kept as a line break. |
| `*em*`, `_em_`, `**strong**`, `~~strike~~`, `` `code` `` | Emphasis, strong, strike-through, inline code. |
| `- item`, `* item`, `+ item`, `1. item`, `1) item` | Bulleted and numbered lists, nested by indenting. |
| `- [ ] task`, `- [x] done` | A checklist inside the text. |
| `> quote` | A block quote. |
| `` ``` `` or `~~~` fences, with an optional language | A code block, shown exactly as written. |
| `---` on its own line | A divider. |
| A pipe table with a `---` separator row; `:--`, `:-:`, `--:` set alignment | A table. Columns of only numbers are right-aligned. |
| `[text](https://example.com)`, `<https://example.com>`, a bare `https://...` address | Links. |
| `\*` and other backslash escapes | The literal character. |

Things that do **not** do what you might expect:

- Raw HTML is shown as text, never run. `<b>x</b>` appears literally.
- Image syntax (`![alt](url)`) becomes a link or plain text. Pictures go in an **images** block.
- Link targets may use `https:`, `http:`, `mailto:` or `#anchor`. A target with no scheme, like `[site](example.org)`, gets `https://`. Anything else (`javascript:`, `data:`, relative paths such as `/page` or `./page`) loses its link and keeps its text. A bare `example.org` in running text is not made into a link; write the full `https://` address.
- There are no footnotes, definition lists, setext headings (underlines) or indented code blocks. Use fences.

To preview what a Markdown file will look like: `python helix.py md notes.md` prints the HTML.

## 7. HTML in a text block

Only these tags survive: `<p>`, `<br>`, `<strong>`, `<em>`, `<a href>`, `<ul>`, `<ol>`, `<li>`.

- `<b>` becomes `<strong>`, `<i>` becomes `<em>`, `<div>` becomes `<p>`.
- Any other tag is removed and its text kept. `<script>` and `<style>` go with their contents.
- Links follow the same rules as in section 6.
- There are no headings inside a text block. Use the block's `title`, or a separate `heading` block.

Prefer `text` (plain) or `markdown` over `html`. They are simpler and cannot go wrong.

## 8. Checks before you deliver

`build` runs these automatically and `check` runs them on any file. Each fault is one `PROBLEM:` line:

- Exactly one `<script>` tag, and it is the JSON data block.
- No inline event handlers and no `javascript:` addresses.
- Nothing loads from outside the file.
- The security policy line is present and unchanged.
- The data block parses, and every image and attachment it lists is embedded.
- Every attachment matches the SHA-256 saved for it.
- The visible page is exactly what the data block says it should be. A file whose page was edited by hand, or made by something else, fails here.
- The file is 25 MB or smaller.

A file made by an older editor passes with a note that its layout was not compared.

Files made before version 1.0 used the extension `.hlx.html` and the identifier `"format":"hlx"`. The editor and `helix.py` still read them; saving one in the editor writes the current format.

Then confirm yourself:

- Every file the user asked for is attached, and none they did not ask for.
- Attachment names mean something to the reader.
- Titles and summaries match the inputs.

If the file is over 25 MB, do not silently drop content. Tell the user and ask which files to leave out, or whether to split into two documents.

## 9. If you cannot run code

Embedding files needs base64 and SHA-256, which cannot be done reliably by hand. Without a code tool, tell the user plainly that you cannot make the document, and offer a Markdown version of the content instead. They can paste it into a Markdown block in the editor and add the files there.

## 10. Opening, editing and sharing

- The user opens the file in the Green Helix Document Editor to change it. Everything is kept: tabs, blocks, attachments, options.
- The editor's **Export for AI (.zip)** makes the same `content.md`, `files/`, `images/` and `SHA256SUMS.txt` that `unpack` makes.
- Anyone can open the file in a browser, on a phone or computer, and print it. Print includes every tab.

## 11. Getting the script out of this guide

Run this with this guide saved in the working folder. It copies the script exactly:

```python
import re
guide = open("HELIX-guide.md", encoding="utf-8").read()
code = re.search(r"<!-- helix.py start -->\n```python\n(.*?)\n```\n<!-- helix.py end -->", guide, re.S).group(1)
open("helix.py", "w", encoding="utf-8").write(code + "\n")
```

If the user gave you `helix.py` as a separate file, use that and ignore the rest of this guide after section 12. **Do not read section 13 line by line:** it is the script, and it is long.

Commands:

```
python helix.py build spec.json output.helix.html [--no-shrink]
python helix.py unpack document.helix.html outfolder
python helix.py check document.helix.html
python helix.py md notes.md
```

`--no-shrink` keeps photos at full size. By default, when Pillow is installed, photos over 1600 px on the longest side are scaled down, as the editor does. From Python you can also call `build_from_spec(spec_dict, base_dir)`, `read_document(text)`, `check_document(text)` and `md_render(text)`.

## 12. Format reference

This describes the file the script writes. Use it to inspect a document or to understand one without running anything.

### File layout

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="generator" content="Green Helix Document Editor 1.0">
<title>TITLE</title>
<script type="application/json" id="doc-source">JSON DATA BLOCK</script>
<style>STYLESHEET</style>
</head>
<body>
<main>
<header class="head">logo and status, only when used</header>
<h1>TITLE</h1>
<p class="sub">SUBTITLE</p>
<div class="tabs">tab bar and panels, only with two or more tabs</div>
RENDERED BLOCKS
<footer class="meta">...</footer>
<details class="about"><summary>About this file</summary>...</details>
</main>
</body>
</html>
```

The data block comes **before** the stylesheet so that anything reading the start of the file finds the whole document first.

### The data block

```json
{"format":"helix","version":1,"about":"This is a Helix document ...",
 "title":"...","subtitle":"...",
 "options":{"toc":true,"accent":"green","footer":{"on":false,"author":"","version":"","date":""},"logo":"","status":"","fingerprints":false,"about":true},
 "tabs":[{"id":"a1b2c3d4e5f6g","title":"Overview","blocks":[
   {"id":"a2b3c4d5e6f7h","type":"markdown","title":"Summary","half":false,"md":"..."},
   {"id":"a3b4c5d6e7f8i","type":"images","title":"Photos","half":false,"items":[{"asset":"a9z8y7x6w5v4u","caption":"..."}]},
   {"id":"a4b5c6d7e8f9j","type":"files","title":"Documents","half":false,"items":["a8y7x6w5v4u3t"],"desc":true,"notes":{"a8y7x6w5v4u3t":"..."}}]}],
 "assets":{"a9z8y7x6w5v4u":{"name":"photo.jpg","type":"image/jpeg","bytes":48211,"sha256":"..."},
           "a8y7x6w5v4u3t":{"name":"quote.pdf","type":"application/pdf","bytes":120344,"sha256":"..."}}}
```

- Ids are the letter `a` followed by 6 to 24 lowercase letters or digits, unique within the file.
- Every `<` inside the block is written as `\u003c`, so the data can never close the script tag. Any JSON parser reads it back normally.
- The `about` field holds the same words as the visible "About this file" section. It is there only when `options.about` is true.
- Each asset's bytes live **once**, in the rendered page, on the element whose id is `asset-` plus the asset id: `<img id="asset-ID" ... src="data:image/jpeg;base64,...">` for images and the logo, `<a class="dl" id="asset-ID" download="name.pdf" href="data:application/pdf;base64,...">Download</a>` for attachments.

### How each block is rendered

| Block | HTML |
|---|---|
| heading | `<h2 class="group" id="s-ID">Text</h2>` |
| other blocks | `<section id="s-ID"><h2>Title</h2>...</section>`; the `<h2>` only when there is a title |
| text | `<div class="rich">sanitised html</div>` |
| markdown | `<div class="rich md">converted html</div>` |
| callout | `<section class="callout c-TONE" id="s-ID"><p class="ctag">Note</p><h2>Title</h2><p>...</p></section>` |
| checklist | `<ul class="checks"><li class="done"><span class="vh">Done: </span>Text</li><li>Text</li></ul>` |
| table | `<div class="scroll"><table><thead><tr><th scope="col">..</th></tr></thead><tbody>...</tbody></table></div>`, `class="num"` on numeric columns |
| collapsible | `<details><summary>Label</summary><p>...</p></details>` per item |
| images | `<div class="gallery"><figure><details class="zoom"><summary ...><img ...></summary></details><figcaption>..</figcaption></figure></div>`; class `gallery one` for a single image |
| files | `<div class="scroll"><table class="ft">` with a row per file: name, optional note and fingerprint, size, Download link |

- Two neighbouring blocks that both have `half` set share a `<div class="row2">`.
- All text is escaped (`&`, `<`, `>`, `"`). A block with nothing to show produces no HTML but stays in the data block.
- With two or more tabs, each tab is `<div class="panel" id="t-ID">` and a tab bar of links `#t-ID` switches between them using only CSS.

### Accent colours

| Name | Light mode | Text on it | Dark mode |
|---|---|---|---|
| green | `#4B8747` | white | `#8fcf8a` |
| gold | `#D1A33A` | dark | `#e3bb5c` |
| crimson | `#B01E33` | white | `#f08a98` |
| plum | `#6b3fa0` | white | `#c3a6ee` |
| slate | `#44505c` | white | `#b4c0cc` |

## 13. The script

<!-- helix.py start -->
```python
#!/usr/bin/env python3
"""helix.py - build, unpack and check Helix documents.

A Helix document is one self-contained .helix.html file: it opens in any browser, runs no scripts,
embeds its images and attachments, and carries its own editing data so the Green Helix Document
Editor can reopen it. This tool makes and reads those files without the editor.

    python helix.py build spec.json output.helix.html
    python helix.py unpack document.helix.html outfolder
    python helix.py check document.helix.html
    python helix.py md notes.md

Format version 1. Standard library only (Pillow is optional, for scaling large photos).
Licensed under the Apache License 2.0. "Green Helix" and its logo are not licensed; see NOTICE.md.
"""
import re

FORMAT_VERSION = 1
GENERATOR = "Green Helix Document Editor 1.0"
DOC_CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
ACCENTS = {"green": ["Green", "#4B8747", "#fff", "#8fcf8a", "#10240f", "#3d7039"], "gold": ["Gold", "#D1A33A", "#2b2005", "#e3bb5c", "#2b2005", "#7a5a0c"], "crimson": ["Crimson", "#B01E33", "#fff", "#f08a98", "#3a0a12", "#B01E33"], "plum": ["Plum", "#6b3fa0", "#fff", "#c3a6ee", "#24143a", "#6b3fa0"], "slate": ["Slate", "#44505c", "#fff", "#b4c0cc", "#161c22", "#44505c"]}
STATUS = {"draft": "Draft", "review": "For review", "final": "Final"}
TONES = {"note": "Note", "important": "Important", "warning": "Warning"}
SPEC = "1.1"
LABEL = {"heading": "Heading", "text": "Text", "markdown": "Markdown", "images": "Images", "table": "Table", "collapsible": "Collapsible", "checklist": "Checklist", "callout": "Callout", "files": "Files"}
WORK = {"assigned": "Assigned", "started": "Started", "submitted": "Submitted", "validated": "Checks reported", "reviewed": "Review reported", "approved": "Approval reported", "blocked": "Blocked", "changes": "Changes requested"}
KINDS = {"human": "person", "ai": "AI", "tool": "tool"}
ABOUT_AI = ["The complete document is stored as JSON in the element with id \u201cdoc-source\u201d, at the start of the file and before any attachment data. It lists the title, every tab and block in order (Markdown blocks keep their original Markdown) and every attachment with its name, type, size and SHA-256 fingerprint.", "To understand the document, read that JSON and stop. The rest of the file shows the same content as HTML and embeds the attachments.", "Attachments are base64 \u201cdata:\u201d links further down. Decode one only when you need its contents; its id in the JSON matches the id of its link (\u201casset-\u201d followed by the id).", "Check an attachment against its SHA-256 fingerprint before relying on it."]
ABOUT_JSON = "This is a Helix document (a single self-contained HTML file with no scripts). The complete document is stored as JSON in the element with id \u201cdoc-source\u201d, at the start of the file and before any attachment data. It lists the title, every tab and block in order (Markdown blocks keep their original Markdown) and every attachment with its name, type, size and SHA-256 fingerprint. To understand the document, read that JSON and stop. The rest of the file shows the same content as HTML and embeds the attachments. Attachments are base64 \u201cdata:\u201d links further down. Decode one only when you need its contents; its id in the JSON matches the id of its link (\u201casset-\u201d followed by the id). Check an attachment against its SHA-256 fingerprint before relying on it."
DOC_CSS = ":root{--bg:#f6f5f1;--card:#fff;--ink:#1f2328;--muted:#5d646c;--line:#dcd9d0;--accent:#4B8747;--accent-ink:#fff;--accent-text:#3d7039;--link:#b4481e;--imp-bg:#fbefd5;--imp-ink:#7a4d00;--warn-bg:#fce9e9;--warn-ink:#8f2424}@media (prefers-color-scheme:dark){:root{--bg:#16181b;--card:#1f2226;--ink:#e8e6e1;--muted:#a2a8ae;--line:#34383d;--accent:#8fcf8a;--accent-ink:#10240f;--accent-text:#8fcf8a;--link:#f2a071;--imp-bg:#3a2e12;--imp-ink:#f0c36a;--warn-bg:#3d1b1b;--warn-ink:#f2a3a3}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,\"Segoe UI\",Roboto,sans-serif}main{max-width:860px;margin:0 auto;padding:32px 20px 64px}h1{font-size:30px;line-height:1.2;margin:0 0 6px;overflow-wrap:anywhere}h2{font-size:20px;margin:0 0 12px;overflow-wrap:anywhere}h2.group{font-size:22px;margin:30px 0 12px}h1+nav,h1+section,h1+.row2,h1+.tabs{margin-top:20px}.tabbar{display:flex;gap:6px;overflow-x:auto;position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;margin-bottom:8px}.tabbar a{flex:none;font-size:15px;font-weight:600;padding:7px 14px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none;white-space:nowrap}.panel{display:none;scroll-margin-top:64px}.panel section,.panel h2.group{scroll-margin-top:70px}.panel:target,.panel:has(:target){display:block}.tabs:not(:has(.panel:target,.panel :target)) .panel:first-of-type{display:block}.ptitle{display:none}@supports not selector(:has(*)){.panel{display:block}.tabbar{display:none}.ptitle{display:block;font-size:24px;margin:28px 0 12px}}p{margin:0 0 12px}.sub{color:var(--muted);margin-bottom:24px}a{color:var(--link);text-decoration:underline;text-underline-offset:2px}a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:18px}section>:last-child,.rich>:last-child{margin-bottom:0}.rich{overflow-wrap:anywhere}.rich ul,.rich ol{margin:0 0 12px;padding-left:24px}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}figure{margin:0}.gallery img{width:100%;height:auto;border-radius:8px;display:block}.gallery.one{display:block}.gallery.one img{width:auto;max-width:100%;max-height:460px}figcaption{font-size:14px;color:var(--muted);margin-top:6px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:13px;color:var(--muted);font-weight:600}.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}td.act{text-align:right;white-space:nowrap}td.fname{overflow-wrap:anywhere;width:99%}.ft td{vertical-align:middle}a.dl{font-size:14px;font-weight:600;padding:5px 12px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-ink);text-decoration:none;display:inline-block}details{border-top:1px solid var(--line);padding:10px 0}details:first-of-type{border-top:0;padding-top:0}summary{cursor:pointer;font-weight:600}details p{margin:8px 0 0}.toc ul{list-style:none;margin:0;padding:0}.toc li{margin:4px 0}.toc li.sub{padding-left:18px}.checks{list-style:none;margin:0;padding:0}.checks li{position:relative;padding:3px 0 3px 30px;overflow-wrap:anywhere}.checks li::before{content:\"\";position:absolute;left:0;top:7px;width:16px;height:16px;border:2px solid var(--muted);border-radius:4px}.checks li.done{color:var(--muted);text-decoration:line-through}.checks li.done::before{background:var(--accent);border-color:var(--accent)}.checks li.done::after{content:\"\";position:absolute;left:6px;top:9px;width:5px;height:10px;border:solid var(--accent-ink);border-width:0 2px 2px 0;transform:rotate(45deg)}.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}.row2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}.row2>section{margin-bottom:0;min-width:0}@media (max-width:700px){.row2{grid-template-columns:1fr}}.zoom{border:0;padding:0}.zoom summary{list-style:none;display:block;font-weight:400;cursor:zoom-in}.zoom summary::-webkit-details-marker{display:none}.zoom[open] summary{cursor:zoom-out}.zoom[open] summary img{position:fixed;inset:0;z-index:20;width:100%;height:100%;max-width:none;max-height:none;object-fit:contain;background:rgba(0,0,0,.9);border-radius:0;padding:2vmin}.meta{font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:14px;margin-top:26px}.fdesc{font-size:14px;color:var(--muted);margin-top:2px}.callout{background:color-mix(in srgb,var(--accent) 10%,var(--card));border-color:color-mix(in srgb,var(--accent) 45%,var(--line))}.ctag{font-size:13px;font-weight:700;letter-spacing:.02em;margin:0 0 6px;color:var(--accent-text)}.c-important{background:var(--imp-bg);border-color:var(--imp-ink)}.c-important .ctag{color:var(--imp-ink)}.c-warning{background:var(--warn-bg);border-color:var(--warn-ink)}.c-warning .ctag{color:var(--warn-ink)}.rich h3,.rich h4,.rich h5,.rich h6{margin:18px 0 8px;line-height:1.3;overflow-wrap:anywhere}.rich h3{font-size:18px}.rich h4{font-size:16px}.rich h5,.rich h6{font-size:15px}.rich>:first-child{margin-top:0}.rich ul ul,.rich ol ol,.rich ul ol,.rich ol ul{margin-bottom:0}.rich li{margin:2px 0}.rich li>p{margin:0 0 6px}.md ul.checks{padding-left:0;list-style:none}.md ul.checks li{margin:0}.md code{font:.92em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:color-mix(in srgb,var(--ink) 8%,var(--card));padding:1px 5px;border-radius:5px}.md pre{background:color-mix(in srgb,var(--ink) 6%,var(--card));border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow-x:auto;margin:0 0 12px}.md pre code{background:none;padding:0;font-size:14px;line-height:1.5;white-space:pre}.md pre[data-lang]::before{content:attr(data-lang);display:block;font:700 11px/1 system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}.md blockquote{margin:0 0 12px;padding:2px 0 2px 14px;border-left:3px solid var(--accent);color:var(--muted)}.md blockquote>:last-child{margin-bottom:0}.md hr{border:0;border-top:1px solid var(--line);margin:16px 0}.md .scroll{margin-bottom:12px}.ctr{text-align:center}.head{display:flex;gap:18px;align-items:center;margin-bottom:24px}.head .ht{min-width:0;flex:1}.head .sub{margin-bottom:0}.logo{display:block;flex:none;width:auto;height:auto;max-width:110px;max-height:80px;border-radius:6px}.status{display:inline-block;margin:0 0 6px;padding:2px 11px;border:1px solid var(--line);border-radius:999px;font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}.st-review{background:var(--imp-bg);border-color:var(--imp-ink);color:var(--imp-ink)}.st-final{background:color-mix(in srgb,var(--accent) 12%,var(--card));border-color:var(--accent);color:var(--accent-text)}@media (prefers-color-scheme:dark){.logo{background:#fff;padding:6px}}@media (max-width:560px){.head{gap:12px}.logo{max-width:72px;max-height:56px}}.fp code{font:12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;overflow-wrap:anywhere;word-break:break-all}.fdesc.fp{margin-top:4px}details.about{margin-top:20px;border:0;padding:0;font-size:14px;color:var(--muted)}.about summary{font-weight:600}.about p,.about ul{margin:8px 0 0}.about ul{padding-left:22px}.about li{margin:4px 0}@page{margin:16mm}@media print{:root{--bg:#fff;--card:#fff;--ink:#000;--muted:#444;--line:#bbb;--link:#000;--imp-bg:#f4f4f4;--imp-ink:#000;--warn-bg:#f4f4f4;--warn-ink:#000}body{font-size:11pt}main{max-width:none;padding:0}h1{font-size:22pt}h1,h2{break-after:avoid}section{break-inside:avoid;padding:14px 16px;margin-bottom:12px}.callout{background:#f4f4f4;border-color:#000}.ctag{color:#000}.callout,.checks li::before,.checks li::after{-webkit-print-color-adjust:exact;print-color-adjust:exact}a.dl{display:none}a{text-decoration:none}.rich a[href^=\"http\"]::after{content:\" (\" attr(href) \")\";font-size:9pt;word-break:break-all}.gallery{grid-template-columns:repeat(3,1fr)}figure,tr{break-inside:avoid}thead{display:table-header-group}.scroll{overflow:visible}.row2{grid-template-columns:1fr 1fr}.tabbar{display:none}.panel{display:block!important}.ptitle{display:block;font-size:16pt;margin:16pt 0 8pt}.zoom[open] summary img{position:static;width:100%;height:auto;background:none;padding:0;border-radius:8px}details::details-content{content-visibility:visible!important;display:block!important}.md pre{break-inside:avoid;white-space:pre-wrap}.md pre code{white-space:pre-wrap}.status,.status.st-review,.status.st-final{background:#fff;color:#000;border-color:#000}.logo{background:none!important;padding:0!important}details.about{display:none!important}summary{list-style:none}summary::-webkit-details-marker{display:none}}@media (max-width:560px){section{padding:16px}th,td{padding:8px 6px}}.hxbar{display:flex;flex-wrap:wrap;gap:8px;margin:-10px 0 22px}details.hx,details.hx:first-of-type{flex:0 1 auto;border:1px solid var(--line);border-radius:999px;padding:4px 14px;background:var(--card);font-size:14px}details.hx[open],details.hx[open]:first-of-type{flex:1 1 100%;border-radius:12px;padding:10px 16px 12px}.hx summary{color:var(--accent-text)}.hx .rich{margin-top:10px}.hxk{margin:10px 0 0}.hxv{font-weight:400;color:var(--muted)}.hxw{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:8px 0 0}.hxw dt{font-weight:600;color:var(--muted)}.hxw dd{margin:0;overflow-wrap:anywhere}.hxw dd p{margin:0 0 6px}.hxw ul{margin:0;padding-left:20px}.hxl{list-style:none;margin:10px 0 0;padding:0}.hxl li{padding:7px 0;border-top:1px solid var(--line)}.hxl li:first-child{border-top:0}.hxs{display:inline-block;padding:0 8px;border:1px solid var(--line);border-radius:999px;font-size:12px;color:var(--muted)}.hxm{color:var(--muted);font-size:13px}@media (max-width:560px){.hxw{grid-template-columns:1fr}.hxw dt{margin-top:6px}}@media print{.hxbar{display:none!important}}"

# ---------------------------------------------------------------------------
# Markdown subset converter. A line-for-line port of the editor's mdRender, so
# a Markdown block renders identically whether the editor or this script made it.
# Strings are processed as UTF-16 code units (like JavaScript) so that length
# limits and character tests agree exactly, including for emoji.
# ---------------------------------------------------------------------------
MD_SPAN = 5000
MD_ESC = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
_JSWS = "\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_NOTNL = "[^\\n\\r\\u2028\\u2029]"
_RE = re.ASCII
MD_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,}) *([^`]*)\Z", _RE)
MD_HEAD = re.compile(r"^ {0,3}(#{1,6})(?: +(" + _NOTNL + r"*?))?(?: +#+)? *\Z", _RE)
MD_HR = re.compile(r"^ {0,3}([-*_])(?: *\1){2,} *\Z", _RE)
MD_ITEM = re.compile(r"^( *)([-*+]|[0-9]{1,9}[.)])(?: +(" + _NOTNL + r"*))?\Z", _RE)
MD_QUOTE = re.compile(r"^ {0,3}> ?(" + _NOTNL + r"*)\Z", _RE)
MD_TDELIM = re.compile(r"^ *\|? *:?-+:? *(?:\| *:?-+:? *)*\|? *\Z", _RE)
MD_TASK = re.compile(r"^\[([ xX])\](?: +(" + _NOTNL + r"*))?\Z", _RE)
_ALNUM = re.compile(r"[A-Za-z0-9]")


def _u16(s):
    """Python text to a string of UTF-16 code units (astral characters become two surrogates)."""
    if all(ord(c) < 0x10000 for c in s):
        return s
    return "".join(c if ord(c) < 0x10000 else chr(0xD800 + ((ord(c) - 0x10000) >> 10)) + chr(0xDC00 + ((ord(c) - 0x10000) & 0x3FF)) for c in s)


def _from_u16(s):
    if not any(0xD800 <= ord(c) <= 0xDFFF for c in s):
        return s
    return s.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _at(s, i):
    return s[i] if 0 <= i < len(s) else ""


def _trim(s):
    return s.strip(_JSWS)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _alnum(c):
    return c != "" and _ALNUM.fullmatch(c) is not None


def _space(c):
    return c == "" or c == " " or c == "\n"


def _indent(l):
    k = 0
    while _at(l, k) == " ":
        k += 1
    return k


def _all(t, ch):
    return all(c == ch for c in t)


def _ticks(s, i):
    k = 0
    while _at(s, i + k) == "`":
        k += 1
    return k


def _code_end(s, i, k):
    j = i
    n = min(len(s), i + MD_SPAN)
    while j < n:
        if s[j] == "`":
            r = _ticks(s, j)
            if r == k:
                return j
            j += r
        else:
            j += 1
    return -1


def _close(s, frm, d):
    j = frm
    n = min(len(s), frm + MD_SPAN)
    L = len(d)
    c0 = d[0]
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            k = _ticks(s, j)
            e = _code_end(s, j + k, k)
            j = j + k if e < 0 else e + k
            continue
        if c == c0:
            if L == 1 and _at(s, j + 1) == c0:
                e = -1 if _space(_at(s, j + 2)) else _close(s, j + 2, d + d)
                j = j + 2 if e < 0 else e + 2
                continue
            if L == 2 and _at(s, j + 1) != c0:
                j += 1
                continue
            if j > frm and not _space(_at(s, j - 1)):
                if L == 2:
                    while _at(s, j + 2) == c0:
                        j += 1
                if c0 != "_" or not _alnum(_at(s, j + L)):
                    return j
            j += L
            continue
        j += 1
    return -1


def _bracket(s, i):
    j = i + 1
    n = min(len(s), i + MD_SPAN)
    d = 1
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            k = _ticks(s, j)
            e = _code_end(s, j + k, k)
            j = j + k if e < 0 else e + k
            continue
        if c == "[":
            d += 1
        elif c == "]":
            d -= 1
            if d == 0:
                break
        j += 1
    if j >= n or _at(s, j + 1) != "(":
        return None
    text = s[i + 1:j]
    p = j + 2
    depth = 1
    url = ""
    while p < n:
        c = s[p]
        if c == "\n":
            return None
        if c == "\\" and p + 1 < n:
            url += s[p + 1]
            p += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        url += c
        p += 1
    if p >= n:
        return None
    url = _trim(url)
    k = url.find(" ")
    if k >= 0:
        url = url[:k]
    if url[:1] == "<" and url[-1:] == ">":
        url = url[1:-1]
    return {"text": text, "url": url, "end": p + 1}


def _href(u):
    u = _trim(u)
    if not u:
        return ""
    if re.match(r"(https?:|mailto:)", u, re.I | re.A) or u[0] == "#":
        return u
    if re.match(r"[a-z][a-z0-9+.-]*:", u, re.I | re.A) or u[0] == "/" or u[0] == ".":
        return ""
    return "https://" + u


def _link(hr, inner):
    return '<a href="' + _esc(hr) + '"' + ("" if hr[0] == "#" else ' target="_blank" rel="noopener noreferrer"') + ">" + inner + "</a>"


_AUTOLINK = re.compile(r"<((?:https?://|mailto:)[^" + re.escape(_JSWS) + r"<>]+)>", re.I | re.A)
_BAREURL = re.compile(r"https?://[^" + re.escape(_JSWS) + r"<>]+", re.I | re.A)


def _inline(s, depth):
    if depth > 12:
        return _esc(s).replace("\n", "<br>")
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and s[i + 1] in MD_ESC:
            out.append(_esc(s[i + 1]))
            i += 2
            continue
        if c == "`":
            k = _ticks(s, i)
            j = _code_end(s, i + k, k)
            if j < 0:
                out.append(s[i:i + k])
                i += k
                continue
            t = s[i + k:j].replace("\n", " ")
            if len(t) > 2 and t[0] == " " and t[-1] == " ":
                t = t[1:-1]
            out.append("<code>" + _esc(t) + "</code>")
            i = j + k
            continue
        if c == "[" or (c == "!" and _at(s, i + 1) == "["):
            m = _bracket(s, i + 1 if c == "!" else i)
            if m:
                hr = _href(m["url"])
                t = _esc(_trim(m["text"]) or m["url"]) if c == "!" else _inline(m["text"], depth + 1)
                out.append(_link(hr, t) if hr else t)
                i = m["end"]
                continue
            out.append(_esc(c))
            i += 1
            continue
        if c == "<":
            m = _AUTOLINK.match(s[i:i + 2100])
            if m:
                out.append(_link(m.group(1), _esc(re.sub(r"^mailto:", "", m.group(1), flags=re.I | re.A))))
                i += len(m.group(0))
                continue
            out.append("&lt;")
            i += 1
            continue
        if (c == "h" or c == "H") and not _alnum(_at(s, i - 1)):
            m = _BAREURL.match(s[i:i + 2100])
            if m:
                t = m.group(0)
                while len(t) > 8:
                    k = t[-1]
                    if k in ".,;:!?'\"*_~" or (k == ")" and "(" not in t):
                        t = t[:-1]
                    else:
                        break
                out.append(_link(t, _esc(t)))
                i += len(t)
                continue
        if c == "*" or c == "_" or c == "~":
            two = _at(s, i + 1) == c
            if c == "~" and not two:
                out.append(c)
                i += 1
                continue
            if not (c == "_" and _alnum(_at(s, i - 1))):
                k = 2 if two else 1
                if not _space(_at(s, i + k)):
                    j = _close(s, i + k, c + c if two else c)
                    if j >= 0:
                        t = "del" if c == "~" else ("strong" if two else "em")
                        out.append("<" + t + ">" + _inline(s[i + k:j], depth + 1) + "</" + t + ">")
                        i = j + k
                        continue
            out.append(c * 2 if two else c)
            i += 2 if two else 1
            continue
        if c == "\n":
            out.append("<br>")
            i += 1
            continue
        out.append(_esc(c))
        i += 1
    return "".join(out)


def _row(line):
    s = _trim(line)
    cells = []
    cell = []
    if s[:1] == "|":
        s = s[1:]
    if s[-1:] == "|" and _at(s, len(s) - 2) != "\\":
        s = s[:-1]
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and _at(s, i + 1) == "|":
            cell.append("|")
            i += 1
        elif c == "|":
            cells.append(_trim("".join(cell)))
            cell = []
        else:
            cell.append(c)
        i += 1
    cells.append(_trim("".join(cell)))
    return cells


def _start(lines, i, in_para):
    l = lines[i]
    if MD_FENCE.match(l):
        return "fence"
    if MD_HEAD.match(l):
        return "head"
    if MD_HR.match(l):
        return "hr"
    if MD_QUOTE.match(l):
        return "quote"
    m = MD_ITEM.match(l)
    if m:
        if not in_para:
            return "item"
        if m.group(3) and _trim(m.group(3)) and (not re.search(r"[0-9]", m.group(2)) or m.group(2)[:-1] == "1"):
            return "item"
    if "|" in l and i + 1 < len(lines) and "-" in lines[i + 1] and MD_TDELIM.match(lines[i + 1]) and len(_row(l)) == len(_row(lines[i + 1])):
        return "table"
    return ""


def _join(bl, wrap):
    return "".join("<p>" + x["h"] + "</p>" if x.get("p") and wrap else x["h"] for x in bl)


_NUM = re.compile(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)%?", re.A)


def _is_num(s):
    s = _trim(s)
    s = re.sub(r"^[-+]?\$", "", s).replace(",", "")
    return s != "" and _NUM.fullmatch(s) is not None


def _table(lines, i):
    n = len(lines)
    head = _row(lines[i])
    rows = []
    al = []
    for c in _row(lines[i + 1]):
        L = c[:1] == ":"
        R = c[-1:] == ":"
        al.append(("ctr" if L else "num") if R else ("left" if L else ""))
    i += 2
    while i < n and _trim(lines[i]) and "|" in lines[i]:
        rows.append(_row(lines[i]))
        i += 1
    fixed = []
    for k, a in enumerate(al):
        if a:
            fixed.append("" if a == "left" else a)
            continue
        any_ = False
        all_ = True
        for r in rows:
            v = _trim((r[k] if k < len(r) else "").replace("**", ""))
            if v:
                any_ = True
                if not _is_num(v):
                    all_ = False
        fixed.append("num" if any_ and all_ else "")
    al = fixed

    def cell(tag, v, k, extra):
        a = al[k] if k < len(al) else ""
        return "<" + tag + (' class="' + a + '"' if a else "") + extra + ">" + _inline(v, 0) + "</" + tag + ">"
    h = ('<div class="scroll"><table><thead><tr>' + "".join(cell("th", v, k, ' scope="col"') for k, v in enumerate(head)) + "</tr></thead>"
         + ("<tbody>" + "".join("<tr>" + "".join(cell("td", r[k] if k < len(r) else "", k, "") for k in range(len(head))) + "</tr>" for r in rows) + "</tbody>" if rows else "")
         + "</table></div>")
    return i, h


def _list(lines, i, depth):
    n = len(lines)
    m = MD_ITEM.match(lines[i])
    base = len(m.group(1))
    ord_ = re.search(r"[0-9]", m.group(2)) is not None
    start = int(re.match(r"[0-9]+", m.group(2)).group(0)) if ord_ else 1
    items = []

    def sibling(k):
        x = MD_ITEM.match(lines[k]) if k < n else None
        return bool(x) and len(x.group(1)) <= base + 1 and (re.search(r"[0-9]", x.group(2)) is not None) == ord_ and not MD_HR.match(lines[k])
    while i < n and sibling(i):
        m = MD_ITEM.match(lines[i])
        w = len(m.group(1)) + len(m.group(2)) + 1
        buf = [m.group(3) or ""]
        i += 1
        while i < n:
            if not _trim(lines[i]):
                j = i
                while j < n and not _trim(lines[j]):
                    j += 1
                if j < n and _indent(lines[j]) >= base + 2:
                    while i < j:
                        buf.append("")
                        i += 1
                    continue
                break
            ind = _indent(lines[i])
            if ind < base + 2:
                break
            buf.append(lines[i][min(ind, w):])
            i += 1
        items.append(buf)
        j = i
        while j < n and not _trim(lines[j]):
            j += 1
        if j > i:
            if sibling(j):
                i = j
            else:
                break
    tasks = (not ord_) and all(MD_TASK.match(b[0]) for b in items)
    parts = []
    for b in items:
        done = False
        if tasks:
            tm = MD_TASK.match(b[0])
            done = tm.group(1) != " "
            b = [tm.group(2) or ""] + b[1:]
        bl = _blocks(b, depth + 1)
        pc = len([x for x in bl if x.get("p")])
        parts.append("<li" + (' class="done"><span class="vh">Done: </span>' if done else ">") + _join(bl, pc > 1) + "</li>")
    html = "".join(parts)
    head = ("<ol" + (' start="%d"' % start if start != 1 else "") + ">") if ord_ else ("<ul" + (' class="checks"' if tasks else "") + ">")
    return i, head + html + ("</ol>" if ord_ else "</ul>")


def _blocks(lines, depth):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        l = lines[i]
        if not _trim(l):
            i += 1
            continue
        k = "" if depth > 8 else _start(lines, i, False)
        if k == "fence":
            m = MD_FENCE.match(l)
            ch = m.group(1)[0]
            ln = len(m.group(1))
            lang = (_trim(m.group(2)).split(" ") or [""])[0]
            buf = []
            i += 1
            while i < n:
                t = _trim(lines[i])
                if len(t) >= ln and _all(t, ch):
                    i += 1
                    break
                buf.append(lines[i])
                i += 1
            out.append({"h": "<pre" + (' data-lang="' + lang + '"' if re.fullmatch(r"[A-Za-z0-9_+#.-]{1,24}", lang) else "") + "><code>" + _esc("\n".join(buf)) + "</code></pre>"})
            continue
        if k == "head":
            m = MD_HEAD.match(l)
            t = min(6, len(m.group(1)) + 2)
            out.append({"h": "<h%d>" % t + _inline(_trim(m.group(2) or ""), 0) + "</h%d>" % t})
            i += 1
            continue
        if k == "hr":
            out.append({"h": "<hr>"})
            i += 1
            continue
        if k == "quote":
            buf = []
            while i < n:
                m = MD_QUOTE.match(lines[i])
                if not m:
                    break
                buf.append(m.group(1))
                i += 1
            out.append({"h": "<blockquote>" + _join(_blocks(buf, depth + 1), True) + "</blockquote>"})
            continue
        if k == "item":
            i, h = _list(lines, i, depth)
            out.append({"h": h})
            continue
        if k == "table":
            i, h = _table(lines, i)
            out.append({"h": h})
            continue
        buf = []
        while i < n and _trim(lines[i]) and (not buf or depth > 8 or not _start(lines, i, True)):
            t = _trim(lines[i])
            if t[-1:] == "\\":
                t = t[:-1]
            buf.append(t)
            i += 1
        out.append({"p": True, "h": _inline("\n".join(buf), 0)})
    return out


def md_render(src):
    """Markdown text to the HTML the editor produces for a Markdown block."""
    s = _u16("" if src is None else str(src)).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    return _from_u16(_join(_blocks(s.split("\n"), 0), True))


# ---------------------------------------------------------------------------
# Small helpers shared by everything below.
# ---------------------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def trim(s):
    """JavaScript's String.prototype.trim (its whitespace set differs from Python's)."""
    return s.strip(_JSWS)


def fmt_size(n):
    M = 1048576
    if n >= M:
        if n >= 10 * M:
            q = (n * 20 + M) // (2 * M)
            return "%d.%d MB" % (q // 10, q % 10)
        q = (n * 200 + M) // (2 * M)
        return "%d.%02d MB" % (q // 100, q % 100)
    if n >= 1024:
        return "%d KB" % ((2 * n + 1024) // 2048)
    return "%d bytes" % n


def clean_type(t):
    t = trim(t or "").lower()
    return t if re.fullmatch(r"[A-Za-z0-9_.+-]+/[A-Za-z0-9_.+-]+", t) else "application/octet-stream"


def safe_href(u):
    u = trim(u or "")
    if not u:
        return ""
    if re.match(r"(https?:|mailto:)", u, re.I | re.A) or u[0] == "#":
        return u
    if re.match(r"[a-z][a-z0-9+.-]*:", u, re.I | re.A):
        return ""
    return "https://" + u


# ---------------------------------------------------------------------------
# HTML fragment parsing for text blocks. This follows the browser's rules for the
# constructs that appear in rich text (paragraphs, lists, bold, italic, links, line
# breaks, stray block tags, unclosed tags). It does not model tables or forms.
# ---------------------------------------------------------------------------
from html.parser import HTMLParser

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "keygen", "basefont", "bgsound", "frame"}
_SPECIAL = set("address applet area article aside base basefont bgsound blockquote body br button caption center col colgroup dd details dir div dl dt embed fieldset figcaption figure footer form frame frameset h1 h2 h3 h4 h5 h6 head header hgroup hr html iframe img input keygen li link listing main marquee menu meta nav noembed noframes noscript object ol p param plaintext pre script search section select source style summary table tbody td template textarea tfoot th thead title tr track ul wbr xmp".split())
_CLOSE_P = set("address article aside blockquote center details dialog dir div dl fieldset figcaption figure footer form header hgroup hr li listing main menu nav ol p pre search section summary table ul xmp h1 h2 h3 h4 h5 h6 dd dt".split())
_FORMAT = {"a", "b", "big", "code", "em", "font", "i", "nobr", "s", "small", "strike", "strong", "tt", "u"}
_SCOPE = {"applet", "caption", "html", "table", "td", "th", "marquee", "object", "template"}
_RAWSKIP = {"script", "style"}


class _Node(object):
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids = []
        self.parent = parent


_MARKERS = {"applet", "object", "marquee", "td", "th", "caption", "template"}
_RECONSTRUCT_VOID = {"br", "img", "input", "embed", "wbr", "area", "keygen"}
_BLOCK_END = {"div", "ul", "ol", "blockquote", "pre", "section", "article", "nav", "header", "footer", "main", "aside", "address", "center", "details", "dl", "fieldset", "figure", "figcaption",
              "form", "menu", "search", "summary", "hgroup", "listing", "dialog", "dir", "button"}
_HEADS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _detach(n):
    if n.parent is not None:
        for i, k in enumerate(n.parent.kids):
            if k is n:
                del n.parent.kids[i]
                break
        n.parent = None


def _attach(parent, n):
    _detach(n)
    n.parent = parent
    parent.kids.append(n)


class _Builder(HTMLParser):
    """HTML5 tree construction, for the parts that matter in rich text (including the
    adoption agency algorithm that browsers use for mis-nested bold, italic and links)."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = _Node("body")
        self.stack = [self.root]
        self.active = []  # _Node or None (marker)

    def _cur(self):
        return self.stack[-1]

    def _is_special(self, n):
        return n.tag in _SPECIAL

    def _in_scope(self, tag, extra=()):
        for n in reversed(self.stack):
            if n.tag == tag:
                return True
            if n.tag in _SCOPE or n.tag in extra:
                return False
        return False

    def _node_in_scope(self, node):
        for n in reversed(self.stack):
            if n is node:
                return True
            if n.tag in _SCOPE:
                return False
        return False

    def _clear_to_marker(self):
        while self.active:
            if self.active.pop() is None:
                break

    def _pop(self):
        n = self.stack.pop()
        if n.tag in _MARKERS:
            self._clear_to_marker()
        return n

    def _pop_through(self, node):
        while self.stack:
            if self._pop() is node:
                break

    def _pop_through_tag(self, tags):
        while self.stack:
            if self._pop().tag in tags:
                break

    def _close_p(self):
        if self._in_scope("p", ("button",)):
            while self._cur().tag in ("dd", "dt", "li", "optgroup", "option", "p", "rb", "rp", "rt", "rtc") and self._cur().tag != "p":
                self._pop()
            self._pop_through_tag(("p",))

    def _push_active(self, n):
        same = []
        for x in reversed(self.active):
            if x is None:
                break
            if x.tag == n.tag and x.attrs == n.attrs:
                same.append(x)
        if len(same) >= 3:
            self.active.remove(same[-1])
        self.active.append(n)

    def _reconstruct(self):
        if not self.active:
            return
        last = self.active[-1]
        if last is None or last in self.stack:
            return
        k = len(self.active) - 1
        while True:
            if k == 0:
                break
            k -= 1
            e = self.active[k]
            if e is None or e in self.stack:
                k += 1
                break
        while k < len(self.active):
            old = self.active[k]
            new = _Node(old.tag, dict(old.attrs))
            _attach(self._cur(), new)
            self.stack.append(new)
            self.active[k] = new
            k += 1

    def _insert(self, tag, attrs):
        n = _Node(tag, attrs)
        _attach(self._cur(), n)
        return n

    def _adoption(self, subject):
        """Returns True if handled, False if the caller should treat it as an ordinary end tag."""
        cur = self._cur()
        if cur.tag == subject and cur not in self.active:
            self._pop()
            return True
        for _ in range(8):
            fe = None
            for x in reversed(self.active):
                if x is None:
                    break
                if x.tag == subject:
                    fe = x
                    break
            if fe is None:
                return False
            if fe not in self.stack:
                self.active.remove(fe)
                return True
            if not self._node_in_scope(fe):
                return True
            fi = self.stack.index(fe)
            fb = None
            for n in self.stack[fi + 1:]:
                if self._is_special(n):
                    fb = n
                    break
            if fb is None:
                while self.stack:
                    if self._pop() is fe:
                        break
                if fe in self.active:
                    self.active.remove(fe)
                return True
            common = self.stack[fi - 1]
            bookmark = self.active.index(fe)
            node = last = fb
            inner = 0
            ni = self.stack.index(node)
            while True:
                inner += 1
                ni -= 1
                node = self.stack[ni]
                if node is fe:
                    break
                if inner > 3 and node in self.active:
                    self.active.remove(node)
                    if self.active.index(fe) < bookmark:
                        bookmark -= 0
                if node not in self.active:
                    self.stack.remove(node)
                    continue
                new = _Node(node.tag, dict(node.attrs))
                self.active[self.active.index(node)] = new
                self.stack[self.stack.index(node)] = new
                node = new
                if last is fb:
                    bookmark = self.active.index(node) + 1
                _attach(node, last)
                last = node
            _attach(common, last)
            new = _Node(fe.tag, dict(fe.attrs))
            for kid in list(fb.kids):
                if isinstance(kid, str):
                    new.kids.append(kid)
                else:
                    _attach(new, kid)
            fb.kids = [k for k in fb.kids if not isinstance(k, str)]
            _attach(fb, new)
            bi = min(bookmark, len(self.active))
            if fe in self.active:
                ei = self.active.index(fe)
                self.active.remove(fe)
                if ei < bi:
                    bi -= 1
            self.active.insert(bi, new)
            self.stack.remove(fe)
            self.stack.insert(self.stack.index(fb) + 1, new)
        return True

    def handle_starttag(self, tag, attrs):
        a = {}
        for k, v in attrs:
            if k not in a:
                a[k] = "" if v is None else v
        if tag in _CLOSE_P:
            self._close_p()
        if tag == "li":
            for n in reversed(self.stack):
                if n.tag == "li":
                    while self._cur().tag != "li":
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SPECIAL and n.tag not in ("address", "div", "p"):
                    break
        elif tag in ("dd", "dt"):
            for n in reversed(self.stack):
                if n.tag in ("dd", "dt"):
                    while self._cur() is not n:
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SPECIAL and n.tag not in ("address", "div", "p"):
                    break
        if tag in _HEADS and self._cur().tag in _HEADS:
            self._pop()
        if tag == "a":
            for x in reversed(self.active):
                if x is None:
                    break
                if x.tag == "a":
                    self._adoption("a")
                    if x in self.active:
                        self.active.remove(x)
                    if x in self.stack:
                        self.stack.remove(x)
                    break
        if tag == "nobr":
            self._reconstruct()
            if self._in_scope("nobr"):
                self._adoption("nobr")
                self._reconstruct()
        elif tag in _FORMAT or tag not in _SPECIAL or tag in _RECONSTRUCT_VOID:
            self._reconstruct()
        n = self._insert(tag, a)
        if tag in _VOID:
            return
        self.stack.append(n)
        if tag in _FORMAT:
            self._push_active(n)
        if tag in _MARKERS:
            self.active.append(None)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "br":
            self.handle_starttag("br", [])
            return
        if tag == "p":
            if not self._in_scope("p", ("button",)):
                self._insert("p", {})
                return
            self._close_p()
            return
        if tag == "li":
            if self._in_scope("li", ("ol", "ul", "button")):
                while self._cur().tag != "li":
                    self._pop()
                self._pop()
            return
        if tag in ("dd", "dt"):
            if self._in_scope(tag, ("button",)):
                while self._cur().tag != tag:
                    self._pop()
                self._pop()
            return
        if tag in _FORMAT:
            if not self._adoption(tag):
                self._any_other(tag)
            return
        if tag in _BLOCK_END:
            if self._in_scope(tag, ("button",)):
                while self._cur().tag != tag:
                    self._pop()
                self._pop()
            return
        if tag in _HEADS:
            for n in reversed(self.stack):
                if n.tag in _HEADS:
                    while self._cur() is not n:
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SCOPE:
                    break
            return
        self._any_other(tag)

    def _any_other(self, tag):
        for n in reversed(self.stack):
            if n.tag == tag:
                while self._cur() is not n:
                    self._pop()
                self._pop()
                return
            if n.tag in _SPECIAL:
                return

    def handle_data(self, data):
        if not data:
            return
        self._reconstruct()
        k = self._cur().kids
        if k and isinstance(k[-1], str):
            k[-1] += data
        else:
            k.append(data)


def parse_fragment(html):
    b = _Builder()
    b.feed("" if html is None else html)
    b.close()
    return b.root


def _clean_node(node):
    out = []
    for n in node.kids:
        if isinstance(n, str):
            out.append(esc(n))
            continue
        tg = n.tag
        if tg in ("script", "style", "template"):
            continue
        t = {"p": "p", "div": "p", "br": "br", "strong": "strong", "b": "strong", "em": "em", "i": "em", "a": "a", "ul": "ul", "ol": "ol", "li": "li"}.get(tg)
        inner = _clean_node(n)
        if not t:
            out.append(inner)
        elif t == "br":
            out.append("<br>")
        elif t == "a":
            hr = safe_href(n.attrs.get("href"))
            if hr:
                out.append('<a href="' + esc(hr) + '"' + ("" if hr[0] == "#" else ' target="_blank" rel="noopener noreferrer"') + ">" + inner + "</a>")
            else:
                out.append(inner)
        elif t == "p" and not trim(inner.replace("<br>", "")):
            out.append("")
        else:
            out.append("<" + t + ">" + inner + "</" + t + ">")
    return "".join(out)


def sanitize(html):
    """Reduce rich text to paragraphs, line breaks, bold, italic, links and lists."""
    return _clean_node(parse_fragment(html))


# ---------------------------------------------------------------------------
# Rendering: a port of the editor's buildDocument.
# ---------------------------------------------------------------------------
import base64
import datetime
import hashlib
import json

_MONTHS = "January February March April May June July August September October November December".split()


def _tab_name(t, i):
    return trim(t["title"]) or "Tab %d" % (i + 1)


def _is_num(s):
    s = trim(s)
    s = re.sub(r"^[-+]?\$", "", s).replace(",", "")
    return s != "" and re.fullmatch(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)%?", s) is not None


def _paras(text):
    return [p for p in re.split(r"\n+", text) if trim(p)]


def fingerprint(a):
    if not a.get("sha"):
        a["sha"] = hashlib.sha256(base64.b64decode(a["b64"])).hexdigest()
    return a["sha"]


def _section(b, inner):
    return '<section id="s-' + b["id"] + '">' + ("<h2>" + esc(trim(b["title"])) + "</h2>" if trim(b["title"]) else "") + inner + "</section>"


def _render_block(b, doc, assets):
    t = b["type"]
    if t == "heading":
        return '<h2 class="group" id="s-' + b["id"] + '">' + esc(trim(b["text"])) + "</h2>" if trim(b["text"]) else ""
    if t == "text":
        c = sanitize(b["html"])
        return _section(b, '<div class="rich">' + c + "</div>") if (c or trim(b["title"])) else ""
    if t == "markdown":
        c = md_render(b["md"])
        return _section(b, '<div class="rich md">' + c + "</div>") if (c or trim(b["title"])) else ""
    if t == "images":
        figs = []
        for it in b["items"]:
            a = assets.get(it["asset"])
            if not a:
                continue
            cap = trim(it["caption"])
            figs.append('<figure><details class="zoom"><summary title="Enlarge or shrink this image"><img id="asset-' + it["asset"] + '" alt="' + esc(cap or a["name"])
                        + '" src="data:' + a["type"] + ";base64," + a["b64"] + '"></summary></details>' + ("<figcaption>" + esc(cap) + "</figcaption>" if cap else "") + "</figure>")
        return _section(b, '<div class="gallery' + (" one" if len(b["items"]) == 1 else "") + '">' + "".join(figs) + "</div>") if figs else ""
    if t == "table":
        rows = b["rows"]
        cols = len(rows[0])
        num = []
        for c in range(cols):
            any_ = False
            all_ = True
            for r in range(1, len(rows)):
                v = trim(rows[r][c] if c < len(rows[r]) else "")
                if v:
                    any_ = True
                    if not _is_num(v):
                        all_ = False
            num.append(any_ and all_)
        head = "<tr>" + "".join("<th" + (' class="num"' if num[i] else "") + ' scope="col">' + esc(x) + "</th>" for i, x in enumerate(rows[0])) + "</tr>"
        body = "".join("<tr>" + "".join("<td" + (' class="num"' if num[i] else "") + ">" + esc(x) + "</td>" for i, x in enumerate(row)) + "</tr>"
                       for row in rows[1:] if any(trim(x) for x in row))
        if not body:
            return ""
        return _section(b, '<div class="scroll"><table><thead>' + head + "</thead><tbody>" + body + "</tbody></table></div>")
    if t == "collapsible":
        d = "".join("<details><summary>" + esc(trim(it["summary"]) or "Details") + "</summary>" + "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(it["body"])) + "</details>"
                    for it in b["items"] if trim(it["summary"]) or trim(it["body"]))
        return _section(b, d) if (d or trim(b["title"])) else ""
    if t == "callout":
        tone = b["tone"] if b["tone"] in TONES else "note"
        ps = "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(b["text"]))
        if not ps and not trim(b["title"]):
            return ""
        return ('<section class="callout c-' + tone + '" id="s-' + b["id"] + '"><p class="ctag">' + TONES[tone] + "</p>"
                + ("<h2>" + esc(trim(b["title"])) + "</h2>" if trim(b["title"]) else "") + ps + "</section>")
    if t == "checklist":
        li = "".join("<li" + (' class="done"><span class="vh">Done: </span>' if it["done"] else ">") + esc(trim(it["text"])) + "</li>" for it in b["items"] if trim(it["text"]))
        return _section(b, '<ul class="checks">' + li + "</ul>") if (li or trim(b["title"])) else ""
    if t == "files":
        rows = []
        for id_ in b["items"]:
            a = assets.get(id_)
            if not a:
                continue
            note = trim(b["notes"][id_]) if b["desc"] and b["notes"] and id_ in b["notes"] and b["notes"][id_] else ""
            rows.append('<tr><td class="fname">' + esc(a["name"]) + ('<div class="fdesc">' + esc(note) + "</div>" if note else "")
                        + ('<div class="fdesc fp">SHA-256 <code>' + fingerprint(a) + "</code></div>" if doc["options"]["fingerprints"] else "")
                        + '</td><td class="num">' + fmt_size(a["bytes"]) + '</td><td class="act"><a class="dl" id="asset-' + id_ + '" download="' + esc(a["name"])
                        + '" href="data:' + a["type"] + ";base64," + a["b64"] + '">Download</a></td></tr>')
        return (_section(b, '<div class="scroll"><table class="ft"><thead><tr><th scope="col">File</th><th class="num" scope="col">Size</th><th scope="col"><span aria-hidden="true"></span></th></tr></thead><tbody>'
                         + "".join(rows) + "</tbody></table></div>") if rows else "")
    return ""


def _name_of(doc, assets, id_):
    """A readable name for a tab, block or attachment id (used in AI Notes and the Revision Log)."""
    for i, t in enumerate(doc["tabs"]):
        if t["id"] == id_:
            return _tab_name(t, i)
        for b in t["blocks"]:
            if b["id"] == id_:
                return trim(b["text"] if b["type"] == "heading" else b["title"]) or LABEL[b["type"]] + " block"
    if id_ in assets:
        return assets[id_]["name"]
    return id_


def _names(doc, assets, ids):
    return esc(", ".join(_name_of(doc, assets, x) for x in ids))


def _work_html(doc, assets, w):
    rows = ""
    for key, label in (("task", "Task"), ("stage", "Stage"), ("role", "Role"), ("assignee", "Assigned to"), ("objective", "Objective")):
        if trim(w.get(key, "")):
            rows += "<dt>" + label + "</dt><dd>" + esc(trim(w[key])) + "</dd>"
    if w.get("status"):
        rows += "<dt>Status</dt><dd>" + WORK[w["status"]] + "</dd>"
    for key, label in (("targets", "Work on"), ("sources", "Read")):
        if w.get(key):
            rows += "<dt>" + label + "</dt><dd>" + _names(doc, assets, w[key]) + "</dd>"
    if _paras(w.get("instructions", "")):
        rows += "<dt>Instructions</dt><dd>" + "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(w["instructions"])) + "</dd>"
    for key, label in (("deliverables", "Deliverables"), ("done", "Done when")):
        if w.get(key):
            rows += "<dt>" + label + "</dt><dd><ul>" + "".join("<li>" + esc(trim(x)) + "</li>" for x in w[key]) + "</ul></dd>"
    if trim(w.get("review", "")):
        rows += "<dt>Review</dt><dd>" + esc(trim(w["review"])) + "</dd>"
    if w.get("base"):
        rows += "<dt>Based on</dt><dd><code>" + w["base"][:12] + "</code></dd>"
    return '<p class="hxk"><strong>Assignment</strong></p><dl class="hxw">' + rows + "</dl>" if rows else ""


def _log_li(doc, assets, e):
    bits = ["<strong>v" + esc(e.get("label") or str(e.get("rev", 0))) + "</strong>"]
    if e.get("at"):
        bits.append(e["at"][:10] + " " + e["at"][11:16] + " UTC")
    who = trim(e.get("by", "")) + (" (" + KINDS[e["kind"]] + ")" if e.get("kind") else "")
    if trim(who):
        bits.append(esc(trim(who)))
    li = "<li>" + " \u00b7 ".join(bits) + (": " + esc(trim(e["summary"])) if trim(e.get("summary", "")) else "")
    if e.get("status"):
        li += ' <span class="hxs">' + WORK[e["status"]] + "</span>"
    if e.get("blocks"):
        li += '<br><span class="hxm">Changed: ' + _names(doc, assets, e["blocks"]) + "</span>"
    if trim(e.get("checks", "")):
        li += '<br><span class="hxm">Checks: ' + esc(trim(e["checks"])) + "</span>"
    if trim(e.get("note", "")):
        li += '<br><span class="hxm">' + esc(trim(e["note"])) + "</span>"
    return li + "</li>"


def hx_panels(doc, assets):
    """The AI Notes and Revision Log buttons under the title. Both are collapsed and never printed."""
    out = ""
    ai = doc.get("ai")
    if ai:
        p = ""
        if trim(ai.get("notes", "")):
            p += '<div class="rich md">' + md_render(ai["notes"]) + "</div>"
        for key, label in (("focus", "Focus"), ("protect", "Do not change")):
            if ai.get(key):
                p += '<p class="hxk"><strong>' + label + ":</strong> " + _names(doc, assets, ai[key]) + "</p>"
        if ai.get("work"):
            p += _work_html(doc, assets, ai["work"])
        if p:
            out += '<details class="hx"><summary>AI Notes</summary>\n' + p + "</details>\n"
    log = doc["meta"]["log"]
    if log:
        lab = doc["meta"]["rev"]["label"]
        out += ('<details class="hx"><summary>Revision Log' + (' <span class="hxv">v' + esc(lab) + "</span>" if lab else "") + '</summary>\n<ul class="hxl">'
                + "".join(_log_li(doc, assets, e) for e in reversed(log)) + "</ul></details>\n")
    return '<div class="hxbar">\n' + out + "</div>\n" if out else ""


def _render_tab(t, doc, assets):
    parts = []
    toc = []
    seen = False
    for b in t["blocks"]:
        out = _render_block(b, doc, assets)
        if not out:
            continue
        if b["type"] == "heading":
            seen = True
            toc.append((b["id"], trim(b["text"]), False))
        elif trim(b.get("title", "")):
            toc.append((b["id"], trim(b["title"]), seen))
        parts.append((out, bool(b.get("half")) and b["type"] != "heading"))
    body = ""
    i = 0
    while i < len(parts):
        if parts[i][1] and i + 1 < len(parts) and parts[i + 1][1]:
            body += '<div class="row2">' + parts[i][0] + parts[i + 1][0] + "</div>\n"
            i += 2
        else:
            body += parts[i][0] + "\n"
            i += 1
    nav = ""
    if doc["options"]["toc"] and len(toc) > 1:
        nav = ('<nav class="toc" aria-label="Contents"><section><h2>Contents</h2><ul>'
               + "".join("<li" + (' class="sub"' if sub else "") + '><a href="#s-' + id_ + '">' + esc(tx) + "</a></li>" for id_, tx, sub in toc) + "</ul></section></nav>\n")
    return nav + body


def about_html(has_files):
    return ('<details class="about"><summary>About this file</summary>\n<p>This is a Helix document: a single web page that opens in any browser. It contains no scripts and never connects to the internet. '
            + ("Its images and attached files are stored inside this file, so it can be emailed, saved or archived on its own. Use the Download buttons to save attachments." if has_files
               else "Everything it shows is stored inside this file, so it can be emailed, saved or archived on its own.") + "</p>\n"
            + "<p><strong>For AI assistants and other software</strong></p>\n<ul>" + "".join("<li>" + esc(x) + "</li>" for x in ABOUT_AI) + "</ul>\n</details>\n")


def _js_json(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def data_block(doc, assets):
    meta = {}
    for id_, a in assets.items():
        meta[id_] = {"name": a["name"], "type": a["type"], "bytes": a["bytes"], "sha256": fingerprint(a)}
    m = doc["meta"]
    head = {"format": "helix", "version": FORMAT_VERSION, "spec": SPEC, "id": m["id"], "rev": prune(m["rev"])}
    for k in ("created", "modified", "source"):
        if m.get(k):
            head[k] = m[k]
    if doc["options"]["about"]:
        head["about"] = ABOUT_JSON
    if doc.get("ai"):
        head["ai"] = doc["ai"]
    head.update({"title": doc["title"], "subtitle": doc["subtitle"], "options": doc["options"], "tabs": doc["tabs"], "assets": meta})
    if m["log"]:
        head["log"] = m["log"]
    return head


def _canon(obj):
    """Canonical JSON (sorted keys, no spaces) exactly as the editor's canon() writes it."""
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return re.sub("[\ud800-\udfff]", lambda m: "\\u%04x" % ord(m.group(0)), s)


def content_hash(doc, assets):
    """SHA-256 of the document's content: everything except the revision record, timestamps and log."""
    c = {"title": doc["title"], "subtitle": doc["subtitle"], "options": doc["options"], "tabs": doc["tabs"],
         "assets": dict((k, fingerprint(a)) for k, a in assets.items())}
    if doc.get("ai"):
        c["ai"] = doc["ai"]
    return hashlib.sha256(_canon(c).encode("utf-8")).hexdigest()


def bump_label(label, major=False):
    """1 -> 1.1 -> 1.2; major: 1.2 -> 2."""
    parts = label.split(".") if re.fullmatch(_LABEL, label or "") else ["1"]
    if major:
        return str(int(parts[0]) + 1)
    if len(parts) == 1:
        return parts[0] + ".1"
    return ".".join(parts[:-1] + [str(int(parts[-1]) + 1)])


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render(doc, assets, today=None):
    """The complete HTML of a document, identical to what the editor saves."""
    source = _js_json(data_block(doc, assets))
    title = trim(doc["title"]) or "Untitled document"
    tabcss = ""
    if len(doc["tabs"]) < 2:
        body = _render_tab(doc["tabs"][0], doc, assets)
    else:
        body = ('<div class="tabs">\n<nav class="tabbar" aria-label="Tabs">' + "".join('<a href="#t-' + t["id"] + '">' + esc(_tab_name(t, i)) + "</a>" for i, t in enumerate(doc["tabs"])) + "</nav>\n"
                + "".join('<div class="panel" id="t-' + t["id"] + '">\n<h2 class="ptitle">' + esc(_tab_name(t, i)) + "</h2>\n" + _render_tab(t, doc, assets) + "</div>\n" for i, t in enumerate(doc["tabs"]))
                + "</div>\n")
        tabcss = (".tabs:not(:has(.panel:target,.panel :target)) .tabbar a:first-child,"
                  + ",".join(".tabs:has(#t-" + t["id"] + ":target,#t-" + t["id"] + ' :target) .tabbar a[href="#t-' + t["id"] + '"]' for t in doc["tabs"])
                  + "{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}")
    f = doc["options"]["footer"]
    foot = ""
    if f and f["on"]:
        if f["date"]:
            d = datetime.date(int(f["date"][:4]), int(f["date"][5:7]), int(f["date"][8:10]))
        else:
            d = today or datetime.date.today()
        bits = []
        if trim(f["author"]):
            bits.append(esc(trim(f["author"])))
        if trim(f["version"]):
            bits.append("Version " + esc(trim(f["version"])))
        bits.append("Updated " + esc("%s %d, %d" % (_MONTHS[d.month - 1], d.day, d.year)))
        foot = '<footer class="meta">' + ' <span aria-hidden="true">\u00b7</span> '.join(bits) + "</footer>\n"
    lg = assets.get(doc["options"]["logo"])
    st = doc["options"]["status"] if doc["options"]["status"] in STATUS else ""
    h1 = "<h1>" + esc(title) + "</h1>\n" + ('<p class="sub">' + esc(trim(doc["subtitle"])) + "</p>\n" if trim(doc["subtitle"]) else "")
    if lg or st:
        h1 = ('<header class="head">\n' + ('<img class="logo" id="asset-' + doc["options"]["logo"] + '" alt="Logo" src="data:' + lg["type"] + ";base64," + lg["b64"] + '">\n' if lg else "")
              + '<div class="ht">\n' + ('<p class="status st-' + st + '">' + STATUS[st] + "</p>\n" if st else "") + h1 + "</div>\n</header>\n")
    ac = ACCENTS.get(doc["options"]["accent"])
    tint = ""
    if ac and doc["options"]["accent"] != "green":
        tint = (":root{--accent:" + ac[1] + ";--accent-ink:" + ac[2] + ";--accent-text:" + ac[5] + "}"
                + "@media (prefers-color-scheme:dark){:root{--accent:" + ac[3] + ";--accent-ink:" + ac[4] + ";--accent-text:" + ac[3] + "}}")
    n_files = len(assets) - (1 if doc["options"]["logo"] in assets else 0)
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            + '<meta http-equiv="Content-Security-Policy" content="' + DOC_CSP + '">\n<meta name="generator" content="' + GENERATOR + '">\n'
            + "<title>" + esc(title) + '</title>\n<script type="application/json" id="doc-source">' + source + "</script>\n<style>" + DOC_CSS + tint + tabcss + "</style>\n</head>\n<body>\n<main>\n"
            + h1 + hx_panels(doc, assets) + body + foot + (about_html(n_files > 0) if doc["options"]["about"] else "") + "</main>\n</body>\n</html>\n")


# ---------------------------------------------------------------------------
# Loading: a port of the editor's loader. It accepts the JSON stored in a document
# (and the older layouts) and returns a clean document plus its attachments.
# ---------------------------------------------------------------------------
_BLOCK_TYPES = ("heading", "text", "markdown", "images", "table", "collapsible", "checklist", "callout", "files")


def _s(x):
    """JavaScript's String(x) for values that come out of JSON."""
    if isinstance(x, str):
        return x
    if x is None:
        return ""
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, float) and x == int(x) and abs(x) < 1e21:
        return str(int(x))
    if isinstance(x, list):
        return ",".join(_s(i) for i in x)
    if isinstance(x, dict):
        return "[object Object]"
    return str(x)


def _b(x):
    """JavaScript truthiness (an empty list or object is true, unlike Python)."""
    if x is None or x is False:
        return False
    if isinstance(x, (int, float)):
        return x != 0 and x == x
    if isinstance(x, str):
        return x != ""
    return True


def _or(a, b):
    return a if _b(a) else b


def _has(d, k):
    return isinstance(k, str) and k in d


class IdMaker(object):
    """Deterministic ids, so the same input always produces the same file."""

    def __init__(self, seed=""):
        self.n = 0
        self.seed = seed

    def next(self):
        self.n += 1
        return "a" + hashlib.sha1(("%s/%d" % (self.seed, self.n)).encode("utf-8")).hexdigest()[:12]


# Version 1.1 metadata: document identity, revision record, AI Notes and Revision Log.
# Every rule here has a twin in the editor's loader, so both read a file the same way.
_ID = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}"
_DOCID = r"[A-Za-z0-9][A-Za-z0-9._:-]{5,63}"
_HASH = r"[0-9a-f]{64}"
_TIME = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
_LABEL = r"[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}"


def prune(o):
    """Drop empty values ('' , [] and None) so the data block stays small."""
    return dict((k, v) for k, v in o.items() if not (v is None or (isinstance(v, str) and v == "") or (isinstance(v, list) and not v)))


def _match(rx, x):
    return x if isinstance(x, str) and re.fullmatch(rx, x) else ""


def _int(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x or x < 0 or x > 1e9 or x != int(x):
        return 0
    return int(x)


def _lf(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _ids(v, known=None):
    out = []
    for x in (v if isinstance(v, list) else []):
        if isinstance(x, str) and re.fullmatch(_ID, x) and x not in out and (known is None or x in known):
            out.append(x)
    return out


def _strs(v):
    return [x for x in v if isinstance(x, str) and trim(x)] if isinstance(v, list) else []


def norm_work(w):
    if not isinstance(w, dict):
        return None
    o = prune({"task": _s(w.get("task")), "stage": _s(w.get("stage")), "role": _s(w.get("role")), "assignee": _s(w.get("assignee")),
               "status": w.get("status") if _has(WORK, w.get("status")) else "", "objective": _lf(_s(w.get("objective"))),
               "instructions": _lf(_s(w.get("instructions"))), "targets": _ids(w.get("targets")), "sources": _ids(w.get("sources")),
               "deliverables": _strs(w.get("deliverables")), "done": _strs(w.get("done")), "review": _lf(_s(w.get("review"))),
               "base": _match(_HASH, w.get("base"))})
    return o or None


def norm_ai(a, known):
    if not isinstance(a, dict):
        return None
    o = prune({"notes": _lf(_s(a.get("notes"))), "focus": _ids(a.get("focus"), known), "protect": _ids(a.get("protect"), known), "work": norm_work(a.get("work"))})
    return o or None


def norm_entry(e):
    if not isinstance(e, dict):
        return None
    return prune({"rev": _int(e.get("rev")), "label": _match(_LABEL, e.get("label")), "at": _match(_TIME, e.get("at")), "by": _s(e.get("by")),
                  "kind": e.get("kind") if _has(KINDS, e.get("kind")) else "", "summary": _lf(_s(e.get("summary"))), "blocks": _ids(e.get("blocks")),
                  "status": e.get("status") if _has(WORK, e.get("status")) else "", "checks": _lf(_s(e.get("checks"))), "note": _lf(_s(e.get("note")))})


def norm_meta(data):
    rev = data.get("rev") if isinstance(data.get("rev"), dict) else {}
    src = data.get("source") if isinstance(data.get("source"), dict) else {}
    log = data.get("log") if isinstance(data.get("log"), list) else []
    return {"id": _match(_DOCID, data.get("id")),
            "rev": {"n": _int(rev.get("n")), "label": _match(_LABEL, rev.get("label")), "hash": _match(_HASH, rev.get("hash")), "parent": _match(_HASH, rev.get("parent"))},
            "created": _match(_TIME, data.get("created")), "modified": _match(_TIME, data.get("modified")),
            "source": prune({"system": _s(src.get("system")), "ref": _s(src.get("ref"))}) or None,
            "log": [x for x in (norm_entry(e) for e in log) if x is not None]}


def new_doc_id():
    import secrets
    return "hx-" + secrets.token_hex(8)


def known_ids(doc):
    s = set()
    for t in doc["tabs"]:
        s.add(t["id"])
        for b in t["blocks"]:
            s.add(b["id"])
    return s


def load_data(data, find, ids=None):
    """data: parsed JSON. find(id) -> dict(name, type, b64, hint) or None.
    Returns (doc, assets, missing, bad)."""
    ids = ids or IdMaker()
    if isinstance(data.get("tabs"), list):
        tabs_in = data["tabs"]
    elif isinstance(data.get("blocks"), list):
        tabs_in = [{"title": "", "blocks": data["blocks"]}]
    else:
        raise ValueError("The data in this file is not in a format this tool knows.")
    op = data.get("options") if isinstance(data.get("options"), dict) else {}
    fo = op.get("footer") if isinstance(op.get("footer"), dict) else {}
    info = data.get("assets") if isinstance(data.get("assets"), dict) else {}
    nd = {"title": _s(data.get("title")), "subtitle": _s(data.get("subtitle")),
          "options": {"toc": _b(op.get("toc")), "accent": op.get("accent") if _has(ACCENTS, op.get("accent")) else "green",
                      "footer": {"on": _b(fo.get("on")), "author": _s(fo.get("author")), "version": _s(fo.get("version")),
                                 "date": fo.get("date") if isinstance(fo.get("date"), str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fo.get("date")) else ""},
                      "logo": "", "status": op.get("status") if _has(STATUS, op.get("status")) else "", "fingerprints": _b(op.get("fingerprints")), "about": _b(op.get("about"))},
          "tabs": []}
    assets = {}
    state = {"missing": 0, "bad": [], "seen": set()}

    def keep(id_):
        id_ = _s(id_)
        if re.fullmatch(r"a[a-z0-9]{6,24}", id_) and id_ not in state["seen"]:
            state["seen"].add(id_)
            return id_
        while True:
            n = ids.next()
            if n not in state["seen"]:
                break
        state["seen"].add(n)
        return n

    def take(id_):
        id_ = _s(id_)
        el = find(id_)
        if not el:
            state["missing"] += 1
            return None
        m = info.get(id_) if isinstance(info.get(id_), dict) else {}
        nid = keep(id_)
        b64 = el["b64"]
        pad = 2 if b64[-2:] == "==" else 1 if b64[-1:] == "=" else 0
        a = {"name": _s(m.get("name")) or el.get("hint") or "file", "type": clean_type(el["type"]), "b64": b64, "bytes": len(b64) * 3 // 4 - pad}
        assets[nid] = a
        if m.get("sha256") and fingerprint(a) != m.get("sha256"):
            state["bad"].append(a["name"])
        return nid

    for tin in tabs_in:
        tin = tin if isinstance(tin, dict) else {}
        tab = {"id": keep(tin.get("id")), "title": _s(tin.get("title")), "blocks": []}
        nd["tabs"].append(tab)
        for s in (tin.get("blocks") if isinstance(tin.get("blocks"), list) else []):
            if not isinstance(s, dict):
                continue
            t = s.get("type")
            t = {"gallery": "images", "attachments": "files"}.get(t, t) if isinstance(t, str) else None
            if t == "keyvalues":
                items = s.get("items") if isinstance(s.get("items"), list) else []
                s = dict(s)
                s["rows"] = [["Detail", "Value"]] + [[_s(it.get("label")), _s(it.get("value"))] for it in items if isinstance(it, dict) and (trim(_s(it.get("label"))) or trim(_s(it.get("value"))))]
                t = "table"
            if t not in _BLOCK_TYPES:
                continue
            b = {"id": keep(s.get("id")), "type": t}
            if t == "heading":
                b["text"] = _s(s.get("text"))
            else:
                b["title"] = _s(s.get("title"))
                b["half"] = _b(s.get("half"))
                if t == "text":
                    h = s.get("html") if s.get("html") is not None else ("<p>" + esc(_s(s.get("text"))) + "</p>" if _b(s.get("text")) else "")
                    b["html"] = sanitize(_s(h))
                if t == "markdown":
                    b["md"] = _s(s.get("md") if s.get("md") is not None else s.get("text")).replace("\r\n", "\n").replace("\r", "\n")
                if t == "images":
                    raw = s.get("items") if _b(s.get("items")) else [{"asset": a} for a in (_or(s.get("assets"), []))]
                    items = []
                    for it in raw:
                        it = it if isinstance(it, dict) else {}
                        id_ = take(it.get("asset"))
                        if id_:
                            items.append({"asset": id_, "caption": _s(it.get("caption"))})
                    b["items"] = items
                if t == "files":
                    b["items"] = []
                    b["desc"] = _b(s.get("desc"))
                    b["notes"] = {}
                    notes = s.get("notes") if isinstance(s.get("notes"), dict) else {}
                    for old in _or(s.get("items"), _or(s.get("assets"), [])):
                        id_ = take(old)
                        n = notes.get(_s(old))
                        if id_:
                            b["items"].append(id_)
                            if _b(n):
                                b["notes"][id_] = _s(n)
                if t == "callout":
                    b["tone"] = s.get("tone") if _has(TONES, s.get("tone")) else "note"
                    b["text"] = _s(s.get("text"))
                if t == "collapsible":
                    its = s.get("items") if isinstance(s.get("items"), list) else []
                    b["items"] = [{"summary": _s(i.get("summary") if isinstance(i, dict) else None), "body": _s(i.get("body") if isinstance(i, dict) else None)} for i in its]
                    if not b["items"]:
                        b["items"] = [{"summary": "", "body": ""}]
                if t == "checklist":
                    its = s.get("items") if isinstance(s.get("items"), list) else []
                    b["items"] = [{"text": _s(i.get("text") if isinstance(i, dict) else None), "done": isinstance(i, dict) and _b(i.get("done"))} for i in its]
                    if not b["items"]:
                        b["items"] = [{"text": "", "done": False}]
                if t == "table":
                    rows = list(s.get("rows")) if isinstance(s.get("rows"), list) else []
                    if isinstance(s.get("columns"), list):
                        rows.insert(0, s["columns"])
                    rows = [r for r in rows if isinstance(r, list)]
                    w = max([len(r) for r in rows] + [1])
                    b["rows"] = [[_s(r[k]) if k < len(r) else "" for k in range(w)] for r in rows]
                    if not b["rows"]:
                        b["rows"] = [["Column 1"], [""]]
                    if len(b["rows"]) < 2:
                        b["rows"].append(["" for _ in b["rows"][0]])
            tab["blocks"].append(b)
    if not nd["tabs"]:
        nd["tabs"].append({"id": keep(""), "title": "", "blocks": []})
    if op.get("logo"):
        lg = take(op["logo"])
        if lg:
            nd["options"]["logo"] = lg
    nd["ai"] = norm_ai(data.get("ai"), known_ids(nd))
    m = norm_meta(data)
    if not m["id"]:
        m["id"] = new_doc_id()
    if m["rev"]["n"] < 1:
        m["rev"]["n"] = 1
    if not m["rev"]["label"]:
        m["rev"]["label"] = str(m["rev"]["n"])
    if not m["rev"]["hash"]:
        m["rev"]["hash"] = content_hash(nd, assets)
    nd["meta"] = m
    return nd, assets, state["missing"], state["bad"]


# ---------------------------------------------------------------------------
# Reading a document file.
# ---------------------------------------------------------------------------
import mimetypes
import os
import sys


class _Reader(HTMLParser):
    """Finds the data block and every element that carries an embedded file."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.source = None
        self.els = {}
        self.scripts = []
        self._in_source = False
        self._buf = []
        self.bad_attrs = []
        self.csp = None
        self.generator = None
        self.external = []

    def handle_starttag(self, tag, attrs):
        a = dict((k, "" if v is None else v) for k, v in attrs)
        if tag == "script":
            self.scripts.append(a)
            if a.get("id") == "doc-source" and self.source is None:
                self._in_source = True
                self._buf = []
        for k in a:
            if k.startswith("on"):
                self.bad_attrs.append(tag + "[" + k + "]")
        if tag == "meta":
            if a.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = a.get("content")
            if a.get("name") == "generator":
                self.generator = a.get("content")
        if a.get("id") and a["id"] not in self.els:
            self.els[a["id"]] = (tag, a)
        for k in ("src", "href"):
            v = a.get(k)
            if v is not None and tag != "a" and not v.startswith("data:") and not v.startswith("#"):
                self.external.append(tag + " " + k + "=" + v[:60])
            if v is not None and tag == "a" and k == "href" and v.lower().startswith("javascript:"):
                self.external.append("a javascript: link")

    def handle_endtag(self, tag):
        if tag == "script" and self._in_source:
            self._in_source = False
            self.source = "".join(self._buf)

    def handle_data(self, data):
        if self._in_source:
            self._buf.append(data)


def read_document(text):
    """Parse a Helix file. Returns (doc, assets, missing, bad, reader)."""
    r = _Reader()
    r.feed(text)
    r.close()
    if r.source is None:
        raise ValueError("This file has no editing data (an element with id doc-source), so it is not a Helix document.")
    try:
        data = json.loads(r.source)
    except ValueError:
        raise ValueError("The data block in this file is damaged.")
    if not isinstance(data, dict):
        raise ValueError("The data block in this file is not in a format this tool knows.")

    def find(id_):
        e = r.els.get("asset-" + id_) or r.els.get(id_)
        if not e:
            return None
        tag, a = e
        url = a.get("src") or a.get("href") or ""
        i = url.find(",")
        head = url[:i]
        if i < 0 or url[:5] != "data:" or not re.search(r";base64$", head, re.I):
            return None
        return {"b64": url[i + 1:], "type": head[5:].split(";")[0], "hint": a.get("download")}
    doc, assets, missing, bad = load_data(data, find)
    return doc, assets, missing, bad, r, data


# ---------------------------------------------------------------------------
# Unpacking: the document as Markdown plus the original files.
# ---------------------------------------------------------------------------
def _ex_plain(t):
    return re.sub(r"([\\*_`\[\]])", r"\\\1", t)


def _ex_inl(n):
    if isinstance(n, str):
        return _ex_plain(n)
    t = n.tag
    inner = "".join(_ex_inl(c) for c in n.kids)
    if t == "br":
        return "  \n"
    if t == "strong":
        return "**" + trim(inner) + "**" if trim(inner) else inner
    if t == "em":
        return "*" + trim(inner) + "*" if trim(inner) else inner
    if t == "a":
        hr = n.attrs.get("href") or ""
        return "[" + inner + "](" + hr.replace(")", "%29") + ")" if hr else inner
    return inner


def _ex_list(l, d):
    ordered = l.tag == "ol"
    k = 0
    lines = []
    pad = " " * (d * 3)
    for li in l.kids:
        if isinstance(li, str) or li.tag != "li":
            continue
        k += 1
        text = ""
        nested = []
        for c in li.kids:
            if not isinstance(c, str) and c.tag in ("ul", "ol"):
                nested.append(_ex_list(c, d + 1))
            else:
                text += _ex_inl(c)
        lines.append(pad + (("%d. " % k) if ordered else "- ") + trim(text).replace("\n", "\n" + pad + "   "))
        lines.extend(nested)
    return "\n".join(lines)


def _ex_html(html):
    root = parse_fragment(html)
    out = []
    buf = [""]

    def flush():
        if trim(buf[0]):
            out.append(trim(buf[0]))
        buf[0] = ""
    for c in root.kids:
        if not isinstance(c, str) and c.tag == "p":
            flush()
            out.append(trim(_ex_inl(c)))
        elif not isinstance(c, str) and c.tag in ("ul", "ol"):
            flush()
            out.append(_ex_list(c, 0))
        else:
            buf[0] += _ex_inl(c)
    flush()
    return "\n\n".join(x for x in out if x)


def _ex_cell(v):
    return trim(re.sub(r"\s*\n\s*", " ", v.replace("|", "\\|")))


def _ex_path(p):
    from urllib.parse import quote
    return quote(p or "", safe=";,/?:@&=+$-_.!~*'()#").replace("(", "%28").replace(")", "%29")


def _ex_paras(t):
    return [_ex_plain(trim(p)) for p in re.split(r"\n+", t) if trim(p)]


def _ex_body(b, assets, paths):
    t = b["type"]
    if t == "text":
        return _ex_html(sanitize(b["html"]))
    if t == "markdown":
        return trim(b["md"])
    if t == "callout":
        tone = TONES.get(b["tone"], "Note")
        return "\n>\n".join("> " + ("**" + tone + ":** " if i == 0 else "") + p for i, p in enumerate(_ex_paras(b["text"])))
    if t == "checklist":
        return "\n".join("- [" + ("x" if it["done"] else " ") + "] " + _ex_plain(trim(it["text"])) for it in b["items"] if trim(it["text"]))
    if t == "collapsible":
        out = []
        for it in b["items"]:
            if not (trim(it["summary"]) or trim(it["body"])):
                continue
            body = "\n\n".join(_ex_paras(it["body"]))
            out.append("**" + _ex_plain(trim(it["summary"]) or "Details") + "**" + ("\n\n" + body if body else ""))
        return "\n\n".join(out)
    if t == "table":
        rows = [r for r in b["rows"][1:] if any(trim(x) for x in r)]
        if not rows:
            return ""
        return "\n".join(["| " + " | ".join(_ex_cell(x) for x in b["rows"][0]) + " |", "| " + " | ".join("---" for _ in b["rows"][0]) + " |"]
                         + ["| " + " | ".join(_ex_cell(x) for x in r) + " |" for r in rows])
    if t == "images":
        out = []
        for it in b["items"]:
            a = assets.get(it["asset"])
            if not a:
                continue
            cap = trim(it["caption"])
            out.append("![" + _ex_plain(cap or a["name"]) + "](" + _ex_path(paths.get(it["asset"])) + ")" + ("\n*" + _ex_plain(cap) + "*" if cap else ""))
        return "\n\n".join(out)
    if t == "files":
        out = []
        for id_ in b["items"]:
            a = assets.get(id_)
            if not a:
                continue
            note = trim(b["notes"][id_]) if b["desc"] and b["notes"] and b["notes"].get(id_) else ""
            out.append("- [" + _ex_plain(a["name"]) + "](" + _ex_path(paths.get(id_)) + ") (" + fmt_size(a["bytes"]) + ")" + (" - " + _ex_plain(note) if note else "") + "\n  SHA-256: `" + fingerprint(a) + "`")
        return "\n".join(out)
    return ""


def gather_files(doc, assets):
    """Plan the folder layout for unpacked files: [(path, id)] in document order."""
    used = {}
    paths = {}
    order = []

    def add(folder, id_):
        a = assets.get(id_)
        if not a:
            return
        base = folder + "/" + (re.sub(r'[\\/:*?"<>|\u0000-\u001f]', "_", a["name"]) or "file")
        name = base
        k = 2
        dot = base.rfind(".")
        while name.lower() in used:
            name = (base[:dot] + " (%d)" % k + base[dot:]) if dot > len(folder) + 1 else base + " (%d)" % k
            k += 1
        used[name.lower()] = 1
        paths[id_] = name
        order.append((name, id_))
    if doc["options"]["logo"]:
        add("images", doc["options"]["logo"])
    for t in doc["tabs"]:
        for b in t["blocks"]:
            if b["type"] == "images":
                for it in b["items"]:
                    add("images", it["asset"])
            if b["type"] == "files":
                for id_ in b["items"]:
                    add("files", id_)
    return order, paths


def doc_to_markdown(doc, assets, paths):
    L = []
    multi = len(doc["tabs"]) > 1
    base = 2 if multi else 1
    st = STATUS.get(doc["options"]["status"])

    def hd(n, t):
        return "#" * min(6, n) + " " + t
    L.append(hd(1, trim(doc["title"]) or "Untitled document"))
    if st:
        L.append("**Status:** " + st)
    if trim(doc["subtitle"]):
        L.append(trim(doc["subtitle"]))
    L.append("> Exported from a Helix document. Images and attached files are in the folders next to this file, and the paths below are relative to it. SHA256SUMS.txt lists the SHA-256 fingerprint of each file.")
    for ti, t in enumerate(doc["tabs"]):
        seen = False
        if multi:
            L.append(hd(2, _tab_name(t, ti)))
        for b in t["blocks"]:
            if b["type"] == "heading":
                if trim(b["text"]):
                    L.append(hd(base + 1, trim(b["text"])))
                    seen = True
                continue
            body = _ex_body(b, assets, paths)
            title = hd(base + (2 if seen else 1), trim(b["title"])) if trim(b.get("title", "")) else ""
            if title:
                L.append(title)
            if body:
                L.append(body)
    return "\n\n".join(L) + "\n"


def spec_from_document(doc, assets, paths):
    """A spec that rebuilds this document from the unpacked files (see the guide)."""
    def named(entry, id_):
        # keep the display name when the file on disk had to be renamed (clashes, characters not allowed in file names)
        if assets[id_]["name"] != paths[id_].split("/")[-1]:
            entry["name"] = assets[id_]["name"]
        return entry

    def bk(b):
        o = {"id": b["id"], "type": b["type"]}
        if b["type"] == "heading":
            o["text"] = b["text"]
            return o
        o["title"] = b["title"]
        if b["half"]:
            o["half"] = True
        t = b["type"]
        if t == "text":
            o["html"] = b["html"]
        elif t == "markdown":
            o["md"] = b["md"]
        elif t == "images":
            o["items"] = [named({"id": i["asset"], "file": paths[i["asset"]], "caption": i["caption"]}, i["asset"]) for i in b["items"]]
        elif t == "files":
            o["desc"] = b["desc"]
            o["items"] = [named({"id": i, "file": paths[i], "note": b["notes"].get(i, "")}, i) for i in b["items"]]
        elif t == "callout":
            o["tone"] = b["tone"]
            o["text"] = b["text"]
        elif t in ("collapsible", "checklist"):
            o["items"] = b["items"]
        elif t == "table":
            o["rows"] = b["rows"]
        return o
    op = dict(doc["options"])
    if op["logo"]:
        op["logo_id"] = op["logo"]
    op["logo"] = paths.get(op["logo"], "")
    m = doc["meta"]
    out = {"id": m["id"], "rev": prune(m["rev"])}
    for k in ("created", "modified", "source"):
        if m.get(k):
            out[k] = m[k]
    if doc.get("ai"):
        out["ai"] = doc["ai"]
    out.update({"title": doc["title"], "subtitle": doc["subtitle"], "options": op,
                "tabs": [{"id": t["id"], "title": t["title"], "blocks": [bk(b) for b in t["blocks"]]} for t in doc["tabs"]]})
    if m["log"]:
        out["log"] = m["log"]
    return out


def unpack(path, outdir):
    text = open(path, encoding="utf-8").read()
    doc, assets, missing, bad, _r, _d = read_document(text)
    order, paths = gather_files(doc, assets)
    os.makedirs(outdir, exist_ok=True)
    sums = []
    for name, id_ in order:
        full = os.path.join(outdir, *name.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        data = base64.b64decode(assets[id_]["b64"])
        with open(full, "wb") as fh:
            fh.write(data)
        sums.append(hashlib.sha256(data).hexdigest() + "  " + name + "\n")
    with open(os.path.join(outdir, "content.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(doc_to_markdown(doc, assets, paths))
    if sums:
        with open(os.path.join(outdir, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(sums))
    with open(os.path.join(outdir, "spec.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(spec_from_document(doc, assets, paths), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return {"files": len(order), "missing": missing, "bad": bad}


# ---------------------------------------------------------------------------
# Building from a spec.
# ---------------------------------------------------------------------------
_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
          ".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv", ".json": "application/json", ".html": "text/html", ".htm": "text/html", ".zip": "application/zip",
          ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".doc": "application/msword", ".xls": "application/vnd.ms-excel", ".ppt": "application/vnd.ms-powerpoint",
          ".mp3": "audio/mpeg", ".mp4": "video/mp4", ".mov": "video/quicktime", ".wav": "audio/wav", ".eml": "message/rfc822", ".rtf": "application/rtf", ".xml": "application/xml"}
LIMIT = 25 * 1048576
MAX_PIXELS = 1600


def _guess_type(name):
    ext = os.path.splitext(name)[1].lower()
    return _TYPES.get(ext) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def _shrink(data, mime):
    """Scale a large photo down (only when Pillow is installed, and only if it gets smaller)."""
    if mime not in ("image/jpeg", "image/png"):
        return data
    try:
        import io
        from PIL import Image, ImageOps
    except ImportError:
        return data
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if max(im.size) <= MAX_PIXELS:
            return data
        im.thumbnail((MAX_PIXELS, MAX_PIXELS))
        out = io.BytesIO()
        if mime == "image/jpeg":
            im.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
        else:
            im.save(out, "PNG", optimize=True)
        return out.getvalue() if len(out.getvalue()) < len(data) else data
    except Exception:
        return data


def build_from_spec(spec, base_dir=".", shrink=True, today=None, now=None):
    """Turn a spec into (html, problems).

    The revision record follows one rule: a spec without rev.hash is a new document (revision 1, or the rev it names);
    a spec whose content still matches rev.hash is rebuilt unchanged; otherwise it becomes the next revision."""
    html, problems, _doc = build_doc_from_spec(spec, base_dir, shrink, today, now)
    return html, problems


def build_doc_from_spec(spec, base_dir=".", shrink=True, today=None, now=None):
    problems = []
    files = {}
    order = []
    taken = set()

    def reg(path, for_images, name=None, want=None):
        if not isinstance(path, str) or not path:
            problems.append("a file reference is empty")
            return None
        full = path if os.path.isabs(path) else os.path.join(base_dir, path)
        key = (full, for_images, name, want)
        if key in files:
            return files[key]
        if not os.path.isfile(full):
            problems.append("file not found: " + path)
            return None
        data = open(full, "rb").read()
        mime = _guess_type(full)
        if for_images and shrink:
            data = _shrink(data, mime)
        id_ = want if isinstance(want, str) and re.fullmatch(r"a[a-z0-9]{6,24}", want) and want not in taken else "spec%d" % len(order)
        taken.add(id_)
        files[key] = id_
        order.append((id_, {"name": name or os.path.basename(full), "type": mime, "b64": base64.b64encode(data).decode("ascii"), "bytes": len(data), "hint": name or os.path.basename(full)}))
        return id_
    spec = json.loads(json.dumps(spec))
    op = spec.get("options") if isinstance(spec.get("options"), dict) else {}
    op.setdefault("about", True)
    spec["options"] = op
    if "tabs" not in spec and isinstance(spec.get("blocks"), list):
        spec["tabs"] = [{"title": "", "blocks": spec["blocks"]}]
    for t in spec.get("tabs") or []:
        for b in (t.get("blocks") or []):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and "html" not in b and isinstance(b.get("text"), str):
                b["html"] = "".join("<p>" + esc(trim(p)) + "</p>" for p in _paras(b["text"]))
                b.pop("text", None)
            if b.get("type") == "images":
                items = []
                for it in b.get("items") or []:
                    it = {"file": it} if isinstance(it, str) else dict(it)
                    items.append({"asset": reg(it.get("file"), True, it.get("name"), it.get("id")), "caption": it.get("caption", "")})
                b["items"] = items
            if b.get("type") == "files":
                items = []
                notes = {}
                for it in b.get("items") or []:
                    it = {"file": it} if isinstance(it, str) else dict(it)
                    id_ = reg(it.get("file"), False, it.get("name"), it.get("id"))
                    if id_:
                        items.append(id_)
                        if it.get("note"):
                            notes[id_] = it["note"]
                b["items"] = items
                b["notes"] = notes
                if notes:
                    b.setdefault("desc", True)
    if isinstance(op.get("logo"), str) and op["logo"]:
        op["logo"] = reg(op["logo"], True, None, op.get("logo_id"))
    op.pop("logo_id", None)
    by_id = dict(order)
    spec["assets"] = {}
    if spec.get("format") == "helix" and isinstance(spec.get("version"), (int, float)) and not isinstance(spec.get("version"), bool) and spec["version"] > FORMAT_VERSION:
        raise ValueError("this spec says format version %s, newer than this tool (version %d)" % (spec["version"], FORMAT_VERSION))
    ids = IdMaker(_s(spec.get("title")))
    raw_rev = spec.get("rev") if isinstance(spec.get("rev"), dict) else {}
    had = _match(_HASH, raw_rev.get("hash"))
    doc, assets, missing, _bad = load_data(spec, lambda i: by_id.get(i), ids)
    m = doc["meta"]
    fresh = content_hash(doc, assets)
    stamp = now or now_iso()
    by = trim(_s(spec.get("by"))) or "helix.py"
    kind = spec.get("kind") if _has(KINDS, spec.get("kind")) else ("tool" if by == "helix.py" else "")
    if not had:
        m["rev"]["hash"] = fresh
        m["rev"]["parent"] = m["rev"]["parent"] if m["rev"]["n"] > 1 else ""
        m["created"] = m["created"] or stamp
        m["modified"] = m["modified"] or m["created"]
        if not m["log"]:
            m["log"] = [prune({"rev": m["rev"]["n"], "label": m["rev"]["label"], "at": m["created"], "by": by, "kind": kind,
                               "summary": _s(spec.get("summary")) or ("Created" if m["rev"]["n"] == 1 else "")})]
    elif fresh != had:
        n = m["rev"]["n"] + 1
        label = bump_label(m["rev"]["label"], bool(spec.get("major")))
        m["rev"] = {"n": n, "label": label, "hash": fresh, "parent": had}
        m["modified"] = stamp
        m["log"].append(prune({"rev": n, "label": label, "at": stamp, "by": by, "kind": kind, "summary": _s(spec.get("summary")) or "Rebuilt from spec"}))
    html = render(doc, assets, today)
    size = len(html.encode("utf-8"))
    if size > LIMIT:
        problems.append("the finished file is %s, over the 25 MB limit" % fmt_size(size))
    return html, problems, doc


# ---------------------------------------------------------------------------
# Checking a document.
# ---------------------------------------------------------------------------
def _outside_data(html):
    return re.sub(r'<script type="application/json" id="doc-source">.*?</script>', "<script/>", html, count=1, flags=re.S)


def check_document(text):
    """Returns (problems, notes)."""
    problems = []
    notes = []
    try:
        doc, assets, missing, bad, r, data = read_document(text)
    except ValueError as e:
        return [str(e)], notes
    others = [s for s in r.scripts if s.get("id") != "doc-source"]
    if others or len(r.scripts) != 1:
        problems.append("the file contains %d script element(s); only the data block is allowed" % len(r.scripts))
    if r.scripts and (r.scripts[0].get("type") != "application/json"):
        problems.append("the data block is not type application/json")
    if r.bad_attrs:
        problems.append("event-handler attributes found: " + ", ".join(sorted(set(r.bad_attrs))[:5]))
    if r.csp != DOC_CSP:
        problems.append("the security policy line is missing or changed")
    if r.external:
        problems.append("references to things outside the file: " + "; ".join(r.external[:3]))
    if data.get("format") not in ("helix", "hlx"):
        notes.append("the data block does not say format helix")
    elif data.get("format") == "hlx":
        notes.append("made before version 1.0 (format hlx); opening and saving it in the editor upgrades it")
    if missing:
        problems.append("%d embedded file(s) could not be read" % missing)
    if bad:
        problems.append("file(s) do not match their saved fingerprint: " + ", ".join(bad[:5]))
    for id_, a in assets.items():
        info = (data.get("assets") or {}).get(id_)
        if not info or not info.get("sha256"):
            notes.append("no fingerprint saved for " + a["name"])
    size = len(text.encode("utf-8"))
    if size > LIMIT:
        problems.append("the file is %s, over the 25 MB limit" % fmt_size(size))
    if r.generator == GENERATOR:
        date = doc["options"]["footer"]["date"]
        try:
            again = render(doc, assets, None if date else _guess_today(text))
        except Exception as e:
            again = ""
            problems.append("could not rebuild the page: %r" % e)
        if again and _outside_data(again) != _outside_data(text):
            problems.append("the visible page does not match the data block (it was edited by hand, or made by something else)")
        try:
            if json.loads(_js_json(data_block(doc, assets))) != data:
                notes.append("the data block was normalised when read (older or unusual layout)")
        except Exception:
            pass
    else:
        notes.append("made by a different version (%s), so the page layout was not compared" % (r.generator or "unknown"))
    return problems, notes


def _guess_today(text):
    m = re.search(r"Updated ((?:%s) \d{1,2}, \d{4})" % "|".join(_MONTHS), text)
    if m:
        mo, d, y = re.match(r"(\w+) (\d+), (\d+)", m.group(1)).groups()
        return datetime.date(int(y), _MONTHS.index(mo) + 1, int(d))
    return datetime.date.today()


# ---------------------------------------------------------------------------
# Command line.
# ---------------------------------------------------------------------------
USAGE = """helix.py - build, unpack and check Helix documents (single-file, script-free HTML documents)

  python helix.py build spec.json output.helix.html [--no-shrink]
      Build a document from a JSON spec. File paths in the spec are relative to the spec's folder.
  python helix.py unpack document.helix.html outfolder
      Write content.md, spec.json, SHA256SUMS.txt and the original files (files/, images/).
  python helix.py check document.helix.html
      Verify the document: no scripts, security policy intact, files match their fingerprints, page matches data.
  python helix.py md notes.md
      Print the HTML that a Markdown block would produce for this file.

Standard library only. Photos in Images blocks are scaled to 1600 px if Pillow is installed (--no-shrink to keep them).
"""


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        sys.stdout.write(USAGE)
        return 0
    cmd = argv[1]
    args = [a for a in argv[2:] if not a.startswith("--")]
    flags = [a for a in argv[2:] if a.startswith("--")]
    try:
        if cmd == "build" and len(args) == 2:
            spec = json.load(open(args[0], encoding="utf-8"))
            html, problems = build_from_spec(spec, os.path.dirname(os.path.abspath(args[0])), "--no-shrink" not in flags)
            for p in problems:
                print("PROBLEM: " + p)
            if problems:
                return 1
            with open(args[1], "w", encoding="utf-8", newline="") as fh:
                fh.write(html)
            problems, notes = check_document(html)
            for p in problems:
                print("PROBLEM: " + p)
            if problems:
                return 1
            print("OK: wrote %s (%s)" % (args[1], fmt_size(len(html.encode("utf-8")))))
            return 0
        if cmd == "unpack" and len(args) == 2:
            res = unpack(args[0], args[1])
            for b in res["bad"]:
                print("WARNING: %s does not match its saved fingerprint" % b)
            print("OK: wrote content.md, spec.json and %d file(s) to %s" % (res["files"], args[1]))
            return 1 if res["bad"] or res["missing"] else 0
        if cmd == "check" and len(args) == 1:
            problems, notes = check_document(open(args[0], encoding="utf-8").read())
            for p in problems:
                print("PROBLEM: " + p)
            for n in notes:
                print("NOTE: " + n)
            if not problems:
                print("OK")
            return 1 if problems else 0
        if cmd == "md" and len(args) == 1:
            sys.stdout.write(md_render(open(args[0], encoding="utf-8").read()) + "\n")
            return 0
    except (ValueError, OSError) as e:
        print("PROBLEM: %s" % e)
        return 1
    sys.stdout.write(USAGE)
    return 2


if __name__ == "__main__":
    sys.setrecursionlimit(20000)
    sys.exit(main(sys.argv))
```
<!-- helix.py end -->
