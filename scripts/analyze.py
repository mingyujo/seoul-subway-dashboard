"""서울 지하철 승하차 CSV를 정제·집계해 data/processed/dashboard_data.json을 생성한다.

docs/ANALYSIS_BASELINE.md에 기록된 기준값과 계산 결과가 다르면 JSON을 만들지 않고 실패한다.
"""

import argparse
import csv
import io
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "CARD_SUBWAY_MONTH_202608.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "dashboard_data.json"

REQUIRED_COLUMNS = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수"]
KNOWN_HEADER = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"]

KST = timezone(timedelta(hours=9))

# docs/ANALYSIS_BASELINE.md (2026-09-27 실행)에 기록된 실제 기준값.
# 계산 결과가 이 값들과 다르면 analyze.py는 JSON을 생성하지 않고 실패해야 한다.
BASELINE = {
    "source_rows": 19133,
    "valid_rows": 19133,
    "date_start": "2026-08-01",
    "date_end": "2026-08-31",
    "line_count": 27,
    "station_count": 531,
    "total_boardings": 208329561,
    "total_alightings": 207340153,
    "total_usage": 415669714,
    "weekday_day_count": 21,
    "weekend_day_count": 10,
    "weekday_daily_average": 15030554.43,
    "weekend_daily_average": 10002807.10,
    "top_stations": [
        {"station": "서울역", "boardings": 3681205, "alightings": 3638971, "total": 7320176},
        {"station": "잠실(송파구청)", "boardings": 3092577, "alightings": 3142711, "total": 6235288},
        {"station": "홍대입구", "boardings": 2897567, "alightings": 3049481, "total": 5947048},
        {"station": "고속터미널", "boardings": 2651833, "alightings": 2658884, "total": 5310717},
        {"station": "강남", "boardings": 2328683, "alightings": 2270438, "total": 4599121},
        {"station": "사당", "boardings": 1933968, "alightings": 1950713, "total": 3884681},
        {"station": "선릉", "boardings": 1880539, "alightings": 1855302, "total": 3735841},
        {"station": "성수", "boardings": 1774772, "alightings": 1904061, "total": 3678833},
        {"station": "신림", "boardings": 1696193, "alightings": 1680449, "total": 3376642},
        {"station": "여의도", "boardings": 1678630, "alightings": 1691619, "total": 3370249},
    ],
    "by_line": {
        "2호선": {"boardings": 41437542, "alightings": 41824025, "total": 83261567},
        "5호선": {"boardings": 19260232, "alightings": 19038172, "total": 38298404},
        "7호선": {"boardings": 16694979, "alightings": 16457126, "total": 33152105},
        "4호선": {"boardings": 15433666, "alightings": 15771813, "total": 31205479},
        "3호선": {"boardings": 15493259, "alightings": 15223910, "total": 30717169},
        "경부선": {"boardings": 13368676, "alightings": 13204788, "total": 26573464},
        "분당선": {"boardings": 10441973, "alightings": 10795188, "total": 21237161},
        "6호선": {"boardings": 9633496, "alightings": 9539634, "total": 19173130},
        "9호선": {"boardings": 8446007, "alightings": 8603337, "total": 17049344},
        "1호선": {"boardings": 7984934, "alightings": 7804988, "total": 15789922},
        "경인선": {"boardings": 7562257, "alightings": 7393871, "total": 14956128},
        "8호선": {"boardings": 6011203, "alightings": 6056963, "total": 12068166},
        "경원선": {"boardings": 6088324, "alightings": 5900152, "total": 11988476},
        "공항철도 1호선": {"boardings": 4259449, "alightings": 3998330, "total": 8257779},
        "9호선2~3단계": {"boardings": 3531284, "alightings": 3514630, "total": 7045914},
        "안산선": {"boardings": 3292756, "alightings": 3267299, "total": 6560055},
        "일산선": {"boardings": 3315470, "alightings": 3228522, "total": 6543992},
        "경의선": {"boardings": 3156342, "alightings": 3088751, "total": 6245093},
        "과천선": {"boardings": 3003701, "alightings": 2995205, "total": 5998906},
        "중앙선": {"boardings": 2428284, "alightings": 2344715, "total": 4772999},
        "수인선": {"boardings": 1736799, "alightings": 1689439, "total": 3426238},
        "신림선": {"boardings": 1427607, "alightings": 1399405, "total": 2827012},
        "우이신설선": {"boardings": 1342101, "alightings": 1295088, "total": 2637189},
        "경춘선": {"boardings": 1126052, "alightings": 1078242, "total": 2204294},
        "경강선": {"boardings": 1024819, "alightings": 989373, "total": 2014192},
        "장항선": {"boardings": 496634, "alightings": 474631, "total": 971265},
        "서해선": {"boardings": 331715, "alightings": 362556, "total": 694271},
    },
    "by_date": {
        "2026-08-01": {"boardings": 5479960, "alightings": 5446554, "total": 10926514},
        "2026-08-02": {"boardings": 4206125, "alightings": 4177789, "total": 8383914},
        "2026-08-03": {"boardings": 7170396, "alightings": 7139015, "total": 14309411},
        "2026-08-04": {"boardings": 7216024, "alightings": 7183202, "total": 14399226},
        "2026-08-05": {"boardings": 7319321, "alightings": 7286473, "total": 14605794},
        "2026-08-06": {"boardings": 7354032, "alightings": 7322049, "total": 14676081},
        "2026-08-07": {"boardings": 7564151, "alightings": 7529401, "total": 15093552},
        "2026-08-08": {"boardings": 5444601, "alightings": 5414167, "total": 10858768},
        "2026-08-09": {"boardings": 4368545, "alightings": 4341566, "total": 8710111},
        "2026-08-10": {"boardings": 7487147, "alightings": 7454410, "total": 14941557},
        "2026-08-11": {"boardings": 7729840, "alightings": 7697562, "total": 15427402},
        "2026-08-12": {"boardings": 7868739, "alightings": 7834541, "total": 15703280},
        "2026-08-13": {"boardings": 7878433, "alightings": 7843842, "total": 15722275},
        "2026-08-14": {"boardings": 7967587, "alightings": 7931869, "total": 15899456},
        "2026-08-15": {"boardings": 5315923, "alightings": 5285111, "total": 10601034},
        "2026-08-16": {"boardings": 4388488, "alightings": 4361839, "total": 8750327},
        "2026-08-17": {"boardings": 4348401, "alightings": 4324237, "total": 8672638},
        "2026-08-18": {"boardings": 7580190, "alightings": 7548370, "total": 15128560},
        "2026-08-19": {"boardings": 7814362, "alightings": 7782113, "total": 15596475},
        "2026-08-20": {"boardings": 7857525, "alightings": 7823874, "total": 15681399},
        "2026-08-21": {"boardings": 8072799, "alightings": 8037156, "total": 16109955},
        "2026-08-22": {"boardings": 5768557, "alightings": 5737840, "total": 11506397},
        "2026-08-23": {"boardings": 4680111, "alightings": 4650236, "total": 9330347},
        "2026-08-24": {"boardings": 7640560, "alightings": 7608209, "total": 15248769},
        "2026-08-25": {"boardings": 7871239, "alightings": 7836766, "total": 15708005},
        "2026-08-26": {"boardings": 7927545, "alightings": 7893161, "total": 15820706},
        "2026-08-27": {"boardings": 7990577, "alightings": 7955926, "total": 15946503},
        "2026-08-28": {"boardings": 8157579, "alightings": 8122075, "total": 16279654},
        "2026-08-29": {"boardings": 5986562, "alightings": 5952470, "total": 11939032},
        "2026-08-30": {"boardings": 4524649, "alightings": 4496978, "total": 9021627},
        "2026-08-31": {"boardings": 7349593, "alightings": 7321352, "total": 14670945},
    },
}


