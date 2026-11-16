# Helix documents: guide for AI assistants

Format version __VERSION__, for Green Helix Document Editor __EDITOR__.

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
<meta name="generator" content="__GENERATOR__">
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
{"format":"helix","version":__VERSION__,"about":"This is a Helix document ...",
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
__ACCENT_ROWS__

## 13. The script

<!-- helix.py start -->
```python
__SCRIPT__
```
<!-- helix.py end -->
