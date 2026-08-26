import json
import os
import re

transcript_path = r'C:\Users\jainr\.gemini\antigravity-ide\brain\1dbd3730-878d-42e1-8330-35a7d0b990b7\.system_generated\logs\transcript_full.jsonl'
output_md_path = r'C:\CSE_BABY\SIH26032\CHAT_EXPORT.md'
output_json_path = r'C:\CSE_BABY\SIH26032\CHAT_EXPORT.json'

if not os.path.exists(transcript_path):
    transcript_path = r'C:\Users\jainr\.gemini\antigravity-ide\brain\1dbd3730-878d-42e1-8330-35a7d0b990b7\.system_generated\logs\transcript.jsonl'

entries = []
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            pass

# Write JSON export
with open(output_json_path, 'w', encoding='utf-8') as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)

# Build a clean Markdown export
md_lines = []
md_lines.append("# 🌾 SmartMandi Queue Manager (SIH26032) — Chat History\n")
md_lines.append(f"> **Conversation ID:** `1dbd3730-878d-42e1-8330-35a7d0b990b7`  \n> **Export Date:** 2026-08-26  \n> **Repository:** https://github.com/RONAKJAIN122/SIH26032-  \n\n---\n")

user_msg_count = 0

for entry in entries:
    etype = entry.get('type')
    source = entry.get('source')
    content = entry.get('content', '') or ''
    tool_calls = entry.get('tool_calls', [])

    # Filter out system checkpoints and internal metadata noise
    if etype in ['CHECKPOINT', 'KNOWLEDGE_ARTIFACTS', 'SYSTEM_MESSAGE']:
        continue

    # User Input
    if etype == 'USER_INPUT' or (source == 'USER_EXPLICIT' and etype not in ['SYSTEM_MESSAGE']):
        clean_content = content
        if '<USER_REQUEST>' in clean_content:
            m = re.search(r'<USER_REQUEST>(.*?)</USER_REQUEST>', clean_content, re.DOTALL)
            if m:
                clean_content = m.group(1).strip()
        
        # Strip system prefix if present
        clean_content = re.sub(r'The USER performed the following action:.*', '', clean_content, flags=re.DOTALL).strip()

        if clean_content and not clean_content.startswith("{{ CHECKPOINT"):
            user_msg_count += 1
            md_lines.append(f"\n## 👤 User Prompt #{user_msg_count}\n")
            md_lines.append(f"{clean_content}\n")
            md_lines.append("\n---\n")

    # Assistant Response
    elif etype == 'PLANNER_RESPONSE' and source == 'MODEL':
        # Ignore purely internal json logs or empty outputs
        if content.strip() and not content.strip().startswith("Created At:"):
            md_lines.append(f"\n## 🤖 Assistant\n")
            md_lines.append(f"{content.strip()}\n")
            md_lines.append("\n---\n")

    # Tool Action Summary (optional concise view)
    elif etype in ['RUN_COMMAND', 'CODE_ACTION', 'VIEW_FILE']:
        pass

with open(output_md_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))

print(f"Exported clean chat history with {user_msg_count} user turns.")
print(f"Markdown: {output_md_path}")
print(f"JSON: {output_json_path}")
