"""Tests for attribution, quality checks and gap classification."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pipeline as p  # noqa: E402

COLS = ["UNIQUE_CARRIER", "ORIGIN", "DEST", "YEAR", "QUARTER", "MONTH", "CLASS", "AIRCRAFT_TYPE",
        "DEPARTURES_PERFORMED", "SEATS", "PASSENGERS", "DISTANCE"]


def row(carrier, origin, dest, month=1, cls="F", seats=100, pax=80, dist=500, ac="1"):
    return [carrier, origin, dest, 2024, (month - 1) // 3 + 1, month, cls, ac, 1, seats, pax, dist]


@pytest.fixture(scope="module")
def spark():
    s = p.get_spark("tests")
    yield s
    s.stop()


def load(spark, tmp_path, rows):
    path = tmp_path / "t100.csv"
    pd.DataFrame(rows, columns=COLS).to_csv(path, index=False)
    p.register_inputs(spark, path)
    p.run_sql_file(spark, "01_scope.sql")
    p.run_sql_file(spark, "03_attribute_to_airline.sql")
    return spark.table("attributed").toPandas()


def test_mainline_and_sole_contract(spark, tmp_path):
    a = load(spark, tmp_path, [row("UA", "DEN", "ORD"), row("YV", "IAH", "MSY"), row("9E", "ATL", "CHA")])
    got = dict(zip(a.carrier, a.airline))
    assert got == {"UA": "UA", "YV": "UA", "9E": "DL"}


def test_multi_contract_assigned_only_when_one_hub_matches(spark, tmp_path):
    a = load(spark, tmp_path, [
        row("OO", "DEN", "BOI"),   # UA-only hub -> UA
        row("OO", "MSP", "FAR"),   # DL-only hub -> DL
        row("OO", "ORD", "MSN"),   # ORD is UA and AA -> ambiguous
        row("YX", "BOI", "GEG"),   # no partner hub -> unallocated
    ])
    got = dict(zip(a.origin, a.airline))
    assert got == {"DEN": "UA", "MSP": "DL", "ORD": "UNALLOCATED", "BOI": "UNALLOCATED"}


def test_out_of_scope_rows_dropped(spark, tmp_path):
    a = load(spark, tmp_path, [row("WN", "DAL", "HOU"), row("WN", "DAL", "HOU", cls="G"),
                               row("WN", "DAL", "HOU", month=7)])
    assert len(a) == 1


def test_rpm_and_asm_definitions(spark, tmp_path):
    a = load(spark, tmp_path, [row("B6", "JFK", "BOS", seats=150, pax=120, dist=187)])
    assert a.loc[0, "rpm"] == 120 * 187
    assert a.loc[0, "asm"] == 150 * 187


def test_blocking_quality_check_fails(spark, tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame([row("WN", "DAL", "HOU", pax=-5)], columns=COLS).to_csv(path, index=False)
    p.register_inputs(spark, path)
    p.run_sql_file(spark, "01_scope.sql")
    with pytest.raises(ValueError, match="negative_values"):
        p.quality_checks(spark)


def _final(rows):
    return pd.DataFrame(rows, columns=["airline", "quarter", "metric", "gap_pct", "estimate", "reported_value"])


def test_classification_rules():
    f = _final([
        ("WN", 1, "rpm", 0.02, 1, 1), ("WN", 1, "asm", 0.01, 1, 1), ("WN", 1, "passengers", 1.8, 1, 1),
        ("UA", 1, "rpm", -1.8, 1, 1), ("UA", 1, "asm", -1.7, 1, 1), ("UA", 1, "passengers", -5.7, 1, 1),
        ("B6", 1, "rpm", 3.0, 1, 1), ("B6", 1, "asm", 0.0, 1, 1), ("B6", 1, "passengers", 0.3, 1, 1),
    ])
    out = p.classify(f, airlines_with_regionals={"UA", "DL"}).set_index(["airline", "metric"])["classification"]
    assert out[("WN", "rpm")].startswith("match")
    assert out[("WN", "passengers")].startswith("data issue: passenger-count")
    assert out[("UA", "passengers")].startswith("data issue: coverage")
    assert out[("B6", "rpm")].startswith("investigate")


def test_growth_check():
    f = pd.DataFrame({"airline": ["WN", "WN"], "metric": ["rpm", "rpm"], "quarter": [1, 2],
                      "estimate": [100.0, 110.0], "reported_value": [200.0, 222.0]})
    g = p.growth_check(f).iloc[0]
    assert g.estimated_qoq_growth_pct == pytest.approx(10.0)
    assert g.reported_qoq_growth_pct == pytest.approx(11.0)
    assert g.growth_error_pp == pytest.approx(-1.0)
