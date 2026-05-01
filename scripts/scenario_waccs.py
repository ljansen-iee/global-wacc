"""
Scenario WACC calculation — cross-environment × risk-profile presets.

Differentiates three risk profiles via beta, holding all other parameters
fixed at base assumptions:

    mature  — established technology / utility-like (β = 0.95)
    base    — central assumptions (matches country_waccs.py default, β = 1.10)
    risky   — frontier / high-growth technology (β = 1.25)

Output: results/wacc_per_country_scenarios.csv
        (long format: country_code, country_name, scenario, wacc, wacc_real)

Usage:
    python scripts/scenario_waccs.py
"""
from __future__ import annotations
import logging
import pandas as pd
from pathlib import Path

from country_waccs import (
    WaccParams,
    download_country_risk_premium,
    process_country_risk_premium,
    calculate_wacc_per_country,
    convert_wacc_nominal_to_real,
    show_country_map_info,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base assumptions (matches the default in country_waccs.py)
# ---------------------------------------------------------------------------
LONG_TERM_MARKET_RETURN = 0.10   # nominal long-term equity return (e.g. S&P 500 historic avg)

BASE = WaccParams(
    r_free=0.035,
    beta=1.10,            # Damodaran: Green & Renewable Energy (unleveraged)
    erp=LONG_TERM_MARKET_RETURN - 0.035,   # ERP = long-term return − r_free
    swap_rate=0.030,
    debt_spread=0.020,
    r_debt=0.050,         # swap_rate + debt_spread
    equity_ratio=0.40,
    debt_ratio=0.60,
    inflation_rate=0.020,
    use_country_erp=False,
)

# ---------------------------------------------------------------------------
# Named presets — only beta varies; all other parameters fixed at BASE.
#
# Beta profiles (unleveraged, from Damodaran):
#   mature — 0.95  (Utilities / Power, established technology)
#   base   — 1.10  (Green & Renewable Energy, central estimate)
#   risky  — 1.25  (Green & Renewable Energy, frontier / high-growth)
# ---------------------------------------------------------------------------
PRESETS: dict[str, WaccParams] = {
    "mature": BASE.model_copy(update={"beta": 0.95}),
    "base":   BASE,
    "risky":  BASE.model_copy(update={"beta": 1.25}),
}


def run_scenarios(
    country_data: pd.DataFrame,
    presets: dict[str, WaccParams] = PRESETS,
    mrt_ref_countries: list[str] | None = None,
) -> pd.DataFrame:
    """
    Calculate WACC for every (country, scenario) combination.

    Returns a long-format DataFrame with columns:
        country_code, country_name, scenario, wacc, wacc_real,
        r_free, beta, erp, r_debt, equity_ratio, debt_ratio
    """
    if mrt_ref_countries is None:
        mrt_ref_countries = ["EGY", "KEN", "NAM"]

    frames: list[pd.DataFrame] = []

    for scenario_name, params in presets.items():
        logger.info(f"Running scenario: {scenario_name!r}  "
                    f"(r_free={params.r_free:.1%}, beta={params.beta}, "
                    f"r_debt={params.r_debt:.1%})")

        result = calculate_wacc_per_country(
            country_data=country_data,
            r_free=params.r_free,
            beta_unleveraged=params.beta,
            erp=params.erp,
            r_debt=params.r_debt,
            equity_ratio=params.equity_ratio,
            debt_ratio=params.debt_ratio,
            use_country_erp=params.use_country_erp,
        )

        result["wacc_real"] = result["wacc"].apply(
            lambda w: convert_wacc_nominal_to_real(w, params.inflation_rate)
        )

        # Add Mauritania as average of reference countries (same logic as country_waccs.py)
        if "MRT" not in result["country_code"].values:
            mrt_avg = result[result["country_code"].isin(mrt_ref_countries)].mean(numeric_only=True)
            mrt_row = mrt_avg.to_dict()
            mrt_row["country_code"] = "MRT"
            mrt_row["country_name"] = "Mauritania"
            result = pd.concat([result, pd.DataFrame([mrt_row])], ignore_index=True)

        result.insert(0, "scenario", scenario_name)
        frames.append(result)

    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    data_path = Path(__file__).resolve().parent.parent / "data"
    results_path = Path(__file__).resolve().parent.parent / "results"
    results_path.mkdir(parents=True, exist_ok=True)

    crp_data_raw = download_country_risk_premium(data_path, skip_download=True)
    country_data = process_country_risk_premium(data_path, crp_data_raw)
    show_country_map_info(data_path)

    results = run_scenarios(country_data)

    out_file = results_path / "wacc_per_country_scenarios.csv"
    results.to_csv(out_file, index=False)
    logger.info(f"Saved scenario results ({len(results)} rows) to {out_file}")

    # --- Summary table ---
    print("\nAverage real WACC by scenario:")
    summary = (
        results.groupby("scenario")["wacc_real"]
        .agg(["mean", "min", "max"])
        .rename(columns={"mean": "avg", "min": "min", "max": "max"})
        .reindex(PRESETS.keys())  # preserve logical order
        * 100
    ).round(2)
    summary.columns = ["Avg (%)", "Min (%)", "Max (%)"]
    print(summary.to_string())
