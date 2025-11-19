"""
Quick fix: Remove all Unicode emojis from Python scripts to fix cp1252 encoding errors
"""

import re
from pathlib import Path

# Unicode replacements
REPLACEMENTS = {
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARNING]',
    '💾': '[SAVED]',
    '📊': '[CHART]',
    '📅': '[DATE]',
    '🗺️': '[MAP]',
    '🔄': '[PROCESS]',
    '⏳': '[WAIT]',
    '→': '->',
    '⏱': '[TIMER]',
    '📂': '[FOLDER]',
    '📏': '[SCALE]',
    '🌍': '',
    '✓': '[OK]',
    'σ': 'sigma',  # Greek letter sigma for standard deviation
}

def fix_file(filepath):
    """Remove Unicode emojis from a file."""
    print(f"Fixing {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Replace all Unicode characters
    for unicode_char, replacement in REPLACEMENTS.items():
        content = content.replace(unicode_char, replacement)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath.name}")
        return True
    else:
        print(f"  - No changes needed in {filepath.name}")
        return False

def main():
    scripts_dir = Path("scripts")
    
    # Fix all Python scripts
    python_files = list(scripts_dir.glob("*.py"))
    
    fixed_count = 0
    for py_file in python_files:
        if fix_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
