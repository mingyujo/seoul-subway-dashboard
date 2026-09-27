// 순수 집계 함수 모음. DOM, Chart.js 등 화면 요소에 의존하지 않는다.

function pad2(n) {
  return String(n).padStart(2, '0');
}

/** Date를 'YYYY-MM-DD' 문자열 키로 변환한다(로컬 시간 기준). */
export function dateKey(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** 토요일(6) 또는 일요일(0)이면 true. */
export function isWeekend(date) {
  const day = date.getDay();
  return day === 0 || day === 6;
}

/**
 * startKey/endKey('YYYY-MM-DD' 문자열 또는 falsy)로 레코드를 필터링한다.
 * 두 값을 모두 포함(inclusive)한다.
 */
export function filterByDateRange(records, startKey, endKey) {
  return records.filter((r) => {
    const key = dateKey(r.date);
    if (startKey && key < startKey) return false;
    if (endKey && key > endKey) return false;
    return true;
  });
}

/** line이 'all'이거나 비어 있으면 전체, 아니면 해당 노선만 반환한다. */
export function filterByLine(records, line) {
  if (!line || line === 'all') return records;
  return records.filter((r) => r.line === line);
}

/** 전체 승차/하차/합계 총합을 계산한다. */
export function getTotals(records) {
  let totalBoarding = 0;
  let totalAlighting = 0;
  for (const r of records) {
    totalBoarding += r.boarding;
    totalAlighting += r.alighting;
  }
  return {
    totalBoarding,
    totalAlighting,
    total: totalBoarding + totalAlighting,
  };
}

/**
 * 역명을 기준으로 승차+하차 합계를 구해 상위 topN개를 반환한다.
 * 같은 역명이 여러 노선에 걸쳐 있어도 역명 단위로 합산한다.
 */
export function getTopStations(records, topN = 10) {
  const map = new Map();
  for (const r of records) {
    const entry = map.get(r.station) || { station: r.station, boarding: 0, alighting: 0 };
    entry.boarding += r.boarding;
    entry.alighting += r.alighting;
    map.set(r.station, entry);
  }
  return Array.from(map.values())
    .map((e) => ({ ...e, total: e.boarding + e.alighting }))
    .sort((a, b) => b.total - a.total)
    .slice(0, topN);
}

/** 노선별 승차/하차/합계를 계산한다. */
export function getLineTotals(records) {
  const map = new Map();
  for (const r of records) {
    const entry = map.get(r.line) || { line: r.line, boarding: 0, alighting: 0 };
    entry.boarding += r.boarding;
    entry.alighting += r.alighting;
    map.set(r.line, entry);
  }
  return Array.from(map.values())
    .map((e) => ({ ...e, total: e.boarding + e.alighting }))
    .sort((a, b) => a.line.localeCompare(b.line, 'ko'));
}

/** 날짜별 승차/하차/합계를 날짜 오름차순으로 계산한다. */
export function getDailyTrend(records) {
  const map = new Map();
  for (const r of records) {
    const key = dateKey(r.date);
    const entry = map.get(key) || { key, date: r.date, boarding: 0, alighting: 0 };
    entry.boarding += r.boarding;
    entry.alighting += r.alighting;
    map.set(key, entry);
  }
  return Array.from(map.values())
    .map((e) => ({ ...e, total: e.boarding + e.alighting }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

/**
 * 평일/주말 각각의 (승차+하차) 일평균을 계산한다.
 * 일평균 = 해당 구분의 총합 ÷ 해당 구분에 속한 서로 다른 날짜 수.
 */
export function getWeekdayWeekendAverage(records) {
  const weekdayTotals = { sum: 0, days: new Set() };
  const weekendTotals = { sum: 0, days: new Set() };

  for (const r of records) {
    const key = dateKey(r.date);
    const bucket = isWeekend(r.date) ? weekendTotals : weekdayTotals;
    bucket.sum += r.boarding + r.alighting;
    bucket.days.add(key);
  }

  const weekdayAvg = weekdayTotals.days.size > 0 ? weekdayTotals.sum / weekdayTotals.days.size : 0;
  const weekendAvg = weekendTotals.days.size > 0 ? weekendTotals.sum / weekendTotals.days.size : 0;

  return { weekdayAvg, weekendAvg };
}

/** 필터 UI를 채우기 위한 고유 노선명 목록(가나다순)을 반환한다. */
export function getUniqueLines(records) {
  return Array.from(new Set(records.map((r) => r.line))).sort((a, b) => a.localeCompare(b, 'ko'));
}
