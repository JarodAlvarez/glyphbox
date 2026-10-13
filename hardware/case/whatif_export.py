"""Export alternate front designs for comparison renders -> render_assets/*_<variant>.stl"""
import glyphbox_case as G
import promo as P
from blender_export import save

for v in ('flat', 'faceplate', 'scoop', 'grille'):
    G.FRONT_STYLE = v
    save('body_' + v, G.build_body())
    scr = dict((mat, m) for m, mat in P.screen_parts())
    save('glass_' + v, scr['glass']); save('lit_' + v, scr['lit'])
    if v == 'faceplate':
        save('plate_faceplate', G.build_faceplate())
