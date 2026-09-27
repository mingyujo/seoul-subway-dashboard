// js/analysis.js(화면 표시용 필터·집계 함수) 단위 테스트.
// CSV 정제·날짜 파싱·숫자 변환은 scripts/analyze.py가 담당하므로 여기서는 다루지 않는다.

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  dateKey,
  isWeekend,
  filterByDateRange,
  filterByLine,
  getTotals,
  getTopStations,
  getLineTotals,
  getDailyTrend,
  getWeekdayWeekendAverage,
  getUniqueLines,
} from '../js/analysis.js';

function d(y, m, day) {
  return new Date(y, m - 1, day);
}

function makeRecord(overrides) {
  return {
    date: d(2026, 8, 3),
    line: '1호선',
    station: '서울역',
    boarding: 100,
    alighting: 50,
    ...overrides,
  };
}

test('dateKey는 로컬 날짜를 YYYY-MM-DD로 변환한다', () => {
  assert.equal(dateKey(d(2026, 8, 3)), '2026-08-03');
});

test('isWeekend은 토/일요일만 true를 반환한다', () => {
  // 2026-08-01은 토요일, 2026-08-03은 월요일
  assert.equal(isWeekend(d(2026, 8, 1)), true);
  assert.equal(isWeekend(d(2026, 8, 3)), false);
});

test('filterByDateRange는 시작일과 종료일을 포함(inclusive)한다', () => {
  const records = [
    makeRecord({ date: d(2026, 8, 1) }),
    makeRecord({ date: d(2026, 8, 5) }),
    makeRecord({ date: d(2026, 8, 10) }),
  ];
  const filtered = filterByDateRange(records, '2026-08-01', '2026-08-05');
  assert.equal(filtered.length, 2);
});

test('filterByLine은 all이면 전체를, 특정 노선이면 해당 노선만 반환한다', () => {
  const records = [
    makeRecord({ line: '1호선' }),
    makeRecord({ line: '2호선' }),
  ];
  assert.equal(filterByLine(records, 'all').length, 2);
  assert.equal(filterByLine(records, '2호선').length, 1);
});

test('getTotals는 승차/하차/합계를 정확히 합산한다', () => {
  const records = [
    makeRecord({ boarding: 100, alighting: 50 }),
    makeRecord({ boarding: 200, alighting: 80 }),
  ];
  const totals = getTotals(records);
  assert.equal(totals.totalBoarding, 300);
  assert.equal(totals.totalAlighting, 130);
  assert.equal(totals.total, 430);
});

test('getTopStations는 같은 역명을 노선과 무관하게 합산 후 승차+하차 합계로 정렬한다', () => {
  const records = [
    makeRecord({ station: '서울역', line: '1호선', boarding: 100, alighting: 50 }),
    makeRecord({ station: '서울역', line: '4호선', boarding: 60, alighting: 40 }),
    makeRecord({ station: '강남역', line: '2호선', boarding: 90, alighting: 90 }),
  ];
  const top = getTopStations(records, 10);
  assert.equal(top.length, 2);
  assert.equal(top[0].station, '서울역');
  assert.equal(top[0].total, 250);
  assert.equal(top[1].station, '강남역');
  assert.equal(top[1].total, 180);
});

test('getTopStations는 topN 개수로 결과를 제한한다', () => {
  const records = Array.from({ length: 15 }, (_, i) =>
    makeRecord({ station: `역${i}`, boarding: i, alighting: 0 })
  );
  const top = getTopStations(records, 10);
  assert.equal(top.length, 10);
});

test('getLineTotals는 노선별 합계를 계산한다', () => {
  const records = [
    makeRecord({ line: '1호선', boarding: 100, alighting: 50 }),
    makeRecord({ line: '1호선', boarding: 10, alighting: 5 }),
    makeRecord({ line: '2호선', boarding: 20, alighting: 20 }),
  ];
  const totals = getLineTotals(records);
  const line1 = totals.find((t) => t.line === '1호선');
  const line2 = totals.find((t) => t.line === '2호선');
  assert.equal(line1.total, 165);
  assert.equal(line2.total, 40);
});

test('getDailyTrend는 날짜별 합계를 날짜 오름차순으로 반환한다', () => {
  const records = [
    makeRecord({ date: d(2026, 8, 5), boarding: 10, alighting: 5 }),
    makeRecord({ date: d(2026, 8, 1), boarding: 20, alighting: 5 }),
    makeRecord({ date: d(2026, 8, 1), boarding: 5, alighting: 5 }),
  ];
  const trend = getDailyTrend(records);
  assert.equal(trend.length, 2);
  assert.equal(trend[0].key, '2026-08-01');
  assert.equal(trend[0].total, 35);
  assert.equal(trend[1].key, '2026-08-05');
});

test('getWeekdayWeekendAverage는 합계가 아니라 날짜 수로 나눈 일평균을 계산한다', () => {
  // 평일 2일(월,화) 총 300, 주말 1일(토) 총 300
  // 합계는 같지만 날짜 수가 달라 평균이 달라야 한다.
  const records = [
    makeRecord({ date: d(2026, 8, 3), boarding: 100, alighting: 50 }), // 월
    makeRecord({ date: d(2026, 8, 4), boarding: 100, alighting: 50 }), // 화
    makeRecord({ date: d(2026, 8, 1), boarding: 200, alighting: 100 }), // 토
  ];
  const { weekdayAvg, weekendAvg } = getWeekdayWeekendAverage(records);
  assert.equal(weekdayAvg, 150); // (150+150)/2
  assert.equal(weekendAvg, 300); // 300/1
});

test('getUniqueLines는 중복 없이 가나다순으로 정렬된 노선 목록을 반환한다', () => {
  const records = [
    makeRecord({ line: '2호선' }),
    makeRecord({ line: '1호선' }),
    makeRecord({ line: '1호선' }),
  ];
  assert.deepEqual(getUniqueLines(records), ['1호선', '2호선']);
});

