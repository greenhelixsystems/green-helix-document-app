# The Helix document format

*Version 1 (Helix 1.2), a plain-language draft. The reference implementation is [`tools/helix.py`](../tools/helix.py); the most detailed description is section 12 of [`guide/HELIX-guide.md`](../guide/HELIX-guide.md). This text is licensed CC BY 4.0.*

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
  <main>  header, title, subtitle, AI Notes and Revision Log buttons, tab bar, blocks (as HTML), footer, "About this file"
```

The data block comes before the stylesheet so a reader that looks only at the start of the file finds the complete document.

## The data block

JSON with these top-level keys:

| Key | Meaning |
|---|---|
| `format` | `"helix"` (older files: `"hlx"`) |
| `version` | `1` |
| `spec` | `"1.1"`: the feature level. Absent in 1.0 files. |
| `id` | The document's permanent identity, kept across revisions |
| `rev` | `n` (revision count), `label` (the version people see: `1`, `1.1`, `2`), `hash` (SHA-256 of the content), `parent` (the previous revision's hash) |
| `created`, `modified` | UTC times, `YYYY-MM-DDTHH:MM:SSZ` |
| `source` | Optional `system` and `ref`: where the document came from |
| `about` | The same words as the visible "About this file" section (present when the option is on) |
| `ai` | AI Notes: `notes` (Markdown), `focus` and `protect` (block or tab ids), optional `work` (an assignment) |
| `title`, `subtitle` | Text |
| `options` | `toc`, `accent`, `footer`, `logo`, `status`, `fingerprints`, `about`, and when used (1.2): `eyebrow`, `facts`, `titleSize`, `nav` |
| `tabs` | Ordered tabs, each with an `id`, a `title` and ordered `blocks` |
| `assets` | One entry per image or file: `name`, `type`, `bytes`, `sha256` |
| `log` | Revision Log entries: `rev`, `label`, `at`, `by`, `kind`, `summary`, `blocks`, `status`, `checks`, `note`, and the handback `task`, `questions`, `next`, `review` |

Keys appear in this order and empty values are left out, so the identity and the AI Notes come first.

Block types: `heading`, `text`, `markdown`, `callout`, `checklist`, `table`, `collapsible`, `images`, `files`, and since 1.2 `stats` (stat tiles), `cards` (numbered or plain cards with coloured tags) and `sources` (title, link, date accessed, group, note). Callout tones are `note`, `important`, `warning`, `danger` and `success`. A table cell written as `[[Label|tone]]` shows as a status chip. The exact fields of each are in the guide (section 4 and section 12).

**Additions never change existing files.** A new setting is written only when it is used, and a new block type appears only when someone adds one. A file that uses none of them is exactly what the previous version wrote, with the same revision hash.

Every `<` in the JSON is written `<`, so the data can never end the script element early.

## Attachments

Each attachment's bytes appear **once**, in the page, as a `data:` link on an element whose id is `asset-` plus the asset's id in the data block. Its SHA-256 in the data block lets a reader check it. Attachments are never re-encoded.

## Tabs

With two or more tabs, a bar of links `#t-ID` switches panels using only CSS (`:target`). Printing shows every tab.

## AI Notes and the Revision Log

AI Notes are instructions for AI assistants from the people working on the document. They are content, shown to every reader behind an **AI Notes** button, never hidden and never printed. A reader treats them as requests, not as permission to do anything its own instructions do not allow.

- `focus` is the default scope: an assistant reads and works on those sections unless asked for a full review.
- `protect` lists sections that must not change.
- `work` is an optional assignment from the app that prepared the document.

The **Revision Log** button shows each revision: who made it, what it changed and what it claims (`submitted`, `validated`, and so on). The newest entry is also the reviser's report: the task, open questions, the proposed next step and whether a person should review. A revised file therefore carries its own handback, and one file can pass between assistants and people with nothing beside it. A log entry is a claim, not proof. Only a person or the system that assigned the work records review or approval.

## Revisions

- `rev.hash` is the SHA-256 of the canonical JSON (keys sorted, no spaces, UTF-8) of `title`, `subtitle`, `options`, `tabs`, `assets` (id to SHA-256) and `ai`. It changes with the content, not with the log or timestamps.
- A change makes a new revision: `n` goes up by one, `parent` is the old hash, and `label` rises from `1` to `1.1` to `1.2`, or to `2` for a major change. File names carry the label: `Report_v1.1.helix.html`.
- Ids of tabs, blocks and attachments never change, so a change to one block can be made, checked and compared without touching the rest.
- A patch names the hash it was made from. If the document has changed since then, the patch is refused.

## Reading a document

1. Find the element with id `doc-source` and parse its JSON. That is the complete content. Stop there.
2. Read `ai` first. Unless asked for a full review, read only the `focus` sections.
3. Read attachments only when needed: decode the `data:` link whose element id is `asset-` plus the asset id, and compare its SHA-256 with the data block.

## Checking a document

`python tools/helix.py check file.helix.html` confirms: exactly one script (the data block), no event handlers, the security line intact, no external references, fingerprints match, the size is within limit, and that the visible page equals what the data block would produce. Files made by another version of the generator pass with a note that the layout was not compared.

## Stability

Version 1 is the first public version. Additions that old readers can safely ignore raise `spec` (1.1 added identity, revisions and AI Notes; 1.2 added report blocks and title-area settings). Software that does not know a block type leaves it out when it saves, so open 1.2 files that use new blocks in 1.2 software. Changes that old readers cannot understand will increase `version`; software must not save over a file whose `version` it does not know. The editor keeps reading earlier versions. Software older than 1.1 does not know the 1.1 fields and drops them if it saves a 1.1 file.
