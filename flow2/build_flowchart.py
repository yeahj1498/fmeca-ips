# -*- coding: utf-8 -*-
"""표준 프로그래밍 플로우차트(시작/입출력/처리/판단 도형) 생성기 -- v2, 대칭 V-병합 패턴.
모든 2지 분기는 다이아몬드 -> 좌(예)/우(아니오) 박스 -> 아래 한 점으로 합류하는
동일한 틀을 쓴다. RCM만 3지 분기라 예외적으로 확장한다."""

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


def elbow(pts, ah=True):
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    m = 'marker-end="url(#ah)"' if ah else ""
    parts.append(f'<path d="{d}" stroke="{INK}" stroke-width="1.8" fill="none" {m}/>')


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
    """중심선을 따라 화살표 하나 그리고 다음 중심 y 반환."""
    ny = cy + gap
    arrow(SPINE_X, cy, SPINE_X, ny)
    return ny


def decision_pair(cy_top, dtext, yes_lines, no_lines, half_w=170, box_dx=250, box_w=270, box_h=58,
                   gap1=44, gap2=40, d_h=100):
    """대칭 V-병합: 다이아몬드 -> 좌(예)/우(아니오) 박스 -> 한 점으로 합류.
       return: (합류 후 중심 y, 이 블록이 차지한 마지막 y)"""
    d_h_ = decision(SPINE_X, cy_top, dtext, w=2*half_w, h=d_h)
    badge(SPINE_X, cy_top - d_h_/2, step_num())
    left_v = (SPINE_X - half_w, cy_top)
    right_v = (SPINE_X + half_w, cy_top)
    box_cy = cy_top + d_h_/2 + gap1 + box_h/2
    yes_x = SPINE_X - box_dx
    no_x = SPINE_X + box_dx
    # diamond vertex -> box top
    elbow([left_v, (yes_x, box_cy - box_h/2)])
    elbow([right_v, (no_x, box_cy - box_h/2)])
    label((left_v[0]+yes_x)/2 - 6, (left_v[1]+box_cy-box_h/2)/2 - 6, "예", size=12, color=GREEN, bold=True, anchor="end")
    label((right_v[0]+no_x)/2 + 6, (right_v[1]+box_cy-box_h/2)/2 - 6, "아니오", size=12, color=RED, bold=True, anchor="start")
    process(yes_x, box_cy, yes_lines, w=box_w, h=box_h)
    process(no_x, box_cy, no_lines, w=box_w, h=box_h)
    merge_y = box_cy + box_h/2 + gap2
    elbow([(yes_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    elbow([(no_x, box_cy+box_h/2), (SPINE_X, merge_y)])
    return merge_y


parts.append(f'''<defs>
  <marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{INK}"/></marker>
</defs>''')

cy = 60
h = terminator(SPINE_X, cy, "시작"); badge(SPINE_X, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = io_box(SPINE_X, cy, ["3개 CSV 입력 (readouts · tte · specifications)"], h=52)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["정제 6단계", "(동기화 → 드리프트제거 → 구간분할 → 결측/이상치 → 코드정합 → 라벨정의)"], h=64)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["차량별 rate(t) → z(t) → anomaly(t) → t*, lead_time 계산"], h=52)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 40)

h = process(SPINE_X, cy, ["groups = [형상A, 형상B, 형상C, 형상D] ;  i = 0"], h=50, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ===== LOOP =====
loop_top_y = cy
d_h = decision(SPINE_X, cy, ["i < len(groups) ?", "(모든 형상군 처리?)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
loop_left_v = (SPINE_X - 160, cy)
loop_right_v = (SPINE_X + 160, cy)
loop_bottom = cy + d_h/2
label(loop_left_v[0]-8, cy-8, "예", size=12.5, color=GREEN, bold=True, anchor="end")
label(loop_right_v[0]+8, cy-8, "아니오", size=12.5, color=RED, bold=True, anchor="start")

cy = flow_down(loop_bottom, 36)
h = process(SPINE_X, cy, ["group = groups[i]"], h=44)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["O, S, D 계산  (§2 공식)",
                           "λ,rate,O등급 · S_raw,S등급(근사)",
                           "guide word+오차율% · 탐지율,이항검정,D등급"], h=78)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 36)

h = process(SPINE_X, cy, ["RPN = O×S×D    RI = 0.4O + 0.4S + 0.2D"], h=48, mono_from=0)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- RCM: 3-way (special) ----
d_h = decision(SPINE_X, cy, ["유의(p<.05) &", "탐지율 ≥ 50% ?"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
d1_bottom = cy + d_h/2
label(lv[0]-8, cy-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "아니오", size=12, color=RED, bold=True, anchor="start")

cbm_cy = d1_bottom + 44 + 29
elbow([lv, (SPINE_X-260, cbm_cy-29)])
process(SPINE_X-260, cbm_cy, ["RCM = CBM", "(상태기반정비)"], w=250, h=58)

# No -> down to second diamond
cy2 = flow_down(d1_bottom, 84)
d_h2 = decision(SPINE_X, cy2, ["S ≥ 5 ?"], w=280, h=96)
badge(SPINE_X, cy2 - d_h2/2, step_num())
lv2, rv2 = (SPINE_X-140, cy2), (SPINE_X+140, cy2)
d2_bottom = cy2 + d_h2/2
label(lv2[0]-8, cy2-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv2[0]+8, cy2-8, "아니오", size=12, color=RED, bold=True, anchor="start")

box_cy = d2_bottom + 40 + 29
elbow([lv2, (SPINE_X-250, box_cy-29)])
elbow([rv2, (SPINE_X+250, box_cy-29)])
process(SPINE_X-250, box_cy, ["RCM = Hard-Time", "(시간기준 예방정비)"], w=260, h=58)
process(SPINE_X+250, box_cy, ["RCM = RTF", "(사후정비)"], w=260, h=58)

merge_y = box_cy + 29 + 40
elbow([(SPINE_X-250, box_cy+29), (SPINE_X, merge_y)])
elbow([(SPINE_X+250, box_cy+29), (SPINE_X, merge_y)])
# CBM long return line, routed clear on the far left (outside everything else)
far_x = SPINE_X - 460
elbow([(SPINE_X-260, cbm_cy+29), (far_x, cbm_cy+29)], ah=False)
elbow([(far_x, cbm_cy+29), (far_x, merge_y), (SPINE_X, merge_y)])
label(far_x-10, (cbm_cy+merge_y)/2, "CBM 결과 합류", size=10, color=DIM, italic=True, anchor="middle")
cy = merge_y

# ---- LORA ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["O ≥ 8 ?"],
                    ["LORA = 창정비 우선상향", "+ 예비품 전진배치"],
                    ["LORA = 표준 2-Level", "(야전교환+창정비모듈수리)"])

# ---- 보급소요 ----
cy = flow_down(cy, 40)
h = process(SPINE_X, cy, ["보급소요 계산", "annual_demand, reorder_point = f(rate, fleet, lead_days)"], h=60)
badge(SPINE_X - 210, cy, step_num())
cy = flow_down(cy + h/2, 84)

# ---- IETM ----
cy = decision_pair(cy, ["유의 & 리드타임", "존재 ?"],
                    ["IETM = 사전점검 SLA", "SLA = 리드타임 × 0.5"],
                    ["IETM = 정기점검 강화", "(사전 SLA 없음)"])

# ---- ECP ----
cy = flow_down(cy, 84)
cy = decision_pair(cy, ["RPN 1위 / O=10 /", "비유의 중 하나 ?"],
                    ["ECP = 후보", "(설계개선 필요)"],
                    ["ECP = 현행유지", "(트리거 없음)"])

# ---- save row, i++, loop back ----
cy = flow_down(cy, 36)
h = process(SPINE_X, cy, ["결과 행 저장 ;  i = i + 1"], h=44)
badge(SPINE_X - 210, cy, step_num())
loopback_y = cy

LOOP_X = 90
elbow([(SPINE_X-210, loopback_y), (LOOP_X, loopback_y), (LOOP_X, loop_top_y), (loop_left_v[0], loop_left_v[1])])
parts.append(f'<g transform="rotate(-90,{LOOP_X-18},{(loopback_y+loop_top_y)/2})">'
             f'<text x="{LOOP_X-18}" y="{(loopback_y+loop_top_y)/2}" text-anchor="middle" font-size="11" fill="{DIM}" font-style="italic">↺ 루프백 — 다음 형상군으로</text></g>')

# loop exit (아니오) -> right, then down to save-output step
exit_x = SPINE_X + 460
elbow([loop_right_v, (exit_x, loop_right_v[1])], ah=False)

cy_out = loopback_y + 110
h = io_box(SPINE_X, cy_out, ["fmeca_worksheet.csv · lifecycle.json 저장"], h=56)
badge(SPINE_X - 210, cy_out, step_num())
elbow([(exit_x, loop_right_v[1]), (exit_x, cy_out), (SPINE_X+210, cy_out)])
cy = flow_down(cy_out + h/2, 84)

# ---- feedback decision ----
d_h = decision(SPINE_X, cy, ["ECP 후보 있음 ?", "(피드백 시뮬레이션)"], w=320, h=100)
badge(SPINE_X, cy - d_h/2, step_num())
lv, rv = (SPINE_X-160, cy), (SPINE_X+160, cy)
db = cy + d_h/2
label(lv[0]-8, cy-8, "예", size=12, color=GREEN, bold=True, anchor="end")
label(rv[0]+8, cy-8, "아니오", size=12, color=RED, bold=True, anchor="start")

fb_cy = db + 40 + 32
elbow([lv, (SPINE_X-260, fb_cy-32)])
process(SPINE_X-260, fb_cy, ["O′=O−2, D′=D−3 재계산 →", "RPN′,RI′,RCM′,LORA′,IETM′,보급소요′"], w=300, h=64)
fb2_cy = fb_cy + 32 + 26 + 26
h_io = io_box(SPINE_X-260, fb2_cy, ["웹앱 §09에 결과 표시"], w=300, h=48)

merge_y = fb2_cy + h_io/2 + 40
elbow([(SPINE_X-260, fb2_cy+h_io/2), (SPINE_X, merge_y)])
elbow([rv, (SPINE_X+40, db+20), (SPINE_X, merge_y)])
label(rv[0]+16, db+20, "(바로 종료로)", size=9.5, color=DIM, italic=True, anchor="start")

cy = flow_down(merge_y, 40)
h = terminator(SPINE_X, cy, "종료")
badge(SPINE_X, cy, step_num())

TOTAL_H = int(cy + h/2 + 60)
CANVAS_W = W

svg = f'''<svg viewBox="0 0 {CANVAS_W} {TOTAL_H}" xmlns="http://www.w3.org/2000/svg" font-family="'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif">
<rect x="0" y="0" width="{CANVAS_W}" height="{TOTAL_H}" fill="#ffffff"/>
<text x="40" y="34" font-family="Georgia,serif" font-size="22" font-weight="700" fill="{INK}">FMECA-IPS 처리 알고리즘 — 프로그래밍 플로우차트</text>
<text x="40" y="54" font-size="12" fill="{DIM}">SCANIA Component X 실측 데이터 기준 · scripts/01_pipeline.py · 02_lifecycle.py · 표준 도형: ⬭시작/종료 ▱입출력 ▭처리 ◇판단</text>
{"".join(parts)}
</svg>'''

with open("flowchart_program.svg", "w", encoding="utf-8") as f:
    f.write(svg)
print("done, height=", TOTAL_H, "width=", CANVAS_W)
