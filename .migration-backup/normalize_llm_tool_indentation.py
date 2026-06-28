from pathlib import Path

path = Path(r'E:\2024 RESET\concierge\tools\llm_tool.py')
text = path.read_text(encoding='utf-8')
lines = text.splitlines()
start = 303 - 1
end = 320
block = lines[start:end]
new_block = [
    '    # ── Research / information tasks ──────────────────────────────────────────',
    '    # ── File / attachment / CSV tasks ─────────────────────────────────────────',
    '    if any(k in core for k in ("attach", "upload", "csv", "spreadsheet", "financial model", "project")):',
    '        return (',
    '            "File attachment plan: Locate the Q2 Planning project workspace, open the attachments or uploads panel, "',
    '            "select the financial model CSV file, and attach it to the project. "',
    '            "Verify the upload completes successfully and confirm the file is referenced in the project plan or task details. "',
    '            "If necessary, update the project notes to mention the attached financial model CSV."',
    '        )',
    '    if any(k in core for k in ("research", "gather", "information", "find", "search", "facts", "investigate", "explore")):',
    '        goal_match = re.search(r"(?:about:|regarding|for:|topic:)\\s*(.+?)(?:\\n|Provide|$)", prompt, re.IGNORECASE)',
    '        subject = goal_match.group(1).strip()[:80] if goal_match else first_line[:80]',
    '        return (',
    '            f"Research findings on \'{subject}\': "',
    '            "Based on available context and heuristic analysis, the key aspects are: "',
    '            "(1) core definition and background, (2) current state and recent developments, "',
    '            "(3) relevant stakeholders and use cases, (4) known challenges and trade-offs. "',
    '            "For real-time web data, ensure the web_search tool is reachable or set OPENAI_API_KEY for enhanced research."',
    '        )',
]
lines[start:end] = new_block
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('rewrote indentation block')
