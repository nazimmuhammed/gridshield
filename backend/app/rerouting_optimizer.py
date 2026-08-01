import copy
import pandapower as pp
import pandas as pd
from grid_topology import load_ieee_grid


def evaluate_without_rerouting(net, failed_line_idx):
    """
    Baseline: what happens with a plain power flow (no corrective action)
    after a line fails. This is your 'do nothing' comparison point.
    """
    net_sim = copy.deepcopy(net)
    net_sim.line.loc[failed_line_idx, "in_service"] = False

    try:
        pp.runpp(net_sim, numba=False)
        loading = net_sim.res_line["loading_percent"]
        return {
            "max_loading_pct": loading.max(),
            "lines_overloaded": int((loading > 100).sum()),
            "status": "OVERLOAD" if (loading > 100).any() else "SAFE",
        }
    except Exception:
        return {"max_loading_pct": None, "lines_overloaded": None, "status": "BLACKOUT"}


def compute_rerouting_plan(net, failed_line_idx):
    """
    Stage 5 - Rerouting Optimization.

    Uses Optimal Power Flow (OPF) to compute the best generator redispatch
    that keeps every line within its safe capacity after a failure, while
    minimizing total generation cost. This is a real constrained
    optimization problem (the pandapower solver uses interior-point
    methods under the hood) - the same class of problem real grid
    operators solve for contingency management.

    Objective: minimize generation cost
    Constraints: line loading <= 100% capacity, generator limits, voltage limits
    """
    net_sim = copy.deepcopy(net)
    net_sim.line.loc[failed_line_idx, "in_service"] = False

    try:
        pp.runopp(net_sim, numba=False)
        loading = net_sim.res_line["loading_percent"]
        return {
            "max_loading_pct": loading.max(),
            "lines_overloaded": int((loading > 100).sum()),
            "total_cost": net_sim.res_cost,
            "status": "REROUTED_SAFE" if (loading <= 100).all() else "INFEASIBLE",
            "generator_dispatch": net_sim.res_gen["p_mw"].to_dict(),
        }
    except Exception as e:
        return {
            "max_loading_pct": None, "lines_overloaded": None,
            "total_cost": None, "status": "NO_FEASIBLE_REROUTE",
            "generator_dispatch": None,
        }


def compare_lines(net, line_indices):
    """
    Runs the before/after comparison across multiple failure scenarios -
    this produces the table for your resume metric: how many previously
    dangerous failures become 'safe' after rerouting.
    """
    results = []
    for idx in line_indices:
        baseline = evaluate_without_rerouting(net, idx)
        rerouted = compute_rerouting_plan(net, idx)
        results.append({
            "failed_line": idx,
            "baseline_status": baseline["status"],
            "baseline_max_loading": baseline["max_loading_pct"],
            "rerouted_status": rerouted["status"],
            "rerouted_max_loading": rerouted["max_loading_pct"],
            "rerouting_cost": rerouted["total_cost"],
            "prevented_overload": (
                baseline["status"] in ("OVERLOAD", "BLACKOUT")
                and rerouted["status"] == "REROUTED_SAFE"
            ),
        })
    return pd.DataFrame(results)


if __name__ == "__main__":
    net = load_ieee_grid()

    # Test on the most dangerous lines identified in your N-1 analysis
    test_lines = [27, 15, 40, 29, 30, 21, 35, 5, 9, 0]

    print("Computing rerouting plans for the 10 most critical lines...\n")
    df = compare_lines(net, test_lines)

    print("=" * 70)
    print("REROUTING OPTIMIZATION RESULTS")
    print("=" * 70)
    print(df.to_string(index=False))

    prevented = df["prevented_overload"].sum()
    total = len(df)
    print(f"\nOverloads prevented via rerouting: {prevented}/{total} "
          f"({prevented/total*100:.1f}%)")

    df.to_csv("data/rerouting_results.csv", index=False)
    print("Saved to data/rerouting_results.csv")