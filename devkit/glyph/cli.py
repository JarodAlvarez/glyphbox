"""glyph: the GLYPHBOX devkit command line.

    glyph new mygame            start a project from the template
    glyph build [dir]           build dir/ into a .gbcart and report its card count
    glyph run [dir]             build, launch the emulator, rebuild and relaunch on every save
    glyph print game.gbcart     make a print-and-cut card PDF
    glyph sprites image.png     convert an image to sprites.txt
    glyph tokens [dir]          count Lua tokens (a complexity signal, not a limit)
"""
import argparse
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import __version__, cart_builder, card_print, img_to_sprites, token_count

MAX_CARDS = 8
CARD_BYTES = card_print.TARGET_CHUNK_BYTES
TEMPLATE = Path(__file__).parent / "template"
WATCHED = ("game.lua", "meta.toml", "sprites.txt", "tilemap.txt", "sfx.txt", "music.txt")


def _die(msg):
    sys.exit(f"glyph: {msg}")


def _project(path):
    p = Path(path or ".").resolve()
    if not (p / "game.lua").is_file():
        _die(f"no game.lua in {p}. Run `glyph new <name>` to start a project.")
    return p


def _cards(cart_path):
    """Card count and compressed size, exactly as `glyph print` will split it."""
    data = Path(cart_path).read_bytes()
    _, payloads = card_print._read_cart(str(cart_path))
    import zlib
    return len(payloads), len(zlib.compress(data, 9))


def _build(project, out, quiet=False):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            cart_builder.build_cart(str(project), str(out))
    except SystemExit as e:
        sys.stdout.write(buf.getvalue())
        if e.code:
            raise
    if not quiet:
        sys.stdout.write(buf.getvalue())
    return out


def _pips(n):
    return "■" * min(n, MAX_CARDS) + "□" * max(0, MAX_CARDS - n)


def cmd_new(a):
    dest = Path(a.name)
    if dest.exists():
        _die(f"{dest} already exists")
    shutil.copytree(TEMPLATE, dest)
    title = dest.name.upper().replace("-", " ").replace("_", " ")[:16]
    meta = dest / "meta.toml"
    meta.write_text(meta.read_text().replace("MY GAME", title))
    print(f"Created {dest}/")
    for f in sorted(dest.iterdir()):
        print(f"  {f.name}")
    print(f"\nNext:  cd {dest} && glyph run")


def cmd_build(a):
    project = _project(a.dir)
    out = Path(a.output or f"{project.name}.gbcart")
    _build(project, out, quiet=not a.verbose)
    n, z = _cards(out)
    left = MAX_CARDS * CARD_BYTES - z
    print(f"{out}  {out.stat().st_size:,} B  →  {n} / {MAX_CARDS} cards")
    print(f"  {_pips(n)}  {max(left, 0):,} B left of {MAX_CARDS * CARD_BYTES:,}")
    if n > MAX_CARDS:
        _die(f"{n} cards is over the {MAX_CARDS}-card limit ({-left:,} B over). Trim the code or assets.")


def _emulator(explicit):
    for c in (explicit, os.environ.get("GLYPHBOX_EMULATOR"), shutil.which("glyphbox")):
        if c and Path(c).exists():
            return c
    _die("can't find the GLYPHBOX emulator. Download it from "
         "https://github.com/JarodAlvarez/glyphbox/releases, then put `glyphbox` on your PATH "
         "or pass --emulator /path/to/glyphbox.")


def cmd_run(a):
    project = _project(a.dir)
    emu = _emulator(a.emulator)
    tmp = Path(tempfile.mkdtemp(prefix="glyph-"))
    cart = tmp / f"{project.name}.gbcart"

    def stamp():
        return tuple((project / f).stat().st_mtime if (project / f).exists() else 0 for f in WATCHED)

    proc, seen = None, None
    print(f"Watching {project}. Save a file to rebuild; Ctrl+C to quit.")
    try:
        while True:
            now = stamp()
            if now != seen:
                seen = now
                try:
                    _build(project, cart, quiet=True)
                    n, _ = _cards(cart)
                    print(f"[{time.strftime('%H:%M:%S')}] built  {n} / {MAX_CARDS} cards")
                    if proc and proc.poll() is None:
                        proc.terminate()
                        proc.wait(timeout=3)
                    proc = subprocess.Popen([emu, str(cart)])
                except SystemExit:
                    print(f"[{time.strftime('%H:%M:%S')}] build failed; fix the error and save again")
            if proc and proc.poll() is not None and not a.keep:
                print("Emulator closed.")
                break
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
        shutil.rmtree(tmp, ignore_errors=True)


def _call(mod, argv):
    old = sys.argv
    sys.argv = [mod.__name__.split(".")[-1]] + argv
    try:
        mod.main()
    finally:
        sys.argv = old


def cmd_print(a):
    _call(card_print, a.args)


def cmd_sprites(a):
    _call(img_to_sprites, a.args)


def cmd_tokens(a):
    _call(token_count, [str(_project(a.dir) / "game.lua")])


def main():
    p = argparse.ArgumentParser(prog="glyph", description="GLYPHBOX devkit",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--version", action="version", version=f"glyph {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new", help="start a project from the template")
    s.add_argument("name"); s.set_defaults(fn=cmd_new)

    s = sub.add_parser("build", help="build a .gbcart and report its card count")
    s.add_argument("dir", nargs="?"); s.add_argument("-o", "--output")
    s.add_argument("-v", "--verbose", action="store_true"); s.set_defaults(fn=cmd_build)

    s = sub.add_parser("run", help="build, run in the emulator, rebuild on save")
    s.add_argument("dir", nargs="?"); s.add_argument("--emulator")
    s.add_argument("--keep", action="store_true", help="keep watching after the emulator closes")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("print", help="make a card PDF (args passed to the card printer)", add_help=False)
    s.add_argument("args", nargs=argparse.REMAINDER); s.set_defaults(fn=cmd_print)

    s = sub.add_parser("sprites", help="convert an image to sprites.txt", add_help=False)
    s.add_argument("args", nargs=argparse.REMAINDER); s.set_defaults(fn=cmd_sprites)

    s = sub.add_parser("tokens", help="count Lua tokens")
    s.add_argument("dir", nargs="?"); s.set_defaults(fn=cmd_tokens)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
