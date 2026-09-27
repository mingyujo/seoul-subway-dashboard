# 서울 지하철 대시보드 구현 계획 (v2.0)

- **계획 버전**: v2.0
- **변경 사유**: 브라우저 직접 CSV 파싱(PapaParse) 방식에서 Python 분석 결과(JSON)를 정적 웹에 전달하는 방식으로 전환
- **이전 계획**: 이 문서가 이전 v1 계획(브라우저 PapaParse 직접 파싱 방식)을 대체함

## Context
v1 구현(HTML+PapaParse 브라우저 직접 파싱) 운영 중 실제 CSV의 혼합 줄바꿈(헤더만 CRLF, 데이터 행은 LF)으로 인해 PapaParse의 줄바꿈 자동 감지가 실패해 "CSV 파일 형식을 해석할 수 없습니다" 오류가 발생함을 진단·재현으로 확인했다. 이를 근본적으로 해결하기 위해 CSV 파싱·정제·집계를 Python(pandas)으로 옮기고, 웹은 그 결과물(JSON)만 fetch해 시각화하는 구조로 전환한다.

## 1. 최종 프로젝트 구조
```
vibecoding/
├── CLAUDE.md
├── README.md
├── requirements.txt              # Python 의존성
├── package.json                  # Node 테스트(analysis.js 검증)용, 유지
├── .gitignore
├── docs/
│   ├── REQUIREMENTS.md
│   ├── PLAN.md                   # 이 문서
│   └── ANALYSIS_BASELINE.md      # Python 분석 결과의 기준값
├── data/
│   ├── raw/
│   │   └── CARD_SUBWAY_MONTH_202608.csv   # 원본, 수정하지 않음
│   └── processed/
│       └── dashboard_data.json   # Python 분석 결과, 웹이 fetch하는 대상
├── scripts/
│   └── analyze.py                # pandas 기반 정제·분석·JSON 생성
├── index.html                    # PapaParse <script> 제거, Chart.js CDN만 유지
├── css/
│   └── style.css                 # 무변경
├── js/
│   ├── data.js                   # JSON fetch + 데이터 계약 검증 + Date 변환 (재작성)
│   ├── analysis.js               # 순수 집계 함수, 무변경(그대로 재사용)
│   └── app.js                    # JSON 로딩 호출로 변경, 초기 KPI는 summary로 표시
└── tests/
    ├── analysis.test.js          # 기존 JS 단위 테스트, CSV 경로만 data/raw로 갱신
    └── test_analysis.py          # Python unittest 회귀 테스트 (신규)
```

## 2. Python 분석 파이프라인 (`scripts/analyze.py`)
1. **안전한 CSV 읽기**: `pd.read_csv(path, encoding="utf-8-sig", dtype=str, header=None, names=[...6개 열+트레일링 필드], skiprows=1)`로 UTF-8 BOM과 혼합 줄바꿈(헤더만 CRLF, 데이터는 LF)을 안전하게 처리한다(pandas C 엔진은 두 줄바꿈을 모두 정상 인식함을 이미 확인함). 트레일링 빈 7번째 필드는 로드 후 제거한다.
2. **실제 열 이름 검증**: 원본 첫 줄을 별도로 읽어 `["사용일자","노선명","역명","승차총승객수","하차총승객수","등록일자"]`와 정확히 일치하는지 확인하고, 다르면 즉시 오류를 발생시켜 중단한다.
3. **명시적 타입 변환**: `사용일자`는 `pd.to_datetime(..., format="%Y%m%d")`, `승차총승객수`/`하차총승객수`는 `pd.to_numeric(..., errors="coerce")`로 변환한다.
4. **결측치·변환 실패 검증**: 날짜 변환 실패(NaT), 노선명/역명 공백, 승차·하차 숫자 변환 실패(NaN)가 하나라도 있는 행은 집계 대상에서 제외하고 개수를 기록한다.
5. **집계 계산**:
   - 유효 행 수, 날짜 범위(최소/최대)
   - 전체 승차·하차·승하차 합계
   - 역명 기준 상위 10개 역(승차+하차 합계 내림차순, 노선 통합)
   - 노선별 승차·하차·합계
   - 날짜별 승차·하차·합계
   - 평일·주말 날짜 수와 일평균(합계 ÷ 날짜 수)
