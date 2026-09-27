"""scripts/analyze.py에 대한 Python unittest 회귀 테스트."""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze  # noqa: E402


def write_csv(path, text):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)


class ReadCsvRowsTests(unittest.TestCase):
    def test_bom_and_mixed_newlines(self):
        """BOM과 혼합 줄바꿈(헤더 CRLF, 데이터 LF)을 안전하게 읽는다."""
        path = REPO_ROOT / "tests" / "_tmp_mixed.csv"
        text = (
            '"사용일자","노선명","역명","승차총승객수","하차총승객수","등록일자"\r\n'
            '"20260801","1호선","서울역","100","50","20260804"\n'
            '"20260802","1호선","시청","200","80","20260805"\n'
        )
        write_csv(path, text)
        try:
            header, rows = analyze.read_csv_rows(path)
            self.assertEqual(header, ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], "20260801")
        finally:
            path.unlink(missing_ok=True)


class TrailingEmptyColumnTests(unittest.TestCase):
    def test_all_empty_trailing_column_is_dropped(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"]
        rows = [
            ["20260801", "1호선", "서울역", "100", "50", "20260804", ""],
            ["20260802", "1호선", "시청", "200", "80", "20260805", ""],
        ]
        new_header, new_rows = analyze.strip_trailing_empty_columns(header, rows)
        self.assertEqual(new_header, header)
        self.assertEqual(new_rows, [row[:6] for row in rows])

    def test_non_empty_trailing_column_raises(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"]
        rows = [
            ["20260801", "1호선", "서울역", "100", "50", "20260804", "값있음"],
        ]
        with self.assertRaises(analyze.AnalysisError):
            analyze.strip_trailing_empty_columns(header, rows)

    def test_too_few_fields_raises(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"]
        rows = [["20260801", "1호선", "서울역"]]
        with self.assertRaises(analyze.AnalysisError):
            analyze.strip_trailing_empty_columns(header, rows)


class RequiredColumnsTests(unittest.TestCase):
    def test_missing_required_column_raises(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수"]  # 하차총승객수 누락
        with self.assertRaises(analyze.AnalysisError):
            analyze.validate_required_columns(header)

    def test_all_required_columns_pass(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수", "등록일자"]
        result = analyze.validate_required_columns(header)
        self.assertEqual(result, header)


class ConvertTypesTests(unittest.TestCase):
    def test_date_and_numeric_conversion(self):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수"]
        rows = [
            ["20260801", "1호선", "서울역", "100", "50"],
            ["bad-date", "1호선", "서울역", "100", "50"],
            ["20260802", "1호선", "서울역", "abc", "50"],
            ["20260803", "1호선", "서울역", "100", ""],
        ]
        df = analyze.build_raw_dataframe(header, rows)
        clean, invalid_count = analyze.convert_types(df)

        self.assertEqual(len(clean), 1)
        self.assertEqual(invalid_count, 3)
        self.assertEqual(clean.iloc[0]["boarding"], 100)
        self.assertEqual(clean.iloc[0]["alighting"], 50)
        self.assertEqual(clean.iloc[0]["date"].strftime("%Y%m%d"), "20260801")


class ComputeSummaryTests(unittest.TestCase):
    def _make_df(self, rows):
        header = ["사용일자", "노선명", "역명", "승차총승객수", "하차총승객수"]
        df = analyze.build_raw_dataframe(header, rows)
        clean, _ = analyze.convert_types(df)
        return clean

    def test_total_sums(self):
        df = self._make_df(
            [
                ["20260801", "1호선", "서울역", "100", "50"],
                ["20260801", "2호선", "강남", "200", "80"],
            ]
        )
        summary = analyze.compute_summary(df)
        self.assertEqual(summary["total_boardings"], 300)
        self.assertEqual(summary["total_alightings"], 130)
        self.assertEqual(summary["total_usage"], 430)

    def test_top_stations_merge_across_lines(self):
        df = self._make_df(
            [
                ["20260801", "1호선", "서울역", "100", "50"],
                ["20260801", "4호선", "서울역", "60", "40"],
                ["20260801", "2호선", "강남", "90", "90"],
            ]
        )
        summary = analyze.compute_summary(df)
        top = summary["top_stations"]
        self.assertEqual(top[0]["station"], "서울역")
        self.assertEqual(top[0]["total"], 250)
        self.assertEqual(top[1]["station"], "강남")
        self.assertEqual(top[1]["total"], 180)

    def test_weekday_weekend_daily_average_uses_day_count(self):
        # 평일(월,화) 총 300, 주말(토) 총 300 -> 합계는 같아도 날짜 수가 달라 평균이 달라야 함
        df = self._make_df(
            [
                ["20260803", "1호선", "서울역", "100", "50"],  # 월요일
                ["20260804", "1호선", "서울역", "100", "50"],  # 화요일
                ["20260801", "1호선", "서울역", "200", "100"],  # 토요일
            ]
        )
        summary = analyze.compute_summary(df)
        self.assertEqual(summary["weekday_day_count"], 2)
        self.assertEqual(summary["weekend_day_count"], 1)
        self.assertEqual(summary["weekday_daily_average"], 150.0)
        self.assertEqual(summary["weekend_daily_average"], 300.0)


class RealCsvIntegrationTests(unittest.TestCase):
    """실제 data/raw CSV로 전체 파이프라인을 실행해 기준값과 대조한다."""

    @classmethod
    def setUpClass(cls):
        cls.metadata, cls.summary, cls.output_path = analyze.run()

    def test_valid_row_count_is_19133(self):
        self.assertEqual(self.metadata["valid_rows"], 19133)
        self.assertEqual(self.metadata["source_rows"], 19133)

    def test_matches_analysis_baseline(self):
        # run()이 내부적으로 compare_with_baseline을 호출해 통과했으므로,
        # 여기서는 핵심 수치를 다시 한번 명시적으로 검증한다.
        self.assertEqual(self.summary["total_boardings"], 208329561)
        self.assertEqual(self.summary["total_alightings"], 207340153)
        self.assertEqual(self.summary["total_usage"], 415669714)
        self.assertEqual(self.summary["line_count"], 27)
        self.assertEqual(self.summary["station_count"], 531)
        self.assertEqual(self.metadata["date_start"], "2026-08-01")
        self.assertEqual(self.metadata["date_end"], "2026-08-31")

    def test_generated_json_has_no_nan_or_infinity(self):
        with open(self.output_path, encoding="utf-8") as f:
            raw_text = f.read()
        self.assertNotIn("NaN", raw_text)
        self.assertNotIn("Infinity", raw_text)

        # 표준 json.load는 allow_nan 기본값이 True라 NaN 리터럴도 파싱해버릴 수 있으므로,
        # parse_constant를 막아 NaN/Infinity 리터럴이 있으면 즉시 실패하게 한다.
        def reject_constant(name):
            raise AssertionError(f"JSON에 허용되지 않는 상수 발견: {name}")

        with open(self.output_path, encoding="utf-8") as f:
            json.load(f, parse_constant=reject_constant)


if __name__ == "__main__":
    unittest.main()
