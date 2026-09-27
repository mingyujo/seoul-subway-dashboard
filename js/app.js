import { loadData } from './data.js';
import {
  filterByDateRange,
  filterByLine,
  getTotals,
  getTopStations,
  getLineTotals,
  getDailyTrend,
  getWeekdayWeekendAverage,
  getUniqueLines,
} from './analysis.js';

const JSON_PATH = 'data/processed/dashboard_data.json';

const el = {
  status: document.getElementById('status-message'),
  startDate: document.getElementById('start-date'),
  endDate: document.getElementById('end-date'),
  lineFilter: document.getElementById('line-filter'),
  kpiBoarding: document.getElementById('kpi-boarding'),
  kpiAlighting: document.getElementById('kpi-alighting'),
  kpiTotal: document.getElementById('kpi-total'),
  kpiWeekdayAvg: document.getElementById('kpi-weekday-avg'),
  kpiWeekendAvg: document.getElementById('kpi-weekend-avg'),
  tableBody: document.getElementById('data-table-body'),
  topStationsCanvas: document.getElementById('top-stations-chart'),
  lineTotalsCanvas: document.getElementById('line-totals-chart'),
  dailyTrendCanvas: document.getElementById('daily-trend-chart'),
};

let allRecords = [];
let summary = null;
let metadata = null;
let chartUnavailableShown = false;

const charts = {
  topStations: null,
  lineTotals: null,
  dailyTrend: null,
};

function isChartAvailable() {
  return typeof globalThis.Chart === 'function';
}

/** Chart.js를 불러오지 못한 경우, 차트 영역에만 오류를 표시하고 KPI/표는 그대로 둔다. */
function showChartUnavailable() {
  if (chartUnavailableShown) return;
  chartUnavailableShown = true;

  const message = '차트 라이브러리를 불러오지 못했습니다. 네트워크 연결을 확인해주세요.';
  [el.topStationsCanvas, el.lineTotalsCanvas, el.dailyTrendCanvas].forEach((canvas) => {
    if (!canvas) return;
    canvas.hidden = true;
    const p = document.createElement('p');
    p.className = 'status-message status-error';
    p.textContent = message;
    canvas.insertAdjacentElement('afterend', p);
  });
}

function showStatus(message, isError = false) {
  el.status.textContent = message;
  el.status.hidden = !message;
  el.status.classList.toggle('status-error', isError);
}

function clearStatus() {
  showStatus('');
}

function formatNumber(n) {
  return Math.round(n).toLocaleString('ko-KR');
}

function destroyChart(key) {
  if (charts[key]) {
    charts[key].destroy();
    charts[key] = null;
  }
}

