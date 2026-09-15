# 데이터셋 형식 (Dataset Contract)

이 저장소의 파이프라인(`scripts/01_pipeline.py` → `02_lifecycle.py` → `03_export_app_data.py`)과
웹앱(`app/index.html`)은 **특정 데이터셋(SCANIA)에 하드코딩되어 있지 않다.** 아래 형식에 맞는
CSV 3개 + `config.yaml` 하나를 `datasets/<이름>/` 폴더에 넣으면 그대로 실행된다.

실제 예시: [`datasets/scania_component_x/config.yaml`](datasets/scania_component_x/config.yaml)

## 1. 필요한 입력 파일 3개

한 자산(장비/차량/구성품 등)을 축으로 아래 세 CSV가 서로 키로 연결되어야 한다.

| 논리적 역할 | 설명 | 최소 컬럼 |
|---|---|---|
| **events** | 자산별 1행 — 관측기간(노출시간)과 고장 라벨 | 자산ID, 노출시간(숫자), 고장라벨(0/1) |
| **readouts** | 자산×시점별 1행 — 시계열 계측값(긴 포맷) | 자산ID, 시점(숫자, 자산별 오름차순), 카운터 컬럼 1개 이상 |
| **groups** | 자산별 1행 — FMECA 행을 나눌 그룹 속성 | 자산ID, 그룹 컬럼 |

- **readouts의 카운터**는 "누적값"이어야 한다(시간이 지날수록 단조증가하는 계측치 — 누적 경고횟수, 누적 가동시간 등). 파이프라인이 내부적으로 증분율(rate)·z-정규화를 계산하기 때문이다. 순간값(온도, 속도 등)을 그대로 쓰려면 `02_drift_removal` 단계를 데이터 성격에 맞게 고쳐야 한다.
- **events의 고장라벨**은 이진(0/1)이어야 한다. 다중 고장모드를 구분하고 싶다면 `groups`의 그룹 컬럼으로 나눠라(= "동일 고장모드가 그룹마다 어떻게 다른가"를 보는 구조).
- 행 수가 많아도 된다 — SCANIA 예시는 readouts 112만 행/23,550대다.

## 2. `config.yaml` 스키마

```yaml
dataset:
  short_id: <폴더명과 동일한 영문 id>
  name: <사람이 읽는 데이터셋 이름>
  component_label: <분석대상 구성품/자산 종류 이름>
  license: <라이선스>
  citation: <출처 논문/기관>
  source_url: <원본 링크>

files:            # 이 config.yaml 파일 기준 상대경로
  events: data_raw/xxx.csv
  readouts: data_raw/yyy.csv
  groups: data_raw/zzz.csv

columns:
  asset_id: <자산ID 컬럼명 — events/groups 공통, readouts는 아래 readout_time과 짝>
  exposure_time: <노출시간 컬럼명, events>
  failure_label: <고장라벨 컬럼명(0/1), events>
  readout_time: <시점 컬럼명, readouts>
  counters: [<카운터 컬럼명 목록>, ...]
  group_col: <FMECA 행을 나눌 주 그룹 컬럼명, groups>
  bonus_group_col: <선택: 보조 드릴다운용 그룹 컬럼명>   # 없으면 생략 가능

groups:            # group_col의 각 값 -> 화면표시 라벨
  <값1>: "<라벨1>"
  <값2>: "<라벨2>"

params:
  lookback_steps: <검출 룩백 윈도, readout_time 단위>
  z_thresh: <이상치 플래그 z 임계값>
  tail_readouts_for_severity: <심각도용 "고장직전" 판독 개수>
  bonus_group_min_size: <bonus_group_col 그룹 최소 표본수>

assumptions:       # 데이터에 없어 IPS 연계에 반드시 필요한 가정치 (전부 웹앱/문서에 "가정"으로 명시됨)
  lead_days: <조달 리드타임(일)>
  unit_cost_krw: <구성품 단가>
  repair_complexity: <수리복잡도 등급>
  fleet_size: <가상 함대 규모>
  daily_op_timesteps: <일일 가동 time_step 환산>
  note: <가정치임을 설명하는 문장>

content:           # 웹앱에 노출되는 서술형 텍스트 (사람이 직접 채워야 하는 부분)
  banner: "..."          # {name} {license} 등 플레이스홀더 치환 가능
  overview_lede: "..."   # {name} {n_vehicles} {component_label} {group_col} {n_groups} 치환 가능
  mapping_rows: [[필드, 원본파일, 의미, FMECA대응, 비고], ...]
  gap_rows: [[공백항목, 이유, 영향], ...]
```

## 3. 실행

```bash
python scripts/run_pipeline.py --dataset datasets/scania_component_x
```

내부적으로 `01_pipeline.py` → `02_lifecycle.py` → `03_export_app_data.py` 를 순서대로 실행하고,
`datasets/<이름>/outputs/` (CSV/JSON 계산 결과)와 `datasets/<이름>/app_data/` (웹앱용 JSON)를 만든 뒤,
`app_data/`를 `app/data/`로 복사해 웹앱이 그 데이터셋을 바로 읽도록 만든다.

## 4. 왜 이런 구조인가

- **O/S/D 계산 로직 자체는 데이터셋과 무관하다** — "그룹별 발생률 → log 등급화", "고장직전 이상지수 → min-max 등급화", "리드타임+통계검정 → 검출력 등급화"라는 방법론은 counters/exposure/failure_label만 있으면 어떤 자산 데이터에도 적용된다.
- **가정치(assumptions)는 데이터가 채울 수 없는 부분**이라 분리했다 — 조달 리드타임 같은 값은 어떤 데이터셋을 넣어도 저절로 나오지 않는다. 이 값을 코드에 박아두지 않고 config로 뽑아, "이건 실측이고 이건 가정"이라는 구분이 데이터셋을 바꿔도 항상 명확하게 유지되도록 했다.
- **content(서술형 텍스트)는 자동화하지 않았다** — "이 데이터에 무슨 공백이 있는지"는 통계로 뽑을 수 없고 사람이 도메인 판단으로 써야 하는 부분이라, 일부러 config에 사람이 채우는 자리로 남겨뒀다.
