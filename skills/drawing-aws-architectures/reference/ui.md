# Local web interface

Start: `python scripts/run.py ui [--port 8765] [--output-dir diagrams] [--browser]`

| Mode | Needs | Reads | Notes |
|---|---|---|---|
| Offline | nothing | text, .md, .txt, PDF, .docx | Keyword rules, milliseconds, nothing leaves the machine |
| AI · GitHub Models | `GITHUB_MODELS_TOKEN` (or `GITHUB_TOKEN`) with `models: read`; optional `GITHUB_MODELS_MODEL` (default `openai/gpt-4.1`) | the above + PNG/JPEG/GIF/WebP | Sends the use case to GitHub Models; separate from Copilot quota; HTTP 429 = rate limit |
| AI · Anthropic | `ANTHROPIC_API_KEY`; optional `ANTHROPIC_MODEL` | the above + images | Sends the use case to the Anthropic API (billed separately) |

An AI mode that fails falls back to offline. Unconfigured modes are disabled in the page.

Windows PowerShell: `$env:GITHUB_MODELS_TOKEN="github_pat_..."` before starting the UI.

Buttons: **Descargar .drawio** (browser download) and **Guardar y abrir en VS Code** (writes to `--output-dir` and runs `code --reuse-window`; needs the `code` command on PATH).

Safety: binds to 127.0.0.1 only; rejects foreign Host/Origin headers; JSON POSTs only; uploads go to a temporary folder with sanitised names and are deleted after each request; saves are confined to `--output-dir`. Scanned PDFs without text need `pdftoppm` (poppler) plus an AI mode.

## Browser version (static, no install)

`python scripts/build_web.py` writes `docs/index.html` and `docs/awsdraw.zip`. The page loads Pyodide from jsDelivr and runs the same `awsdraw` package in the browser (`web_entry.py`). AI calls are made by the page's JavaScript with the token the user pastes (kept in memory only); parsing, validation, layout and drawing run in Python. Providers may block direct browser calls (CORS); the page then tells the user to use the local UI. Publish with GitHub Pages: branch `main`, folder `/docs`.
