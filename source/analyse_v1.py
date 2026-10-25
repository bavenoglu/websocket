import pandas as pd
import os


import numpy as np
from scipy.stats import binom

def percentile_ci(data, percentile, confidence=0.95):
    data = np.sort(np.asarray(data, dtype=float))
    data = data[np.isfinite(data)]

    n = len(data)
    if n == 0:
        return np.nan, np.nan

    p = percentile / 100
    alpha = 1 - confidence

    lower_rank = int(binom.ppf(alpha / 2, n, p))
    upper_rank = int(binom.ppf(1 - alpha / 2, n, p)) + 1

    lower_rank = max(1, lower_rank)
    upper_rank = min(n, upper_rank)

    return data[lower_rank - 1], data[upper_rank - 1]


TEST_COUNT = 240
MESSAGES_PER_CLIENT = 300

# TestID -> Expected Client Mapping
def get_expected_clients(test_id):
    idx = (test_id - 1) // 48

    CLIENT_COUNTS = [1, 32, 128, 512, 2048]

    if idx < 0 or idx >= len(CLIENT_COUNTS):
        return None

    return CLIENT_COUNTS[idx]


# ==============================
# ANALYSIS
# ==============================

def analyze_logs(base_dir="logs"):
    results = []

    libraries = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]

    for lib in libraries:

        for test_id in range(1, TEST_COUNT + 1):

            client_file = os.path.join(base_dir, lib, "client", f"client_log_{test_id}.csv")
            server_file = os.path.join(base_dir, lib, "server", f"server_log_{test_id}.csv")

            if not os.path.exists(client_file) or not os.path.exists(server_file):
                continue

            try:
                df_c = pd.read_csv(client_file)
                df_s = pd.read_csv(server_file)

                if df_c.empty:
                    continue

                # ===== EXPECTED =====
                expected_clients = get_expected_clients(test_id)
                expected_total_msgs = expected_clients * MESSAGES_PER_CLIENT

                # ===== ACTUAL =====
                actual_clients = df_c["conn_id"].nunique()
                client_received = len(df_c)

                server_ok = (df_s["status"] == "OK").sum()
                server_fail = (df_s["status"] == "FAIL").sum()
                server_total_log = len(df_s)

                # ===== LOSSES =====
                net_loss = expected_total_msgs - client_received
                log_gap = client_received - server_total_log

                # ===== RATES =====
                conn_success_rate = (actual_clients / expected_clients) * 100 if expected_clients else 0
                msg_success_rate = (server_ok / expected_total_msgs) * 100 if expected_total_msgs else 0

                # ===== PERFORMANCE =====
                avg_rtt = df_c["latency_ms"].mean()
                p50_rtt, p95_rtt, p99_rtt = df_c["latency_ms"].quantile([0.50, 0.95, 0.99])
                median_rtt = df_c["latency_ms"].median()
                std_rtt = df_c["latency_ms"].std()

                avg_proc = df_s["process_ms"].mean() if not df_s.empty else 0
                median_proc = df_s["process_ms"].median() if not df_s.empty else 0
                std_proc = df_s["process_ms"].std() if not df_s.empty else 0

                p50_ci_low, p50_ci_high = percentile_ci(df_c["latency_ms"], 50)
                p95_ci_low, p95_ci_high = percentile_ci(df_c["latency_ms"], 95)
                p99_ci_low, p99_ci_high = percentile_ci(df_c["latency_ms"], 99)


                duration_ns = df_c["received_at"].max() - df_c["sent_at"].min()
                duration_sec = duration_ns / 1e9 if duration_ns > 0 else 0
                throughput = client_received / duration_sec if duration_sec > 0 else 0
                

                # ===== TEST PARAMS (log içinden alıyoruz) =====
                interval = df_c["interval"].iloc[0]
                msg_size = df_c["message_size"].iloc[0]
                timeout = df_c["timeout_ms"].iloc[0]

                results.append({
                    "Library": lib,
                    "TestID": test_id,

                    "Clients_Target": expected_clients,
                    "Clients_Actual": actual_clients,
                    "Conn_Success_%": round(conn_success_rate, 2),

                    "Client_Log_Count": client_received,
                    "Server_Log_Count": server_total_log,
                    "Server_FAIL": server_fail,

                    "Msg_Success_%": round(msg_success_rate, 2),

                    "Interval_ms": interval,
                    "Timeout_ms": timeout,
                    "Msg_Size": msg_size,

                    "Avg_RTT_ms": round(avg_rtt, 4),
                    "Avg_Server_Proc_ms": round(avg_proc, 4),
                    "Std_Server_Proc_ms": round(std_proc, 4),
                    "Median_Server_Proc_ms": round(median_proc, 4),

                    "Throughput_Msg_s": round(throughput, 2),

                    "P50_RTT_ms": round(p50_rtt, 4),
                    "P95_RTT_ms": round(p95_rtt, 4),
                    "P99_RTT_ms": round(p99_rtt, 4),
                    "Std_RTT_ms": round(std_rtt, 4),
                    "Median_RTT_ms": round(median_rtt, 4),

                    "P50_CI95_Lower_ms": round(p50_ci_low, 4),
                    "P50_CI95_Upper_ms": round(p50_ci_high, 4),
                    "P95_CI95_Lower_ms": round(p95_ci_low, 4),
                    "P95_CI95_Upper_ms": round(p95_ci_high, 4),
                    "P99_CI95_Lower_ms": round(p99_ci_low, 4),
                    "P99_CI95_Upper_ms": round(p99_ci_high, 4),
                })

            except Exception as e:
                print(f"Error: {lib} - Test {test_id} could not be processed: {e}")

    return pd.DataFrame(results)


# ==============================
# RUN
# ==============================

report = analyze_logs()
report.to_csv("final_performance_report.csv", index=False)

print("Analiz tamamlandı.")