import numpy as np
import pandas as pd


def calculate_wlps_and_sensitivity(csv_filepath):
  # Load the raw dataset containing repeated runs (MID 1, 2, 3 per configuration)
  df = pd.read_csv(csv_filepath)

  # 1. Compute Repeatability (CV) across the 3 repeated runs for each TestID and Library
  # CV = (Sample Std Dev of Avg_RTT_ms across 3 runs / Arithmetic Mean of Avg_RTT_ms) * 100
  run_agg = (
      df.groupby(
          [
              "TestID",
              "ClientCount",
              "Interval",
              "Timeout",
              "MsgSize",
              "Library",
          ]
      )
      .agg(
          Std_runs=("Avg_RTT_ms", "std"),
          Mean_runs=("Avg_RTT_ms", "mean"),
          Avg_RTT_ms=("Avg_RTT_ms", "mean"),
          Median_RTT_ms=("Median_RTT_ms", "mean"),
          Std_RTT_ms=("Std_RTT_ms", "mean"),
          P99_RTT_ms=("P99_RTT_ms", "mean"),
          Msg_Success_pct=("Msg_Success_%", "mean"),
          Conn_Success_pct=("Conn_Success_%", "mean"),
          Throughput_Msg_s=("Throughput_Msg_s", "mean"),
      )
      .reset_index()
  )

  # Calculate Coefficient of Variation (CV)
  run_agg["CV"] = (run_agg["Std_runs"] / run_agg["Mean_runs"]) * 100
  run_agg["CV"] = run_agg["CV"].fillna(0.0)

  # 2. Min-Max Normalization Helper Functions (per TestID / configuration)
  def norm_lower(s):
    # Lower is better (Latency, Std RTT, CV)
    s_min, s_max = s.min(), s.max()
    if s_min == s_max:
      return pd.Series(100.0, index=s.index)
    return 100.0 * (s_max - s) / (s_max - s_min)

  def norm_higher(s):
    # Higher is better (Success rates, Throughput)
    s_min, s_max = s.min(), s.max()
    if s_min == s_max:
      return pd.Series(100.0, index=s.index)
    return 100.0 * (s - s_min) / (s_max - s_min)

  grouped_cfg = run_agg.groupby("TestID")

  # Normalize Repeatability (V_lc: lower CV gets 100, highest gets 0)
  run_agg["V_lc"] = grouped_cfg["CV"].transform(norm_lower)

  # Normalize Latency metrics (lower is better)
  run_agg["Norm_Avg_RTT"] = grouped_cfg["Avg_RTT_ms"].transform(norm_lower)
  run_agg["Norm_Median_RTT"] = grouped_cfg["Median_RTT_ms"].transform(norm_lower)
  run_agg["Norm_Std_RTT"] = grouped_cfg["Std_RTT_ms"].transform(norm_lower)
  run_agg["Norm_P99_RTT"] = grouped_cfg["P99_RTT_ms"].transform(norm_lower)

  # Normalize Reliability and Throughput metrics (higher is better)
  run_agg["Norm_Msg_Succ"] = grouped_cfg["Msg_Success_pct"].transform(
      norm_higher
  )
  run_agg["Norm_Conn_Succ"] = grouped_cfg["Conn_Success_pct"].transform(
      norm_higher
  )
  run_agg["Norm_Throughput"] = grouped_cfg["Throughput_Msg_s"].transform(
      norm_higher
  )

  # 3. Calculate 4 Dimension Scores per Configuration
  run_agg["Latency_Score"] = (
      0.20 * run_agg["Norm_Avg_RTT"]
      + 0.40 * run_agg["Norm_Median_RTT"]
      + 0.20 * run_agg["Norm_Std_RTT"]
      + 0.20 * run_agg["Norm_P99_RTT"]
  )

  run_agg["Reliability_Score"] = (
      0.60 * run_agg["Norm_Msg_Succ"] + 0.40 * run_agg["Norm_Conn_Succ"]
  )

  run_agg["Throughput_Score"] = run_agg["Norm_Throughput"]
  run_agg["Repeatability_Score"] = run_agg["V_lc"]

  # 4. Define Weighting Profiles for Sensitivity Analysis
  profiles = {
      "Baseline": {
          "Latency": 0.30,
          "Reliability": 0.35,
          "Throughput": 0.25,
          "Repeatability": 0.10,
      },
      "Reliability-Centric": {
          "Latency": 0.20,
          "Reliability": 0.50,
          "Throughput": 0.20,
          "Repeatability": 0.10,
      },
      "Latency-Centric": {
          "Latency": 0.50,
          "Reliability": 0.20,
          "Throughput": 0.20,
          "Repeatability": 0.10,
      },
      "Throughput-Centric": {
          "Latency": 0.20,
          "Reliability": 0.20,
          "Throughput": 0.50,
          "Repeatability": 0.10,
      },
      "Equal Weights": {
          "Latency": 0.25,
          "Reliability": 0.25,
          "Throughput": 0.25,
          "Repeatability": 0.25,
      },
  }

  results = {}

  # 5. Compute WLPS for each profile and average across all 240 configurations
  for p_name, w in profiles.items():
    run_agg[f"WLPS_{p_name}"] = (
        w["Latency"] * run_agg["Latency_Score"]
        + w["Reliability"] * run_agg["Reliability_Score"]
        + w["Throughput"] * run_agg["Throughput_Score"]
        + w["Repeatability"] * run_agg["Repeatability_Score"]
    )
    results[p_name] = run_agg.groupby("Library")[f"WLPS_{p_name}"].mean()

  comparison_table = pd.DataFrame(results)
  ranks_table = comparison_table.rank(ascending=False, method="min").astype(int)

  return comparison_table, ranks_table


if __name__ == "__main__":
  scores, ranks = calculate_wlps_and_sensitivity("final_performance_report.csv")
  print("=== WLPS SCORES ACROSS WEIGHTING PROFILES ===")
  print(scores.round(2))
  print("\n=== LIBRARY RANKINGS ACROSS WEIGHTING PROFILES ===")
  print(ranks)