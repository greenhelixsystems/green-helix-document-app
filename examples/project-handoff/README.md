# Example: a project handed from one AI to another

Invented example data showing the Helix 1.1 workflow end to end.

| File | What it is |
|---|---|
| `spec.json` | Project data from a planning app, mapped to a readable document: phases as headings, steps as a checklist plus numbered Markdown sections, tasks and budget as tables, links as a Markdown list, files with notes. AI Notes say what the next AI should do, with `focus` on the Budget, `protect` on the Goal and an assignment (`work`). |
| `Community-Garden-Launch_v1.helix.html` | The document as built from the spec by "Planner AI". Open it in any browser and press **AI Notes**. |
| `patch.json` | What "Reviewer AI" sent back after reading only the focus (`helix.py get --focus`): a change to one table and a note added to the AI Notes. |
| `Community-Garden-Launch_v1.1.helix.html` | The result of `helix.py patch`, and the **only** file handed back: version 1.1, every other block and both attachments byte for byte unchanged. Its Revision Log holds the reviewer's report: summary, open question, proposed next step and "needs review". `helix.py return-check --doc ..._v1.1.helix.html --base ..._v1.helix.html` checks it and prints the report. |
| `make.py` | Rebuilds all of the above. The document id and times are fixed so the output is reproducible. |

Try it:

```
python tools/helix.py outline examples/project-handoff/Community-Garden-Launch_v1.helix.html
python tools/helix.py get examples/project-handoff/Community-Garden-Launch_v1.helix.html --focus --md
python tools/helix.py diff examples/project-handoff/Community-Garden-Launch_v1.helix.html examples/project-handoff/Community-Garden-Launch_v1.1.helix.html
```
