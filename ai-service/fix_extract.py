#!/usr/bin/env python
"""Fix the extract_value function to prevent greedy multi-line extraction."""
import re

filepath = r"C:\Users\vinod\Downloads\clinevo-smart-inbox-ai\ai-service\main.py"

with open(filepath, 'r') as f:
    content = f.read()

# Find and replace the extract_value function
old_pattern = r'''    pattern = \(
        rf"\(\\?<\\!\w\)\{re\.escape\(label\)\}\\\\s\*\[\\:\\\\\-\]\\\\s\*"
        rf"\(\.\*?\)"
        rf"\(\\?=\\\\s\+\(\?:\{label_pattern\}\)\(\?:\\\\s\*\[\\:\\\\\-\]\|\\\\s\)\|$\)"
    \)'''

# Simple approach: replace the specific lines
lines = content.split('\n')
new_lines = []
in_extract_value = False
skip_until_next_def = False

for i, line in enumerate(lines):
    if 'def extract_value(' in line:
        in_extract_value = True
        skip_until_next_def = False
        new_lines.append(line)
        continue
    
    if in_extract_value and line.strip().startswith('def '):
        in_extract_value = False
        new_lines.append(line)
        continue
    
    if in_extract_value:
        # Replace the pattern line
        if 'rf"(?=\\s+(?:{label_pattern})' in line:
            new_lines.append('        rf"(?=\\s+(?:{label_pattern})(?:\\s*[\\:\\-]|\\s)|\\n|$)"')
            continue
        # Replace the value processing line
        if 'value = re.sub(r"\\s+", " ", match.group(1)).strip(" :-")' in line:
            new_lines.append('        value = re.sub(r"\\s+", " ", match.group(1)).strip(" :-\\n\\r\\t")')
            new_lines.append('        value = value.split("\\n")[0].strip(" :-\\n\\r\\t")')
            continue
        new_lines.append(line)
    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

with open(filepath, 'w') as f:
    f.write(new_content)

print("Fixed extract_value function")
