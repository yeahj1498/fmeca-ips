# -*- coding: utf-8 -*-
"""Clean textbook-style flowchart (HAZOP-reference grammar: monochrome,
uniform boxes, inline do-while loop diamonds with a side return rail),
laid out in 4 columns left-to-right so the whole thing fits a 16:9 PPT
slide instead of one very tall strip. Column 1 = 01_pipeline.py (nested
failure_mode/group loop), column 2 = 02_lifecycle.py part A (RCM/LORA/
supply/IETM), column 3 = 02_lifecycle.py part B (ECP onward) + row loop,
column 4 = export steps + feedback branch + End.

Height math is explicit everywhere: next box center = prev center +
prev_h/2 + pad + next_h/2, via next_cy() -- no blind "gap" guessing."""

W, HGT = 2100, 1180
COL_W = 440
COLX = [260, 780, 1300, 1820]
TITLE_H = 56

INK = "#101414"
LINE = "#101414"
FONT = "'Times New Roman',Georgia,serif"

parts = []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def elbow(pts, ah=True):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    m = 'marker-end="url(#ah)"' if ah else ""
    parts.append(f'<path d="{d}" stroke="{LINE}" stroke-width="1.6" fill="none" {m}/>')


def label(x, y_, text, size=12, color=INK, anchor="middle", bold=False, italic=False):
    w = 'font-weight="700"' if bold else ""
    it = 'font-style="italic"' if italic else ""
    parts.append(f'<text x="{x}" y="{y_}" text-anchor="{anchor}" font-size="{size}" fill="{color}" {w} {it}>{esc(text)}</text>')


def multiline(cx, cy, lines, size=12.5, color=INK, lh=16):
    n = len(lines)
    start = cy - (n - 1) * lh / 2 + 4
    for i, ln in enumerate(lines):
        parts.append(f'<text x="{cx}" y="{start + i*lh}" text-anchor="middle" font-size="{size}" fill="{color}">{esc(ln)}</text>')


def terminator(cx, cy, text, w=170, h=42):
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" rx="{h/2}" fill="#ffffff" stroke="{LINE}" stroke-width="1.6"/>')
    label(cx, cy+5, text, size=13.5, bold=True)
    return h


def io_box(cx, cy, lines, w=COL_W-40, h=48):
    x, yt = cx - w/2, cy - h/2
    skew = 18
    pts = f"{x+skew},{yt} {x+w},{yt} {x+w-skew},{yt+h} {x},{yt+h}"
    parts.append(f'<polygon points="{pts}" fill="#ffffff" stroke="{LINE}" stroke-width="1.6"/>')
    multiline(cx, cy, lines)
    return h


def process(cx, cy, lines, w=COL_W-40, h=None):
    n = len(lines)
    if h is None:
        h = max(34, 18 + n * 16)
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" fill="#ffffff" stroke="{LINE}" stroke-width="1.6"/>')
    multiline(cx, cy, lines)
    return h


def decision(cx, cy, lines, w=300, h=76):
    x, yt = cx - w/2, cy - h/2
    pts = f"{cx},{yt} {cx+w/2},{cy} {cx},{yt+h} {cx-w/2},{cy}"
    parts.append(f'<polygon points="{pts}" fill="#ffffff" stroke="{LINE}" stroke-width="1.6"/>')
    multiline(cx, cy, lines, size=12)
    return h


def next_cy(cy, h_prev, h_next, pad=14):
    """Correct spacing: distance from prev CENTER to next CENTER, given
    both heights explicitly, so boxes never overlap regardless of size."""
    return cy + h_prev/2 + pad + h_next/2


def vline(x, cy, h, pad_before, pad_after):
    """draw the connecting arrow before placing a shape of height h at x;
    returns the shape's center y given the previous bottom edge y0."""
    pass  # (kept as a no-op placeholder; real spine arrows drawn inline below)


def spine(x, y0, y1):
    elbow([(x, y0), (x, y1)])


def loop_check(x, cy, lines, target_cy, side_x, w=280, h=70):
    """Inline do-while diamond. NO continues straight down (spine drawn by
    caller); YES exits the right vertex, runs up the rail at side_x, and
    re-enters the repeated step from the right with an arrowhead."""
    decision(x, cy, lines, w=w, h=h)
    right_v = (x + w/2, cy)
    label(right_v[0]+8, cy-3, "YES", size=11, bold=True, anchor="start")
    label(x+10, cy+h/2+16, "NO", size=11, bold=True, anchor="start")
    target_x = x + (COL_W-40)/2
    elbow([right_v, (side_x, cy)], ah=False)
    elbow([(side_x, cy), (side_x, target_cy)], ah=False)
    elbow([(side_x, target_cy), (target_x, target_cy)])


