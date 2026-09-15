# -*- coding: utf-8 -*-
"""Standard programming-flowchart generator (Terminator/IO/Process/Decision
shapes) -- English version of build_flowchart.py. Draws the real control flow
executed by scripts/run_pipeline.py (01_pipeline -> 02_lifecycle ->
04_export_transform_sample -> 03_export_app_data): an outer loop over
config.yaml's failure_modes, with a NESTED inner loop over each mode's groups.
Every 2-way branch uses the symmetric V-merge pattern (diamond -> Yes/No boxes
-> single merge point below); RCM is the one 3-way exception."""

SPINE_X = 520
W = 1560

INK = "#1a2422"
DIM = "#55635e"
ACCENT = "#2c6b73"
LINE = "#aab5af"
GREEN = "#3c7a4f"
RED = "#a8342c"

parts = []
n_counter = 0


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def arrow(x1, y1, x2, y2, ah=True):
    m = 'marker-end="url(#ah)"' if ah else ""
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{INK}" stroke-width="1.8" fill="none" {m}/>')


def elbow(pts, ah=True, color=INK, dash=None):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    m = 'marker-end="url(#ah)"' if ah else ""
    dd = f'stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<path d="{d}" stroke="{color}" stroke-width="1.8" fill="none" {m} {dd}/>')


def label(x, y_, text, size=11, color=DIM, anchor="middle", bold=False, italic=False):
    w = 'font-weight="700"' if bold else ""
    it = 'font-style="italic"' if italic else ""
    parts.append(f'<text x="{x}" y="{y_}" text-anchor="{anchor}" font-size="{size}" fill="{color}" {w} {it}>{esc(text)}</text>')


def multiline(cx, cy, lines, size=12.2, color=INK, bold=False, mono_from=None, lh=16):
    n = len(lines)
    start = cy - (n - 1) * lh / 2 + 4
    for i, ln in enumerate(lines):
        mono = mono_from is not None and i >= mono_from
        fam = 'font-family="Consolas,monospace"' if mono else ""
        sz = size - 1 if mono else size
        w = 'font-weight="700"' if bold else ""
        parts.append(f'<text x="{cx}" y="{start + i*lh}" text-anchor="middle" font-size="{sz}" fill="{color}" {fam} {w}>{esc(ln)}</text>')


def step_num():
    global n_counter
    n_counter += 1
    return n_counter


def badge(cx, top_y, num):
    parts.append(f'<circle cx="{cx-2}" cy="{top_y-15}" r="12.5" fill="#ffffff" stroke="{LINE}" stroke-width="1"/>')
    label(cx-2, top_y-10.5, str(num), size=11, color=ACCENT, bold=True)


def terminator(cx, cy, text, w=210, h=48):
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" rx="{h/2}" fill="#eef1ef" stroke="{INK}" stroke-width="1.6"/>')
    label(cx, cy+5, text, size=13.5, color=INK, bold=True)
    return h


def io_box(cx, cy, lines, w=420, h=64):
    x, yt = cx - w/2, cy - h/2
    skew = 22
    pts = f"{x+skew},{yt} {x+w},{yt} {x+w-skew},{yt+h} {x},{yt+h}"
    parts.append(f'<polygon points="{pts}" fill="#eeeeee" stroke="{ACCENT}" stroke-width="1.4"/>')
    multiline(cx, cy, lines, size=11.8, bold=True)
    return h


def process(cx, cy, lines, w=420, h=None, mono_from=None):
    n = len(lines)
    if h is None:
        h = max(50, 26 + n * 18)
    x, yt = cx - w/2, cy - h/2
    parts.append(f'<rect x="{x}" y="{yt}" width="{w}" height="{h}" fill="#ffffff" stroke="{LINE}" stroke-width="1.3"/>')
    multiline(cx, cy, lines, size=12, mono_from=mono_from)
    return h


