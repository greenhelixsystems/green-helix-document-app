# Contributing

Thank you for your interest.

**Pull requests are not being accepted for now.** The project is young and the maintainers want to keep the licensing simple while it settles.

**Issues are welcome.** If something does not work, or you have an idea, please open an issue and include:

- the browser and device you used (for example "Safari on iPhone 15" or "Chrome on Windows 11"),
- what you did, what you expected and what happened,
- if a file is involved, whether it opened in the editor, and the output of `python tools/helix.py check yourfile.helix.html`. Please do not attach files that contain private information.

Security problems: please open an issue that says only that you have found a security problem and how to reach you, without technical details, and the maintainers will get in touch.

You are free to fork the project under its licences (see [NOTICE.md](NOTICE.md); the Green Helix name and logo must be replaced in a fork).

## Working on the code yourself

```
python build/build.py          # rebuild editor/, mobile/, tools/helix.py and guide/HELIX-guide.md from src/
python tests/run_all.py        # run every suite
```

Edit only files under `src/`; everything else is generated. The tests need Python 3.8+, Node.js, Pillow and Playwright with Chromium
(`pip install playwright pillow` then `playwright install chromium`). Set `HELIX_CHROME` to use a browser you already have.
