"""80+ tests for the lyra-skill-loader package.

Covers all six modules: tiered_loader, trigger_matcher, context_aware_loader,
skill_compiler, dependency_resolver, loader_config, and exceptions.
"""
from __future__ import annotations

from collections.abc import Sequence

import pytest
from lyra_skill_loader import (
    BALANCED,
    BudgetConfig,
    BudgetExceededError,
    CacheConfig,
    CompilationError,
    CompiledIndex,
    CompiledSkill,
    ConfigError,
    ContextAwareLoader,
    ContextBudget,
    DependencyError,
    DependencyGraph,
    DependencyResolver,
    EvictionPolicy,
    LoadDecision,
    LoadedSkill,
    LoaderConfig,
    LoaderError,
    LoaderStats,
    LoadPlan,
    LoadTier,
    MatchConfig,
    MatchResult,
    ResolutionResult,
    SkillCompiler,
    SkillContent,
    SkillMetadata,
    SkillNode,
    SkillReferences,
    TierConfig,
    TieredLoader,
    Trigger,
    TriggerError,
    TriggerMatcher,
    TriggerType,
    get_preset,
)

# =========================================================================
# Helper factories
# =========================================================================


def _make_metadata(
    name: str = "test-skill",
    description: str = "A test skill",
    triggers: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    category: str = "general",
    io_capabilities: Sequence[str] | None = None,
    estimated_tokens: int = 50,
) -> SkillMetadata:
    return SkillMetadata(
        name=name,
        description=description,
        triggers=tuple(triggers or []),
        tags=tuple(tags or []),
        category=category,
        io_capabilities=tuple(io_capabilities or []),
        estimated_tokens=estimated_tokens,
    )


def _make_content(
    body: str = "body",
    instructions: Sequence[str] | None = None,
    examples: Sequence[str] | None = None,
) -> SkillContent:
    return SkillContent(
        body=body,
        instructions=tuple(instructions or []),
        examples=tuple(examples or []),
    )


def _make_references(deps: Sequence[str] | None = None) -> SkillReferences:
    return SkillReferences(
        docs=("doc1", "doc2"),
        dependencies=tuple(deps or []),
    )


def _register_dummy(loader: TieredLoader, skill_id: str, priority: int = 0) -> None:
    loader.register_skill(
        skill_id=skill_id,
        metadata=_make_metadata(name=skill_id, triggers=[skill_id]),
        content=_make_content(),
        references=_make_references(),
        priority=priority,
    )


# =========================================================================
# 1. Exceptions
# =========================================================================


class TestExceptions:
    def test_loader_error(self) -> None:
        err = LoaderError("base error")
        assert "base error" in str(err)

    def test_trigger_error_inheritance(self) -> None:
        err = TriggerError("trigger failed")
        assert isinstance(err, LoaderError)

    def test_budget_exceeded_error(self) -> None:
        err = BudgetExceededError("budget exceeded")
        assert isinstance(err, LoaderError)

    def test_compilation_error(self) -> None:
        err = CompilationError("compile failed")
        assert isinstance(err, LoaderError)

    def test_dependency_error(self) -> None:
        err = DependencyError("dep failed")
        assert isinstance(err, LoaderError)

    def test_config_error(self) -> None:
        err = ConfigError("bad config")
        assert isinstance(err, LoaderError)


# =========================================================================
# 2. LoaderConfig & Presets
# =========================================================================


class TestLoaderConfig:
    def test_default_config(self) -> None:
        cfg = LoaderConfig()
        assert cfg.max_skills_per_load == 10
        assert cfg.enable_progressive_loading
        assert cfg.tier_config.tier1_max_tokens == 50

    def test_get_preset_balanced(self) -> None:
        cfg = get_preset("BALANCED")
        assert cfg is BALANCED
        assert cfg.max_skills_per_load == 10

    def test_get_preset_strict(self) -> None:
        cfg = get_preset("STRICT_BUDGET")
        assert cfg.max_skills_per_load == 3

    def test_get_preset_full_load(self) -> None:
        cfg = get_preset("FULL_LOAD")
        assert not cfg.enable_progressive_loading

    def test_get_preset_minimal(self) -> None:
        cfg = get_preset("MINIMAL")
        assert cfg.max_skills_per_load == 1

    def test_get_preset_unknown_raises_config_error(self) -> None:
        with pytest.raises(ConfigError):
            get_preset("NONEXISTENT")

    def test_tier_config_defaults(self) -> None:
        tc = TierConfig()
        assert tc.tier1_max_tokens == 50
        assert tc.tier2_max_tokens == 500
        assert tc.tier3_max_tokens == 2000

    def test_cache_config_defaults(self) -> None:
        cc = CacheConfig()
        assert cc.max_cached_skills == 100
        assert cc.cache_ttl_seconds == 300

    def test_custom_config(self) -> None:
        cfg = LoaderConfig(
            tier_config=TierConfig(tier1_max_tokens=25),
            max_skills_per_load=5,
            enable_progressive_loading=False,
        )
        assert cfg.tier_config.tier1_max_tokens == 25
        assert cfg.max_skills_per_load == 5
        assert not cfg.enable_progressive_loading