def branch_merge(x, cy_top, dtext, yes_lines, no_lines, half_w=140, box_dx=145, box_w=160, box_h=44,
                  pad1=20, pad2=18, d_h=68):
    """Compact 2-way branch -> merge for TRUE decisions (different
    persistent outcomes, not a loop repeat). Returns merge-point y."""
    decision(x, cy_top, dtext, w=2*half_w, h=d_h)
    left_v = (x - half_w, cy_top)
    right_v = (x + half_w, cy_top)
    box_cy = cy_top + d_h/2 + pad1 + box_h/2
    yes_x = x - box_dx
    no_x = x + box_dx
    elbow([left_v, (yes_x, box_cy - box_h/2)])
    elbow([right_v, (no_x, box_cy - box_h/2)])
    label((left_v[0]+yes_x)/2 - 4, (left_v[1]+box_cy-box_h/2)/2 - 5, "YES", size=10.5, bold=True, anchor="end")
    label((right_v[0]+no_x)/2 + 4, (right_v[1]+box_cy-box_h/2)/2 - 5, "NO", size=10.5, bold=True, anchor="start")
    process(yes_x, box_cy, yes_lines, w=box_w, h=box_h)
    process(no_x, box_cy, no_lines, w=box_w, h=box_h)
    merge_y = box_cy + box_h/2 + pad2
    elbow([(yes_x, box_cy+box_h/2), (x, merge_y)])
    elbow([(no_x, box_cy+box_h/2), (x, merge_y)])
    return merge_y


parts.append(f'''<defs>
  <marker id="ah" markerWidth="8" markerHeight="8" refX="6.5" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="{INK}"/></marker>
</defs>''')

C1, C2, C3, C4 = COLX
ATTIC_Y = TITLE_H + 20   # a clear horizontal lane above all column content,
                         # reserved for the row-loop's cross-column return edge
TOP = TITLE_H + 60

# ===========================================================================
# COLUMN 1 -- 01_pipeline.py
# ===========================================================================
cy = TOP
h_start = terminator(C1, cy, "Start")
cy2 = next_cy(cy, h_start, 46); spine(C1, cy+h_start/2, cy2-46/2)
h = process(C1, cy2, ["Load config.yaml", "(parse failure_modes, assumptions, content)"], h=52); cy = cy2

mode_top_y = next_cy(cy, h, 34); spine(C1, cy+h/2, mode_top_y-17)
h = process(C1, mode_top_y, ["mode = next failure mode"], h=34); cy = mode_top_y

cy2 = next_cy(cy, h, 54); spine(C1, cy+h/2, cy2-27)
h = process(C1, cy2, ["Load events / readouts / groups CSV", "(mode-specific columns and counters)"], h=54); cy = cy2

cy2 = next_cy(cy, h, 68); spine(C1, cy+h/2, cy2-34)
h = process(C1, cy2, ["6-step cleansing: sync -> drift removal", "-> segmentation -> missing/outlier ->", "code reconcile -> labeling"], h=68); cy = cy2

cy2 = next_cy(cy, h, 52); spine(C1, cy+h/2, cy2-26)
h = process(C1, cy2, ["Per asset: rate(t) -> z(t) -> anomaly(t)", "-> t*, lead_time"], h=52); cy = cy2

group_top_y = next_cy(cy, h, 34, pad=20); spine(C1, cy+h/2, group_top_y-17)
h = process(C1, group_top_y, ["group = next group in this mode"], h=34); cy = group_top_y

cy2 = next_cy(cy, h, 54); spine(C1, cy+h/2, cy2-27)
h = process(C1, cy2, ["Compute O, S, D  (guide word + error %,", "detection rate, binomial test)"], h=54); cy = cy2

cy2 = next_cy(cy, h, 76, pad=20); spine(C1, cy+h/2, cy2-38)
INNER_RAIL = C1 + (COL_W-40)/2 + 20
loop_check(C1, cy2, ["Other groups", "in this mode?"], group_top_y, INNER_RAIL, w=260, h=76); cy = cy2; h = 76

cy2 = next_cy(cy, h, 76, pad=22); spine(C1, cy+h/2, cy2-38)
OUTER_RAIL = C1 + (COL_W-40)/2 + 50
loop_check(C1, cy2, ["Other failure", "modes?"], mode_top_y, OUTER_RAIL, w=260, h=76); cy = cy2; h = 76

