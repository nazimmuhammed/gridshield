import itertools
import copy
import pandapower as pp
import pandas as pd
from grid_topology import load_ieee_grid, convert_to_networkx


def simulate_dual_line_failure(net, line_idx_1, line_idx_2, max_iterations=10):
    """
    N-2 Contingency Analysis: simulates TWO lines failing simultaneously.
    This catches compound-failure risks that N-1 analysis misses -
    e.g., two lines that are each individually safe to lose, but together
    cause a much worse cascade than either alone (a real, documented
    grid vulnerability pattern).
    """
    net_sim = copy.deepcopy(net)
    failed_lines = [line_idx_1, line_idx_2]

    for iteration in range(max_iterations):
        net_sim.line.loc[failed_lines, "in_service"] = False

        try:
            pp.runpp(net_sim, numba=False)
        except Exception:
            return failed_lines, "BLACKOUT"

        loading = net_sim.res_line["loading_percent"]
        overloaded = loading[
            (loading > 100) & (~net_sim.line.index.isin(failed_lines))
        ]

        if overloaded.empty:
            return failed_lines, "CONTAINED"

        failed_lines.extend(list(overloaded.index))

    return failed_lines, "MAX_ITERATIONS_REACHED"


def run_n2_contingency_analysis(net):
    """
    Tests every PAIR of lines failing together. With 41 lines, this is
    C(41,2) = 820 combinations - more expensive than N-1 but still
    computationally feasible for a system this size.
    """
    all_lines = net.line.index.tolist()
    pairs = list(itertools.combinations(all_lines, 2))

    print(f"Running N-2 contingency analysis across {len(pairs)} line pairs...")
    print("(This will take longer than N-1 - grab a coffee)\n")

    results = []
    for i, (l1, l2) in enumerate(pairs):
        failed_lines, status = simulate_dual_line_failure(net, l1, l2)
        results.append({
            "line_pair": (l1, l2),
            "total_cascade_failures": len(failed_lines) if failed_lines else None,
            "status": status,
        })
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(pairs)} pairs tested...")

    return pd.DataFrame(results)


if __name__ == "__main__":
    net = load_ieee_grid()

    df_n2 = run_n2_contingency_analysis(net)

    print("\n" + "=" * 60)
    print("N-2 CONTINGENCY ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total pairs tested: {len(df_n2)}")
    print(f"Pairs causing blackout (non-convergence): {(df_n2['status'] == 'BLACKOUT').sum()}")
    print(f"Pairs contained: {(df_n2['status'] == 'CONTAINED').sum()}")

    print(f"\nMost dangerous line PAIRS (by cascade size):")
    print(df_n2.sort_values("total_cascade_failures", ascending=False).head(10))

    df_n2.to_csv("data/n2_contingency_results.csv", index=False)
    print("\nSaved full results to data/n2_contingency_results.csv")