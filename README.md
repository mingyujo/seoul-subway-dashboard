# 서울 지하철 승하차 대시보드

서울시 지하철 승하차 데이터를 필터링·시각화하는 정적 웹 대시보드입니다.

## 데이터 흐름
```
원본 CSV (data/raw/CARD_SUBWAY_MONTH_202608.csv)
    ↓ python scripts/analyze.py
data/processed/dashboard_data.json
    ↓ fetch (js/data.js)
웹 시각화 (index.html + js/app.js + Chart.js)
```
브라우저는 원본 CSV를 직접 읽거나 분석하지 않습니다. CSV 파싱·정제·집계는 전부 `scripts/analyze.py`(Python/pandas)에서 수행하며, 웹은 그 결과물인 `data/processed/dashboard_data.json`만 `fetch`합니다.

## 데이터 출처
- 원본: `data/raw/CARD_SUBWAY_MONTH_202608.csv`
- 내용: 2026년 8월 서울 수도권 전철 노선별·역별 일일 승하차 인원
- 원본 CSV 값은 수정하지 않으며, 정제·타입 변환은 `scripts/analyze.py`가 메모리 상에서만 수행해 JSON으로 저장합니다.

## 실행 순서

### 1. Python 환경 준비
```bash
pip install -r requirements.txt
```

### 2. Python 분석 실행
```bash
python scripts/analyze.py
```
`data/processed/dashboard_data.json`이 생성/갱신됩니다. `docs/ANALYSIS_BASELINE.md`의 기준값과 계산 결과가 다르면 실행이 실패하고 JSON을 생성하지 않습니다.

### 3. Python 테스트
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 4. 로컬 웹 실행
브라우저의 `fetch`로 로컬 JSON 파일을 읽기 때문에, `index.html`을 `file://`로 직접 열면 브라우저 정책상 로드가 차단될 수 있습니다. 프로젝트 루트에서 정적 파일 서버를 띄운 뒤 접속하세요.

```bash
py -m http.server 8000
```

이후 안내된 주소(`http://localhost:8000`)를 브라우저로 열면 대시보드가 표시됩니다.

## Node.js는 필수 환경이 아닙니다
이 프로젝트는 HTML, CSS, 바닐라 JavaScript(ES Modules)로 동작하며 웹 실행에 Node.js나 npm이 필요하지 않습니다. `package.json`과 `npm test`는 `js/analysis.js`(화면 표시용 필터·집계 함수)에 대한 **선택적** 단위 테스트 실행 수단일 뿐이며, 대시보드 자체를 보는 데는 위 1~4단계(Python + 정적 서버)만으로 충분합니다.

### (선택) js/analysis.js 단위 테스트
Node가 설치되어 있다면 Node 내장 테스트 러너(`node:test`)로 실행할 수 있습니다.
```bash
npm test
# 또는
node --test
```

## 파일 구성
- `scripts/analyze.py` — CSV 정제·집계·JSON 생성 (Python/pandas)
- `tests/test_analysis.py` — Python 분석 파이프라인 단위/통합 테스트
- `data/raw/` — 원본 CSV (수정하지 않음)
- `data/processed/dashboard_data.json` — 웹이 fetch하는 분석 결과
- `index.html` — 화면 뼈대와 필터 UI
- `css/style.css` — 레이아웃 및 반응형 스타일
- `js/data.js` — JSON 로딩(fetch) 및 데이터 계약(필수 키/필드) 검증
- `js/analysis.js` — DOM에 의존하지 않는 순수 함수(화면 표시용 날짜·노선 필터, KPI, 상위 역, 노선별·날짜별 집계)
- `js/app.js` — 필터 이벤트 처리, KPI/차트/표 갱신
- `tests/analysis.test.js` — `js/analysis.js` 단위 테스트(선택 사항, Node 필요)
