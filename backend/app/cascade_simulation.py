import networkx as nx
import pandapower as pp
import pandapower.networks as pn
from grid_topology import load_ieee_grid, convert_to_networkx
import copy


def simulate_line_failure(net, G, failed_line_idx, max_iterations=10):
    """
    Simulates a cascading failure starting from one failed transmission line.

    Logic:
    1. Remove the failed line from the network
    2. Re-run power flow to see how load redistributes
    3. Check if any OTHER line now exceeds its capacity (max_i_ka)
    4. If yes, that line fails too -> repeat
    5. Stop when no new failures occur, or max_iterations reached

    This directly mirrors what happened in real cascading blackouts:
    one line trips -> load reroutes -> overloads another line -> repeats.
    """
    net_sim = copy.deepcopy(net)
    failed_lines = [failed_line_idx]

    print(f"\n{'='*60}")
    print(f"SIMULATING CASCADE: starting failure at line {failed_line_idx}")
    print(f"{'='*60}")

    for iteration in range(max_iterations):
        # Take the line out of service
        net_sim.line.loc[failed_lines, "in_service"] = False

        try:
            pp.runpp(net_sim)  # run real AC power flow calculation
        except Exception as e:
            print(f"Power flow did NOT converge at iteration {iteration} "
                  f"-> this itself indicates a full blackout / grid collapse.")
            break

        # Check line loading percentages after redistribution
        loading = net_sim.res_line["loading_percent"]
        overloaded = loading[
            (loading > 100) & (~net_sim.line.index.isin(failed_lines))
        ]

        if overloaded.empty:
            print(f"Iteration {iteration}: cascade STOPPED. "
                  f"No further lines overloaded. Total failed lines: {len(failed_lines)}")
            break

        new_failures = list(overloaded.index)
        print(f"Iteration {iteration}: {len(new_failures)} new line(s) overloaded "
              f"-> {new_failures}")
        failed_lines.extend(new_failures)

    return failed_lines, net_sim


if __name__ == "__main__":
    net = load_ieee_grid()
    G = convert_to_networkx(net)

    # Test: simulate failure starting at line 0
    failed_lines, net_sim = simulate_line_failure(net, G, failed_line_idx=0)

    print(f"\nFinal result: {len(failed_lines)} total line(s) failed in cascade")
    print(f"Failed line indices: {failed_lines}")