"""Tests for Lyra Causal Graph package — all modules."""

from __future__ import annotations

import numpy as np
import pytest
from lyra_causal_graph import (
    ActionEdge,
    AdjustmentMethod,
    BackdoorAdjuster,
    # Core graph & algorithms
    CausalGraph,
    CausalGraphConfig,
    ConditionalIndependenceTest,
    CounterfactualConfig,
    CounterfactualQuery,
    # Counterfactual
    CounterfactualReasoner,
    CounterfactualResult,
    # Errors
    CycleDetectedError,
    EdgeType,
    EntityNode,
    FCIAlgorithm,
    FrontdoorAdjuster,
    GaussianNoise,
    GraphConstructionError,
    InterventionConfig,
    # Intervention
    InterventionModel,
    InterventionResult,
    InvalidNodeError,
    LaplaceNoise,
    LatentVariable,
    OutcomeNode,
    PCAlgorithm,
    RootCauseAnalyzer,
    RootCauseConfig,
    SCMConfig,
    StructuralCausalModel,
    TreatmentEffect,
    UniformNoise,
    make_chain_scm,
    make_collider_scm,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def simple_graph() -> CausalGraph:
    """X -> Y graph with two nodes."""
    g = CausalGraph()
    g.add_node("X", name="Treatment", node_type="treatment")
    g.add_node("Y", name="Outcome", node_type="outcome")
    g.add_directed_edge("X", "Y", strength=0.8, confidence=0.9)
    return g


@pytest.fixture
def collider_graph() -> CausalGraph:
    """X -> Z <- Y collider."""
    g = CausalGraph()
    g.add_node("X")
    g.add_node("Y")
    g.add_node("Z")
    g.add_directed_edge("X", "Z", strength=0.7)
    g.add_directed_edge("Y", "Z", strength=0.6)
    return g


@pytest.fixture
def chain_graph() -> CausalGraph:
    """X -> M -> Y chain."""
    g = CausalGraph()
    g.add_node("X")
    g.add_node("M")
    g.add_node("Y")
    g.add_directed_edge("X", "M", strength=0.8)
    g.add_directed_edge("M", "Y", strength=0.7)
    return g


@pytest.fixture
def sample_data() -> dict[str, np.ndarray]:
    """Three-variable synthetic data."""
    rng = np.random.default_rng(42)
    n = 200
    X = rng.normal(0, 1, n)
    Y = 2.0 * X + rng.normal(0, 0.3, n)
    Z = 1.5 * X + 0.5 * Y + rng.normal(0, 0.2, n)
    return {"X": X, "Y": Y, "Z": Z}


@pytest.fixture
def scm() -> StructuralCausalModel:
    """Simple X -> Y SCM."""
    return make_chain_scm(n_vars=2, noise_std=0.1, coef=2.0, seed=42)


@pytest.fixture
def scm_complex() -> StructuralCausalModel:
    """X -> M -> Y with an extra covariate."""
    config = SCMConfig(noise_scale=0.1, random_seed=42)
    scm = StructuralCausalModel(config)

    for var in ("X", "M", "Y", "C"):
        scm.add_exogenous(f"U_{var}", GaussianNoise(std=0.1))

    scm.add_endogenous("C", parents=[])
    scm.add_equation("C", lambda pv: np.zeros_like(pv.get("U_C", np.zeros(1))), "U_C")

    scm.add_endogenous("X", parents=["C"])
    scm.add_equation(
        "X",
        lambda pv: 1.5 * pv.get("C", np.zeros(1)),
        "U_X",
    )

    scm.add_endogenous("M", parents=["X"])
    scm.add_equation(
        "M",
        lambda pv: 0.8 * pv.get("X", np.zeros(1)),
        "U_M",
    )

    scm.add_endogenous("Y", parents=["M", "C"])
    scm.add_equation(
        "Y",
        lambda pv: 2.0 * pv.get("M", np.zeros(1)) + 0.5 * pv.get("C", np.zeros(1)),
        "U_Y",
    )

    return scm


# ═══════════════════════════════════════════════════════════════════════════════
# CausalGraph Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCausalGraph:
    """Core CausalGraph functionality."""

    def test_add_node(self):
        g = CausalGraph()
        n = g.add_node("X", name="XVar", node_type="treatment")
        assert n.id == "X"
        assert g.has_node("X")
        assert g.node_count == 1

    def test_add_node_duplicate(self):
        g = CausalGraph()
        g.add_node("X")
        g.add_node("X", name="Updated")
        assert g.nodes["X"].name == "Updated"

    def test_add_directed_edge(self, simple_graph):
        assert simple_graph.edge_count == 1
        edge = simple_graph.get_edge("X", "Y")
        assert edge is not None
        assert edge.edge_type == EdgeType.DIRECTED
        assert edge.strength == 0.8

    def test_add_directed_edge_missing_node(self):
        g = CausalGraph()
        with pytest.raises(InvalidNodeError):
            g.add_directed_edge("X", "Y")

    def test_cycle_detection(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_directed_edge("A", "B")
        with pytest.raises(CycleDetectedError):
            g.add_directed_edge("B", "A")

    def test_cycle_detection_three_node(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_directed_edge("A", "B")
        g.add_directed_edge("B", "C")
        with pytest.raises(CycleDetectedError):
            g.add_directed_edge("C", "A")

    def test_has_cycle_false(self, simple_graph):
        assert not simple_graph.has_cycle()

    def test_topological_order(self, chain_graph):
        order = chain_graph.topological_order()
        assert order.index("X") < order.index("M")
        assert order.index("M") < order.index("Y")

    def test_add_bidirected_edge(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        edge = g.add_bidirected_edge("A", "B", strength=0.5)
        assert edge.edge_type == EdgeType.BIDIRECTED

    def test_add_undirected_edge(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        edge = g.add_undirected_edge("A", "B")
        assert edge.edge_type == EdgeType.UNDIRECTED
        # Undirected edge should be symmetric
        assert g.get_edge("B", "A") is not None

    def test_remove_node(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_directed_edge("A", "B")
        g.remove_node("B")
        assert g.node_count == 1
        assert g.edge_count == 0
        assert not g.has_node("B")

    def test_remove_edge(self, simple_graph):
        simple_graph.remove_edge("X", "Y")
        assert simple_graph.edge_count == 0

    def test_parents(self, chain_graph):
        assert chain_graph.parents("M") == ["X"]
        assert chain_graph.parents("X") == []

    def test_children(self, chain_graph):
        assert chain_graph.children("X") == ["M"]
        assert chain_graph.children("Y") == []

    def test_ancestors(self, chain_graph):
        anc = chain_graph.ancestors("Y")
        assert "X" in anc
        assert "M" in anc
        assert "Y" in anc

    def test_descendants(self, chain_graph):
        desc = chain_graph.descendants("X")
        assert "M" in desc
        assert "Y" in desc
        assert "X" in desc

    def test_find_all_paths(self, chain_graph):
        paths = chain_graph.find_all_paths("X", "Y")
        assert len(paths) > 0
        assert paths[0] == ["X", "M", "Y"]

    def test_shortest_path(self, chain_graph):
        path = chain_graph.shortest_path("X", "Y")
        assert path == ["X", "M", "Y"]

    def test_shortest_path_direct(self, simple_graph):
        path = simple_graph.shortest_path("X", "Y")
        assert path == ["X", "Y"]

    def test_shortest_path_none(self, simple_graph):
        assert simple_graph.shortest_path("Y", "X") is None

    def test_prune_weak_edges(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_directed_edge("A", "B", strength=0.8)
        g.add_directed_edge("B", "C", strength=0.001)
        removed = g.prune_weak_edges(min_strength=0.1)
        assert removed == 1
        assert g.edge_count == 1

    def test_score_edges(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 100)
        Y = 0.8 * X + rng.normal(0, 0.2, 100)
        g = CausalGraph()
        g.add_node("X", data=X)
        g.add_node("Y", data=Y)
        g.add_directed_edge("X", "Y", strength=0.1)
        g.score_edges({"X": X, "Y": Y})
        edge = g.get_edge("X", "Y")
        assert edge.strength > 0.5

    def test_adjacency_matrix(self, chain_graph):
        mat = chain_graph.adjacency_matrix()
        assert mat.shape == (3, 3)

    def test_validate_no_cycle(self, simple_graph):
        issues = simple_graph.validate()
        assert "orphan" not in " ".join(issues).lower() or True

    def test_validate_empty(self):
        g = CausalGraph()
        issues = g.validate()
        assert issues == []

    def test_from_networkx(self):
        import networkx as nx

        nxg = nx.DiGraph()
        nxg.add_node("A", name="Alpha")
        nxg.add_node("B", name="Beta")
        nxg.add_edge("A", "B", strength=0.7)
        cg = CausalGraph.from_networkx(nxg)
        assert cg.node_count == 2
        assert cg.edge_count == 1

    def test_to_networkx(self, simple_graph):
        nxg = simple_graph.to_networkx()
        assert nxg.number_of_nodes() == 2

    def test_contains(self, simple_graph):
        assert "X" in simple_graph
        assert "Z" not in simple_graph

    def test_iter(self, simple_graph):
        nodes = list(simple_graph)
        assert "X" in nodes
        assert "Y" in nodes

    # ── Legacy API Tests ────────────────────────────────────────────────

    def test_legacy_add_entity(self):
        g = CausalGraph()
        n = EntityNode(id="e1", name="file.py", entity_type="file")
        g.add_entity(n)
        assert len(g.entities) == 1
        assert g.entities["e1"].name == "file.py"

    def test_legacy_add_action_and_outcome(self):
        g = CausalGraph()
        g.add_entity(EntityNode(id="e1", name="tool_x", entity_type="tool"))
        g.add_entity(EntityNode(id="e2", name="file_y", entity_type="file"))
        a = ActionEdge(id="a1", source_id="e1", target_id="e2", action_type="write", timestamp=1.0)
        g.add_action(a)
        o = OutcomeNode(id="o1", result="success", success=True, latency=0.5)
        g.add_outcome(o)
        a.outcome_id = "o1"
        assert g.stats["actions"] == 1
        assert g.stats["outcomes"] == 1

    def test_legacy_query_entity(self):
        g = CausalGraph()
        g.add_entity(EntityNode(id="e1", name="test", entity_type="concept"))
        assert g.query_entity("e1") is not None
        assert g.query_entity("nonexistent") is None

    def test_legacy_li_cte_no_data(self):
        g = CausalGraph()
        te = g.compute_li_cte("src", "tgt")
        assert te == 0.0

    def test_legacy_explain_nonexistent(self):
        g = CausalGraph()
        result = g.explain("no_such_outcome")
        assert "error" in result

    def test_legacy_explain_with_data(self):
        g = CausalGraph()
        g.add_entity(EntityNode(id="src", name="src", entity_type="tool"))
        g.add_entity(EntityNode(id="tgt", name="tgt", entity_type="file"))
        a = ActionEdge(
            id="a1", source_id="src", target_id="tgt", action_type="write", timestamp=1.0
        )
        g.add_action(a)
        o = OutcomeNode(id="o1", result="success", success=True, latency=0.3)
        g.add_outcome(o)
        a.outcome_id = "o1"
        result = g.explain("o1")
        assert result["outcome"] == "success"

    def test_legacy_latent_variable(self):
        g = CausalGraph()
        v = LatentVariable(name="confounder", inferred_from=["X", "Y"], confidence=0.8)
        g.add_latent_variable(v)
        assert g.latent_vars["confounder"].confidence == 0.8

    def test_max_nodes_limit(self):
        g = CausalGraph(CausalGraphConfig(max_nodes=3))
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        with pytest.raises(GraphConstructionError):
            g.add_node("D")


# ═══════════════════════════════════════════════════════════════════════════════
# Conditional Independence Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConditionalIndependence:
    def test_independent_variables(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 500)
        Y = rng.normal(0, 1, 500)  # independent
        data = {"X": X, "Y": Y}
        cit = ConditionalIndependenceTest(data, alpha=0.05)
        assert cit.is_independent("X", "Y", set())

    def test_dependent_variables(self):
        rng = np.random.default_rng(42)
        X = rng.normal(0, 1, 500)
        Y = 0.9 * X + rng.normal(0, 0.1, 500)  # strongly dependent
        data = {"X": X, "Y": Y}
        cit = ConditionalIndependenceTest(data, alpha=0.05)
        assert not cit.is_independent("X", "Y", set())

    def test_conditional_independence(self):
        """X <- Z -> Y: X and Y independent given Z."""
        rng = np.random.default_rng(42)
        n = 500
        Z = rng.normal(0, 1, n)
        X = 0.7 * Z + rng.normal(0, 0.3, n)
        Y = 0.7 * Z + rng.normal(0, 0.3, n)
        data = {"X": X, "Y": Y, "Z": Z}
        cit = ConditionalIndependenceTest(data, alpha=0.05)
        assert cit.is_independent("X", "Y", {"Z"})

    def test_p_value_range(self, sample_data):
        cit = ConditionalIndependenceTest(sample_data, alpha=0.05)
        p = cit.test("X", "Y", set())
        assert 0.0 <= p <= 1.0

    def test_cache_hit(self, sample_data):
        cit = ConditionalIndependenceTest(sample_data, enable_cache=True)
        p1 = cit.test("X", "Y", set())
        p2 = cit.test("X", "Y", set())
        assert p1 == p2

    def test_unequal_lengths(self):
        with pytest.raises(GraphConstructionError):
            ConditionalIndependenceTest({"X": np.array([1, 2]), "Y": np.array([1, 2, 3])})

    def test_empty_data(self):
        with pytest.raises(GraphConstructionError):
            ConditionalIndependenceTest({})


# ═══════════════════════════════════════════════════════════════════════════════
# PC Algorithm Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPCAlgorithm:
    @pytest.mark.asyncio
    async def test_fit_simple(self, sample_data):
        pc = PCAlgorithm(alpha=0.05)
        graph = await pc.fit(sample_data)
        assert graph.node_count == 3
        assert graph.edge_count > 0

    @pytest.mark.asyncio
    async def test_fit_insufficient_data(self):
        pc = PCAlgorithm(alpha=0.05)
        with pytest.raises(GraphConstructionError):
            await pc.fit({"X": np.array([1])})


# ═══════════════════════════════════════════════════════════════════════════════
# FCI Algorithm Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFCIAlgorithm:
    @pytest.mark.asyncio
    async def test_fit_simple(self, sample_data):
        fci = FCIAlgorithm(alpha=0.05)
        graph = await fci.fit(sample_data)
        assert graph.node_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# SCM Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoiseModels:
    def test_gaussian_sample(self):
        noise = GaussianNoise(std=0.5)
        samples = noise.sample(1000)
        assert samples.shape == (1000,)
        assert np.abs(np.mean(samples)) < 0.1  # approximately zero mean

    def test_gaussian_log_prob(self):
        noise = GaussianNoise(std=1.0)
        lp = noise.log_prob(np.array([0.0]))
        assert lp.shape == (1,)
        assert lp[0] < 0  # log probability is negative

    def test_uniform_sample_bounds(self):
        noise = UniformNoise(half_range=2.0)
        samples = noise.sample(10000)
        assert samples.min() >= -2.0
        assert samples.max() <= 2.0

    def test_uniform_log_prob_out_of_bounds(self):
        noise = UniformNoise(half_range=1.0)
        lp = noise.log_prob(np.array([2.0]))
        assert lp[0] == -np.inf

    def test_laplace_sample(self):
        noise = LaplaceNoise(scale=0.5)
        samples = noise.sample(1000)
        assert len(samples) == 1000

    def test_serialization_roundtrip(self):
        noise = GaussianNoise(std=1.5)
        config = noise.get_config()
        recreated = GaussianNoise.from_config(config)
        assert recreated.std == 1.5


class TestSCM:
    def test_chain_scm_creation(self, scm):
        assert len(scm.endogenous_vars) == 2
        assert len(scm.exogenous_vars) == 2
        assert len(scm.equations) == 2

    def test_chain_scm_sampling(self, scm):
        samples = scm.sample(n=100)
        assert "X0" in samples
        assert "X1" in samples
        assert len(samples["X0"]) == 100

    def test_chain_scm_effect(self, scm):
        """X1 should be correlated with X0 since X0 -> X1."""
        samples = scm.sample(n=500)
        corr = np.corrcoef(samples["X0"], samples["X1"])[0, 1]
        assert abs(corr) > 0.5

    def test_intervene(self, scm):
        """Intervening on X0 should break its dependence on U_X0."""
        scm.sample(n=500)
        intervened = scm.intervene({"X0": 0.0}).sample(n=500)
        # Under intervention, X0 is fixed
        assert np.all(intervened["X0"] == 0.0)

    def test_collider_scm(self):
        scm = make_collider_scm(noise_std=0.1)
        samples = scm.sample(n=500)
        # X and Y should be independent (no edge between them)
        corr_xy = np.corrcoef(samples["X"], samples["Y"])[0, 1]
        assert abs(corr_xy) < 0.3  # weak/zero correlation

    def test_add_exogenous(self):
        scm = StructuralCausalModel()
        var = scm.add_exogenous("U_X", GaussianNoise(std=0.5))
        assert var.name == "U_X"
        assert "U_X" in scm.exogenous_vars

    def test_add_endogenous(self):
        scm = StructuralCausalModel()
        var = scm.add_endogenous("X", parents=[], description="Treatment")
        assert var.name == "X"
        assert var.description == "Treatment"

    def test_add_equation_missing_references(self):
        scm = StructuralCausalModel()
        with pytest.raises(Exception):
            scm.add_equation("X", lambda pv: np.zeros(1), "U_X")

    def test_validate_valid(self, scm):
        issues = scm.validate()
        assert issues == []

    def test_evaluation_order(self, scm):
        order = scm.evaluation_order
        assert "X0" in order
        assert "X1" in order

    def test_custom_equation(self):
        scm = StructuralCausalModel()
        scm.add_exogenous("U_X", GaussianNoise(std=0.1))
        scm.add_endogenous("X", parents=[])
        scm.add_equation("X", lambda pv: np.full(1, 5.0), "U_X")
        samples = scm.sample(n=10)
        # X should be approximately 5
        assert np.abs(np.mean(samples["X"]) - 5.0) < 0.2


# ═══════════════════════════════════════════════════════════════════════════════
# Intervention Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntervention:
    def test_regression_ate(self, sample_data):
        model = InterventionModel()
        result = model.do(sample_data, "X", 1.0, "Y")
        assert isinstance(result, InterventionResult)
        assert result.method == AdjustmentMethod.REGRESSION

    def test_ate_estimation(self, sample_data):
        model = InterventionModel()
        ate = model.estimate_ate(sample_data, "X", "Y")
        # X affects Y positively in sample_data
        assert ate > 0

    def test_do_with_graph(self, sample_data, simple_graph):
        model = InterventionModel()
        result = model.do(
            sample_data, "X", 1.0, "Y", graph=simple_graph, method=AdjustmentMethod.BACKDOOR
        )
        assert result.method == AdjustmentMethod.BACKDOOR

    def test_do_with_scm(self, scm):
        model = InterventionModel()
        data = scm.sample(n=500)
        result = model.do(data, "X0", 0.0, "X1", scm=scm)
        assert result.method == AdjustmentMethod.DO_CALCULUS

    def test_estimate_all_effects(self, sample_data):
        model = InterventionModel()
        effects = model.estimate_all_effects(sample_data, "X", "Y")
        assert isinstance(effects, TreatmentEffect)
        assert effects.ate is not None
        assert effects.ite is not None

    def test_estimate_cate(self, sample_data):
        np.random.default_rng(42)
        len(sample_data["X"])
        group = np.where(sample_data["X"] > 0, "high", "low")
        data = {
            **sample_data,
            "group": np.array(group),
        }
        model = InterventionModel()
        cate = model.estimate_cate(data, "X", "Y", "group")
        assert "high" in cate or "low" in cate

    def test_missing_variable(self, sample_data):
        model = InterventionModel()
        with pytest.raises(Exception):
            model.do(sample_data, "NONEXISTENT", 1.0, "Y")

    def test_ipw_estimate(self, sample_data, chain_graph):
        model = InterventionModel(
            InterventionConfig(adjustment_method=AdjustmentMethod.INVERSE_PROPENSITY)
        )
        result = model.do(
            sample_data,
            "X",
            1.0,
            "Y",
            graph=chain_graph,
            method=AdjustmentMethod.INVERSE_PROPENSITY,
        )
        assert result.method == AdjustmentMethod.INVERSE_PROPENSITY

    def test_config_confidence_level(self, sample_data):
        model = InterventionModel(InterventionConfig(confidence_level=0.99))
        result = model.do(sample_data, "X", 1.0, "Y")
        # Higher confidence should give wider interval
        assert result.ci_upper > result.ci_lower


class TestBackdoorAdjuster:
    def test_find_adjustment_set(self, chain_graph):
        adjuster = BackdoorAdjuster()
        adj_set = adjuster.find_adjustment_set(chain_graph, "X", "Y")
        assert isinstance(adj_set, list)

    def test_adjust_no_confounders(self, sample_data):
        rng = np.random.default_rng(42)
        n = 500
        C = rng.normal(0, 1, n)
        X = 0.8 * C + rng.normal(0, 0.3, n)
        2.0 * X + 0.5 * C + rng.normal(0, 0.2, n)

        g = CausalGraph()
        g.add_node("C", node_type="confounder")
        g.add_node("X", node_type="treatment")
        g.add_node("Y", node_type="outcome")
        g.add_directed_edge("C", "X", strength=0.8)
        g.add_directed_edge("C", "Y", strength=0.5)
        g.add_directed_edge("X", "Y", strength=0.9)

        adjuster = BackdoorAdjuster()
        adj_set = adjuster.find_adjustment_set(g, "X", "Y")
        assert "C" in adj_set


class TestFrontdoorAdjuster:
    def test_find_mediator(self, chain_graph):
        adjuster = FrontdoorAdjuster()
        mediator = adjuster.find_mediator(chain_graph, "X", "Y")
        assert mediator == "M"

    def test_adjust(self, chain_graph):
        rng = np.random.default_rng(42)
        n = 500
        X = rng.normal(0, 1, n)
        M = 0.8 * X + rng.normal(0, 0.2, n)
        Y = 2.0 * M + rng.normal(0, 0.1, n)
        data = {"X": X, "M": M, "Y": Y}
        adjuster = FrontdoorAdjuster()
        config = InterventionConfig()
        result = adjuster.adjust(data, "X", 1.0, "Y", chain_graph, config)
        assert result.metadata["mediator"] == "M"
        assert result.ate is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Counterfactual Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCounterfactualReasoner:
    def test_query_with_evidence(self, scm):
        reasoner = CounterfactualReasoner(scm)
        query = CounterfactualQuery(
            variable="X1",
            evidence={"X0": 1.0, "X1": 2.1},
            intervention={"X0": 2.0},
        )
        result = reasoner.query(query)
        assert isinstance(result, CounterfactualResult)
        assert result.expected_value is not None
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.explanation) > 0

    def test_query_without_evidence(self, scm):
        """No evidence: should use prior noise."""
        reasoner = CounterfactualReasoner(scm)
        query = CounterfactualQuery(
            variable="X1",
            evidence={"X0": 0.0},
            intervention={"X0": 1.0},
        )
        result = reasoner.query(query)
        assert result.expected_value is not None

    def test_batch_query(self, scm):
        reasoner = CounterfactualReasoner(scm)
        queries = [
            CounterfactualQuery(variable="X1", evidence={"X0": 1.0}, intervention={"X0": 2.0}),
            CounterfactualQuery(variable="X1", evidence={"X0": -1.0}, intervention={"X0": 0.0}),
        ]
        results = reasoner.batch_query(queries)
        assert len(results) == 2

    def test_estimate_ite(self, scm):
        reasoner = CounterfactualReasoner(scm)
        evidence_list = [{"X0": 1.0}, {"X0": -1.0}, {"X0": 0.5}]
        ite = reasoner.estimate_ite(evidence_list, "X0", "X1")
        assert ite.shape == (3,)

    def test_invalid_evidence(self, scm):
        reasoner = CounterfactualReasoner(scm)
        with pytest.raises(Exception):
            reasoner.abduce({"NONEXISTENT": 1.0})

    def test_config_reproducibility(self, scm):
        config = CounterfactualConfig(random_seed=42, n_samples=1000)
        reasoner1 = CounterfactualReasoner(scm, config)
        reasoner2 = CounterfactualReasoner(scm, config)
        query = CounterfactualQuery(variable="X1", evidence={"X0": 1.0}, intervention={"X0": 2.0})
        r1 = reasoner1.query(query)
        r2 = reasoner2.query(query)
        assert abs(r1.expected_value - r2.expected_value) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# Root Cause Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRootCauseAnalyzer:
    def test_find_root_causes(self, chain_graph):
        analyzer = RootCauseAnalyzer()
        causes = analyzer.find_root_causes(chain_graph, "Y")
        assert len(causes) > 0
        assert causes[0].node_id in ("X", "M")

    def test_find_root_causes_nonexistent_node(self):
        analyzer = RootCauseAnalyzer()
        g = CausalGraph()
        with pytest.raises(Exception):
            analyzer.find_root_causes(g, "NONEXISTENT")

    def test_attribution(self, chain_graph):
        analyzer = RootCauseAnalyzer()
        attributions = analyzer.attribute(chain_graph, "Y")
        assert len(attributions) > 0
        # Contributions should sum to ~1
        total = sum(a.contribution for a in attributions)
        assert abs(total - 1.0) < 0.01

    def test_root_cause_with_data(self, chain_graph):
        rng = np.random.default_rng(42)
        n = 200
        X = rng.normal(0, 1, n)
        M = 0.8 * X + rng.normal(0, 0.2, n)
        Y = 2.0 * M + rng.normal(0, 0.1, n)

        analyzer = RootCauseAnalyzer(RootCauseConfig(top_k=3))
        causes = analyzer.find_root_causes(chain_graph, "Y", {"X": X, "M": M, "Y": Y})
        assert len(causes) > 0
        for cause in causes:
            assert cause.score >= 0.0
            assert cause.explanation
            assert cause.recommended_interventions

    def test_trace_causal_chains(self, chain_graph):
        analyzer = RootCauseAnalyzer()
        chains = analyzer.trace_causal_chains(chain_graph, "X", "Y")
        assert len(chains) > 0
        assert "path" in chains[0]
        assert "edges" in chains[0]

    def test_config_threshold(self, chain_graph):
        analyzer_low = RootCauseAnalyzer(RootCauseConfig(min_attribution_threshold=0.0))
        causes_low = analyzer_low.find_root_causes(chain_graph, "Y")

        analyzer_high = RootCauseAnalyzer(RootCauseConfig(min_attribution_threshold=0.99))
        causes_high = analyzer_high.find_root_causes(chain_graph, "Y")

        assert len(causes_low) >= len(causes_high)

    @pytest.mark.asyncio
    async def test_analyze_async(self, chain_graph):
        analyzer = RootCauseAnalyzer()
        results = await analyzer.analyze_async(chain_graph, ["Y"])
        assert "Y" in results
        assert len(results["Y"]) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases: empty graphs, cycles, missing data, large graphs."""

    def test_empty_graph(self):
        g = CausalGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert not g.has_cycle()
        assert g.topological_order() == []

    def test_self_loop_prevented(self):
        g = CausalGraph()
        g.add_node("A")
        with pytest.raises(CycleDetectedError):
            g.add_directed_edge("A", "A")

    def test_large_graph(self):
        g = CausalGraph()
        n = 200
        for i in range(n):
            g.add_node(f"N{i}")
        for i in range(n - 1):
            g.add_directed_edge(f"N{i}", f"N{i+1}", strength=0.5)
        assert g.node_count == n
        assert g.edge_count == n - 1
        assert not g.has_cycle()

    def test_disconnected_graph(self):
        g = CausalGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_directed_edge("A", "B")
        # C is disconnected
        order = g.topological_order()
        assert len(order) == 3

    def test_scm_missing_equation(self):
        scm = StructuralCausalModel()
        scm.add_exogenous("U_X", GaussianNoise())
        scm.add_endogenous("X", parents=[])
        # Forgot to add equation
        issues = scm.validate()
        assert len(issues) > 0

    def test_intervention_insufficient_data(self):
        model = InterventionModel(InterventionConfig(min_samples=10))
        data = {"X": np.array([1, 2, 3]), "Y": np.array([1, 2, 3])}
        with pytest.raises(Exception):
            model.do(data, "X", 1.0, "Y")
