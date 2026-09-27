// Python(scripts/analyze.py)이 생성한 dashboard_data.json을 로딩하고
// 데이터 계약(필수 키/필드)을 검증한다. CSV 파싱은 하지 않는다(Python이 이미 처리함).

const REQUIRED_TOP_LEVEL_KEYS = ['metadata', 'summary', 'records'];
const REQUIRED_RECORD_FIELDS = ['date', 'line', 'station', 'boardings', 'alightings', 'total'];

/** "YYYY-MM-DD" 문자열을 로컬 Date로 변환한다. */
function parseIsoDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function validateContract(payload) {
  if (!payload || typeof payload !== 'object') {
    throw new Error('JSON 데이터 형식이 올바르지 않습니다.');
  }

  const missingTopLevel = REQUIRED_TOP_LEVEL_KEYS.filter((key) => !(key in payload));
  if (missingTopLevel.length > 0) {
    throw new Error(`JSON에 필수 항목이 없습니다: ${missingTopLevel.join(', ')}`);
  }

  if (!Array.isArray(payload.records)) {
    throw new Error('records가 배열 형식이 아닙니다.');
  }

  if (payload.records.length === 0) {
    throw new Error('표시할 데이터가 없습니다.');
  }

  for (let i = 0; i < payload.records.length; i++) {
    const record = payload.records[i];
    const missingFields = REQUIRED_RECORD_FIELDS.filter((field) => !(field in record));
    if (missingFields.length > 0) {
      throw new Error(`데이터 항목(${i}번째)에 필수 필드가 없습니다: ${missingFields.join(', ')}`);
    }
  }
}

/**
 * records의 date 문자열을 Date 객체로 변환하고,
 * js/analysis.js가 기대하는 필드명(boarding, alighting)으로 매핑한다.
 */
function mapRecords(rawRecords) {
  return rawRecords.map((r) => ({
    date: parseIsoDate(r.date),
    line: r.line,
    station: r.station,
    boarding: r.boardings,
    alighting: r.alightings,
  }));
}

/**
 * dashboard_data.json을 fetch해 { metadata, summary, records } 형태로 반환한다.
 * HTTP 상태와 데이터 계약을 검증하며, 오류는 한국어 메시지로 던진다.
 */
export async function loadData(jsonPath) {
  let response;
  try {
    response = await fetch(jsonPath);
  } catch (err) {
    throw new Error('JSON 데이터를 요청하는 중 네트워크 오류가 발생했습니다.');
  }

  if (!response.ok) {
    throw new Error(`JSON 데이터를 불러오지 못했습니다. (상태 코드: ${response.status})`);
  }

  let payload;
  try {
    payload = await response.json();
  } catch (err) {
    throw new Error('JSON 형식을 해석할 수 없습니다.');
  }

  validateContract(payload);

  return {
    metadata: payload.metadata,
    summary: payload.summary,
    records: mapRecords(payload.records),
  };
}
