"""Airline Passenger KPI Tracker.

Estimates each airline's quarterly passengers, RPMs and ASMs from BTS T-100
segment data with PySpark + Spark SQL, benchmarks the estimates against the
figures the airlines reported, and explains every gap.

Usage:  python src/pipeline.py [--raw data/raw/T_T100_SEGMENT_ALL_CARRIER.csv]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession, functions as F

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
REF = ROOT / "data" / "reference"
OUT = ROOT / "outputs"

# A gap this small is treated as a match (rounding / minor reporting differences)
TOLERANCE_PCT = 1.0


def get_spark(app: str = "airline-kpi-tracker") -> SparkSession:
    return (
        SparkSession.builder.appName(app)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )


def run_sql_file(spark: SparkSession, name: str):
    """Run every statement in a .sql file; return the last result."""
    text = (SQL / name).read_text()
    statements = [s.strip() for s in text.split(";") if s.strip()]
    result = None
    for stmt in statements:
        result = spark.sql(stmt)
    return result


def register_inputs(spark: SparkSession, raw_path: Path) -> None:
    raw = spark.read.csv(str(raw_path), header=True, inferSchema=False)
    # Stable row id, persisted so every view sees the same ids
    raw = raw.withColumn("row_id", F.monotonically_increasing_id()).persist()
    raw.createOrReplaceTempView("raw_t100")
    for name in ("regional_partners", "partner_hubs"):
        spark.read.csv(str(REF / f"{name}.csv"), header=True).createOrReplaceTempView(name)
    reported = spark.read.csv(str(REF / "reported_operating_stats.csv"), header=True, inferSchema=True)
    reported.createOrReplaceTempView("reported")


def quality_checks(spark: SparkSession) -> pd.DataFrame:
    checks = run_sql_file(spark, "02_quality_checks.sql").toPandas()
    failed = checks[(checks["action"] == "fail if > 0") & (checks["rows_flagged"] > 0)]
    if not failed.empty:
        raise ValueError(f"Blocking data-quality checks failed:\n{failed}")
    return checks


def attribution_coverage(spark: SparkSession) -> pd.DataFrame:
    """How much regional flying could be attributed to an airline."""
    return spark.sql(
        """
        SELECT carrier AS regional_carrier, link_type, airline,
               SUM(rpm) / 1e6 AS rpm_millions,
               SUM(passengers) / 1e3 AS passengers_thousands
        FROM attributed
        WHERE link_type <> 'mainline'
        GROUP BY ALL ORDER BY regional_carrier, airline
        """
    ).toPandas()


def build_comparison(estimates: pd.DataFrame, reported: pd.DataFrame) -> pd.DataFrame:
    """Long table: one row per airline x quarter x metric x attribution stage."""
    est = estimates.melt(
        id_vars=["stage", "stage_name", "airline", "year", "quarter"],
        value_vars=["passengers", "rpm", "asm"], var_name="metric", value_name="estimate")
    rep = reported.rename(columns={"carrier": "airline", "airline": "airline_name"})
    comp = est.merge(
        rep[["airline", "airline_name", "year", "quarter", "metric", "reported_value", "source_metric_name"]],
        on=["airline", "year", "quarter", "metric"])
    comp["gap_pct"] = (comp["estimate"] / comp["reported_value"] - 1) * 100
    return comp.sort_values(["airline", "metric", "quarter", "stage"]).reset_index(drop=True)


def classify(final: pd.DataFrame, airlines_with_regionals: set[str]) -> pd.DataFrame:
    """Label each final-stage gap as a match or a specific data issue."""
    final = final.copy()
    gaps = final.pivot_table(index=["airline", "quarter"], columns="metric", values="gap_pct")

    def label(row: pd.Series) -> str:
        if abs(row["gap_pct"]) <= TOLERANCE_PCT:
            return "match (within 1%)"
        traffic_matches = all(abs(gaps.loc[(row["airline"], row["quarter"]), m]) <= TOLERANCE_PCT
                              for m in ("rpm", "asm"))
        if row["metric"] == "passengers" and traffic_matches:
            return "data issue: passenger-count definition (miles match, counts differ)"
        if row["airline"] in airlines_with_regionals and row["gap_pct"] < 0:
            return "data issue: coverage (regional flying T-100 cannot attribute)"
        return "investigate: possible business or data change"

    final["classification"] = final.apply(label, axis=1)
    # A gap that moves between quarters would hint at a real change; a stable gap is a fixed bias
    final["gap_change_q1_to_q2_pp"] = final.groupby(["airline", "metric"])["gap_pct"].transform(
        lambda g: g.iloc[-1] - g.iloc[0])
    return final


def growth_check(final: pd.DataFrame) -> pd.DataFrame:
    """Does the proxy capture the business trend (Q1 -> Q2 growth) even where levels are off?"""
    rows = []
    for (airline, metric), g in final.groupby(["airline", "metric"]):
        g = g.set_index("quarter")
        if {1, 2} <= set(g.index):
            est_g = (g.loc[2, "estimate"] / g.loc[1, "estimate"] - 1) * 100
            rep_g = (g.loc[2, "reported_value"] / g.loc[1, "reported_value"] - 1) * 100
            rows.append({"airline": airline, "metric": metric,
                         "estimated_qoq_growth_pct": est_g, "reported_qoq_growth_pct": rep_g,
                         "growth_error_pp": est_g - rep_g})
    return pd.DataFrame(rows)


def main(raw_path: Path) -> dict[str, pd.DataFrame]:
    spark = get_spark()
    register_inputs(spark, raw_path)
    run_sql_file(spark, "01_scope.sql")
    checks = quality_checks(spark)
    run_sql_file(spark, "03_attribute_to_airline.sql")
    coverage = attribution_coverage(spark)
    estimates = run_sql_file(spark, "04_quarterly_estimates.sql").toPandas()
    reported = spark.table("reported").toPandas()
    partners = set(spark.table("regional_partners").toPandas()["partner"])
    spark.stop()

    comp = build_comparison(estimates, reported)
    final = classify(comp[comp["stage"] == comp["stage"].max()], partners)
    growth = growth_check(final)

    OUT.mkdir(exist_ok=True)
    checks.to_csv(OUT / "data_quality_results.csv", index=False)
    coverage.round(1).to_csv(OUT / "regional_attribution_coverage.csv", index=False)
    comp.round(3).to_csv(OUT / "estimate_vs_reported_by_stage.csv", index=False)
    final.round(3).to_csv(OUT / "final_estimate_vs_reported.csv", index=False)
    growth.round(3).to_csv(OUT / "growth_check.csv", index=False)
    return {"checks": checks, "coverage": coverage, "comparison": comp, "final": final, "growth": growth}


def summary(final: pd.DataFrame, growth: pd.DataFrame) -> dict[str, float]:
    return {
        "comparisons": len(final),
        "mape_all_pct": final["gap_pct"].abs().mean(),
        "mape_rpm_asm_pct": final.loc[final["metric"].isin(["rpm", "asm"]), "gap_pct"].abs().mean(),
        "max_abs_growth_error_pp": growth["growth_error_pp"].abs().max(),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw" / "T_T100_SEGMENT_ALL_CARRIER.csv")
    res = main(ap.parse_args().raw)
    pd.set_option("display.width", 200)
    print(res["checks"].to_string(index=False))
    print(res["coverage"].round(1).to_string(index=False))
    print(res["final"][["airline", "metric", "quarter", "gap_pct", "gap_change_q1_to_q2_pp", "classification"]].round(2).to_string(index=False))
    print(summary(res["final"], res["growth"]))
    print(res["growth"].round(2).to_string(index=False))
