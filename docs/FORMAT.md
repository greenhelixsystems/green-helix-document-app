# The Helix document format

*Version 1, a plain-language draft. The reference implementation is [`tools/helix.py`](../tools/helix.py); the most detailed description is section 12 of [`guide/HELIX-guide.md`](../guide/HELIX-guide.md). This text is licensed CC BY 4.0.*

## Goal

One file that carries a complete deliverable, opens anywhere, can be trusted not to run code, and can still be taken apart and edited later by a person or a program.

## Files

- Extension: **`.helix.html`**. Media type: `text/html`.
- Files made before 1.0 used `.hlx.html` and `"format":"hlx"`. Readers should accept them.
- Maximum recommended size: 25 MB.

## The three rules

1. **No scripts.** The only `<script>` element is `<script type="application/json" id="doc-source">`. There are no event-handler attributes and no `javascript:` links.
2. **Nothing external.** A `<meta http-equiv="Content-Security-Policy">` line restricts everything to the file itself:
   `default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`. Images and attachments are base64 `data:` links.
3. **Everything visible.** No hidden elements or text. What the data block says, the page shows.

## Layout

```
<head>
  charset, viewport, Content-Security-Policy, generator, title
  <script type="application/json" id="doc-source">   the whole document as JSON, first
  <style>
<body>
  <main>  header, title, subtitle, tab bar, blocks (as HTML), footer, "About this file"
```

The data block comes before the stylesheet so a reader that looks only at the start of the file finds the complete document.

## The data block

JSON with these top-level keys:

| Key | Meaning |
|---|---|
| `format` | `"helix"` (older files: `"hlx"`) |
| `version` | `1` |
| `about` | The same words as the visible "About this file" section (present when the option is on) |
| `title`, `subtitle` | Text |
| `options` | `toc`, `accent`, `footer`, `logo`, `status`, `fingerprints`, `about` |
| `tabs` | Ordered tabs, each with an `id`, a `title` and ordered `blocks` |
| `assets` | One entry per image or file: `name`, `type`, `bytes`, `sha256` |

Block types: `heading`, `text`, `markdown`, `callout`, `checklist`, `table`, `collapsible`, `images`, `files`. The exact fields of each are in the guide (section 4 and section 12).

Every `<` in the JSON is written `<`, so the data can never end the script element early.

## Attachments

Each attachment's bytes appear **once**, in the page, as a `data:` link on an element whose id is `asset-` plus the asset's id in the data block. Its SHA-256 in the data block lets a reader check it. Attachments are never re-encoded.

## Tabs

With two or more tabs, a bar of links `#t-ID` switches panels using only CSS (`:target`). Printing shows every tab.

## Reading a document

1. Find the element with id `doc-source` and parse its JSON. That is the complete content.
2. Read attachments only when needed: decode the `data:` link whose element id is `asset-` plus the asset id, and compare its SHA-256 with the data block.

## Checking a document

`python tools/helix.py check file.helix.html` confirms: exactly one script (the data block), no event handlers, the security line intact, no external references, fingerprints match, the size is within limit, and that the visible page equals what the data block would produce. Files made by another version of the generator pass with a note that the layout was not compared.

## Stability

Version 1 is the first public version. Changes that old readers cannot understand will increase the version number; the editor will keep reading earlier versions.
