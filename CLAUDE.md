# CLAUDE.md

이 파일은 이 프로젝트에서 작업할 때 지켜야 할 기준을 정리한 문서입니다. 상세 요구사항 원문은 [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)를 참고하세요 (원본: Notion, 확인일 2026-09-27). 구현 계획 이력은 [docs/PLAN.md](docs/PLAN.md)(v2.0, Python → JSON 전환)를 참고하세요.

## 프로젝트 목적
서울시 실제 지하철 승하차 데이터를 사용해 이용 패턴을 브라우저에서 확인하는 정적 웹 대시보드를 만든다.

## 데이터 흐름
```
원본 CSV (data/raw/CARD_SUBWAY_MONTH_202608.csv)
    ↓ python scripts/analyze.py
data/processed/dashboard_data.json
    ↓ fetch (js/data.js)
웹 시각화 (index.html + js/app.js + js/analysis.js + Chart.js)
```
- **원본 CSV는 Python만 읽는다.** 브라우저는 원본 CSV를 절대 직접 파싱하지 않는다.
- **Python(`scripts/analyze.py`)이 `data/processed/dashboard_data.json`을 생성한다.** CSV 정제, BOM/혼합 줄바꿈 처리, 날짜·숫자 변환, 집계는 전부 여기서 수행한다.
- **웹은 처리된 JSON만 읽는다.** `js/data.js`는 `dashboard_data.json`을 fetch하고 데이터 계약(필수 키/필드)만 검증하며, CSV 파싱이나 PapaParse를 사용하지 않는다.

## 최종 파일 구조와 역할
```
vibecoding/
├── CLAUDE.md
├── README.md
├── requirements.txt           # Python 의존성(pandas)
├── package.json                # js/analysis.js 단위 테스트 실행용(node --test)
├── docs/
│   ├── REQUIREMENTS.md         # 원본 요구사항 (Notion에서 확인한 내용만)
│   ├── PLAN.md                  # 구현 계획 (v2.0: Python → JSON 전환)
│   └── ANALYSIS_BASELINE.md     # 원본 CSV 독립 분석 기준값
├── data/
│   ├── raw/CARD_SUBWAY_MONTH_202608.csv     # 원본 데이터, 값 임의 수정 금지
│   └── processed/dashboard_data.json         # analyze.py가 생성하는 결과물
├── scripts/analyze.py           # CSV 정제·집계·JSON 생성 (Python/pandas)
├── index.html                    # 화면 뼈대, 필터 UI, 차트/표 컨테이너
├── js/
│   ├── data.js                    # JSON fetch + 데이터 계약 검증 (CSV/PapaParse 사용 안 함)
│   ├── analysis.js                # 순수 함수: 화면 표시용 필터·집계 계산 (DOM 비의존)
│   └── app.js                      # data.js/analysis.js 결과를 받아 화면(DOM, Chart.js)에 반영
└── tests/
    ├── test_analysis.py            # Python 분석 파이프라인 테스트 (unittest)
    └── analysis.test.js             # js/analysis.js 단위 테스트 (node:test)
```

- **scripts/analyze.py**: 원본 CSV 로딩, BOM/혼합 줄바꿈 처리, 필수 열 검증, 날짜·숫자 타입 변환, 결측치 검증, 집계, `docs/ANALYSIS_BASELINE.md` 기준값 대조, JSON 생성까지 전부 담당. 기준값과 다르면 JSON을 생성하지 않고 실패한다.
- **js/data.js**: `data/processed/dashboard_data.json`을 fetch하고 HTTP 상태·최상위 키(`metadata/summary/records`)·record 필수 필드를 검증한 뒤, `date` 문자열을 `Date`로 변환해 반환한다. CSV 디코딩·BOM 처리·PapaParse는 사용하지 않는다(Python이 이미 처리함).
- **js/analysis.js**: JSON에서 로드한 레코드를 입력받아 **화면 표시용** 필터·집계 결과를 반환하는 순수 함수 모음(날짜/노선 필터, KPI, 상위 역, 노선별·날짜별 합계, 평일·주말 일평균). DOM, Chart.js 등 화면 요소에 의존하지 않는다. CSV 정제나 원본 데이터 검증 역할은 하지 않는다(Python의 역할과 중복시키지 않는다).
- **js/app.js**: data.js와 analysis.js를 호출해 필터 상태를 관리하고, 결과를 DOM/Chart.js로 렌더링한다. 초기 KPI/차트/표는 JSON의 `summary`를 그대로 사용하고, 필터가 적용된 이후에만 `analysis.js`로 재계산한다.

## 실제 확인된 CSV 데이터
- 파일: `data/raw/CARD_SUBWAY_MONTH_202608.csv`
- 인코딩: UTF-8 with BOM (`utf-8-sig`), 혼합 줄바꿈(헤더 CRLF, 데이터 행 LF)
- 헤더 열 이름(6개): `사용일자`, `노선명`, `역명`, `승차총승객수`, `하차총승객수`, `등록일자`
- 데이터 행마다 헤더에 없는 빈 7번째 필드가 한 개 더 붙어 있음(트레일링 콤마) — `scripts/analyze.py`가 모두 빈 값인지 확인한 뒤에만 제거한다
- 사용일자 범위: 20260801~20260831 (`YYYYMMDD` 문자열, Python에서 날짜로 변환)
- 승차·하차총승객수: 숫자 문자열, 이 파일 기준 결측치 없음 (유효 행 19,133건, `docs/ANALYSIS_BASELINE.md` 참고)

## 기본 명령
- 분석 실행: `python scripts/analyze.py`
- Python 테스트: `python -m unittest discover -s tests -p "test_*.py"`
- 로컬 웹 실행: `py -m http.server 8000` (또는 `python -m http.server 8000`)
- (선택) js/analysis.js 단위 테스트: `npm test` 또는 `node --test`

## 완료 조건
- Python 분석 스크립트가 `docs/ANALYSIS_BASELINE.md` 기준값과 일치해야 JSON을 생성한다.
- `js/analysis.js`의 단위 테스트가 통과해야 한다.
- 초기 KPI가 `dashboard_data.json`의 `summary`와 정확히 일치해야 한다.
- 브라우저 콘솔에 오류가 없어야 한다.
- 날짜 범위 필터와 노선 필터가 정상 작동해야 한다.

## 작업 시 지켜야 할 절차
- 커밋 또는 푸시 전에 반드시 `git diff`로 변경 내용을 확인한다.
- **commit, push, Notion 페이지 수정은 사용자 승인 이후에만 수행한다.**