function renderTopStationsChart(topStations) {
  destroyChart('topStations');
  charts.topStations = new Chart(el.topStationsCanvas, {
    type: 'bar',
    data: {
      labels: topStations.map((s) => s.station),
      datasets: [
        {
          label: '승차+하차 합계',
          data: topStations.map((s) => s.total),
          backgroundColor: '#3b82f6',
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderLineTotalsChart(lineTotals) {
  destroyChart('lineTotals');
  charts.lineTotals = new Chart(el.lineTotalsCanvas, {
    type: 'bar',
    data: {
      labels: lineTotals.map((l) => l.line),
      datasets: [
        {
          label: '이용량 합계',
          data: lineTotals.map((l) => l.total),
          backgroundColor: '#10b981',
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderDailyTrendChart(dailyTrend) {
  destroyChart('dailyTrend');
  charts.dailyTrend = new Chart(el.dailyTrendCanvas, {
    type: 'line',
    data: {
      labels: dailyTrend.map((d) => d.key),
      datasets: [
        {
          label: '일별 이용량 합계',
          data: dailyTrend.map((d) => d.total),
          borderColor: '#f59e0b',
          backgroundColor: '#f59e0b',
          tension: 0.2,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderTable(dailyTrend) {
  el.tableBody.innerHTML = '';
  for (const row of dailyTrend) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.key}</td>
      <td>${formatNumber(row.boarding)}</td>
      <td>${formatNumber(row.alighting)}</td>
      <td>${formatNumber(row.total)}</td>
    `;
    el.tableBody.appendChild(tr);
  }
}

function renderKpi(totals, weekdayAvg, weekendAvg) {
  el.kpiBoarding.textContent = formatNumber(totals.totalBoarding);
  el.kpiAlighting.textContent = formatNumber(totals.totalAlighting);
  el.kpiTotal.textContent = formatNumber(totals.total);
  el.kpiWeekdayAvg.textContent = formatNumber(weekdayAvg);
  el.kpiWeekendAvg.textContent = formatNumber(weekendAvg);
}

/** summary(dashboard_data.json)를 analysis.js 결과와 동일한 형태로 변환한다. */
function buildViewFromSummary() {
  const totals = {
    totalBoarding: summary.total_boardings,
    totalAlighting: summary.total_alightings,
    total: summary.total_usage,
  };
  const topStations = summary.top_stations.map((s) => ({
    station: s.station,
    boarding: s.boardings,
    alighting: s.alightings,
    total: s.total,
  }));
  const lineTotals = summary.by_line.map((l) => ({
    line: l.line,
    boarding: l.boardings,
    alighting: l.alightings,
    total: l.total,
  }));
  const dailyTrend = summary.by_date.map((d) => ({
    key: d.date,
    boarding: d.boardings,
    alighting: d.alightings,
    total: d.total,
  }));
  return {
    totals,
    topStations,
    lineTotals,
    dailyTrend,
    weekdayAvg: summary.weekday_daily_average,
    weekendAvg: summary.weekend_daily_average,
    isEmpty: false,
  };
}

/** 필터링된 records로 analysis.js를 이용해 화면 표시용 값을 계산한다. */
function buildViewFromFilteredRecords(startKey, endKey, line) {
  const filtered = filterByLine(filterByDateRange(allRecords, startKey, endKey), line);
  return {
    totals: getTotals(filtered),
    topStations: getTopStations(filtered, 10),
    lineTotals: getLineTotals(filtered),
    dailyTrend: getDailyTrend(filtered),
    ...getWeekdayWeekendAverage(filtered),
    isEmpty: filtered.length === 0,
  };
}

function isDefaultFilter(startKey, endKey, line) {
  return startKey === metadata.date_start && endKey === metadata.date_end && line === 'all';
}

function render() {
  const startKey = el.startDate.value || metadata.date_start;
  const endKey = el.endDate.value || metadata.date_end;
  const line = el.lineFilter.value || 'all';

  // 필터가 전체 범위/전체 노선이면 Python summary를 그대로 사용해 초기 KPI와의
  // 완전한 일치를 보장하고, 그 외에는 선택된 날짜·노선에 대해서만 records를
  // 필터링해 analysis.js로 재계산한다.
  const view = isDefaultFilter(startKey, endKey, line)
    ? buildViewFromSummary()
    : buildViewFromFilteredRecords(startKey, endKey, line);

  if (view.isEmpty) {
    showStatus('선택한 조건에 해당하는 데이터가 없습니다.');
  } else {
    clearStatus();
  }

  // Chart.js CDN이 실패해도 KPI와 표는 항상 먼저 채운 뒤 차트만 격리해서 시도한다.
  renderKpi(view.totals, view.weekdayAvg, view.weekendAvg);
  renderTable(view.dailyTrend);

  if (isChartAvailable()) {
    renderTopStationsChart(view.topStations);
    renderLineTotalsChart(view.lineTotals);
    renderDailyTrendChart(view.dailyTrend);
  } else {
    showChartUnavailable();
  }
}

function populateFilters() {
  const lines = getUniqueLines(allRecords);
  el.lineFilter.innerHTML = '<option value="all">전체 노선</option>';
  for (const line of lines) {
    const option = document.createElement('option');
    option.value = line;
    option.textContent = line;
    el.lineFilter.appendChild(option);
  }

  el.startDate.min = metadata.date_start;
  el.startDate.max = metadata.date_end;
  el.startDate.value = metadata.date_start;
  el.endDate.min = metadata.date_start;
  el.endDate.max = metadata.date_end;
  el.endDate.value = metadata.date_end;
}

async function init() {
  showStatus('데이터를 불러오는 중입니다...');
  let result;
  try {
    result = await loadData(JSON_PATH);
  } catch (err) {
    showStatus(`데이터를 불러오지 못했습니다: ${err.message}`, true);
    return;
  }

  allRecords = result.records;
  summary = result.summary;
  metadata = result.metadata;

  clearStatus();
  populateFilters();
  render();

  el.startDate.addEventListener('change', render);
  el.endDate.addEventListener('change', render);
  el.lineFilter.addEventListener('change', render);
}

init();
