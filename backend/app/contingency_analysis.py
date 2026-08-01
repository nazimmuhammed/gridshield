from cascade_simulation import simulate_line_failure
from grid_topology import load_ieee_grid, convert_to_networkx
import pandas as pd


def run_n1_contingency_analysis(net, G):
    """
    N-1 Contingency Analysis: tests EVERY single line failure independently
    to identify which ones cause cascading failures vs. which the grid
    safely absorbs. This is standard real-world grid planning practice
    (NERC/CERC reliability standards).
    """
    results = []
    all_line_indices = net.line.index.tolist()

    print(f"Running N-1 contingency analysis across {len(all_line_indices)} lines...")

    for line_idx in all_line_indices:
        try:
            failed_lines, _ = simulate_line_failure(net, G, failed_line_idx=line_idx)
            results.append({
                "initial_failure": line_idx,
                "total_cascade_failures": len(failed_lines),
                "cascaded": len(failed_lines) > 1,
                "all_failed_lines": failed_lines,
            })
        except Exception as e:
            results.append({
                "initial_failure": line_idx,
                "total_cascade_failures": None,
                "cascaded": "BLACKOUT",
                "all_failed_lines": None,
            })

    return pd.DataFrame(results)


if __name__ == "__main__":
    net = load_ieee_grid()
    G = convert_to_networkx(net)

    df_results = run_n1_contingency_analysis(net, G)

    print("\n" + "=" * 60)
    print("N-1 CONTINGENCY ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total lines tested: {len(df_results)}")
    print(f"Lines causing cascading failures: {df_results['cascaded'].sum()}")
    print(f"\nMost dangerous single points of failure (most cascade damage):")
    print(df_results.sort_values("total_cascade_failures", ascending=False).head(10))

    df_results.to_csv("data/n1_contingency_results.csv", index=False)
    print("\nSaved full results to data/n1_contingency_results.csv")