6. **기준값 대조**: 계산 결과가 `docs/ANALYSIS_BASELINE.md`에 기록된 값(유효 행 19,133 / 총 승차 208,329,561 / 총 하차 207,340,153 / 노선 27개 / 역 531개 등)과 일치하는지 스크립트 실행 중 자체 검증(assert)한다.
7. **JSON 저장**: `json.dump(..., ensure_ascii=False, allow_nan=False)`로 한글이 깨지지 않고 NaN/Infinity가 포함되지 않는 유효한 JSON을 `data/processed/dashboard_data.json`에 기록한다.

## 3. `dashboard_data.json` 데이터 계약
```json
{
  "metadata": {
    "source_file": "data/raw/CARD_SUBWAY_MONTH_202608.csv",
    "generated_at": "2026-09-28T00:00:00+09:00",
    "row_count": 19133,
    "date_range": { "start": "2026-08-01", "end": "2026-08-31" }
  },
  "summary": {
    "total_boarding": 208329561,
    "total_alighting": 207340153,
    "total": 415669714,
    "line_count": 27,
    "station_count": 531,
    "top_stations": [
      { "station": "서울역", "boarding": 3681205, "alighting": 3638971, "total": 7320176 }
    ],
    "line_totals": [
      { "line": "2호선", "boarding": 41437542, "alighting": 41824025, "total": 83261567 }
    ],
    "daily_totals": [
      { "date": "2026-08-01", "boarding": 5479960, "alighting": 5446554, "total": 10926514 }
    ],
    "weekday_weekend": {
      "weekday": { "day_count": 21, "total": 315641643, "daily_average": 15030554.43 },
      "weekend": { "day_count": 10, "total": 100028071, "daily_average": 10002807.1 }
    }
  },
  "records": [
    { "date": "2026-08-01", "line": "중앙선", "station": "양원", "boardings": 1912, "alightings": 1927, "total": 3839 }
  ]
}
```
`summary`의 모든 수치는 `docs/ANALYSIS_BASELINE.md` 기준값과 정확히 일치해야 한다. `records`는 필터 UI가 사용할 원자료이며, `js/data.js`에서 `boardings/alightings` → `analysis.js`가 기대하는 `boarding/alighting` 필드명으로 매핑한다(매핑은 `js/data.js` 한 곳에서만 처리).

## 4. 웹의 JSON 로딩과 필터 흐름
- `js/data.js`: `fetch('data/processed/dashboard_data.json')` → JSON 파싱 → 필수 키(`metadata`, `summary`, `records`) 존재 검증 → 각 `records` 원소의 `date` 문자열("YYYY-MM-DD")을 `Date` 객체로, `boardings/alightings`를 `boarding/alighting`으로 매핑 → `{ summary, records }` 형태로 반환. PapaParse·fetch+ArrayBuffer+TextDecoder+CSV 파싱 로직은 전부 제거한다.
- `js/app.js`: `init()`에서 `loadData()`로 `{ summary, records }`를 받아 `allRecords = records`로 저장. **초기 KPI 카드는 `summary` 값으로 직접 표시**(분석 함수 재계산 없이)해 Python 집계 결과와 정확히 일치시킨다. 이후 날짜·노선 필터가 바뀔 때만 기존과 동일하게 `js/analysis.js`(`filterByDateRange` → `filterByLine` → `getTotals`/`getTopStations`/`getLineTotals`/`getDailyTrend`/`getWeekdayWeekendAverage`)로 재계산해 KPI·차트·표를 갱신한다. 이 파이프라인 자체(필터 → 동일 함수들 → 화면 갱신)는 v1과 동일하게 유지된다.

## 5. 생성·수정·이동할 파일
| 구분 | 경로 | 내용 |
|---|---|---|
| 이동 | `data/CARD_SUBWAY_MONTH_202608.csv` → `data/raw/CARD_SUBWAY_MONTH_202608.csv` | 원본 보존 위치 변경(체크섬 확인 후 이동) |
| 신규 | `scripts/analyze.py` | Python 분석 파이프라인 |
| 신규 | `data/processed/dashboard_data.json` | 웹이 fetch할 결과물 |
| 신규 | `requirements.txt` | Python 의존성(pandas) |
| 신규 | `tests/test_analysis.py` | Python unittest 회귀 테스트 |
| 수정 | `js/data.js` | CSV/PapaParse 로직 제거 → JSON 로딩 + 계약 검증 |
| 수정 | `js/app.js` | 데이터 로딩 호출부 및 초기 KPI 표시 방식만 수정 |
| 수정 | `index.html` | PapaParse CDN `<script>` 태그 제거 |
| 수정 | `README.md` | 실행 방법을 Python 분석 실행 → 정적 서버 순서로 갱신 |
| 수정(경로만) | `tests/analysis.test.js` | 실제 CSV 대조 테스트의 경로를 `data/raw/...`로 갱신 |
| 무변경 | `js/analysis.js`, `css/style.css`, `docs/ANALYSIS_BASELINE.md`, `docs/REQUIREMENTS.md`, `CLAUDE.md`, `.mcp.json` | 그대로 유지 |

