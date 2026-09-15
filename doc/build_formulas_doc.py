# -*- coding: utf-8 -*-
"""FMECA-IPS 산출 공식 정리 문서 (python-docx; docx-js용 Node.js가 이 환경에 없어 대체)."""
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BODY_FONT = "맑은 고딕"
MONO_FONT = "Consolas"
HEAD_FONT = "맑은 고딕"

INK = RGBColor(0x1A, 0x24, 0x22)
INK_DIM = RGBColor(0x55, 0x63, 0x5E)
ACCENT = RGBColor(0x2C, 0x6B, 0x73)
AMBER = RGBColor(0xB5, 0x65, 0x1D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = "F0F4F2"
HEADER_GRAY = "2C6B73"


def set_font(run, name=BODY_FONT, size=11, bold=False, italic=False, color=INK):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name)


def set_cell_shading(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def set_cell_border(cell, color="CCD5CF", sz=4):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:color'), color)
        borders.append(el)
    tcPr.append(borders)


def add_para(doc, text="", size=11, bold=False, italic=False, color=INK, font=BODY_FONT,
             align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=6, indent=None):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    if text:
        r = p.add_run(text)
        set_font(r, font, size, bold, italic, color)
    return p


def add_title(doc, text, subtitle):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    set_font(r, HEAD_FONT, 24, True, False, INK)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_after = Pt(18)
    r2 = p2.add_run(subtitle)
    set_font(r2, BODY_FONT, 10.5, False, False, INK_DIM)
    # rule
    p3 = doc.add_paragraph()
    p3.paragraph_format.space_after = Pt(14)
    pPr = p3._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '10')
    bottom.set(qn('w:color'), HEADER_GRAY)
    pbdr.append(bottom)
    pPr.append(pbdr)


def add_h1(doc, num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"{num}  {text}")
    set_font(r, HEAD_FONT, 15.5, True, False, ACCENT)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:color'), 'CCD5CF')
    pbdr.append(bottom)
    pPr.append(pbdr)
    p.paragraph_format.space_after = Pt(10)


def add_h2(doc, text):
    add_para(doc, text, size=12.5, bold=True, color=INK, space_before=10, space_after=4)


