# Prompt: exploratory session

Used with an MCP-capable agent (VS Code agent mode / any MCP client) connected to the Playwright
MCP server in `.vscode/mcp.json`. The app must be running (`scripts/run_local_app.sh`).

---

You are exploring a web form as a tester, not writing code yet.

Open http://127.0.0.1:8788/registration.html. It is an 8-step player registration wizard.

1. Walk through every step once with valid data and submit. Note the result screen.
2. Then go back through and try to break each step:
   - submit each step empty
   - unusual but valid input (Bangla names, very long names, numbers with dashes/spaces)
   - invalid input (wrong mobile formats, huge images, non-image files)
   - change your mind: switch options back and forth, double-click choices, use Back
   - switch the language to বাংলা in the middle of the form
3. Use the accessibility snapshot, not screenshots, to judge whether every control has an
   accessible name.

Report as a table: step · what you did · what happened · why it might be a bug.
Report only what you observed. Do not guess at implementation details.