def decision(cx, cy, lines, w=320, h=100):
    x, yt = cx - w/2, cy - h/2
    pts = f"{cx},{yt} {cx+w/2},{cy} {cx},{yt+h} {cx-w/2},{cy}"
    parts.append(f'<polygon points="{pts}" fill="#f7ebdd" stroke="#b5651d" stroke-width="1.5"/>')
    multiline(cx, cy, lines, size=11.5, color="#8a4a15", bold=True, lh=15)
    return h


# ---------------------------------------------------------------------------
def flow_down(cy, gap=36):
    """Draw one arrow down the spine, return the next center y."""
    ny = cy + gap
    arrow(SPINE_X, cy, SPINE_X, ny)
    return ny


def decision_pair(cy_top, dtext, yes_lines, no_lines, half_w=170, box_dx=250, box_w=270, box_h=58,
                   gap1=44, gap2=40, d_h=100):
    """Symmetric V-merge: diamond -> Yes(left)/No(right) boxes -> single merge point.
       returns: center y after the merge."""
    d_h_ = decision(SPINE_X, cy_top, dtext, w=2*half_w, h=d_h)
    badge(SPINE_X, cy_top - d_h_/2, step_num())
    left_v = (SPINE_X - half_w, cy_top)
    right_v = (SPINE_X + half_w, cy_top)
    box_cy = cy_top + d_h_/2 + gap1 + box_h/2
    yes_x = SPINE_X - box_dx
    no_x = SPINE_X + box_dx
    elbow([left_v, (yes_x, box_cy - box_h/2)])
    elbow([right_v, (no_x, box_cy - box_h/2)])
    label((left_v[0]+yes_x)/2 - 6, (left_v[1]+box_cy-box_h/2)/2 - 6, "Yes", size=12, color=GREEN, bold=True, anchor="end")
    label((right_v[0]+no_x)/2 + 6, (right_v[1]+box_cy-box_h/2)/2 - 6, "No", size=12, color=RED, bold=True, anchor="start")
    process(yes_x, box_cy, yes_lines, w=box_w, h=box_h)
    process(no_x, box_cy, no_lines, w=box_w, h=box_h)
    merge_y = box_cy + box_h/2 + gap2
    elbow([(yes_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    elbow([(no_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    return merge_y


def loop_back(loop_x, from_y, top_y, left_v_xy, from_x=None, text=None, color=DIM):
    """Return path to a loop-condition diamond's left vertex. from_x defaults to SPINE_X-210."""
    fx = from_x if from_x is not None else SPINE_X - 210
    elbow([(fx, from_y), (loop_x, from_y), (loop_x, top_y), left_v_xy])
    if text:
        parts.append(f'<g transform="rotate(-90,{loop_x-18},{(from_y+top_y)/2})">'
                      f'<text x="{loop_x-18}" y="{(from_y+top_y)/2}" text-anchor="middle" font-size="10.5" '
                      f'fill="{color}" font-style="italic">{esc(text)}</text></g>')


parts.append(f'''<defs>
  <marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{INK}"/></marker>
</defs>''')

cy = 60
h = terminator(SPINE_X, cy, "Start"); badge(SPINE_X, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["Load config.yaml", "(parse failure_modes, assumptions, content)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["modes = failure_modes ;  i = 0"], h=44, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ===== OUTER LOOP: failure_mode =====
outer_top_y = cy
d_h = decision(SPINE_X, cy, ["i < len(modes) ?", "(all modes processed?)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
outer_left_v = (SPINE_X - 160, cy)
outer_right_v = (SPINE_X + 160, cy)
outer_bottom = cy + d_h/2
label(outer_left_v[0]-8, cy-8, "Yes", size=12.5, color=GREEN, bold=True, anchor="end")
label(outer_right_v[0]+8, cy-8, "No", size=12.5, color=RED, bold=True, anchor="start")

cy = flow_down(outer_bottom, 36)
h = process(SPINE_X, cy, ["mode = modes[i]", "Load events/readouts/groups CSV (per-mode columns)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["6-step cleansing",
                           "sync -> drift removal -> segmentation ->",
                           "missing/outlier -> code reconcile -> labeling"], h=78)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["Per asset: rate(t) -> z(t) -> anomaly(t) -> t*, lead_time"], w=460, h=52)
badge(SPINE_X - 230, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["groups = values of mode.group_col ;  j = 0"], h=44, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- NESTED INNER LOOP: group -- compute O, S, D ----
inner_top_y = cy
d_h2 = decision(SPINE_X, cy, ["j < len(groups) ?", "(all groups done?)"], w=280, h=92)
badge(SPINE_X, cy - d_h2/2, step_num())
inner_left_v = (SPINE_X - 140, cy)
inner_right_v = (SPINE_X + 140, cy)
inner_bottom = cy + d_h2/2
label(inner_left_v[0]-8, cy-8, "Yes", size=12, color=GREEN, bold=True, anchor="end")
label(inner_right_v[0]+8, cy-8, "No", size=12, color=RED, bold=True, anchor="start")

cy = flow_down(inner_bottom, 32)
h = process(SPINE_X, cy, ["group = groups[j]"], w=340, h=40)
badge(SPINE_X - 170, cy, step_num())
cy = flow_down(cy + h/2, 50)

h = process(SPINE_X, cy, ["Compute O, S, D  (see §2 formulas)",
                           "λ, rate, O grade · S_raw, S grade (proxy)",
                           "guide word + error% → detection rate, binomial test, D"], w=440, h=78)
badge(SPINE_X - 220, cy, step_num())
cy = flow_down(cy + h/2, 32)

h = process(SPINE_X, cy, ["j = j + 1"], w=200, h=36)
badge(SPINE_X - 100, cy, step_num())
inner_incr_y = cy

INNER_LOOP_X = 260
loop_back(INNER_LOOP_X, inner_incr_y, inner_top_y, inner_left_v, from_x=SPINE_X-100,
          text="↺ group loop-back", color=ACCENT)

# inner loop exit ("No") -> routes right, then down, then into i++ box (NOT a
# spine fallthrough from j++ -- the inner loop's only way out is the diamond's "No")
inner_exit_x = SPINE_X + 360
elbow([inner_right_v, (inner_exit_x, inner_right_v[1])], ah=False)
cy = inner_incr_y + 18 + 30 + 18  # j++ box bottom + gap + i++ box half-height, no drawn line

h = process(SPINE_X, cy, ["i = i + 1"], w=200, h=36)
badge(SPINE_X - 100, cy, step_num())
elbow([(inner_exit_x, inner_right_v[1]), (inner_exit_x, cy), (SPINE_X+100, cy)])
outer_incr_y = cy

OUTER_LOOP_X = 90
loop_back(OUTER_LOOP_X, outer_incr_y, outer_top_y, outer_left_v, from_x=SPINE_X-100,
          text="↺ failure-mode loop-back — next mode", color=DIM)

# outer loop exit ("No") -> down to combine step
outer_exit_x = SPINE_X + 460
elbow([outer_right_v, (outer_exit_x, outer_right_v[1])], ah=False)

cy_combine = outer_incr_y + 110
h = process(SPINE_X, cy_combine, ["Combine all (failure_mode, group) rows",
                                   "RPN = O×S×D    RI = 0.4O + 0.4S + 0.2D"], h=60, mono_from=1)
badge(SPINE_X - 210, cy_combine, step_num())
elbow([(outer_exit_x, outer_right_v[1]), (outer_exit_x, cy_combine), (SPINE_X+210, cy_combine)])
cy = flow_down(cy_combine + h/2, 36)

h = io_box(SPINE_X, cy, ["Save fmeca_worksheet.csv etc. to outputs/", "— 01_pipeline.py ends —"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ===== LOOP: 02_lifecycle.py -- each worksheet row =====
lc_top_y = cy
d_h3 = decision(SPINE_X, cy, ["k < len(worksheet) ?", "(all worksheet rows done?)"], w=340, h=100)
badge(SPINE_X, cy - d_h3/2, step_num())
lc_left_v = (SPINE_X - 170, cy)
lc_right_v = (SPINE_X + 170, cy)
lc_bottom = cy + d_h3/2
label(lc_left_v[0]-8, cy-8, "Yes", size=12.5, color=GREEN, bold=True, anchor="end")
label(lc_right_v[0]+8, cy-8, "No", size=12.5, color=RED, bold=True, anchor="start")

cy = flow_down(lc_bottom, 36)
h = process(SPINE_X, cy, ["row = worksheet[k]  (failure_mode, group)"], w=440, h=40)
badge(SPINE_X - 220, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- RCM: 3-way (special) ----
d_h = decision(SPINE_X, cy, ["Significant (p<.05) &", "detection rate ≥ 50% ?"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
d1_bottom = cy + d_h/2
label(lv[0]-8, cy-8, "Yes", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "No", size=12, color=RED, bold=True, anchor="start")

cbm_cy = d1_bottom + 44 + 29
elbow([lv, (SPINE_X-260, cbm_cy-29)])
process(SPINE_X-260, cbm_cy, ["RCM = CBM", "(Condition-Based Maintenance)"], w=270, h=58)

cy2 = flow_down(d1_bottom, 84)
d_h2b = decision(SPINE_X, cy2, ["S ≥ 5 ?"], w=280, h=96)
badge(SPINE_X, cy2 - d_h2b/2, step_num())
lv2, rv2 = (SPINE_X-140, cy2), (SPINE_X+140, cy2)
d2_bottom = cy2 + d_h2b/2
label(lv2[0]-8, cy2-8, "Yes", size=12, color=GREEN, bold=True, anchor="end")
label(rv2[0]+8, cy2-8, "No", size=12, color=RED, bold=True, anchor="start")

box_cy = d2_bottom + 40 + 29
elbow([lv2, (SPINE_X-250, box_cy-29)])
elbow([rv2, (SPINE_X+250, box_cy-29)])
process(SPINE_X-250, box_cy, ["RCM = Hard-Time", "(time-based preventive maintenance)"], w=300, h=58)
process(SPINE_X+250, box_cy, ["RCM = RTF", "(Run-to-Failure)"], w=300, h=58)

merge_y = box_cy + 29 + 40
elbow([(SPINE_X-250, box_cy+29), (SPINE_X, merge_y)])
elbow([(SPINE_X+250, box_cy+29), (SPINE_X, merge_y)])
far_x = SPINE_X - 460
elbow([(SPINE_X-260, cbm_cy+29), (far_x, cbm_cy+29)], ah=False)
elbow([(far_x, cbm_cy+29), (far_x, merge_y), (SPINE_X, merge_y)])
label(far_x-10, (cbm_cy+merge_y)/2, "CBM result merges here", size=10, color=DIM, italic=True, anchor="middle")
cy = merge_y

# ---- LORA ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["O ≥ 8 ?"],
                    ["LORA = elevate depot-repair", "priority + forward stock"],
                    ["LORA = standard 2-level", "(field exchange + depot repair)"])

# ---- Supply requirement ----
cy = flow_down(cy, 40)
h = process(SPINE_X, cy, ["Compute supply requirement (assumption + measured O)",
                           "annual_demand, reorder_point = f(rate, fleet_size, lead_days)"], w=460, h=60)
badge(SPINE_X - 230, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- IETM ----
cy = decision_pair(cy, ["Significant & lead time", "available ?"],
                    ["IETM = pre-emptive", "SLA = lead time × 0.5"],
                    ["IETM = enhanced periodic", "inspection (no pre-emptive SLA)"])

# ---- ECP ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["RPN rank 1 / O=10 /", "not significant — any ?"],
                    ["ECP = candidate", "(design change needed)"],
                    ["ECP = no change", "(no trigger)"])

# ---- save row, k++, loop back ----
cy = flow_down(cy, 36)
h = process(SPINE_X, cy, ["Save result row ;  k = k + 1"], h=44)
badge(SPINE_X - 210, cy, step_num())
lc_loopback_y = cy

LC_LOOP_X = 90
loop_back(LC_LOOP_X, lc_loopback_y, lc_top_y, lc_left_v, text="↺ row loop-back — next (failure_mode, group)")

lc_exit_x = SPINE_X + 460
elbow([lc_right_v, (lc_exit_x, lc_right_v[1])], ah=False)

cy_out = lc_loopback_y + 110
h = io_box(SPINE_X, cy_out, ["Save lifecycle.csv/json", "— 02_lifecycle.py ends —"], h=60)
badge(SPINE_X - 210, cy_out, step_num())
elbow([(lc_exit_x, lc_right_v[1]), (lc_exit_x, cy_out), (SPINE_X+210, cy_out)])
cy = flow_down(cy_out + h/2, 40)

# ---- 04: raw-vs-processed comparison sample selection ----
h = process(SPINE_X, cy, ["Auto-select sample assets per mode (1 hit + 1 miss)",
                           "recompute raw readouts → transform_sample.json",
                           "— 04_export_transform_sample.py —"], h=78)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

# ---- 03: JSON export ----
h = io_box(SPINE_X, cy, ["Generate dataset/fmeca/lifecycle/events/cleansing.json",
                          "— 03_export_app_data.py —"], w=460, h=60)
badge(SPINE_X - 230, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = io_box(SPINE_X, cy, ["Copy app_data/ → app/data/ (run_pipeline.py)"], h=48)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- feedback decision (web app §09) ----
d_h = decision(SPINE_X, cy, ["ECP candidate exists ?", "(feedback simulator, web app)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
db = cy + d_h/2
label(lv[0]-8, cy-8, "Yes", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "No", size=12, color=RED, bold=True, anchor="start")

fb_cy = db + 40 + 32
elbow([lv, (SPINE_X-260, fb_cy-32)])
process(SPINE_X-260, fb_cy, ["Recompute O′=O−2, D′=D−3 →", "RPN′, RI′, RCM′, LORA′, IETM′, supply′"], w=300, h=64)
fb2_cy = fb_cy + 32 + 26 + 26
h_io = io_box(SPINE_X-260, fb2_cy, ["Show result in web app §09"], w=300, h=48)

merge_y = fb2_cy + h_io/2 + 40
elbow([(SPINE_X-260, fb2_cy+h_io/2), (SPINE_X, merge_y)])
elbow([rv, (SPINE_X+40, db+20), (SPINE_X, merge_y)])
label(rv[0]+16, db+20, "(straight to End)", size=9.5, color=DIM, italic=True, anchor="start")

cy = flow_down(merge_y, 40)
h = terminator(SPINE_X, cy, "End")
badge(SPINE_X, cy, step_num())

TOTAL_H = int(cy + h/2 + 60)
CANVAS_W = W

svg = f'''<svg viewBox="0 0 {CANVAS_W} {TOTAL_H}" xmlns="http://www.w3.org/2000/svg" font-family="Arial,'Malgun Gothic','Apple SD Gothic Neo',sans-serif">
<rect x="0" y="0" width="{CANVAS_W}" height="{TOTAL_H}" fill="#ffffff"/>
<text x="40" y="34" font-family="Georgia,serif" font-size="22" font-weight="700" fill="{INK}">FMECA-IPS Pipeline — Programming Flowchart</text>
<text x="40" y="54" font-size="12" fill="{DIM}">Generic dataset schema (see DATASET_FORMAT.md) · run_pipeline.py executes 01→02→04→03 in order · Shapes: ⬭ Start/End ▱ I/O ▭ Process ◇ Decision</text>
{"".join(parts)}
</svg>'''

with open("flowchart_program_en.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("done, height=", TOTAL_H, "width=", CANVAS_W, "steps=", n_counter)