def add_formula_box(doc, lines):
    """lines: list of (text, note_or_None) tuples. Rendered in a shaded 1-col table."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(16)
    cell = table.rows[0].cells[0]
    cell.width = Cm(16)
    set_cell_shading(cell, LIGHT_GRAY)
    set_cell_border(cell, "AACBCE", 4)
    cell.text = ""
    first = True
    for item in lines:
        text, note = item if isinstance(item, tuple) else (item, None)
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.space_before = Pt(2)
        r = p.add_run(text)
        set_font(r, MONO_FONT, 11, False, False, INK)
        if note:
            r2 = p.add_run("   " + note)
            set_font(r2, BODY_FONT, 9.5, False, True, INK_DIM)
    # spacer paragraph after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(2)


def add_logic_note(doc, text):
    """왜 이렇게 계산하는가 -- 수식 아래 붙는 평이한 논리 설명 (호박색 좌측 강조)."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Cm(16)
    cell = table.rows[0].cells[0]
    cell.width = Cm(16)
    set_cell_shading(cell, "FBF3EA")
    # thick left border only, thin others -- visually reads as a callout
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '18'); left.set(qn('w:color'), 'B5651D')
    borders.append(left)
    for edge in ('top', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single'); el.set(qn('w:sz'), '2'); el.set(qn('w:color'), 'EEDFC8')
        borders.append(el)
    tcPr.append(borders)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r0 = p.add_run("왜 이렇게 계산하는가  ")
    set_font(r0, BODY_FONT, 9.5, True, False, AMBER)
    r1 = p.add_run(text)
    set_font(r1, BODY_FONT, 10, False, False, INK)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


def add_glossary_table(doc, rows):
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [Cm(3.6), Cm(12.4)]
    table.columns[0].width, table.columns[1].width = widths

    hdr = table.rows[0].cells
    for i, htext in enumerate(["약어", "설명"]):
        hdr[i].width = widths[i]
        set_cell_shading(hdr[i], HEADER_GRAY)
        set_cell_border(hdr[i], "1F4F55", 4)
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(htext)
        set_font(r, BODY_FONT, 10.5, True, False, WHITE)

    for term, desc in rows:
        row = table.add_row().cells
        row[0].width, row[1].width = widths
        set_cell_shading(row[0], "FFFFFF")
        set_cell_shading(row[1], "FFFFFF")
        set_cell_border(row[0], "DDE3DF", 4)
        set_cell_border(row[1], "DDE3DF", 4)
        row[0].text = ""
        p0 = row[0].paragraphs[0]
        r0 = p0.add_run(term)
        set_font(r0, MONO_FONT, 10, True, False, ACCENT)
        row[1].text = ""
        p1 = row[1].paragraphs[0]
        r1 = p1.add_run(desc)
        set_font(r1, BODY_FONT, 10, False, False, INK)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(2)


# ===========================================================================
doc = Document()
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.left_margin = Cm(2.2)
section.right_margin = Cm(2.2)
section.top_margin = Cm(1.8)
section.bottom_margin = Cm(1.8)

# default style
normal = doc.styles['Normal']
normal.font.name = BODY_FONT
normal.font.size = Pt(11)
rpr = normal.element.get_or_add_rPr()
rfonts = rpr.find(qn('w:rFonts'))
if rfonts is None:
    rfonts = OxmlElement('w:rFonts')
    rpr.append(rfonts)
rfonts.set(qn('w:eastAsia'), BODY_FONT)

add_title(doc, "FMECA–IPS 산출 공식 정리",
          "SCANIA Component X 실측 데이터 기준  ·  원본: scripts/01_pipeline.py · scripts/02_lifecycle.py · app/index.html §09")

add_para(doc, "이 문서는 앞서 전달한 플로우차트·코드 캡쳐에 사용된 모든 계산식을 표기법으로 정리한 것이다. "
              "각 공식은 실제 코드에서 그대로 가져왔으며, 코드 변수명을 수식 표기로 옮길 때 의미가 바뀌지 않도록 원문 표현을 최대한 보존했다. "
              "각 공식 아래에는 호박색 박스로 \"왜 이렇게 계산하는가\"를 수식 없이 평이한 말로 설명해 두었다.",
         size=10.5, color=INK_DIM, space_after=14)

# ---------------------------------------------------------------------------
add_h1(doc, "1.", "원시데이터 → 열화추세 → 이상지수")
add_para(doc, "8개 누적카운터 각각에 대해, 판독 간 증가 \"속도\"를 계산하고 차량 자기 자신의 과거 이력으로 정규화한다.", size=10.5)
add_formula_box(doc, [
    ("rate(t) = [ value(t) − value(t−1) ] / [ t − (t−1) ]", "— 8개 채널 각각"),
    ("z(t) = [ rate(t) − μ ] / σ", "— μ,σ = 그 차량 과거 이력(마지막 판독 제외)의 평균·표준편차"),
    ("anomaly(t) = mean( |z₁(t)|, |z₂(t)|, …, |z₈(t)| )", "— 8채널 종합 이상지수"),
    ("t* = min{ t : anomaly(t) > 2.5 }", "— 최초 경보시점(임계값 2.5σ)"),
    ("lead_time = 수리시점 − t*", "— 0 ≤ lead_time ≤ 60 이면 \"탐지됨\""),
])
add_logic_note(doc,
    "누적 카운터는 시간이 지날수록 계속 커지기만 해서, 절대값만 봐서는 \"지금 상태가 이상한지\" 알 수 없다. "
    "그래서 판독 사이의 증가폭(rate)을 보고, 그 증가폭이 그 차량 평소 패턴(μ, σ)에서 얼마나 벗어났는지(z)를 표준화해서 비교한다. "
    "8개 채널의 |z|를 평균 내면 \"지금 이 순간이 평소와 얼마나 다른가\"를 숫자 하나(anomaly_score)로 압축할 수 있다. "
    "이 값이 2.5σ를 처음 넘는 시점(t*)이 \"경고가 울린 시점\"이고, 실제 수리까지 남은 시간이 lead_time — 즉 \"몇 시간 전에 미리 알 수 있었는가\"다.")

# ---------------------------------------------------------------------------
add_h1(doc, "2.", "FMECA 입력값 — O · S · D")

add_h2(doc, "2.1  O (발생도, Occurrence)")
add_formula_box(doc, [
    ("λ = k / Σt", "— k = 수리건수, Σt = 노출시간(Σ time-step)"),
    ("rate = λ × 1000", "— 1000 time-step당 발생건수"),
    ("O등급 = bin( log₁₀(rate) )", "— 관측범위를 log 축 10구간 균등분할해 1~10 배정"),
    ("CI_lo = χ²(0.025, 2k) / 2 / Σt × 1000", "— Poisson exact 95% 신뢰구간 하한"),
    ("CI_hi = χ²(0.975, 2(k+1)) / 2 / Σt × 1000", "— Poisson exact 95% 신뢰구간 상한"),
])
add_logic_note(doc,
    "단순히 \"고장이 몇 번 났는가\"만 보면 오래 운행한 차량이 불리해 보인다. 공정하게 비교하려면 \"단위 운행시간당 고장 빈도(λ)\"를 봐야 한다. "
    "이 값을 log 스케일로 등급화하는 이유는, 고장률이 10배 차이 나는 경우와 1.1배 차이 나는 경우를 같은 눈금 위에서 비교하기 위해서다 "
    "(선형 눈금이면 극단값 하나에 등급이 쏠려버린다). 신뢰구간(CI)은 표본이 적은 사양군의 등급을 과신하지 않기 위한 안전장치다.")

add_h2(doc, "2.2  S (심각도, Severity) — 근사 대리지표임을 먼저 밝힘")
add_logic_note(doc,
    "⚠ 정직성 고지: 전통적 FMECA의 S는 \"이 고장이 실제로 발생했을 때 안전·임무·비용에 미치는 결과\"를 뜻한다. "
    "그러나 SCANIA Component X 데이터셋에는 부상·정지시간·수리비용 같은 \"결과\" 기록이 전혀 없다 — 있는 것은 수리 시점뿐이다. "
    "그래서 진짜 결과심각도는 산출 불가이며, 아래 S는 \"고장 직전 신호가 얼마나 비정상적이었는가\"를 재는 대리지표(proxy)다. "
    "이 간극을 숨기지 않고 HAZOP guide word(이탈 방향)와 오차율(이탈 크기)로 \"무엇을 측정한 대리값인지\"를 명시한다.")
add_formula_box(doc, [
    ("guide word = MORE  if mean(z_signed) > 0  else LESS", "— 그룹 평균 부호부 z, 이탈 방향(HAZOP)"),
    ("오차율(%) = mean( |rate − 기준선평균| / 기준선평균 × 100 )", "— 채널별 이탈 크기, 8채널 평균"),
    ("S_raw = mean( anomaly_score )", "— 수리 직전 마지막 3개 판독 평균 |이상지수|"),
    ("S_norm = (S_raw − min) / (max − min)", "— 사양군(형상) 간 min–max 정규화"),
    ("S등급 = round( 1 + 9 × S_norm )", "— 1~10"),
])
add_logic_note(doc,
    "HAZOP은 원래 공정 변수(유량·온도·압력 등)에 No/More/Less/Reverse 같은 guide word를 붙여 이탈을 식별하고, "
    "그 이탈이 실제로 어떤 결과를 낳는지 전문가가 판단해 심각도를 매기는 기법이다. 이 데이터는 변수의 물리적 의미가 익명화돼 있고 "
    "결과 기록도 없어 guide word를 결과심각도에 그대로 연결할 수는 없지만, \"이탈의 방향(MORE/LESS)\"과 \"이탈의 크기(오차율 %)\"만은 "
    "데이터에서 직접, 조작 없이 계산할 수 있다. 카운터가 누적값이라 구조적으로 REVERSE·NO 같은 다른 guide word는 이 데이터에서 성립하지 않는다 — "
    "그래서 MORE/LESS 두 가지만 쓴다. S등급 자체는 기존과 같이 \"고장 직전 이상 정도\"의 그룹 간 상대적 위치(min–max)로 계산하며, "
    "마지막 3개 판독만 쓰는 이유·min–max 정규화 이유는 기존과 동일하다: 고장 훨씬 전의 평온한 데이터가 아니라 고장 직전 상태를 봐야 하고, "
    "사양군마다 이상지수의 절대 크기가 달라 그룹 안에서의 상대적 위치로 비교해야 공정하기 때문이다.")

add_h2(doc, "2.3  D (검출도, Detection)")
add_formula_box(doc, [
    ("탐지율 = n_detected / n_repairs", "— 0~60 time-step 이내 탐지된 비율"),
    ("탐지력 = 0.6 × 탐지율 + 0.4 × min( mean_lead_time / 60, 1 )", ""),
    ("D등급 = clip( round( 10 − 9 × 탐지력 ), 1, 10 )", "— 탐지력이 높을수록 등급이 낮아짐(=좋아짐)"),
    ("p_null = 1 − exp( −λ_warn × 168 )", "— 무고장 차량의 우연 경보 확률(귀무가설)"),
    ("p = P( X ≥ n_detected )  where X ~ Binomial(n_repairs, p_null)", "— 단측 이항검정, p<0.05면 유의"),
])
add_logic_note(doc,
    "탐지율이 90%라고 해도, 애초에 경고가 자주 울리는 차량이라면 우연히 맞았을 수도 있다. 그래서 \"고장 없는 차량도 같은 기간에 "
    "우연히 경고가 뜰 확률(p_null)\"을 계산해, 실제 탐지율이 그보다 통계적으로 유의하게 높은지(이항검정)를 확인한다. "
    "이 검증이 없으면 \"탐지율이 높다\"는 결과가 착시일 수 있다.")

# ---------------------------------------------------------------------------
add_h1(doc, "3.", "위험지수")
add_formula_box(doc, [
    ("RPN = O × S × D", "— 전통적 곱셈식 위험 우선순위 지수"),
    ("RI = 0.4·O + 0.4·S + 0.2·D", "— 가중합산 대안 지수 (곱셈식의 극단값 민감성을 완충)"),
])
add_logic_note(doc,
    "RPN(곱셈)은 한 지표가 10점이면 나머지가 아무리 낮아도 전체 값을 확 끌어올린다 — 극단값에 민감하다. "
    "RI(가중합산)는 그 영향을 완만하게 반영한다. 두 지표의 순위가 서로 갈리는지 비교해보면, "
    "\"한 지표의 극단값 때문에 우선순위가 왜곡되지는 않았는가\"를 점검할 수 있다.")

# ---------------------------------------------------------------------------
add_h1(doc, "4.", "IPS 연계 결정식")

add_h2(doc, "4.1  RCM (정비전략)")
add_formula_box(doc, [
    ("IF  significant  AND  탐지율 ≥ 50%", ""),
    ("    →  상태기반정비 (CBM)", ""),
    ("ELIF  S ≥ 5", ""),
    ("    →  시간기준 예방정비 (Hard-Time)", ""),
    ("ELSE", ""),
    ("    →  사후정비 (Run-to-Failure)", ""),
])
add_logic_note(doc,
    "정비 전략을 고를 때 가장 먼저 물어야 할 질문은 \"고장 전에 미리 알 수 있는가\"다. 알 수 있다면(유의한 조기신호 + 충분한 탐지율) "
    "평소엔 지켜보다가 필요할 때만 정비하는 게 가장 효율적이다(CBM). 미리 알 수 없다면 \"고장났을 때 피해가 큰가(S≥5)\"를 본다 — "
    "피해가 크면 정해진 주기로 강제 교체(Hard-Time)하고, 피해가 작으면 고장날 때까지 쓰다가 고치는 편(RTF)이 총비용이 가장 싸다.")

add_h2(doc, "4.2  LORA (수리수준분석)")
add_formula_box(doc, [
    ("IF  O ≥ 8   →  창정비 우선순위 상향 + 예비품 전진배치", ""),
    ("ELSE        →  표준 2-Level (야전 LRU교환 + 창정비 모듈수리)", ""),
])
add_logic_note(doc,
    "자주 고장 나는 부품(O 높음)을 매번 후방 창정비까지 보내면 병목이 생긴다. 그래서 발생빈도가 높은 부품은 정비 대응력을 "
    "앞단(창정비 대기열 우선순위, 예비품 전진배치)에 두고, 드물게 고장 나는 부품은 표준 절차로도 충분하다고 본다.")

add_h2(doc, "4.3  보급소요 산정")
add_formula_box(doc, [
    ("annual_demand = (rate/1000) × fleet_size × (daily_op × 365)", "— 가정 함대 규모·가동일에 실측 rate 적용"),
    ("lead_time_demand = annual_demand × (lead_days / 365)", ""),
    ("safety_stock = z₀.₉₅ × √(lead_time_demand)", "— z₀.₉₅ = 1.645 (서비스수준 95%, Poisson 근사)"),
    ("reorder_point = lead_time_demand + safety_stock", ""),
])
add_logic_note(doc,
    "재주문점은 \"리드타임 동안 소비될 양(리드타임수요)\"에 \"수요가 예상보다 튈 때를 대비한 여유분(안전재고)\"을 더한 것이다. "
    "안전재고를 리드타임수요의 제곱근에 비례하게 잡는 것(Poisson 근사)은, 수요의 변동폭이 평균 수요량 자체에 비례해서 커지는 "
    "통계적 성질을 반영한 것이다 — 소요량이 클수록 안전재고도 커지되, 비례가 아니라 제곱근으로 완만하게 커진다.")

add_h2(doc, "4.4  IETM 연계")
add_formula_box(doc, [
    ("IF  significant  AND  mean_lead_time 존재", ""),
    ("    →  SLA = mean_lead_time × 0.5   (사전점검 절차)", ""),
    ("ELSE", ""),
    ("    →  정기점검 강화 (사전 SLA 없음)", ""),
])
add_logic_note(doc,
    "\"사전점검하라\"는 절차를 정의하려면 실제로 사전에 알 수 있어야 의미가 있다. 조기신호가 통계적으로 유의하지 않다면 "
    "사전점검 절차를 만들어봤자 근거 없는 지시가 된다 — 그런 경우는 대신 정기점검을 강화하는 쪽으로 대체한다.")

add_h2(doc, "4.5  ECP (설계개선) 트리거")
add_formula_box(doc, [
    ("IF  rank(RPN) = 1   OR   O = 10   OR   NOT significant", ""),
    ("    →  ECP 후보(설계개선 필요)", ""),
])
add_logic_note(doc,
    "RPN이 높은 것만 설계개선 후보로 삼으면, \"자주 고장나진 않지만 전혀 예측 불가능한\" 위험한 고장모드를 놓친다. "
    "그래서 발생도가 극단적으로 높거나(O=10), 위험지수 순위가 1위이거나, 조기신호 자체가 통계적으로 없는(비유의) 경우까지 "
    "모두 후보에 포함시켜 \"눈에 잘 안 띄는 위험\"을 놓치지 않게 한다.")

# ---------------------------------------------------------------------------
add_h1(doc, "5.", "피드백 시뮬레이션 (ECP 적용 가정)")
add_para(doc, "설계개선을 적용했다고 가정할 때, 아래 새 등급이 §3·§4의 모든 식에 그대로 재대입되어 RPN′·RI′·RCM′·LORA′·보급소요′·IETM′이 재계산된다.",
         size=10.5, color=INK_DIM)
add_formula_box(doc, [
    ("O′ = max( 1, O − 2 )", "— 근본설계 개선 가정 (발생률 ≈ 40%↓과 짝)"),
    ("rate′ = rate × 0.60", "— 보급소요 재계산에 사용되는 발생률 감소 가정"),
    ("D′ = max( 1, D − 3 )", "— 진단 알고리즘/센서 고도화 가정 (탐지율 60%까지 개선)"),
    ("RPN′ = O′ × S × D′", ""),
    ("RI′ = 0.4·O′ + 0.4·S + 0.2·D′", ""),
])
add_logic_note(doc,
    "설계개선이 실제로 효과가 있다면 그 효과는 \"더 이상 그렇게 자주 고장 나지 않는다(O 개선)\" 또는 \"더 일찍 알 수 있다(D 개선)\" "
    "둘 중 하나로 나타나야 한다. 이 가정을 실제 등급에 대입해보면, 그 개선이 정비전략·보급소요까지 구체적으로 어떻게 파급되는지 "
    "확인할 수 있다 — 이것이 \"피드백 루프\"가 실제로 뜻하는 것이다.")
add_para(doc, "등급 변화폭(−2, −3, ×0.60) 자체는 이 시뮬레이션을 위한 가정치이며, 재계산 산식 자체는 §3·§4와 동일한 실제 코드(computeIntervention)다.",
         size=9.5, italic=True, color=AMBER, space_after=14)

# ---------------------------------------------------------------------------
add_h1(doc, "6.", "약어 설명 (Glossary)")
glossary = [
    ("O", "발생도(Occurrence) — 수리건수 ÷ 노출시간 기반 등급"),
    ("S", "심각도(Severity, 근사) — 결과심각도 기록이 없어 고장직전 이상지수 크기를 대리지표로 등급화"),
    ("Guide word", "HAZOP 용어 — 이탈 방향(MORE=증가/LESS=감소). 이 데이터엔 REVERSE·NO 등은 성립 안 함"),
    ("오차율", "채널별 |증분율−기준선평균|/기준선평균×100의 평균 — S의 이탈 크기(%) 정량치"),
    ("D", "검출도(Detection) — 조기경보 탐지력 기반 등급"),
    ("RPN", "Risk Priority Number — O×S×D 곱셈 위험지수"),
    ("RI", "Risk Index — 0.4O+0.4S+0.2D 가중합산 위험지수"),
    ("RCM", "Reliability Centered Maintenance — 신뢰도중심정비"),
    ("LORA", "Level Of Repair Analysis — 수리수준분석(야전/창정비)"),
    ("IETM", "Interactive Electronic Technical Manual — 전자식 기술교범"),
    ("ECP", "Engineering Change Proposal — 설계변경요청(설계개선)"),
    ("CBM", "Condition Based Maintenance — 상태기반정비"),
    ("RTF", "Run To Failure — 사후정비(고장까지 운용 후 조치)"),
    ("Hard-Time", "시간기준 예방정비 — 정기 강제교체"),
    ("TTE", "Time To Event — 사건(수리)까지 경과시간(train_tte.csv)"),
    ("SLA", "Service Level Agreement — 점검 착수 기한 약속"),
    ("CI", "Confidence Interval — 95% 신뢰구간(Poisson exact)"),
    ("χ²", "카이제곱 분포 — Poisson 정확신뢰구간 계산에 사용"),
    ("z", "Z-score — 자기 이력 평균 대비 표준화 편차"),
    ("Spec_3", "차량 사양 그룹 변수 — SCANIA 데이터셋의 익명화된 범주형 필드"),
]
add_glossary_table(doc, glossary)

# ---------------------------------------------------------------------------
add_h1(doc, "7.", "출처")
add_para(doc, "O·S·D 산출:  scripts/01_pipeline.py", size=10, font=MONO_FONT, color=INK_DIM, space_after=2)
add_para(doc, "IPS 연계(RCM~ECP):  scripts/02_lifecycle.py", size=10, font=MONO_FONT, color=INK_DIM, space_after=2)
add_para(doc, "피드백 시뮬레이터(브라우저):  app/index.html §09 (computeIntervention)", size=10, font=MONO_FONT, color=INK_DIM, space_after=2)
add_para(doc, "데이터: SCANIA Component X dataset, Kharazian et al. 2025, Scientific Data — CC BY 4.0", size=10, font=MONO_FONT, color=INK_DIM, space_after=2)
add_para(doc, "웹 워크벤치: claude.ai/code/artifact/7c5a27c2-d582-48db-a00b-f4c421afe933", size=10, font=MONO_FONT, color=INK_DIM, space_after=2)

doc.save("FMECA_IPS_공식정리.docx")
print("saved")
