"""Tests for SwarmTopology."""

from __future__ import annotations

import pytest

from lyra_cli.swarm.topology import (
    SwarmTopology,
    TopologyNode,
    TopologyConfig,
    TopologyType,
    RoutingEntry,
)


def test_add_and_remove_node() -> None:
    """Adding and removing nodes should update the topology."""
    topo = SwarmTopology()
    node = TopologyNode(node_id="n1", node_type="worker")
    topo.add_node(node)
    assert "n1" in topo.nodes

    topo.remove_node("n1")
    assert "n1" not in topo.nodes


def test_mesh_topology_connects_all() -> None:
    """Mesh topology should connect every node to every other."""
    topo = SwarmTopology(TopologyConfig(topology_type=TopologyType.MESH))
    topo.add_node(TopologyNode("a"))
    topo.add_node(TopologyNode("b"))
    topo.add_node(TopologyNode("c"))
    topo.build_initial_connections()

    assert len(topo.get_neighbors("a")) == 2
    assert len(topo.get_neighbors("b")) == 2
    assert len(topo.get_neighbors("c")) == 2


def test_star_topology_connects_to_center() -> None:
    """Star topology should connect all nodes through the center."""
    topo = SwarmTopology(TopologyConfig(topology_type=TopologyType.STAR))
    topo.add_node(TopologyNode("center"))
    topo.add_node(TopologyNode("leaf1"))
    topo.add_node(TopologyNode("leaf2"))
    topo.build_initial_connections()

    assert "center" in topo.get_neighbors("leaf1")
    assert "center" in topo.get_neighbors("leaf2")
    assert "leaf2" in topo.get_neighbors("center")


def test_discover_route_finds_path() -> None:
    """discover_route should find a valid path between nodes."""
    topo = SwarmTopology(TopologyConfig(topology_type=TopologyType.MESH))
    topo.add_node(TopologyNode("a"))
    topo.add_node(TopologyNode("b"))
    topo.add_node(TopologyNode("c"))
    topo.build_initial_connections()

    path = topo.discover_route("a", "c")
    assert len(path) >= 2
    assert path[0] == "a"
    assert path[-1] == "c"


def test_validate_topology_detects_dag_cycle() -> None:
    """Validation should detect cycles in a DAG topology."""
    topo = SwarmTopology(TopologyConfig(
        topology_type=TopologyType.DAG,
        dag_dependency_graph={
            "a": ["b"],
            "b": ["c"],
            "c": ["a"],
        },
    ))
    topo.add_node(TopologyNode("a"))
    topo.add_node(TopologyNode("b"))
    topo.add_node(TopologyNode("c"))
    topo.build_initial_connections()

    errors = topo.validate_topology()
    assert any("cycle" in e.lower() for e in errors)
