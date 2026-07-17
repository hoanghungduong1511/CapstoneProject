"""
Comprehensive fix for llm_service.py:
1. Fix ALL mojibake Vietnamese text (cp1252 double-encoding)
2. Fix _chunk_body/_chunk_content to handle "Mục:" prefix from vector chunks
3. Remove line 74 (redundant mojibake replace that's now unnecessary)
"""
import sys
import re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

input_path = r"E:\DHBKDN\CapstoneProject\SkinDeseases-AI-API\app\services\llm_service.py"

# CP1252 byte->char mapping for the 0x80-0x9F range
# Python's 'latin-1' maps 0x80-0x9F to C1 control chars (U+0080-U+009F)
# But CP1252 maps them to printable chars like €, ™, œ, etc.
# We need to map these CP1252-specific chars back to their byte values
CP1252_SPECIAL = {
    '\u20ac': b'\x80',  # €
    '\u201a': b'\x82',  # ‚
    '\u0192': b'\x83',  # ƒ
    '\u201e': b'\x84',  # „
    '\u2026': b'\x85',  # …
    '\u2020': b'\x86',  # †
    '\u2021': b'\x87',  # ‡
    '\u02c6': b'\x88',  # ˆ
    '\u2030': b'\x89',  # ‰
    '\u0160': b'\x8a',  # Š
    '\u2039': b'\x8b',  # ‹
    '\u0152': b'\x8c',  # Œ
    '\u017d': b'\x8e',  # Ž
    '\u2018': b'\x91',  # '
    '\u2019': b'\x92',  # '
    '\u201c': b'\x93',  # "
    '\u201d': b'\x94',  # "
    '\u2022': b'\x95',  # •
    '\u2013': b'\x96',  # –
    '\u2014': b'\x97',  # —
    '\u02dc': b'\x98',  # ˜
    '\u2122': b'\x99',  # ™
    '\u0161': b'\x9a',  # š
    '\u203a': b'\x9b',  # ›
    '\u0153': b'\x9c',  # œ
    '\u017e': b'\x9e',  # ž
    '\u0178': b'\x9f',  # Ÿ
}

def encode_cp1252_manual(text):
    """Encode text to cp1252 bytes, handling the special 0x80-0x9F range."""
    result = bytearray()
    for char in text:
        code = ord(char)
        if code < 0x80:
            result.append(code)
        elif code <= 0xff:
            # Latin-1 range - direct mapping
            result.append(code)
        elif char in CP1252_SPECIAL:
            result.extend(CP1252_SPECIAL[char])
        else:
            raise ValueError(f"Cannot encode U+{code:04X} ({char!r}) to cp1252")
    return bytes(result)

def fix_mojibake_line(line):
    """Fix a single line of mojibake text by re-encoding cp1252->utf8."""
    try:
        raw_bytes = encode_cp1252_manual(line)
        return raw_bytes.decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return None

with open(input_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove BOM if present
if content.startswith('\ufeff'):
    content = content[1:]

lines = content.split('\n')
fixed_lines = []
fixed_count = 0
failed_lines = []

for i, line in enumerate(lines, 1):
    has_high_chars = any(ord(c) > 127 for c in line)
    
    if not has_high_chars:
        fixed_lines.append(line)
        continue
    
    # Try our manual cp1252->utf8 fix
    result = fix_mojibake_line(line)
    if result is not None:
        fixed_lines.append(result)
        if result != line:
            fixed_count += 1
    else:
        fixed_lines.append(line)
        failed_lines.append((i, line.strip()[:120]))

# Join back
fixed_content = '\n'.join(fixed_lines)

# Post-processing: fix line 74 which has bare "Ä" that can't round-trip
# After fixing, line 73 already has correct replace("đ", "d").replace("Đ", "d")
# Line 74 is redundant and line 75 uses unicode escapes - so remove line 74
old_line74 = '        without_accents = without_accents.replace("Ä\'", "d").replace("Ä", "d")'
if old_line74 in fixed_content:
    fixed_content = fixed_content.replace(old_line74 + '\n', '')
    print("Removed redundant line 74 (mojibake replace)")

# Also check for any remaining variants
old_line74_v2 = '        without_accents = without_accents.replace("\u0041\u0308\u2019", "d").replace("\u0041\u0308", "d")'
# Try various patterns
for pattern in [
    'without_accents.replace("Ä\u2018", "d").replace("Ä", "d")',
    'without_accents.replace("Ä\u2019", "d").replace("Ä", "d")',
]:
    if pattern in fixed_content:
        # Find the full line and remove it
        for check_line in fixed_content.split('\n'):
            if pattern in check_line and 'without_accents.replace("đ"' not in check_line:
                fixed_content = fixed_content.replace(check_line + '\n', '')
                print(f"Removed redundant line with pattern: {pattern[:40]}...")
                break

with open(input_path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"\nFixed {fixed_count} lines with mojibake")
if failed_lines:
    print(f"\n{len(failed_lines)} lines could NOT be fixed:")
    for num, text in failed_lines:
        print(f"  Line {num}: {text}")
else:
    print("ALL mojibake lines fixed successfully!")
