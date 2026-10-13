"""Cycles studio renders of the GLYPHBOX console.

    .venv/bin/python blender_export.py
    blender -b -P blender_render.py -- [test|all] [samples]

Output: preview/blender_*.png
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'render_assets')
OUT = os.path.join(HERE, 'preview')
MM = 0.001
W, D, H, DOCK_Z, USB_X, USB_Z, SPK_Y, SPK_Z = [float(v) * MM for v in open(os.path.join(ASSETS, 'dims.txt')).read().split()]

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
MODE = argv[0] if argv else 'test'
SAMPLES = int(argv[1]) if len(argv) > 1 else 200
EXPOSURE = float(argv[2]) if len(argv) > 2 else -2.7      # stops
SCALE = float(argv[3]) if len(argv) > 3 else 1.0          # resolution multiplier
WALL = 420.0                                              # backdrop wash light power

COLORS = {            # sRGB
    'yellow': (0.98, 0.78, 0.16),
    'red': (0.82, 0.12, 0.15),
    'white': (0.93, 0.93, 0.92),
    'lilac': (0.73, 0.65, 0.90),
    'indigo': (0.22, 0.21, 0.55),
    'black': (0.035, 0.035, 0.04),
    'lime': (0.56, 0.83, 0.20),
    # additional colourways
    'classic': (0.84, 0.80, 0.72),
    'teal': (0.10, 0.58, 0.57),
    'orange': (0.96, 0.47, 0.13),
    'sky': (0.53, 0.75, 0.93),
    'pink': (0.96, 0.66, 0.75),
}


def lin(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)


# --------------------------------------------------------------------------- setup
MESHES = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MESHES.clear()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = 'GPU'
    except Exception as e:                       # CPU fallback
        print('GPU unavailable:', e)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = EXPOSURE
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    world = bpy.data.worlds.new('world'); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (1, 1, 1, 1)
    bg.inputs['Strength'].default_value = 0.55
    return sc


def load(name):
    """Import an STL once (mm -> m), weld it, smooth-shade with sharp creases."""
    if name not in MESHES:
        bpy.ops.wm.stl_import(filepath=os.path.join(ASSETS, name + '.stl'), global_scale=MM)
        ob = bpy.context.selected_objects[0]
        me = ob.data
        me.transform(ob.matrix_world)           # bake the importer's mm->m scale into the mesh
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bm.to_mesh(me); bm.free()
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.set_sharp_from_angle(angle=math.radians(38))
        bpy.data.objects.remove(ob)
        MESHES[name] = me
    return MESHES[name]


def plastic(name, rgb, rough=0.34):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(rgb)
    b.inputs['Roughness'].default_value = rough
    b.inputs['IOR'].default_value = 1.49
    b.inputs['Coat Weight'].default_value = 0.08
    b.inputs['Coat Roughness'].default_value = 0.25
    bev = nt.nodes.new('ShaderNodeBevel')             # soft rounded edges at render time
    bev.samples = 6
    bev.inputs['Radius'].default_value = 0.0006
    nt.links.new(bev.outputs['Normal'], b.inputs['Normal'])
    return m


def fixed_materials():
    mats = {}
    g = bpy.data.materials.new('glass'); g.use_nodes = True
    b = g.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.004, 0.004, 0.005, 1)
    b.inputs['Roughness'].default_value = 0.06
    b.inputs['Coat Weight'].default_value = 0.35
    b.inputs['Coat Roughness'].default_value = 0.03
    mats['glass'] = g
    e = bpy.data.materials.new('lit'); e.use_nodes = True
    b = e.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0, 0, 0, 1)
    b.inputs['Emission Color'].default_value = (1, 1, 0.97, 1)
    b.inputs['Emission Strength'].default_value = 9.0
    mats['lit'] = e
    mats['card'] = plastic('card', (0.80, 0.63, 0.38), 0.85)
    mats['dark'] = plastic('dark', (0.03, 0.03, 0.035), 0.4)
    for nm, col, rough in (('steel', (0.62, 0.63, 0.65, 1), 0.28), ('gold', (0.83, 0.62, 0.22, 1), 0.3)):
        mm_ = bpy.data.materials.new(nm); mm_.use_nodes = True
        bb = mm_.node_tree.nodes['Principled BSDF']
        bb.inputs['Base Color'].default_value = col
        bb.inputs['Metallic'].default_value = 1.0
        bb.inputs['Roughness'].default_value = rough
        mats[nm] = mm_
    mats['ivory'] = plastic('ivory', (0.85, 0.85, 0.83), 0.45)
    f = bpy.data.materials.new('floor'); f.use_nodes = True
    b = f.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.92, 0.92, 0.935, 1)
    b.inputs['Roughness'].default_value = 0.22
    b.inputs['Specular IOR Level'].default_value = 0.35
    mats['floor'] = f
    return mats


def add(sc, mesh, mat, loc=(0, 0, 0), rot_z=0.0):
    ob = bpy.data.objects.new(mesh, load(mesh))
    sc.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (0, 0, rot_z)
    if not ob.material_slots:
        ob.data.materials.append(None)
    ob.material_slots[0].link = 'OBJECT'
    ob.material_slots[0].material = mat
    return ob


def console(sc, mats, color, off=(0.0, 0.0), docked=True, card=True, loose=None, panel=False, body_mesh='body', variant=''):
    """One console in colourway `color` at xy offset (metres)."""
    rgb = COLORS[color]
    dark = sum(rgb) / 3 < 0.2
    body = plastic('body_' + color, rgb, 0.30 if dark else 0.36)
    shell = plastic('shell_' + color, tuple(min(1, v * 1.02 + 0.006) for v in rgb), 0.30 if dark else 0.34)
    btn = plastic('btn_' + color, tuple(v * 0.93 for v in rgb), 0.28)
    loc = (off[0], off[1], 0)
    add(sc, body_mesh + ('_' + variant if variant else ''), body, loc)
    sfx = '_' + variant if variant else ''
    add(sc, 'glass' + sfx, mats['glass'], loc); add(sc, 'lit' + sfx, mats['lit'], loc)
    if variant == 'faceplate':
        add(sc, 'plate_faceplate', mats['dark'], loc)
    add(sc, 'usb_nose', mats['dark'], loc); add(sc, 'usb_shell', mats['steel'], loc)
    add(sc, 'usb_tongue', mats['ivory'], loc); add(sc, 'usb_pins', mats['gold'], loc)
    add(sc, 'speaker', mats['dark'], loc)
    if panel:
        add(sc, 'panel', body, loc)
        add(sc, 'pwr_nose', mats['dark'], loc); add(sc, 'pwr_shell', mats['steel'], loc)
        add(sc, 'rear_screws', mats['steel'], loc)
    if card:
        add(sc, 'card', mats['card'], loc)
    if docked:
        add(sc, 'puck_shell', shell, loc); add(sc, 'puck_btn', btn, loc); add(sc, 'puck_port', mats['dark'], loc)
    if loose:                                    # (x, y, rot_deg) relative to the console
        l = (off[0] + loose[0], off[1] + loose[1], 0); r = math.radians(loose[2])
        add(sc, 'loose_shell', shell, l, r); add(sc, 'loose_btn', btn, l, r); add(sc, 'loose_port', mats['dark'], l, r)


def backdrop(sc, mat, x_half=40.0, y_front=-5.0, y_back=2.2, radius=1.2, height=5.0):
    """Seamless cyclorama: floor sweeping up into a back wall."""
    prof = [(y_front, 0.0)]
    for i in range(25):
        a = math.pi / 2 * i / 24
        prof.append((y_back + radius * math.sin(a), radius * (1 - math.cos(a))))
    prof.append((y_back + radius, height))
    verts, faces = [], []
    for (y, z) in prof:
        verts += [(-x_half, y, z), (x_half, y, z)]
    for i in range(len(prof) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    me = bpy.data.meshes.new('cyc'); me.from_pydata(verts, [], faces)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    me.materials.append(mat)
    ob = bpy.data.objects.new('cyc', me); sc.collection.objects.link(ob)


def area(sc, name, loc, target, size, power, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.shape = 'RECTANGLE'
    l.size, l.size_y = size
    l.energy = power; l.color = color
    ob = bpy.data.objects.new(name, l); sc.collection.objects.link(ob)
    ob.location = Vector(loc)
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def lights(sc, cx=0.0, span=1.0):
    """Big overhead softbox + side fills, scaled to the scene width."""
    s = span
    area(sc, 'key', (cx - 0.5 * s, -0.9 * s - 0.2, 1.25 * s + 0.3), (cx, D / 2, H / 2), (1.5 * s, 1.1 * s), 130 * s * s)
    area(sc, 'fill', (cx + 1.3 * s, -0.7 * s, 0.55 * s + 0.1), (cx, D / 2, H / 2), (1.0 * s, 1.3 * s), 38 * s * s)
    area(sc, 'top', (cx, D / 2 + 0.1, 1.6 * s + 0.4), (cx, D / 2, 0), (2.0 * s, 1.6 * s), 70 * s * s)
    area(sc, 'wall', (cx, 0.8, 2.6), (cx, 3.4, 1.2), (5.0 * max(s, 1.2), 2.0), WALL * max(s, 1.2))


def camera(sc, az, el, dist, lens, target, res, fstop=None):
    cam = bpy.data.cameras.new('cam'); cam.lens = lens; cam.sensor_width = 36; cam.sensor_fit = 'HORIZONTAL'
    ob = bpy.data.objects.new('cam', cam); sc.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    fwd = Vector((-math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)))
    t = Vector(target)
    ob.location = t - fwd * dist
    ob.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler()
    if fstop:
        cam.dof.use_dof = True; cam.dof.focus_distance = dist; cam.dof.aperture_fstop = fstop
    sc.camera = ob
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = int(100 * SCALE)


def shoot(sc, name):
    os.makedirs(os.path.dirname(os.path.join(OUT, name)), exist_ok=True)
    if MODE in ('final', 'colors', 'flatset') and os.path.exists(os.path.join(OUT, name)):   # resume an interrupted run
        print('skip', name, flush=True)
        return
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print('wrote', name, flush=True)


# --------------------------------------------------------------------------- shots
def hero(color, name=None, **kw):
    sc = reset(); mats = fixed_materials()
    backdrop(sc, mats['floor']); lights(sc)
    console(sc, mats, color, **kw)
    return sc


def main():
    os.makedirs(OUT, exist_ok=True)
    names = list(COLORS)
    if MODE == 'grooves':
        for v in ('ring', 'recess', 'face'):
            sc = hero('lilac', body_mesh='body_' + v)
            camera(sc, 22, 8, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1400, 1750))
            shoot(sc, f'blender_groove_{v}.png')
        return
    if MODE == 'white':
        for tag, az, el in (('hero', 26, 9), ('front', 0, 4), ('left', -24, 9)):
            sc = hero('white')
            camera(sc, az, el, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
            shoot(sc, f'blender_white_{tag}.png')
        return
    if MODE == 'set2':
        product_set(['white', 'yellow', 'lilac', 'black'])
        return
    if MODE == 'side':
        sc = hero('white')
        camera(sc, -52, 9, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
        shoot(sc, 'blender_white_speaker_side.png')
        return
    if MODE == 'final':
        final_set()
        return
    if MODE == 'whatif':
        for v in (argv[4:] or ('flat', 'faceplate', 'scoop', 'grille', 'plain')):
            sc = hero('white', variant=v)
            camera(sc, 24, 9, 0.95, 110, (0, D / 2, H / 2 - 0.016), (1000, 1250))
            shoot(sc, f'../renders/whatif/{v}.png')
        return
    if MODE == 'flatpuck':
        sc = hero('white', panel=True); spun(sc, 26)
        camera(sc, 26, 9, 0.95, 110, (0, D / 2, H / 2 - 0.016), (1800, 2250))
        shoot(sc, '../renders/final/white_flat_controller.png')
        return
    if MODE == 'flatset':
        F = '../renders/flat_controller/'
        C = (0, D / 2, H / 2 - 0.016)
        sel = ['black', 'yellow', 'lilac', 'teal']
        for c, (tag, az, el) in zip(sel, (('front_left', -26, 9), ('front_right', 26, 9),
                                          ('front_left', -26, 9), ('front_right', 26, 9))):
            sc = hero(c, panel=True); spun(sc, az)
            camera(sc, az, el, 0.95, 110, C, (1800, 2250))
            shoot(sc, f'{F}{c}_{tag}.png')
        for c in ('black', 'yellow'):
            sc = hero(c, panel=True); spun(sc, 32)
            camera(sc, 32, 28, 0.98, 110, C, (1800, 2250))
            shoot(sc, f'{F}{c}_high.png')
        sc = reset(); mats = fixed_materials()
        backdrop(sc, mats['floor'], y_back=2.8); lights(sc, cx=0.2, span=1.3)
        for i, c in enumerate(sel):
            console(sc, mats, c, (i * 0.135, i * 0.110), panel=True)
        camera(sc, -27, 9, 1.9, 85, (0.215, 0.20, H / 2 - 0.012), (3000, 2000))
        shoot(sc, F + 'lineup_diagonal.png')
        return
    if MODE == 'cable':
        sc = hero('white', panel=True, docked=False, loose=(0.020, -0.100, -10))
        white = plastic('cable_white', (0.94, 0.94, 0.93), 0.42)
        add(sc, 'cable', white); add(sc, 'plug_a', white); add(sc, 'plug_micro', white)
        add(sc, 'dock_magnet', bpy.data.materials['steel'])
        camera(sc, -22, 14, 1.12, 105, (0, -0.010, H / 2 - 0.035), (2000, 2300))
        shoot(sc, '../renders/final/white_undocked_cable.png')
        return
    if MODE == 'colors':
        color_set()
        return
    if MODE == 'spktest':
        sc = hero('white', panel=True); spun(sc, -55)
        camera(sc, -55, 9, 0.95, 110, (0, D / 2, H / 2 - 0.016), (1800, 2250))
        shoot(sc, 'blender_spk_a.png')
        sc = hero('white', panel=True); spun(sc, -72)
        camera(sc, -72, 6, 0.42, 110, (-W / 2, SPK_Y, SPK_Z - 0.004), (2400, 1700))
        shoot(sc, 'blender_spk_b.png')
        return
    if MODE == 'usbtest':
        sc = hero('white', panel=True)
        camera(sc, -14, 9, 0.30, 110, (USB_X, 0, USB_Z + 0.004), (1400, 1000))
        shoot(sc, 'blender_usb_test.png')
        return
    if MODE == 'rear':
        rear_shot()
        return
    if MODE == 'test':
        sc = hero('yellow')
        camera(sc, 26, 9, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1200, 1500))
        shoot(sc, 'blender_test.png')
        return

    for c in names:                                             # hero per colour
        sc = hero(c)
        camera(sc, 26, 9, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
        shoot(sc, f'blender_hero_{c}.png')

    sc = reset(); mats = fixed_materials()                      # straight-on line-up
    backdrop(sc, mats['floor']); lights(sc, span=1.5)
    for i, c in enumerate(names):
        console(sc, mats, c, ((i - 3) * 0.176, 0))
    camera(sc, 0, 5, 3.4, 90, (0, D / 2, H / 2 - 0.018), (2800, 952))
    shoot(sc, 'blender_lineup_front.png')

    sc = reset(); mats = fixed_materials()                      # receding diagonal line-up
    backdrop(sc, mats['floor'], y_back=3.0); lights(sc, cx=0.36, span=1.5)
    for i, c in enumerate(names):
        console(sc, mats, c, (i * 0.128, i * 0.104))
    camera(sc, -27, 9, 2.3, 85, (0.36, 0.30, H / 2 - 0.015), (2600, 1560))
    shoot(sc, 'blender_lineup_fan.png')

    for c in ('lilac', 'lime', 'black', 'white'):               # controller out of the dock
        sc = hero(c, docked=False, loose=(-0.048, -0.092, 12))
        camera(sc, -22, 13, 1.1, 105, (0, 0, H / 2 - 0.030), (1800, 1980))
        shoot(sc, f'blender_undocked_{c}.png')

    rear_shot()


def product_set(sel, tag='set'):
    """Packaging / advertising set for a short list of colourways."""
    n = len(sel)
    for c in sel:                                               # hero per colour
        sc = hero(c)
        camera(sc, 26, 9, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
        shoot(sc, f'{tag}_hero_{c}.png')

    sc = reset(); mats = fixed_materials()                      # straight-on row
    backdrop(sc, mats['floor']); lights(sc, span=1.2)
    for i, c in enumerate(sel):
        console(sc, mats, c, ((i - (n - 1) / 2) * 0.180, 0))
    camera(sc, 0, 5, 2.6, 100, (0, D / 2, H / 2 - 0.018), (2600, 1200))
    shoot(sc, f'{tag}_lineup_front.png')

    sc = reset(); mats = fixed_materials()                      # receding diagonal
    backdrop(sc, mats['floor'], y_back=2.8); lights(sc, cx=0.2, span=1.3)
    for i, c in enumerate(sel):
        console(sc, mats, c, (i * 0.135, i * 0.110))
    camera(sc, -27, 9, 1.9, 85, (0.215, 0.20, H / 2 - 0.012), (2400, 1600))
    shoot(sc, f'{tag}_lineup_fan.png')

    for c in sel[:2]:                                           # controller out of the dock
        sc = hero(c, docked=False, loose=(-0.048, -0.092, 12))
        camera(sc, -22, 13, 1.1, 105, (0, 0, H / 2 - 0.030), (1800, 1980))
        shoot(sc, f'{tag}_undocked_{c}.png')

    sc = hero(sel[0])                                           # straight-on front
    camera(sc, 0, 4, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
    shoot(sc, f'{tag}_front_{sel[0]}.png')

    sc = hero(sel[2])                                           # logo + controller close-up
    camera(sc, 30, 14, 0.55, 110, (0.022, 0, 0.040), (2000, 1400))
    shoot(sc, f'{tag}_detail_{sel[2]}.png')

    sc = hero(sel[1])                                           # screen + card slot close-up
    camera(sc, -20, 6, 0.55, 110, (0, 0, 0.165), (2000, 1500))
    shoot(sc, f'{tag}_face_{sel[1]}.png')


def spun(sc, az=180.0):
    """Turn the studio (backdrop + lights) around the console so a camera at
    azimuth `az` sees the product lit like a front three-quarter shot."""
    from mathutils import Matrix
    turn = 0.0 if abs(az) <= 40 else az - math.copysign(26, az) if abs(az) < 120 else 180.0
    if not turn:
        return
    c = Vector((0, D / 2, 0))
    spin = Matrix.Translation(c) @ Matrix.Rotation(math.radians(turn), 4, 'Z') @ Matrix.Translation(-c)
    bpy.context.view_layer.update()
    for ob in sc.collection.objects:
        if ob.name in ('cyc', 'key', 'fill', 'top', 'wall'):
            ob.matrix_world = spin @ ob.matrix_world


def final_set(main_color='white', others=('yellow', 'lilac', 'black')):
    """Finalised packaging / advertising set -> ../renders/final/."""
    F = '../renders/final/'
    C = (0, D / 2, H / 2 - 0.016)
    P_, L_ = (1800, 2250), (2400, 1700)
    c = main_color

    # --- whole-product angles, main colour
    for tag, az, el in (('01_front', 0, 4), ('02_front_right', 26, 9), ('03_front_left', -26, 9),
                        ('04_left_speaker', -55, 9), ('05_right', 55, 9), ('06_high', 32, 30),
                        ('07_low', 18, 1.5), ('08_top_down', 24, 52)):
        sc = hero(c, panel=True); spun(sc, az)
        camera(sc, az, el, 0.95 if el < 40 else 1.0, 110, C, P_)
        shoot(sc, f'{F}{c}_{tag}.png')
    for tag, az, el in (('09_rear_right', 206, 9), ('10_rear', 180, 4), ('11_rear_left', 154, 9)):
        sc = hero(c, panel=True); spun(sc, az)
        camera(sc, az, el, 0.95, 110, C, P_)
        shoot(sc, f'{F}{c}_{tag}.png')

    # --- controller out of the dock
    sc = hero(c, panel=True, docked=False, loose=(-0.048, -0.092, 12))
    camera(sc, -22, 13, 1.12, 105, (0, 0, H / 2 - 0.030), (2000, 2200))
    shoot(sc, f'{F}{c}_12_undocked.png')
    sc = hero(c, panel=True, docked=False, loose=(0.050, -0.095, -14))
    camera(sc, 24, 20, 1.12, 105, (0.01, 0, H / 2 - 0.035), (2000, 2200))
    shoot(sc, f'{F}{c}_13_undocked_high.png')

    # --- close-ups
    for tag, az, el, dist, tgt in (('14_detail_screen', -18, 6, 0.50, (0, 0, 0.166)),
                                   ('15_detail_controller', 28, 14, 0.50, (0.015, 0, 0.050)),
                                   ('16_detail_usb', -14, 9, 0.30, (USB_X, 0, USB_Z + 0.004)),
                                   ('17_detail_logo', 16, 10, 0.30, (0.034, 0, 0.014)),
                                   ('18_detail_speaker', -72, 6, 0.42, (-W / 2, SPK_Y, SPK_Z - 0.004))):
        sc = hero(c, panel=True); spun(sc, az)
        camera(sc, az, el, dist, 110, tgt, L_)
        shoot(sc, f'{F}{c}_{tag}.png')
    sc = hero(c, panel=True); spun(sc)
    camera(sc, 196, 8, 0.42, 110, (0, D, 0.105), L_)
    shoot(sc, f'{F}{c}_19_detail_rear_engraving.png')

    # --- other colours: the three key angles each
    for o in others:
        for tag, az, el in (('front_right', 26, 9), ('front', 0, 4), ('left_speaker', -55, 9)):
            sc = hero(o, panel=True); spun(sc, az)
            camera(sc, az, el, 0.95, 110, C, P_)
            shoot(sc, f'{F}{o}_{tag}.png')
        sc = hero(o, panel=True, docked=False, loose=(-0.048, -0.092, 12))
        camera(sc, -22, 13, 1.12, 105, (0, 0, H / 2 - 0.030), (2000, 2200))
        shoot(sc, f'{F}{o}_undocked.png')

    # --- line-ups of all four
    sel = [c] + list(others); n = len(sel)
    sc = reset(); mats = fixed_materials()
    backdrop(sc, mats['floor']); lights(sc, span=1.2)
    for i, o in enumerate(sel):
        console(sc, mats, o, ((i - (n - 1) / 2) * 0.180, 0), panel=True)
    camera(sc, 0, 5, 2.6, 100, (0, D / 2, H / 2 - 0.018), (3000, 1400))
    shoot(sc, f'{F}lineup_front.png')

    sc = reset(); mats = fixed_materials()
    backdrop(sc, mats['floor'], y_back=2.8); lights(sc, cx=0.2, span=1.3)
    for i, o in enumerate(sel):
        console(sc, mats, o, (i * 0.135, i * 0.110), panel=True)
    camera(sc, -27, 9, 1.9, 85, (0.215, 0.20, H / 2 - 0.012), (3000, 2000))
    shoot(sc, f'{F}lineup_diagonal.png')

    sc = reset(); mats = fixed_materials()                      # mirrored diagonal, speaker sides showing
    backdrop(sc, mats['floor'], y_back=2.8); lights(sc, cx=-0.2, span=1.3)
    for i, o in enumerate(sel):
        console(sc, mats, o, (-i * 0.135, i * 0.110), panel=True)
    camera(sc, 27, 9, 1.9, 85, (-0.215, 0.20, H / 2 - 0.012), (3000, 2000))
    shoot(sc, f'{F}lineup_diagonal_right.png')


ORIGINAL7 = ['yellow', 'red', 'white', 'lilac', 'indigo', 'black', 'lime']
EXTRA5 = ['classic', 'teal', 'orange', 'sky', 'pink']


def color_set():
    """Full colour range renders -> ../renders/colors/."""
    F = '../renders/colors/'
    C = (0, D / 2, H / 2 - 0.016)
    allc = ORIGINAL7 + EXTRA5

    def row(sel, name, res):                                    # straight-on row
        n = len(sel)
        sc = reset(); mats = fixed_materials()
        backdrop(sc, mats['floor']); lights(sc, span=0.25 * n)
        for i, c in enumerate(sel):
            console(sc, mats, c, ((i - (n - 1) / 2) * 0.178, 0), panel=True)
        camera(sc, 0, 5, 0.55 * n - 0.3, 95, (0, D / 2, H / 2 - 0.018), res)
        shoot(sc, F + name)

    row(ORIGINAL7, 'lineup_original7_front.png', (3200, 1100))
    row(EXTRA5, 'lineup_new5_front.png', (3000, 1300))

    sc = reset(); mats = fixed_materials()                      # receding diagonal, original seven
    backdrop(sc, mats['floor'], y_back=3.2); lights(sc, cx=0.36, span=1.6)
    for i, c in enumerate(ORIGINAL7):
        console(sc, mats, c, (i * 0.132, i * 0.108), panel=True)
    camera(sc, -27, 9, 2.45, 85, (0.38, 0.31, H / 2 - 0.012), (3000, 1900))
    shoot(sc, F + 'lineup_original7_diagonal.png')

    sc = reset(); mats = fixed_materials()                      # all twelve, two staggered rows
    backdrop(sc, mats['floor'], y_back=3.4); lights(sc, span=1.7)
    order = ['indigo', 'teal', 'lime', 'yellow', 'orange', 'red',      # back row
             'black', 'sky', 'lilac', 'white', 'classic', 'pink']       # front row
    for i, c in enumerate(order):
        r, k = divmod(i, 6)
        console(sc, mats, c, ((k - 2.5) * 0.205 + (0.10 if r == 0 else 0), 0.30 if r == 0 else 0), panel=True)
    camera(sc, 10, 17, 4.1, 90, (0.04, 0.20, H / 2 - 0.035), (3200, 1500))
    shoot(sc, F + 'group_all12.png')

    for c in ['red', 'indigo', 'lime'] + EXTRA5:                # heroes not in the earlier final set
        sc = hero(c, panel=True)
        camera(sc, 26, 9, 0.95, 110, C, (1800, 2250))
        shoot(sc, f'{F}{c}_front_right.png')


def rear_shot():
    """Rear three-quarter: spin the whole studio (backdrop + lights) half a turn
    around the console so the back is lit and framed like the front shots."""
    from mathutils import Matrix
    sc = hero('white', panel=True)
    c = Vector((0, D / 2, 0))
    spin = Matrix.Translation(c) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Translation(-c)
    bpy.context.view_layer.update()
    for ob in sc.collection.objects:
        if ob.name in ('cyc', 'key', 'fill', 'top', 'wall'):
            ob.matrix_world = spin @ ob.matrix_world
    camera(sc, 206, 9, 0.93, 110, (0, D / 2, H / 2 - 0.016), (1600, 2000))
    shoot(sc, 'blender_rear_white.png')

main()