class AnalysisError(Exception):
    """분석 파이프라인에서 발생하는 명확한 오류(입력 형식, 기준값 불일치 등)."""


def find_csv_path(explicit_path=None):
    """명시적 경로가 있으면 그것을, 없으면 기본 경로를 사용한다.
    기본 경로가 없으면 data/raw, data 폴더에서 CSV를 자동 탐색한다."""
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise AnalysisError(f"지정한 CSV 파일을 찾을 수 없습니다: {path}")
        return path

    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT

    candidates = list((REPO_ROOT / "data" / "raw").glob("*.csv"))
    candidates += list((REPO_ROOT / "data").glob("*.csv"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) == 0:
        raise AnalysisError(
            f"CSV 파일을 찾을 수 없습니다. 기본 경로({DEFAULT_INPUT})에 파일이 없고, "
            "data/raw, data 폴더에서도 자동 탐색에 실패했습니다. --input으로 직접 지정하세요."
        )
    raise AnalysisError(
        f"CSV 후보가 여러 개 발견되어 자동으로 선택할 수 없습니다: {candidates}. "
        "--input으로 직접 지정하세요."
    )


def read_csv_rows(path):
    """UTF-8-SIG로 읽고 혼합 줄바꿈(CRLF/LF)을 LF로 정규화한 뒤 csv.reader로 파싱한다."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        text = f.read()

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    reader = csv.reader(io.StringIO(normalized))
    rows = [row for row in reader if row != []]

    if len(rows) < 2:
        raise AnalysisError("CSV에 헤더 또는 데이터 행이 없습니다.")

    header, data_rows = rows[0], rows[1:]
    return header, data_rows


def strip_trailing_empty_columns(header, data_rows):
    """데이터 행의 열 수가 헤더보다 많을 때, 초과분이 모두 빈 값인 경우에만 제거한다.
    빈 값이 아닌 초과 필드나 헤더보다 적은 필드가 있으면 오류를 발생시킨다."""
    header_len = len(header)
    field_counts = {len(row) for row in data_rows}

    if field_counts == {header_len}:
        return header, data_rows

    if any(count < header_len for count in field_counts):
        raise AnalysisError(
            f"일부 데이터 행의 열 수({sorted(field_counts)})가 헤더 열 수({header_len})보다 적습니다."
        )

    extra_len = max(field_counts) - header_len
    if len(field_counts) > 1 or extra_len <= 0:
        raise AnalysisError(
            f"데이터 행의 열 수가 일정하지 않습니다: {sorted(field_counts)} (헤더 열 수: {header_len})"
        )

    non_empty_extra = [
        row for row in data_rows if any(v.strip() != "" for v in row[header_len:])
    ]
    if non_empty_extra:
        raise AnalysisError(
            f"trailing 열에 값이 있는 행이 {len(non_empty_extra)}개 있어 자동으로 제거할 수 없습니다. "
            f"예시: {non_empty_extra[0]}"
        )

    trimmed_rows = [row[:header_len] for row in data_rows]
    return header, trimmed_rows


def validate_required_columns(header):
    trimmed_header = [h.strip() for h in header]
    missing = [col for col in REQUIRED_COLUMNS if col not in trimmed_header]
    if missing:
        raise AnalysisError(f"필수 열이 없습니다: {missing} (실제 열: {trimmed_header})")
    return trimmed_header


def build_raw_dataframe(header, data_rows):
    df = pd.DataFrame(data_rows, columns=header)
    return df


def convert_types(df):
    """날짜·숫자를 명시적으로 변환하고, 유효/무효 행을 분리한다."""
    date = pd.to_datetime(df["사용일자"].str.strip(), format="%Y%m%d", errors="coerce")
    line = df["노선명"].str.strip()
    station = df["역명"].str.strip()
    boarding = pd.to_numeric(df["승차총승객수"].str.strip(), errors="coerce")
    alighting = pd.to_numeric(df["하차총승객수"].str.strip(), errors="coerce")

    valid_mask = (
        date.notna()
        & line.ne("")
        & station.ne("")
        & boarding.notna()
        & alighting.notna()
        & boarding.apply(math.isfinite)
        & alighting.apply(math.isfinite)
    )

    invalid_count = int((~valid_mask).sum())

    clean = pd.DataFrame(
        {
            "date": date[valid_mask],
            "line": line[valid_mask],
            "station": station[valid_mask],
            "boarding": boarding[valid_mask].astype("int64"),
            "alighting": alighting[valid_mask].astype("int64"),
        }
    ).reset_index(drop=True)

    return clean, invalid_count


def compute_summary(df):
    total_boardings = int(df["boarding"].sum())
    total_alightings = int(df["alighting"].sum())
    total_usage = total_boardings + total_alightings

    station_group = df.groupby("station")[["boarding", "alighting"]].sum()
    station_group["total"] = station_group["boarding"] + station_group["alighting"]
    top_stations = (
        station_group.sort_values("total", ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={"boarding": "boardings", "alighting": "alightings"})
    )
    top_stations_list = [
        {
            "station": row["station"],
            "boardings": int(row["boardings"]),
            "alightings": int(row["alightings"]),
            "total": int(row["total"]),
        }
        for _, row in top_stations.iterrows()
    ]

    line_group = df.groupby("line")[["boarding", "alighting"]].sum()
    line_group["total"] = line_group["boarding"] + line_group["alighting"]
    line_group = line_group.sort_values("line")
    by_line_list = [
        {
            "line": line,
            "boardings": int(row["boarding"]),
            "alightings": int(row["alighting"]),
            "total": int(row["total"]),
        }
        for line, row in line_group.iterrows()
    ]

    date_group = df.groupby(df["date"].dt.strftime("%Y-%m-%d"))[["boarding", "alighting"]].sum()
    date_group["total"] = date_group["boarding"] + date_group["alighting"]
    date_group = date_group.sort_index()
    by_date_list = [
        {
            "date": date_key,
            "boardings": int(row["boarding"]),
            "alightings": int(row["alighting"]),
            "total": int(row["total"]),
        }
        for date_key, row in date_group.iterrows()
    ]

    is_weekend = df["date"].dt.dayofweek >= 5
    combined = df["boarding"] + df["alighting"]
    weekday_dates = set(df.loc[~is_weekend, "date"].dt.strftime("%Y-%m-%d"))
    weekend_dates = set(df.loc[is_weekend, "date"].dt.strftime("%Y-%m-%d"))
    weekday_sum = int(combined[~is_weekend].sum())
    weekend_sum = int(combined[is_weekend].sum())
    weekday_day_count = len(weekday_dates)
    weekend_day_count = len(weekend_dates)
    weekday_daily_average = round(weekday_sum / weekday_day_count, 2) if weekday_day_count else 0.0
    weekend_daily_average = round(weekend_sum / weekend_day_count, 2) if weekend_day_count else 0.0

    return {
        "total_boardings": total_boardings,
        "total_alightings": total_alightings,
        "total_usage": total_usage,
        "line_count": int(df["line"].nunique()),
        "station_count": int(df["station"].nunique()),
        "weekday_day_count": weekday_day_count,
        "weekend_day_count": weekend_day_count,
        "weekday_daily_average": weekday_daily_average,
        "weekend_daily_average": weekend_daily_average,
        "top_stations": top_stations_list,
        "by_line": by_line_list,
        "by_date": by_date_list,
    }


def compare_with_baseline(metadata, summary):
    """기준값과 다르면 AnalysisError를 발생시킨다."""
    mismatches = []

    def check(label, actual, expected):
        if actual != expected:
            mismatches.append(f"{label}: 실제={actual!r} 기대={expected!r}")

    check("valid_rows", metadata["valid_rows"], BASELINE["valid_rows"])
    check("date_start", metadata["date_start"], BASELINE["date_start"])
    check("date_end", metadata["date_end"], BASELINE["date_end"])
    check("line_count", summary["line_count"], BASELINE["line_count"])
    check("station_count", summary["station_count"], BASELINE["station_count"])
    check("total_boardings", summary["total_boardings"], BASELINE["total_boardings"])
    check("total_alightings", summary["total_alightings"], BASELINE["total_alightings"])
    check("total_usage", summary["total_usage"], BASELINE["total_usage"])
    check("weekday_day_count", summary["weekday_day_count"], BASELINE["weekday_day_count"])
    check("weekend_day_count", summary["weekend_day_count"], BASELINE["weekend_day_count"])
    check("weekday_daily_average", summary["weekday_daily_average"], BASELINE["weekday_daily_average"])
    check("weekend_daily_average", summary["weekend_daily_average"], BASELINE["weekend_daily_average"])

    actual_top = [
        {"station": s["station"], "boardings": s["boardings"], "alightings": s["alightings"], "total": s["total"]}
        for s in summary["top_stations"]
    ]
    check("top_stations", actual_top, BASELINE["top_stations"])

    actual_by_line = {row["line"]: {"boardings": row["boardings"], "alightings": row["alightings"], "total": row["total"]} for row in summary["by_line"]}
    check("by_line", actual_by_line, BASELINE["by_line"])

    actual_by_date = {row["date"]: {"boardings": row["boardings"], "alightings": row["alightings"], "total": row["total"]} for row in summary["by_date"]}
    check("by_date", actual_by_date, BASELINE["by_date"])

    if mismatches:
        raise AnalysisError(
            "기준값(docs/ANALYSIS_BASELINE.md)과 계산 결과가 다릅니다:\n  " + "\n  ".join(mismatches)
        )


def build_records(df):
    records = []
    for row in df.itertuples(index=False):
        records.append(
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "line": row.line,
                "station": row.station,
                "boardings": int(row.boarding),
                "alightings": int(row.alighting),
                "total": int(row.boarding) + int(row.alighting),
            }
        )
    return records


def assert_no_nan_or_inf(value, path="root"):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise AnalysisError(f"JSON 값에 NaN/Infinity가 포함되어 있습니다: {path} = {value}")
    elif isinstance(value, dict):
        for k, v in value.items():
            assert_no_nan_or_inf(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            assert_no_nan_or_inf(v, f"{path}[{i}]")


def run(input_path=None, output_path=None):
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT

    csv_path = find_csv_path(input_path)
    header, data_rows = read_csv_rows(csv_path)
    source_rows = len(data_rows)

    header, data_rows = strip_trailing_empty_columns(header, data_rows)
    header = validate_required_columns(header)

    raw_df = build_raw_dataframe(header, data_rows)
    clean_df, invalid_count = convert_types(raw_df)
    valid_rows = len(clean_df)

    if valid_rows == 0:
        raise AnalysisError("유효한 데이터 행이 없습니다.")

    date_start = clean_df["date"].min().strftime("%Y-%m-%d")
    date_end = clean_df["date"].max().strftime("%Y-%m-%d")

    metadata = {
        "source_file": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_at": datetime.now(tz=KST).isoformat(),
        "source_rows": source_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_count,
        "date_start": date_start,
        "date_end": date_end,
    }

    summary = compute_summary(clean_df)

    compare_with_baseline(metadata, summary)

    records = build_records(clean_df)

    payload = {"metadata": metadata, "summary": summary, "records": records}
    assert_no_nan_or_inf(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)

    return metadata, summary, output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="원본 CSV 경로 (생략 시 자동 탐색)")
    parser.add_argument("--output", help="출력 JSON 경로 (생략 시 data/processed/dashboard_data.json)")
    args = parser.parse_args()

    try:
        metadata, summary, output_path = run(args.input, args.output)
    except AnalysisError as e:
        print(f"[분석 실패] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"원본 행 수: {metadata['source_rows']}")
    print(f"유효 행 수: {metadata['valid_rows']} (제외: {metadata['invalid_rows']})")
    print(f"날짜 범위: {metadata['date_start']} ~ {metadata['date_end']}")
    print(f"총 승차: {summary['total_boardings']:,}")
    print(f"총 하차: {summary['total_alightings']:,}")
    print(f"총 이용: {summary['total_usage']:,}")
    print(f"기준값 대조: 통과")
    print(f"JSON 생성 완료: {output_path} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