cy2 = next_cy(cy, h, 52, pad=20); spine(C1, cy+h/2, cy2-26)
h = process(C1, cy2, ["Combine all (failure_mode, group) rows;", "RPN = O×S×D   RI = 0.4O+0.4S+0.2D"], h=52); cy = cy2

cy2 = next_cy(cy, h, 52); spine(C1, cy+h/2, cy2-26)
h = io_box(C1, cy2, ["Save fmeca_worksheet.csv etc. to outputs/", "(01_pipeline.py ends)"], h=52); cy = cy2
col1_end_y = cy
col1_end_h = h

# ===========================================================================
# COLUMN 2 -- 02_lifecycle.py part A (RCM / LORA / supply / IETM)
# ===========================================================================
cy = TOP
h = process(C2, cy, ["row = next worksheet row", "(failure_mode, group)"], h=52)
row_top_y = cy
col2_top_h = h

cy2 = next_cy(cy, h, 76, pad=24); spine(C2, cy+h/2, cy2-38)
d_h = decision(C2, cy2, ["Significant (p<.05) &", "detection rate >= 50%?"], w=300, h=76)
lv, rv = (C2-150, cy2), (C2+150, cy2)
d1_bottom = cy2 + d_h/2
label(lv[0]-6, cy2-4, "YES", size=10.5, bold=True, anchor="end")
label(rv[0]+6, cy2-4, "NO", size=10.5, bold=True, anchor="start")

cbm_cy = d1_bottom + 22 + 19
elbow([lv, (C2-140, cbm_cy-19)])
process(C2-140, cbm_cy, ["RCM = CBM", "(condition-based)"], w=130, h=38)

cy3 = next_cy(d1_bottom+0, 0, 62, pad=65)
d_h2 = decision(C2, cy3, ["S >= 5?"], w=210, h=62)
lv2, rv2 = (C2-105, cy3), (C2+105, cy3)
d2_bottom = cy3 + d_h2/2
label(lv2[0]-6, cy3-4, "YES", size=10.5, bold=True, anchor="end")
label(rv2[0]+6, cy3-4, "NO", size=10.5, bold=True, anchor="start")

box_cy = d2_bottom + 20 + 19
elbow([lv2, (C2-160, box_cy-19)])
elbow([rv2, (C2+160, box_cy-19)])
process(C2-160, box_cy, ["RCM = Hard-Time", "(time-based)"], w=140, h=38)
process(C2+160, box_cy, ["RCM = RTF", "(run-to-failure)"], w=140, h=38)

merge_y = box_cy + 19 + 20
elbow([(C2-160, box_cy+19), (C2, merge_y)])
elbow([(C2+160, box_cy+19), (C2, merge_y)])
far_x = C2 - 230
elbow([(C2-140, cbm_cy+19), (far_x, cbm_cy+19)], ah=False)
elbow([(far_x, cbm_cy+19), (far_x, merge_y), (C2, merge_y)])
label(far_x-8, (cbm_cy+merge_y)/2, "CBM merges here", size=8.5, italic=True, anchor="middle")
spine(C2, cy+h/2, cy2-38)  # already drawn above; keep RCM block self-contained
cy = merge_y; h = 4  # merge point treated as a zero-height node for spacing math

cy2 = next_cy(cy, h, 68, pad=18); spine(C2, cy, cy2-34)
lora_merge = branch_merge(C2, cy2, ["O >= 8?"],
                           ["LORA = elevate", "depot priority"],
                           ["LORA = standard", "2-level"], d_h=68)
cy = lora_merge; h = 4

cy2 = next_cy(cy, h, 52, pad=18); spine(C2, cy, cy2-26)
h = process(C2, cy2, ["Compute supply requirement", "(assumption + measured O)"], h=52); cy = cy2

cy2 = next_cy(cy, h, 68, pad=18); spine(C2, cy+h/2, cy2-34)
ietm_merge = branch_merge(C2, cy2, ["Significant & lead", "time available?"],
                           ["IETM = pre-emptive", "SLA = lead x 0.5"],
                           ["IETM = enhanced", "periodic inspection"], d_h=68)
cy = ietm_merge
col2_end_y = cy

# ===========================================================================
# COLUMN 3 -- 02_lifecycle.py part B (ECP onward) + row loop
# ===========================================================================
cy = TOP
ecp_merge = branch_merge(C3, cy, ["RPN rank 1 / O=10 /", "not significant?"],
                          ["ECP = candidate", "(design change)"],
                          ["ECP = no change", "(no trigger)"], d_h=68)
