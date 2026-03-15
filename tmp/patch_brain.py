"""Patch brain_api_v2.py to wire heal_and_learn pipeline."""

target_file = r"c:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend\api\brain_api_v2.py"

with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Lines 970-999 (1-indexed) = 969-998 (0-indexed)
new_lines = [
    '    # Code errors (NameError, KeyError, etc.) -> HEAL + LEARN (full autonomous pipeline)\n',
    '    # Critical path: detect -> fetch external knowledge -> heal code -> verify -> remember\n',
    '    code_error_patterns = [\n',
    '        "nameerror", "keyerror", "attributeerror", "importerror", "syntaxerror",\n',
    '        "typeerror", "modulenotfounderror", "indentationerror", "valueerror",\n',
    '        "import", "module", "dependency", "not defined", "has no attribute",\n',
    '        "missing required", "cannot import",\n',
    '    ]\n',
    '    if any(pat in r for pat in code_error_patterns):\n',
    '        return {\n',
    '            "escalate": False,\n',
    '            "brain": "system",\n',
    '            "action": "heal_and_learn",\n',
    '            "payload": {\n',
    '                "file_path": target if target.endswith(".py") else "",\n',
    '                "error": reason,\n',
    '                "target": target,\n',
    '                "fetch_knowledge": True,\n',
    '                "tags": ["autonomous", "code-heal", "self-learning"],\n',
    '            },\n',
    '            "type": "heal",\n',
    '        }\n',
    '\n',
    '    # Test failures -> HEAL + LEARN\n',
    '    if "test" in r or "failure" in r:\n',
    '        return {\n',
    '            "escalate": False,\n',
    '            "brain": "system",\n',
    '            "action": "heal_and_learn",\n',
    '            "payload": {\n',
    '                "file_path": target if target.endswith(".py") else "",\n',
    '                "error": reason,\n',
    '                "target": target,\n',
    '                "fetch_knowledge": True,\n',
    '                "tags": ["autonomous", "gap", "test-failure"],\n',
    '            },\n',
    '            "type": "heal",\n',
    '        }\n',
    '\n',
    '    # Default: escalate\n',
    '    return {"escalate": True, "reason": reason, "type": "escalate"}\n',
    '\n',
]

lines[969:999] = new_lines

with open(target_file, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"Patched {target_file}: replaced lines 970-999 with heal_and_learn pipeline")
