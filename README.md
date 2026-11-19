# drawing-aws-architectures

Agent Skill that turns requirements (text, PDF, Word or image of a use case) into a **high-level AWS architecture** as an editable **draw.io** diagram, in 1-3 minutes. AWS only, VS Code first.

## Use it in VS Code

1. Install the **Draw.io Integration** extension (`hediet.vscode-drawio`).
2. Install the skill (needs Python 3.10+, no packages):
   ```
   python scripts/run.py install --scope project --target copilot
   ```
   This copies the skill to `.github/skills/drawing-aws-architectures` and recommends the extension in `.vscode/extensions.json`. Use `--scope user` to make it available in every project, or `--target claude` / `--target agents` for the other folders VS Code reads.
3. In Copilot Chat (agent mode) or Claude Code, ask: *"Diseña una arquitectura AWS de alto nivel para ..."*. The agent writes a spec, runs the generator and opens the `.drawio` file.

## Without an agent

```
python scripts/run.py plan "Portal web con login, SQL, colas, archivos" -o arch.drawio --open
python scripts/run.py generate examples/serverless-web.json -o arch.drawio --open
python scripts/run.py ui --browser      # local web interface
```

Windows: use `py` or `python`. `--open` needs the `code` command on PATH (VS Code: Command Palette > "Shell Command: Install 'code' command").

## Layout

```
SKILL.md              instructions for the agent
scripts/run.py        entry point
scripts/awsdraw/      domain (catalog, rules, layout, planner) > application (use cases, ports) > adapters (draw.io, readers, UI, LLM) > cli
reference/  examples/  tests/
```

Run tests: `python -m unittest discover -s tests`.
Icons come from draw.io's own AWS4 library; a test checks every catalog entry against it.
