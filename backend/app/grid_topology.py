import pandapower as pp
import pandapower.networks as pn
import networkx as nx

def load_ieee_grid():
    """
    Loads the IEEE 30-bus standard test system - a real, published grid
    topology used in actual academic and utility cascade-failure research.
    """
    net = pn.case30()
    print(f"Loaded IEEE 30-bus test system")
    print(f"Number of buses (nodes): {len(net.bus)}")
    print(f"Number of lines (edges): {len(net.line)}")
    print(f"Number of generators: {len(net.gen)}")
    print(f"Number of loads: {len(net.load)}")
    return net


def convert_to_networkx(net):
    """
    Converts the pandapower network into a NetworkX graph so we can run
    our own cascade-failure simulation logic on it.
    """
    G = nx.Graph()

    for idx, bus in net.bus.iterrows():
        G.add_node(idx, name=bus["name"], vn_kv=bus["vn_kv"])

    for idx, line in net.line.iterrows():
        G.add_edge(
            line["from_bus"],
            line["to_bus"],
            length_km=line["length_km"],
            max_i_ka=line["max_i_ka"],
        )

    print(f"\nConverted to NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


if __name__ == "__main__":
    net = load_ieee_grid()
    G = convert_to_networkx(net)

    print("\nSample node data:")
    print(list(G.nodes(data=True))[:3])
    print("\nSample edge data:")
    print(list(G.edges(data=True))[:3])