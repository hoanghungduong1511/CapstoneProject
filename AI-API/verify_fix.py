"""Verify no mojibake remains in llm_service.py"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

path = r"E:\DHBKDN\CapstoneProject\SkinDeseases-AI-API\app\services\llm_service.py"

# Common mojibake bi-grams produced when UTF-8 Vietnamese bytes are read as CP1252
mojibake_patterns = [
    "\u00c3\u00b4",  # Ã´ (ô)
    "\u00c3\u00a0",  # Ã  (à) - note: \xa0 = NBSP
    "\u00c3\u00a1",  # Ã¡ (á)
    "\u00c3\u00a9",  # Ã© (é)
    "\u00c3\u00aa",  # Ãª (ê)
    "\u00c3\u00ac",  # Ã¬ (ì)
    "\u00c3\u00ad",  # Ã­ (í)
    "\u00c3\u00b9",  # Ã¹ (ù)
    "\u00c3\u00ba",  # Ãº (ú)
    "\u00c3\u00b3",  # Ã³ (ó)
    "\u00c4\u2018",  # Ä' (đ via cp1252)
    "\u00c6\u00b0",  # Æ° (ư)
    "\u1ebd\u00bb",  # part of ệ
    "\u00e1\u00bb",  # á» (start of 3-byte Vietnamese)
    "\u00e1\u00ba",  # áº (start of 3-byte Vietnamese)
]

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

found = False
for i, line in enumerate(lines, 1):
    for pattern in mojibake_patterns:
        if pattern in line:
            print(f"MOJIBAKE Line {i}: {line.strip()[:120]}")
            found = True
            break

if not found:
    print("SUCCESS: No mojibake patterns found! File is clean.")

# Also check for "Mục:" in string literals (should not appear in output)
muc_count = 0
for i, line in enumerate(lines, 1):
    # Skip the _strip_section_prefix and _chunk_body methods where Mục: is expected
    stripped = line.strip()
    if '"Mục:' in stripped or "'Mục:" in stripped:
        # These are OK - they're in the stripping logic
        if '_strip_section_prefix' in ''.join(lines[max(0,i-10):i+2]):
            continue
        if 'startswith' in stripped:
            continue
        muc_count += 1
        print(f"'Mục:' in output string at line {i}: {stripped[:100]}")

if muc_count == 0:
    print("SUCCESS: No unhandled 'Mục:' prefix in output strings.")
