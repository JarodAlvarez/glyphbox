"""Run a Blender render mode in a time-boxed slice (resumable): render_slice.py <mode> [samples]"""
import subprocess, sys
cmd = ['/Applications/Blender.app/Contents/MacOS/Blender', '-b', '-P', 'blender_render.py', '--'] + sys.argv[1:]
try:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=560)
    out, state = r.stdout, 'finished'
except subprocess.TimeoutExpired as e:
    out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or '')
    state = 'time slice ended'
print(state)
print('\n'.join(l for l in out.splitlines() if l.startswith('wrote') or 'Error' in l))