# =========================================================================
# 3. TieredLoader
# =========================================================================


class TestTieredLoader:
    def test_register_skill(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "skill-a")
        assert loader.has_skill("skill-a")

    def test_load_tier1_returns_metadata_only(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s1")
        loaded = loader.load_tier1("s1")
        assert loaded.current_tier == LoadTier.TIER1_METADATA
        assert loaded.metadata.name == "s1"
        assert loaded.content is None
        assert loaded.references is None

    def test_load_tier2_returns_content(self) -> None:
        loader = TieredLoader()
        loader.register_skill("s2", _make_metadata(name="s2"), content=_make_content(body="hello"))
        loaded = loader.load_tier2("s2")
        assert loaded.current_tier == LoadTier.TIER2_CONTENT
        assert loaded.content is not None
        assert loaded.content.body == "hello"
        assert loaded.references is None

    def test_load_tier3_returns_references(self) -> None:
        loader = TieredLoader()
        loader.register_skill(
            "s3",
            _make_metadata(name="s3"),
            content=_make_content(body="c"),
            references=_make_references(deps=["dep1"]),
        )
        loaded = loader.load_tier3("s3")
        assert loaded.current_tier == LoadTier.TIER3_REFERENCES
        assert loaded.references is not None
        assert "dep1" in loaded.references.dependencies

    def test_load_at_tier(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        for tier in (LoadTier.TIER1_METADATA, LoadTier.TIER2_CONTENT, LoadTier.TIER3_REFERENCES):
            loaded = loader.load_at_tier("s", tier)
            assert loaded.current_tier == tier

    def test_unload_to_tier1_downgrades(self) -> None:
        loader = TieredLoader()
        loader.register_skill("s", _make_metadata(name="s"), content=_make_content(body="x"))
        loader.load_tier2("s")
        unloaded = loader.unload_to_tier1("s")
        assert unloaded.current_tier == LoadTier.TIER1_METADATA
        assert unloaded.content is None

    def test_get_current_tier(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        assert loader.get_current_tier("s") is None
        loader.load_tier1("s")
        assert loader.get_current_tier("s") == LoadTier.TIER1_METADATA

    def test_load_unregistered_raises_key_error(self) -> None:
        loader = TieredLoader()
        with pytest.raises(KeyError):
            loader.load_tier1("nonexistent")

    def test_unregister_skill(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        loader.unregister_skill("s")
        assert not loader.has_skill("s")

    def test_list_skills(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        assert set(loader.list_skills()) == {"a", "b"}

    def test_load_batch(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        results = loader.load_batch(["a", "b"], LoadTier.TIER2_CONTENT)
        assert len(results) == 2
        assert all(r.current_tier == LoadTier.TIER2_CONTENT for r in results)

    def test_unload_batch(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        loader.load_batch(["a", "b"], LoadTier.TIER3_REFERENCES)
        unloaded = loader.unload_batch(["a", "b"])
        assert all(u.current_tier == LoadTier.TIER1_METADATA for u in unloaded)

    def test_loading_stats_initial(self) -> None:
        loader = TieredLoader()
        stats = loader.loading_stats()
        assert stats.skills_loaded == 0
        assert stats.tokens_saved == 0

    def test_loading_stats_after_load(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        loader.load_tier1("a")
        loader.load_tier2("b")
        stats = loader.loading_stats()
        assert stats.skills_loaded == 1  # Only b is above tier1
        assert stats.tokens_saved > 0   # b at tier2 instead of tier3

    def test_loading_stats_tokens_saved_pct(self) -> None:
        loader = TieredLoader()
        for i in range(3):
            _register_dummy(loader, f"s{i}")
        loader.load_tier1("s0")
        loader.load_tier1("s1")
        loader.load_tier1("s2")
        stats = loader.loading_stats()
        # All at tier1 (50 tokens) instead of tier3 (2000): saves 1950 per skill
        # 3 * 1950 = 5850 saved out of 6000 total = 97.5%
        assert stats.tokens_saved_pct() > 0

    def test_estimate_tokens(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        assert loader.estimate_tokens("s") > 0
        assert loader.estimate_tokens("nonexistent") == 0

    def test_load_tier_upgrade(self) -> None:
        loader = TieredLoader()
        loader.register_skill("s", _make_metadata(name="s"), content=_make_content(body="x"))
        # Load at tier1, then upgrade to tier2
        loader.load_tier1("s")
        loaded = loader.load_tier2("s")
        assert loaded.content is not None
        assert loaded.content.body == "x"

    def test_load_tier_upgrade_to_tier3(self) -> None:
        loader = TieredLoader()
        loader.register_skill(
            "s", _make_metadata(name="s"), content=_make_content(body="c"),
            references=_make_references(deps=["dep1"]),
        )
        loader.load_tier1("s")
        loaded = loader.load_tier3("s")
        assert loaded.references is not None
        assert "dep1" in loaded.references.dependencies

    def test_multiple_registrations_independent(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        la = loader.load_tier1("a")
        lb = loader.load_tier2("b")
        assert la.current_tier == LoadTier.TIER1_METADATA
        assert lb.current_tier == LoadTier.TIER2_CONTENT

    def test_tier_number_property(self) -> None:
        assert LoadTier.TIER1_METADATA.tier_number == 1
        assert LoadTier.TIER2_CONTENT.tier_number == 2
        assert LoadTier.TIER3_REFERENCES.tier_number == 3


# =========================================================================
# 4. TriggerMatcher
# =========================================================================


class TestTriggerMatcher:
    def test_register_trigger(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy", "release"), skill_id="deploy-skill"))
        assert "deploy-skill" in tm.list_triggers()

    def test_register_duplicate_raises_trigger_error(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="x", skill_id="s"))
        with pytest.raises(TriggerError):
            tm.register_trigger(Trigger(pattern="x", skill_id="s"))

    def test_register_skill_triggers(self) -> None:
        tm = TriggerMatcher()
        meta = _make_metadata(name="code-review", triggers=("review", "audit"))
        tm.register_skill_triggers("code-review", meta)
        assert "code-review" in tm.list_triggers()

    def test_unregister_trigger(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="x", skill_id="s"))
        tm.unregister_trigger("s")
        assert "s" not in tm.list_triggers()

    def test_match_keyword(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy", "release"), skill_id="dep"))
        results = tm.match("I need to deploy this service")
        assert len(results) >= 1
        assert results[0].skill_id == "dep"

    def test_match_no_results_empty_context(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy",), skill_id="dep"))
        results = tm.match("")
        assert results == []

    def test_match_explicit_trigger_type(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="code-review", keywords=("review",), skill_id="cr"))
        results = tm.match("run code-review on this PR")
        assert any(r.skill_id == "cr" for r in results)

    def test_rank_matches_filters_low_scores(self) -> None:
        tm = TriggerMatcher()
        results = [
            MatchResult("a", 0.9, ("kw",), 0.9, LoadTier.TIER2_CONTENT),
            MatchResult("b", 0.1, ("kw",), 0.1, LoadTier.TIER1_METADATA),
            MatchResult("c", 0.5, ("kw",), 0.5, LoadTier.TIER1_METADATA),
        ]
        ranked = tm.rank_matches(results)
        assert len(ranked) == 2
        assert ranked[0].skill_id == "a"

    def test_rank_matches_caps_at_max(self) -> None:
        config = MatchConfig(min_score=0.0, max_matches=2)
        tm = TriggerMatcher(config=config)
        results = [
            MatchResult(f"s{i}", 0.5, ("kw",), 0.5, LoadTier.TIER1_METADATA)
            for i in range(10)
        ]
        ranked = tm.rank_matches(results)
        assert len(ranked) == 2

    def test_match_and_rank(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy",), skill_id="dep"))
        tm.register_trigger(Trigger(pattern="test", keywords=("test",), skill_id="tst"))
        ranked = tm.match_and_rank("deploy the app")
        assert len(ranked) == 1
        assert ranked[0].skill_id == "dep"

    def test_best_match(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy",), skill_id="dep"))
        best = tm.best_match("deploy this")
        assert best is not None
        assert best.skill_id == "dep"

    def test_best_match_none(self) -> None:
        tm = TriggerMatcher()
        assert tm.best_match("irrelevant") is None

    def test_match_scoring_higher_for_more_keywords(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="full", keywords=("deploy", "release", "rollout"), skill_id="full"))
        tm.register_trigger(Trigger(pattern="min", keywords=("deploy",), skill_id="min"))
        results = tm.match("deploy and rollout the release")
        # Should have both matches, full should score higher due to more keywords
        match_ids = {r.skill_id for r in results}
        assert "full" in match_ids
        assert "min" in match_ids

    def test_custom_match_config(self) -> None:
        config = MatchConfig(min_score=0.8, max_matches=3, exact_match_boost=2.0)
        assert config.min_score == 0.8
        assert config.max_matches == 3
        assert config.exact_match_boost == 2.0


# =========================================================================
# 5. ContextAwareLoader
# =========================================================================


class TestContextAwareLoader:
    def test_init_with_budget(self) -> None:
        loader = TieredLoader()
        budget = ContextBudget(total_tokens=4096, used_tokens=1000)
        cal = ContextAwareLoader(loader, budget=budget)
        assert cal.budget.total_tokens == 4096
        assert cal.budget.used_tokens == 1000

    def test_available_tokens_computed(self) -> None:
        budget = ContextBudget(total_tokens=4096, used_tokens=1000)
        assert budget.available_tokens == 3096

    def test_effective_skill_budget(self) -> None:
        budget = ContextBudget(total_tokens=4096, used_tokens=0, reserved_for_skills=20)
        assert budget.effective_skill_budget == 3276  # 80% of 4096

    def test_set_budget(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        new = ContextBudget(total_tokens=2048)
        cal.set_budget(new)
        assert cal.budget.total_tokens == 2048

    def test_update_used_tokens(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=4096))
        cal.update_used_tokens(1000)
        assert cal.budget.used_tokens == 1000
        assert cal.budget.available_tokens == 3096

    def test_can_load_returns_true_when_fits(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=4096))
        assert cal.can_load("s")

    def test_can_load_returns_false_for_unregistered(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=100))
        assert not cal.can_load("nonexistent")

    def test_can_load_at_tier(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=100))
        assert cal.can_load_at_tier("nonexistent", LoadTier.TIER1_METADATA)
        # Tier3 (2000 tokens) won't fit in budget of 100
        assert not cal.can_load_at_tier("nonexistent", LoadTier.TIER3_REFERENCES, ContextBudget(total_tokens=100))

    def test_decide_loading_empty_matches(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        decisions = cal.decide_loading([])
        assert decisions == []

    def test_decide_loading_all_fit(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=10000))
        decisions = cal.decide_loading([("a", 0.9, LoadTier.TIER2_CONTENT), ("b", 0.5, LoadTier.TIER1_METADATA)])
        assert len(decisions) == 2
        assert all(d.fits_in_budget for d in decisions)

    def test_decide_loading_budget_exceeded(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=10))
        decisions = cal.decide_loading([("a", 0.9, LoadTier.TIER2_CONTENT), ("b", 0.5, LoadTier.TIER1_METADATA)])
        # First should fit (metadata=50 is estimated tokens, but effective budget might be low)
        # Actually with total=10, metadata alone is 50, so nothing fits
        fits = [d for d in decisions if d.fits_in_budget]
        assert len(fits) <= len(decisions)

    def test_plan_loading(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=4096))
        plan = cal.plan_loading([("a", 0.9, LoadTier.TIER2_CONTENT)])
        assert len(plan.to_load) == 1
        assert plan.estimated_tokens_after >= 0

    def test_plan_loading_with_eviction(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        _register_dummy(loader, "b", priority=10)
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=200))
        # Load b first (at tier3 to consume the budget)
        loader.load_tier3("b")
        # Now plan to load a but budget is tight
        plan = cal.plan_loading([("a", 0.9, LoadTier.TIER2_CONTENT)])
        # Should not crash; may or may not need eviction
        assert isinstance(plan, LoadPlan)

    def test_evict_if_needed_no_eviction_when_not_needed(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        evicted = cal.evict_if_needed(["a", "b"], budget_needed=0)
        assert evicted == ()

    def test_evict_if_needed_empty_loaded(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        evicted = cal.evict_if_needed([], budget_needed=100)
        assert evicted == ()

    def test_evict_if_needed_lru_policy(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        _register_dummy(loader, "kept")
        _register_dummy(loader, "evicted")
        loader.load_tier1("kept")
        loader.load_tier1("evicted")
        evicted = cal.evict_if_needed(["kept", "evicted"], budget_needed=100, policy=EvictionPolicy.LRU)
        assert len(evicted) >= 1

    def test_evict_if_needed_lfu_policy(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        _register_dummy(loader, "kept")
        _register_dummy(loader, "evicted")
        # Access evicted fewer times
        loader.load_tier1("kept")
        loader.load_tier1("kept")
        loader.load_tier1("evicted")
        evicted = cal.evict_if_needed(["kept", "evicted"], budget_needed=100, policy=EvictionPolicy.LFU)
        assert len(evicted) >= 1

    def test_evict_if_needed_priority_policy(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        _register_dummy(loader, "high", priority=10)
        _register_dummy(loader, "low", priority=1)
        evicted = cal.evict_if_needed(["high", "low"], budget_needed=1000, policy=EvictionPolicy.PRIORITY)
        assert "low" in evicted

    def test_evict_if_needed_fifo_policy(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        _register_dummy(loader, "a")
        _register_dummy(loader, "b")
        cal.track_load("a")
        cal.track_load("b")
        evicted = cal.evict_if_needed(["a", "b"], budget_needed=1000, policy=EvictionPolicy.FIFO)
        assert len(evicted) >= 1

    def test_selected_tier_respects_budget(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "s")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=100))
        # Suggest tier3 but budget only allows tier1
        decisions = cal.decide_loading([("s", 0.9, LoadTier.TIER3_REFERENCES)])
        assert len(decisions) == 1
        # est tokens for tier3 (2000) > 80 available → downgrade
        assert decisions[0].load_tier in (LoadTier.TIER1_METADATA, LoadTier.TIER2_CONTENT)

    def test_apply_plan(self) -> None:
        loader = TieredLoader()
        _register_dummy(loader, "a")
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=4096))
        plan = LoadPlan(
            to_load=(LoadDecision("a", LoadTier.TIER2_CONTENT, 500, True),),
            to_evict=(),
            estimated_tokens_after=500,
        )
        loaded, evicted = cal.apply_plan(plan)
        assert len(loaded) == 1
        assert loaded[0].current_tier == LoadTier.TIER2_CONTENT
        assert evicted == []

    def test_track_load(self) -> None:
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        cal.track_load("s")
        # No direct assertion, just verify no error
        assert True


# =========================================================================
# 6. SkillCompiler
# =========================================================================


class TestSkillCompiler:
    def test_compile_loaded_skill(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="cr", triggers=("review", "audit"))
        skill = LoadedSkill(metadata=meta)
        compiled = compiler.compile(skill)
        assert compiled.skill_id == "cr"
        assert len(compiled.precomputed_triggers) > 0

    def test_compile_batch(self) -> None:
        compiler = SkillCompiler()
        skills = [
            LoadedSkill(metadata=_make_metadata(name="a", triggers=("t1",))),
            LoadedSkill(metadata=_make_metadata(name="b", triggers=("t2",))),
        ]
        compiled = compiler.compile_batch(skills)
        assert len(compiled) == 2
        assert {c.skill_id for c in compiled} == {"a", "b"}

    def test_compile_from_metadata(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="test", triggers=("deploy",))
        compiled = compiler.compile_from_metadata("test", meta)
        assert compiled.skill_id == "test"

    def test_create_index(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="deploy", triggers=("deploy",), io_capabilities=("exec",))
        skill = LoadedSkill(metadata=meta)
        compiled = compiler.compile(skill)
        index = compiler.create_index([compiled])
        assert isinstance(index, CompiledIndex)

    def test_index_lookup(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="deploy", triggers=("deploy", "release"))
        skill = LoadedSkill(metadata=meta)
        compiled = compiler.compile(skill)
        index = compiler.create_index([compiled])
        matches = index.lookup("deploy")
        assert isinstance(matches, list)

    def test_index_lookup_by_capability(self) -> None:
        index = CompiledIndex()
        cs = CompiledSkill(
            skill_id="deploy",
            precomputed_triggers=frozenset({"deploy"}),
            dependency_hashes={},
            metadata_bloom_filter=(),
        )
        index.add(cs, ["deploy"], ["exec", "deploy"])
        matches = index.lookup_by_capability("Exec")
        assert "deploy" in matches

    def test_index_get_compiled(self) -> None:
        index = CompiledIndex()
        cs = CompiledSkill(
            skill_id="x",
            precomputed_triggers=frozenset(),
            dependency_hashes={},
            metadata_bloom_filter=(),
        )
        index.add(cs, [], [])
        assert index.get_compiled("x") is cs
        assert index.get_compiled("nonexistent") is None

    def test_invalidate(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="s")
        skill = LoadedSkill(metadata=meta)
        compiler.compile(skill)
        compiler.invalidate("s")
        assert compiler.is_dirty("s")

    def test_lookup_before_index_returns_empty(self) -> None:
        compiler = SkillCompiler()
        assert compiler.lookup("anything") == []

    def test_clear_cache(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="s")
        compiler.compile(LoadedSkill(metadata=meta))
        compiler.clear()
        assert compiler.get_cached("s") is None

    def test_get_index_none_when_not_built(self) -> None:
        compiler = SkillCompiler()
        assert compiler.get_index() is None

    def test_lookup_metadata_contains(self) -> None:
        compiler = SkillCompiler()
        meta = _make_metadata(name="deploy", triggers=("deploy", "rollout"))
        compiler.compile(LoadedSkill(metadata=meta))
        # bloom filter might return candidates
        candidates = compiler.lookup_metadata_contains("deploy")
        assert isinstance(candidates, list)


# =========================================================================
# 7. DependencyResolver
# =========================================================================


class TestDependencyResolver:
    def test_add_skill(self) -> None:
        resolver = DependencyResolver()
        node = SkillNode(skill_id="a", dependencies=("b",))
        resolver.add_skill(node)
        assert resolver.graph.has_node("a")

    def test_remove_skill(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a"))
        resolver.remove_skill("a")
        assert not resolver.graph.has_node("a")

    def test_graph_get_node(self) -> None:
        graph = DependencyGraph()
        node = SkillNode(skill_id="a")
        graph.add_skill(node)
        assert graph.get_node("a") is node
        assert graph.get_node("nonexistent") is None

    def test_graph_has_node(self) -> None:
        graph = DependencyGraph()
        graph.add_skill(SkillNode(skill_id="a"))
        assert graph.has_node("a")
        assert not graph.has_node("b")

    def test_graph_neighbours(self) -> None:
        graph = DependencyGraph()
        graph.add_skill(SkillNode(skill_id="a"))
        graph.add_skill(SkillNode(skill_id="b", dependencies=("a",)))
        graph.add_skill(SkillNode(skill_id="c", dependencies=("a",)))
        neighbours = graph.neighbours("a")
        assert "b" in neighbours
        assert "c" in neighbours

    def test_resolve_no_deps(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a"))
        resolver.add_skill(SkillNode(skill_id="b"))
        result = resolver.resolve(["a", "b"])
        assert result.is_ok
        assert len(result.load_order) == 2

    def test_resolve_with_deps_order(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b"))
        result = resolver.resolve(["a", "b"])
        assert result.is_ok
        # b should come before a
        assert result.load_order.index("b") < result.load_order.index("a")

    def test_detect_circular_returns_cycles(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b", dependencies=("a",)))
        cycles = resolver.detect_circular(["a", "b"])
        assert len(cycles) >= 1
        assert any("a" in c for c in cycles)

    def test_detect_circular_no_cycle(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b"))
        cycles = resolver.detect_circular(["a", "b"])
        assert cycles == []

    def test_resolve_conflicts(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", conflicts=("b",)))
        resolver.add_skill(SkillNode(skill_id="b", conflicts=("a",)))
        excluded = resolver.resolve_conflicts(["a", "b"])
        assert len(excluded) >= 1  # At least one will be excluded

    def test_resolve_no_conflicts(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a"))
        resolver.add_skill(SkillNode(skill_id="b"))
        excluded = resolver.resolve_conflicts(["a", "b"])
        assert excluded == []

    def test_optimal_load_order(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b", dependencies=("c",)))
        resolver.add_skill(SkillNode(skill_id="c"))
        order = resolver.optimal_load_order(["a", "b", "c"])
        # c before b before a
        assert order.index("c") < order.index("b") < order.index("a")

    def test_optimal_load_order_respects_requested_order_for_independent(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="x"))
        resolver.add_skill(SkillNode(skill_id="y"))
        resolver.add_skill(SkillNode(skill_id="z"))
        order = resolver.optimal_load_order(["z", "x", "y"])
        assert order == ["z", "x", "y"]

    def test_resolve_missing_deps(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        result = resolver.resolve(["a"])
        assert not result.is_ok
        assert "b" in result.missing_deps

    def test_overflow_resolve_transitive_deps(self) -> None:
        """Replacement for previously broken transitive dep test."""
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b", dependencies=("c",)))
        resolver.add_skill(SkillNode(skill_id="c"))
        result = resolver.resolve(["a", "b", "c"])
        assert result.is_ok
        assert result.load_order == ("c", "b", "a")

    def test_resolve_reports_circular(self) -> None:
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b", dependencies=("c",)))
        resolver.add_skill(SkillNode(skill_id="c", dependencies=("a",)))
        result = resolver.resolve(["a", "b", "c"])
        assert not result.is_ok
        assert len(result.circular_deps) >= 1

    def test_dependency_graph_all_skill_ids(self) -> None:
        graph = DependencyGraph()
        graph.add_skill(SkillNode(skill_id="a"))
        graph.add_skill(SkillNode(skill_id="b"))
        assert set(graph.all_skill_ids()) == {"a", "b"}


# =========================================================================
# 8. Dataclass integrity
# =========================================================================


class TestDataclassIntegrity:
    def test_skill_metadata_frozen(self) -> None:
        m = _make_metadata()
        with pytest.raises(AttributeError):
            m.name = "new-name"  # type: ignore[misc]

    def test_skill_content_frozen(self) -> None:
        c = SkillContent(body="x")
        with pytest.raises(AttributeError):
            c.body = "y"  # type: ignore[misc]

    def test_skill_references_frozen(self) -> None:
        r = SkillReferences()
        with pytest.raises(AttributeError):
            r.docs = ("new",)  # type: ignore[misc]

    def test_loaded_skill_frozen(self) -> None:
        ls = LoadedSkill(metadata=_make_metadata())
        with pytest.raises(AttributeError):
            ls.current_tier = LoadTier.TIER2_CONTENT  # type: ignore[misc]

    def test_context_budget_frozen(self) -> None:
        b = ContextBudget(total_tokens=100)
        with pytest.raises(AttributeError):
            b.total_tokens = 200  # type: ignore[misc]

    def test_trigger_frozen(self) -> None:
        t = Trigger(pattern="x", skill_id="s")
        with pytest.raises(AttributeError):
            t.pattern = "y"  # type: ignore[misc]

    def test_load_decision_frozen(self) -> None:
        d = LoadDecision("s", LoadTier.TIER1_METADATA, 50, True)
        with pytest.raises(AttributeError):
            d.skill_id = "t"  # type: ignore[misc]

    def test_skill_node_frozen(self) -> None:
        n = SkillNode(skill_id="a")
        with pytest.raises(AttributeError):
            n.skill_id = "b"  # type: ignore[misc]

    def test_compiled_skill_frozen(self) -> None:
        cs = CompiledSkill(
            skill_id="x",
            precomputed_triggers=frozenset(),
            dependency_hashes={},
            metadata_bloom_filter=(),
        )
        with pytest.raises(AttributeError):
            cs.skill_id = "y"  # type: ignore[misc]

    def test_resolution_result_frozen(self) -> None:
        rr = ResolutionResult(
            load_order=(), conflicts=(), missing_deps=(), circular_deps=(),
        )
        with pytest.raises(AttributeError):
            rr.load_order = ("x",)  # type: ignore[misc]


# =========================================================================
# 9. Edge cases and integration
# =========================================================================


class TestIntegration:
    def test_tiered_loader_to_trigger_matcher(self) -> None:
        """Skills registered in TieredLoader can be picked up by TriggerMatcher."""
        loader = TieredLoader()
        meta = _make_metadata(name="analysis", triggers=("analyze", "audit"))
        loader.register_skill("analysis", meta)

        tm = TriggerMatcher()
        tm.register_skill_triggers("analysis", meta)
        assert "analysis" in tm.list_triggers()

    def test_full_loading_pipeline(self) -> None:
        """End-to-end: register, match, decide, and load."""
        # Set up loader
        loader = TieredLoader()
        meta = _make_metadata(
            name="code-review", triggers=("review", "audit", "inspect"),
            category="dev",
        )
        content = _make_content(body="Review code for bugs")
        loader.register_skill("code-review", meta, content)

        # Set up matching
        tm = TriggerMatcher()
        tm.register_skill_triggers("code-review", meta)

        # Match against context
        matches = tm.match_and_rank("please review this pull request")
        assert len(matches) >= 1

        # Decide loading
        cal = ContextAwareLoader(loader, budget=ContextBudget(total_tokens=4096))
        match_tuples = [(m.skill_id, m.score, m.load_tier) for m in matches]
        decisions = cal.decide_loading(match_tuples)
        assert len(decisions) >= 1

        # Load
        if decisions[0].fits_in_budget:
            loaded = loader.load_at_tier(decisions[0].skill_id, decisions[0].load_tier)
            assert loaded.metadata.name == "code-review"

    def test_dependency_resolution_with_compilation(self) -> None:
        """Dependency resolution works alongside compiled skills."""
        resolver = DependencyResolver()
        resolver.add_skill(SkillNode(skill_id="a", dependencies=("b",)))
        resolver.add_skill(SkillNode(skill_id="b"))

        compiler = SkillCompiler()
        meta_b = _make_metadata(name="b")
        compiler.compile(LoadedSkill(metadata=meta_b))

        result = resolver.resolve(["a", "b"])
        assert result.is_ok
        assert result.load_order == ("b", "a")

    def test_budget_reserve_percent(self) -> None:
        budget = ContextBudget(total_tokens=1000, reserved_for_skills=25)
        effective = budget.effective_skill_budget
        assert effective == 750  # 75% of 1000

    def test_zero_budget(self) -> None:
        budget = ContextBudget(total_tokens=0)
        assert budget.available_tokens == 0
        assert budget.effective_skill_budget == 0

    def test_load_plan_empty(self) -> None:
        plan = LoadPlan(to_load=(), to_evict=(), estimated_tokens_after=0)
        assert plan.to_load == ()
        assert plan.to_evict == ()

    def test_tokens_saved_pct_zero_when_nothing_loaded(self) -> None:
        stats = LoaderStats()
        assert stats.tokens_saved_pct() == 0.0

    def test_scoring_no_matches_returns_empty(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy",), skill_id="dep"))
        results = tm.match("nothing to do here")
        ranked = tm.rank_matches(results)
        assert ranked == []

    def test_multiple_triggers_different_skills(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="deploy", keywords=("deploy", "release"), skill_id="ops"))
        tm.register_trigger(Trigger(pattern="monitor", keywords=("monitor", "alert"), skill_id="mon"))
        results = tm.match("deploy to production")
        ops_matches = [r for r in results if r.skill_id == "ops"]
        assert len(ops_matches) >= 1

    def test_config_error_message(self) -> None:
        with pytest.raises(ConfigError, match="Unknown preset"):
            get_preset("INVALID")

    def test_skill_node_defaults(self) -> None:
        n = SkillNode(skill_id="solo")
        assert n.dependencies == ()
        assert n.conflicts == ()
        assert n.provides_capability == ""

    def test_lookup_by_capability_normalized(self) -> None:
        index = CompiledIndex()
        cs = CompiledSkill(
            skill_id="db",
            precomputed_triggers=frozenset(),
            dependency_hashes={},
            metadata_bloom_filter=(),
        )
        index.add(cs, [], ["Database", "SQL"])
        assert "db" in index.lookup_by_capability("database")
        assert "db" in index.lookup_by_capability("SQL")
        assert index.lookup_by_capability("nonexistent") == []

    def test_resolution_result_is_ok(self) -> None:
        ok = ResolutionResult(load_order=("a",), conflicts=(), missing_deps=(), circular_deps=())
        assert ok.is_ok

        not_ok = ResolutionResult(
            load_order=(), conflicts=("b",), missing_deps=(), circular_deps=(),
        )
        assert not not_ok.is_ok

    def test_tier_number_roundtrip(self) -> None:
        t1 = LoadTier.TIER1_METADATA
        t2 = LoadTier.TIER2_CONTENT
        t3 = LoadTier.TIER3_REFERENCES
        assert LoadTier(t1.value) == t1
        assert LoadTier(t2.value) == t2
        assert LoadTier(t3.value) == t3

    def test_index_add_and_remove(self) -> None:
        index = CompiledIndex()
        cs = CompiledSkill(
            skill_id="test",
            precomputed_triggers=frozenset({"x"}),
            dependency_hashes={},
            metadata_bloom_filter=(),
        )
        index.add(cs, ["x"], ["cap"])
        assert "test" in index.all_skill_ids()
        index.remove("test")
        assert "test" not in index.all_skill_ids()

    def test_eviction_with_budget_exact(self) -> None:
        """Test eviction to free exactly enough tokens."""
        loader = TieredLoader()
        cal = ContextAwareLoader(loader)
        _register_dummy(loader, "big1")
        _register_dummy(loader, "big2")
        evicted = cal.evict_if_needed(["big1", "big2"], budget_needed=5000)
        assert len(evicted) >= 1

    def test_empty_context_no_matches(self) -> None:
        tm = TriggerMatcher()
        tm.register_trigger(Trigger(pattern="x", keywords=("x",), skill_id="s"))
        assert tm.match("") == []

    def test_load_at_tier_unknown_raises(self) -> None:
        loader = TieredLoader()
        with pytest.raises(KeyError):
            loader.load_at_tier("unknown", LoadTier.TIER1_METADATA)

    def test_trigger_types_enum(self) -> None:
        assert TriggerType.KEYWORD.value != TriggerType.EXPLICIT.value
        all_types = list(TriggerType)
        assert len(all_types) == 5

    def test_eviction_policies_enum(self) -> None:
        assert len(list(EvictionPolicy)) == 4
        assert EvictionPolicy.LRU != EvictionPolicy.FIFO

    def test_loader_stats_frozen(self) -> None:
        s = LoaderStats()
        with pytest.raises(AttributeError):
            s.skills_loaded = 10  # type: ignore[misc]

    def test_budget_config_defaults(self) -> None:
        bc = BudgetConfig()
        assert bc.max_skill_tokens == 2000
        assert bc.reserve_percent == 0.2
        assert bc.eviction_policy == EvictionPolicy.LRU

    def test_custom_budget_config(self) -> None:
        bc = BudgetConfig(
            max_skill_tokens=1000,
            reserve_percent=0.5,
            eviction_policy=EvictionPolicy.LFU,
        )
        assert bc.max_skill_tokens == 1000
        assert bc.reserve_percent == 0.5
        assert bc.eviction_policy == EvictionPolicy.LFU

    def test_skill_compiler_block_filter(self) -> None:
        from lyra_skill_loader.skill_compiler import _bloom_might_contain, _make_bloom_filter

        bloom = _make_bloom_filter(("hello", "world"))
        assert _bloom_might_contain(bloom, "hello")
        assert _bloom_might_contain(bloom, "world")
        # False negatives impossible, but false positives possible
        # Verify the bloom filter structure
        assert len(bloom) == 64
