#!/usr/bin/env python3
"""token-count.py — counts Lua tokens; enforces 2048 limit.

Usage: python tools/token-count.py demos/bouncer/game.lua
Exit: 0 if within limit, 1 if over.
"""
import re
import sys

LIMIT = 2048

LUA_KEYWORDS = {
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
    'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or',
    'repeat', 'return', 'then', 'true', 'until', 'while',
}

# Ordered token patterns (most specific first)
TOKEN_PATTERNS = [
    # Long strings / block comments (must come before single-line)
    r'\-\-\[\[.*?\]\]',             # block comment --[[ ... ]]
    r'\[\[.*?\]\]',                 # long string [[ ... ]]
    # Single-line comment (consume but don't count)
    r'\-\-[^\n]*',
    # String literals
    r'"(?:[^"\\]|\\.)*"',
    r"'(?:[^'\\]|\\.)*'",
    # Numbers (hex, float, int)
    r'0[xX][0-9a-fA-F]+',
    r'\d+\.?\d*(?:[eE][+-]?\d+)?',
    # Multi-char operators
    r'==|~=|<=|>=|\.\.\.|\.\.|\:\:',
    # Single-char tokens (operators, punctuation)
    r'[+\-*/%^#&|~<>=(){}\[\];:,.]',
    # Identifiers / keywords
    r'[A-Za-z_]\w*',
]

COMBINED = re.compile(
    '|'.join(f'({p})' for p in TOKEN_PATTERNS),
    re.DOTALL
)

SKIP_PATTERNS = re.compile(
    r'(\-\-\[\[.*?\]\]|\-\-[^\n]*)',
    re.DOTALL
)


def count_tokens(source: str) -> int:
    count = 0
    for m in COMBINED.finditer(source):
        text = m.group(0)
        # Skip comments
        if text.startswith('--'):
            continue
        # Skip whitespace (shouldn't match but be safe)
        if not text.strip():
            continue
        count += 1
    return count


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.lua>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
    except OSError as e:
        print(f"Error: {e}")
        sys.exit(1)

    n = count_tokens(source)

    if n <= LIMIT:
        print(f"Tokens: {n} / {LIMIT}  [OK]")
        sys.exit(0)
    else:
        over = n - LIMIT
        print(f"Tokens: {n} / {LIMIT}  [OVER LIMIT — {over} tokens over]")
        sys.exit(1)


if __name__ == '__main__':
    main()