## 6. 제거 후보 파일과 제거 이유
- **완전히 삭제할 파일 없음.**
- `js/data.js` 내부의 `stripBom`, `parseCsvText`, `Papa.parse` 호출, CSV `fetch+ArrayBuffer+TextDecoder` 로직: JSON 로딩 방식으로 대체되므로 코드에서 제거(파일 자체는 유지).
- `index.html`의 PapaParse CDN `<script>` 태그: 더 이상 브라우저에서 CSV를 파싱하지 않으므로 제거.
- 이전에 검토만 하고 보류했던 "Node 테스트용 papaparse devDependency 설치" 방안: CSV 파싱이 전부 Python으로 이동하므로 완전히 폐기(적용하지 않음).
- (전환 검증 완료 후, 구 경로 `data/CARD_SUBWAY_MONTH_202608.csv`는 `data/raw/`로 옮긴 뒤 구 경로 파일 제거 — 8번 단계별 순서 참고)

## 7. Python 분석 및 테스트 명령
```bash
pip install -r requirements.txt
python scripts/analyze.py
python -m unittest discover -s tests -p "test_analysis.py"
```

## 8. 로컬 웹 실행 명령
```bash
npx serve .
# 또는
python -m http.server 8000
```
(기존과 동일하게, 로컬 `fetch`의 `file://` 제한 때문에 정적 서버 사용 권장. `npm test`로 기존 JS 단위 테스트도 계속 실행 가능)

## 9. 기준값 대조 방법
- `tests/test_analysis.py`에 `docs/ANALYSIS_BASELINE.md`에 기록된 숫자(유효 행 19,133 / 날짜 범위 2026-08-01~08-31 / 노선 27개 / 역 531개 / 총 승차 208,329,561 / 총 하차 207,340,153 / 총 합계 415,669,714 / 평일 21일·일평균 15,030,554.43 / 주말 10일·일평균 10,002,807.10 / 결측치 0 / 숫자 변환 실패 0 / 중복 의심 0)를 상수로 하드코딩해 `scripts/analyze.py`의 계산 결과와 정확히 일치하는지 assert한다.
- `scripts/analyze.py` 실행 시에도 동일한 기준값과 자체 대조(assert)해, JSON 생성 시점에 기준값과 다르면 즉시 실패하도록 한다.

## 10. 단계별 구현 순서
1. `data/raw/` 생성 후 원본 CSV를 **복사**하고 md5 체크섬으로 원본과 동일한지 확인(아직 구 경로 파일 삭제 안 함).
2. `requirements.txt`, `scripts/analyze.py`, `tests/test_analysis.py` 작성 후 `python -m unittest`로 기준값 대조 통과 확인.
3. `python scripts/analyze.py` 실행해 `data/processed/dashboard_data.json` 생성.
4. 교체 전 `js/data.js`를 임시 백업(`js/data.js.bak`)한 뒤, JSON 로딩 버전으로 재작성.
5. `js/app.js`의 데이터 로딩 호출부와 초기 KPI 표시 로직만 최소 수정, `index.html`에서 PapaParse `<script>` 제거.
6. `tests/analysis.test.js`의 CSV 경로를 `data/raw/...`로 갱신 후 `npm test` 재실행해 기존 테스트 유지 확인.
7. 정적 서버로 브라우저에서 필터·KPI·차트·표가 v1과 동일하게 동작하는지 수동 확인.
8. 문제없으면 구 경로 `data/CARD_SUBWAY_MONTH_202608.csv`와 임시 백업(`js/data.js.bak`) 정리.

## 11. 실패 시 롤백 방법
- 프로젝트가 아직 git 저장소가 아니므로, 4~7단계 중 문제가 발생하면 백업해 둔 `js/data.js.bak`으로 되돌리고 `index.html`의 PapaParse `<script>` 태그를 복원한다.
- `data/raw/`로 이동 작업은 8단계(최종 정리)까지 구 경로 파일을 지우지 않으므로, 문제가 있으면 구 경로 CSV와 v1 코드 조합으로 즉시 되돌릴 수 있다.
