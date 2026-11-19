# Local web interface

Start: `python scripts/run.py ui [--port 8765] [--output-dir diagrams] [--browser]`

| Mode | Needs | Reads | Notes |
|---|---|---|---|
| Offline | nothing | text, .md, .txt, PDF, .docx | Keyword rules, runs in milliseconds, nothing leaves the machine |
| AI | `ANTHROPIC_API_KEY` (optional `ANTHROPIC_MODEL`) | the above + PNG/JPEG/GIF/WebP | Sends the use case to the Anthropic API; falls back to offline if the call fails |

Windows PowerShell: `$env:ANTHROPIC_API_KEY="sk-ant-..."` before starting the UI.

Buttons: **Descargar .drawio** (browser download) and **Guardar y abrir en VS Code** (writes to `--output-dir` and runs `code --reuse-window`; needs the `code` command on PATH).

Safety: binds to 127.0.0.1 only; rejects foreign Host/Origin headers; JSON POSTs only; uploads go to a temporary folder with sanitised names and are deleted after each request; saves are confined to `--output-dir`. Scanned PDFs without text need `pdftoppm` (poppler) plus AI mode.
