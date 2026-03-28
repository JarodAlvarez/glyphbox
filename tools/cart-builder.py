#!/usr/bin/env python3
"""cart-builder.py — assembles a .gbcart binary from a game project directory.

Usage: python tools/cart-builder.py demos/bouncer/ -o cartridges/bouncer.gbcart
"""
import argparse
import os
import struct
import subprocess
import sys
import zlib

MAGIC           = b'\x47\x42\x43\x31'  # GBC1
BYTECODE_MAX    = 4096
SPRITES_BYTES   = 1024   # 128 tiles × 8×8 × 1bpp
TILEMAP_BYTES   = 512    # 16×16 × 2 bytes (uint16 LE)
SFX_BYTES       = 512    # 16 patterns × 32 bytes
MUSIC_BYTES     = 256    # 4 patterns × 64 bytes


# ── Parsers ────────────────────────────────────────────────────────────────

def parse_meta(path: str) -> dict:
    """Minimal TOML parser for title/author/version fields."""
    meta = {'title': 'UNTITLED', 'author': 'UNKNOWN', 'version': 1}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key == 'title':
                meta['title'] = val[:16]
            elif key == 'author':
                meta['author'] = val[:8]
            elif key == 'version':
                try:
                    meta['version'] = int(val)
                except ValueError:
                    pass
    return meta


def parse_sprites(path: str) -> bytes:
    """Parse sprites.txt → 1024-byte bitplane.
    128 sprites × 8 rows × 1 byte (MSB = leftmost pixel).
    Blank lines separate sprites; each sprite is 8 lines of 8 '0'/'1' chars.
    """
    result = bytearray(SPRITES_BYTES)
    sprites: list[list[str]] = []

    if not os.path.exists(path):
        return bytes(result)

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            if current:
                sprites.append(current)
                current = []
        else:
            current.append(stripped)
    if current:
        sprites.append(current)

    for s_idx, sprite in enumerate(sprites[:128]):
        for r_idx, row in enumerate(sprite[:8]):
            byte = 0
            for c_idx in range(min(8, len(row))):
                if row[c_idx] == '1':
                    byte |= (1 << (7 - c_idx))
            result[s_idx * 8 + r_idx] = byte

    return bytes(result)


def parse_tilemap(path: str) -> bytes:
    """Parse tilemap.txt → 512-byte array (16×16 uint16 LE)."""
    result = bytearray(TILEMAP_BYTES)
    if not os.path.exists(path):
        return bytes(result)

    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    idx = 0
    for row_line in lines[:16]:
        parts = row_line.split()
        for col in parts[:16]:
            try:
                val = int(col) & 0xFFFF
            except ValueError:
                val = 0
            struct.pack_into('<H', result, idx * 2, val)
            idx += 1
            if idx >= 256:
                break
        if idx >= 256:
            break

    return bytes(result)


def parse_sfx(path: str) -> bytes:
    """Parse sfx.txt → 512 bytes.
    Format: 16 SFX patterns. Each pattern is a line of up to 16 note-events.
    Each note-event: 'note,vol,wave,dur' (all 0–127 integers).
    Packed as 2 bytes per event: byte0=note, byte1=(vol<<4)|(wave<<2)|(dur&3).
    Patterns are separated by blank lines.
    """
    result = bytearray(SFX_BYTES)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return bytes(result)

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
    for p_idx, block in enumerate(blocks[:16]):
        lines = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith('#')]
        for n_idx, line in enumerate(lines[:16]):
            parts = line.split(',')
            if len(parts) < 4:
                continue
            try:
                note = int(parts[0]) & 0x7F
                vol  = int(parts[1]) & 0x7
                wave = int(parts[2]) & 0x3
                dur  = int(parts[3]) & 0x3
            except ValueError:
                continue
            base = p_idx * 32 + n_idx * 2
            result[base]     = note
            result[base + 1] = (vol << 4) | (wave << 2) | dur

    return bytes(result)


def parse_music(path: str) -> bytes:
    """Parse music.txt → 256 bytes.
    Format: 4 music patterns, each a line of space-separated SFX IDs (0–15).
    Packed: byte0=count, bytes1..63=sfx_ids.
    """
    result = bytearray(MUSIC_BYTES)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return bytes(result)

    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines()
                 if l.strip() and not l.strip().startswith('#')]

    for p_idx, line in enumerate(lines[:4]):
        parts = line.split()
        ids = []
        for p in parts[:63]:
            try:
                ids.append(int(p) & 0xFF)
            except ValueError:
                pass
        base = p_idx * 64
        result[base] = len(ids)
        for i, sfx_id in enumerate(ids):
            result[base + 1 + i] = sfx_id

    return bytes(result)