cy = ecp_merge

cy2 = next_cy(cy, 4, 34, pad=16); spine(C3, cy, cy2-17)
h = process(C3, cy2, ["Save result row"], h=34); cy = cy2

cy2 = next_cy(cy, h, 76, pad=22); spine(C3, cy+h/2, cy2-38)
# This loop-back returns to column 2 (a DIFFERENT column than the diamond
# itself), so the generic same-column loop_check() helper doesn't apply --
# route the YES edge out to the right, up into the attic lane above every
# column's content, left across to column 2, then down into the target box
# from above.
d_h = decision(C3, cy2, ["Other worksheet", "rows?"], w=260, h=76)
right_v = (C3 + 130, cy2)
label(right_v[0]+8, cy2-3, "YES", size=11, bold=True, anchor="start")
label(C3+10, cy2+76/2+16, "NO", size=11, bold=True, anchor="start")
ROW_RAIL_X = C3 + 250
elbow([right_v, (ROW_RAIL_X, cy2)], ah=False)
elbow([(ROW_RAIL_X, cy2), (ROW_RAIL_X, ATTIC_Y)], ah=False)
elbow([(ROW_RAIL_X, ATTIC_Y), (C2, ATTIC_Y)], ah=False)
elbow([(C2, ATTIC_Y), (C2, row_top_y - col2_top_h/2)])
cy = cy2; h = 76

cy2 = next_cy(cy, h, 52, pad=20); spine(C3, cy+h/2, cy2-26)
h = io_box(C3, cy2, ["Save lifecycle.csv/json", "(02_lifecycle.py ends)"], h=52); cy = cy2

cy2 = next_cy(cy, h, 68, pad=18); spine(C3, cy+h/2, cy2-34)
h = process(C3, cy2, ["Auto-select sample assets per mode", "(1 detected + 1 missed); recompute ->", "transform_sample.json"], h=68); cy = cy2
col3_end_y = cy
col3_end_h = h

# ===========================================================================
# COLUMN 4 -- export + feedback + End
# ===========================================================================
cy = TOP
h = io_box(C4, cy, ["Generate dataset / fmeca / lifecycle /", "events / cleansing.json"], h=52)
col4_top_h = h

cy2 = next_cy(cy, h, 38, pad=18); spine(C4, cy+h/2, cy2-19)
h = io_box(C4, cy2, ["Copy app_data/ -> app/data/"], h=38); cy = cy2

cy2 = next_cy(cy, h, 68, pad=22); spine(C4, cy+h/2, cy2-34)
fb_merge = branch_merge(C4, cy2, ["ECP candidate", "exists?"],
                         ["Recompute O', D' ->", "RPN', RCM', etc."],
                         ["(straight to End)", ""], d_h=68, box_w=190)
cy = fb_merge

cy2 = next_cy(cy, 4, 46, pad=20)
h = terminator(C4, cy2, "End"); spine(C4, cy, cy2-23)

# ===========================================================================
# inter-column connectors (bottom of col N -> top of col N+1)
# ===========================================================================
def connect(x1, y1, x2, y2, mid_y):
    elbow([(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)])

connect(C1, col1_end_y + col1_end_h/2, C2, TOP - col2_top_h/2, HGT-60)
connect(C2, col2_end_y, C3, TOP - 68/2, HGT-40)
connect(C3, col3_end_y + col3_end_h/2, C4, TOP - col4_top_h/2, HGT-20)

# column headers
for x, txt in [(C1, "01_pipeline.py — cleansing + O/S/D"), (C2, "02_lifecycle.py — RCM / LORA / supply / IETM"),
               (C3, "02_lifecycle.py — ECP + row loop"), (C4, "04 + 03 export, then feedback (web app)")]:
    label(x, TOP - 14, txt, size=12, color="#55635e", italic=True)

svg = f'''<svg viewBox="0 0 {W} {HGT}" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">
<rect x="0" y="0" width="{W}" height="{HGT}" fill="#ffffff"/>
<text x="{W/2}" y="{TITLE_H}" text-anchor="middle" font-size="24" font-weight="700" fill="{INK}">Figure. FMECA-IPS Pipeline Flowchart</text>
{"".join(parts)}
</svg>'''

with open("flowchart_ppt.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("done, W=", W, "H=", HGT,
      "col_ends=", col1_end_y+col1_end_h/2, col2_end_y, col3_end_y+col3_end_h/2, cy2+46/2)