def compile_lua(lua_path: str) -> bytes:
    """Compile Lua source to LuaJIT bytecode."""
    result = subprocess.run(
        ['luajit', '-b', lua_path, '-'],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"ERROR: luajit compilation failed:\n{result.stderr.decode()}")
        sys.exit(1)
    return result.stdout


# ── Assembly ───────────────────────────────────────────────────────────────

FLAG_COMPRESSED_BYTECODE = 0x0002
CART_SIZE_LIMIT          = 6144   # reference limit for build summary


def build_cart(project_dir: str, out_path: str, no_compress: bool = False) -> None:
    def p(name):
        return os.path.join(project_dir, name)

    meta     = parse_meta(p('meta.toml'))
    bytecode = compile_lua(p('game.lua'))
    sprites  = parse_sprites(p('sprites.txt'))
    tilemap  = parse_tilemap(p('tilemap.txt'))
    sfx      = parse_sfx(p('sfx.txt'))
    music    = parse_music(p('music.txt'))

    # Pack common header fields (same for both formats)
    title_b  = meta['title'].encode('ascii', errors='replace')[:16].ljust(16, b'\x00')
    author_b = meta['author'].encode('ascii', errors='replace')[:8].ljust(8,  b'\x00')
    version  = struct.pack('<H', meta['version'] & 0xFFFF)

    # Try compression
    compressed   = zlib.compress(bytecode, level=9)
    use_compress = (not no_compress) and (len(compressed) < len(bytecode))

    if use_compress:
        # ── v0.4 compressed format ───────────────────────────────────────────
        stored = compressed
        ratio  = 100 * len(stored) // len(bytecode)
        print(f"  Compressed: {len(bytecode)} → {len(stored)} bytes ({ratio}% of original)")

        if len(stored) > 0xFFFF or len(bytecode) > 0xFFFF:
            print(f"ERROR: bytecode length exceeds uint16 range")
            sys.exit(1)

        flags_val = FLAG_COMPRESSED_BYTECODE
        flags     = struct.pack('<H', flags_val)
        header    = MAGIC + title_b + author_b + version + flags
        assert len(header) == 0x20, f"header size mismatch: {len(header)}"

        size_info = struct.pack('<HH', len(stored), len(bytecode))
        body      = header + size_info + stored + sprites + tilemap + sfx + music
        fmt_name  = 'v0.4-compressed'

    else:
        # ── v0.2 legacy format ───────────────────────────────────────────────
        # Actual bytecode + 4-byte length prefix must fit in 4096 bytes
        if len(bytecode) + 4 > BYTECODE_MAX:
            print(f"ERROR: bytecode too large ({len(bytecode)} + 4 prefix > {BYTECODE_MAX} bytes)")
            sys.exit(1)

        flags_val = 0x0000
        flags     = struct.pack('<H', flags_val)
        header    = MAGIC + title_b + author_b + version + flags
        assert len(header) == 0x20, f"header size mismatch: {len(header)}"

        # Prefix the bytecode section with a 4-byte uint32 LE actual length,
        # so cart.c can pass the exact number of bytes to luaL_loadbuffer.
        bc_len_prefix = struct.pack('<I', len(bytecode))
        bc_payload    = bc_len_prefix + bytecode
        bc_padded     = bc_payload + b'\x00' * (BYTECODE_MAX - len(bc_payload))

        body     = header + bc_padded + sprites + tilemap + sfx + music
        assert len(body) == 0x1920, f"body size mismatch: {len(body)}"
        fmt_name = 'v0.2-legacy'

    crc   = struct.pack('<I', zlib.crc32(body) & 0xFFFFFFFF)
    total = len(body) + 4

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(body + crc)

    pct = 100 * total // CART_SIZE_LIMIT
    print(f"Built: {out_path} ({total} bytes, {pct}% of {CART_SIZE_LIMIT}-byte limit)")
    print(f"  Format:   {fmt_name}")
    print(f"  Title:    {meta['title']}")
    print(f"  Author:   {meta['author']}")
    print(f"  Version:  {meta['version']}")
    print(f"  Bytecode: {len(bytecode)} bytes raw / {BYTECODE_MAX} max")


def main():
    parser = argparse.ArgumentParser(description='Assemble a GLYPHBOX cartridge.')
    parser.add_argument('project_dir', help='Game project directory')
    parser.add_argument('-o', '--output', required=True, help='Output .gbcart path')
    parser.add_argument('--no-compress', action='store_true',
                        help='Disable bytecode compression (produce v0.2 legacy format)')
    args = parser.parse_args()
    build_cart(args.project_dir, args.output, no_compress=args.no_compress)


if __name__ == '__main__':
    main()
