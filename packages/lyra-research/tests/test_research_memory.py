"""
Tests for lyra_research.memory — Research Memory System.

All file I/O uses tmp_path pytest fixture. Never writes to ~/.lyra.
"""

from datetime import datetime


from lyra_research.memory import (
    CorpusEntry,
    LocalCorpus,
    ResearchCase,
    ResearchNote,
    ResearchNoteStore,
    ResearchStrategy,
    ResearchStrategyMemory,
    SessionCaseBank,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_note(**kwargs) -> ResearchNote:
    defaults = dict(
        topic="attention mechanisms",
        title="Attention is All You Need",
        content="Transformers use self-attention to capture dependencies.",
        tags=["nlp", "transformers", "attention"],
        note_type="finding",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return ResearchNote(**defaults)


def make_corpus_entry(**kwargs) -> CorpusEntry:
    from uuid import uuid4
    defaults = dict(
        id=str(uuid4()),
        source_id="arxiv:1234.5678",
        title="Attention is All You Need",
        url="https://arxiv.org/abs/1706.03762",
        abstract="We propose a new network architecture, the Transformer.",
        full_text="The Transformer model relies entirely on self-attention.",
        source_type="paper",
    )
    defaults.update(kwargs)
    return CorpusEntry(**defaults)


def make_strategy(**kwargs) -> ResearchStrategy:
    defaults = dict(
        topic_type="ml_paper_search",
        domain="nlp",
        strategy_steps=["Search arxiv", "Filter by citations", "Read abstracts"],
        outcome_score=0.8,
        lessons_learned="Start broad, then narrow by citation count.",
    )
    defaults.update(kwargs)
    return ResearchStrategy(**defaults)


def make_case(**kwargs) -> ResearchCase:
    defaults = dict(
        topic="attention mechanisms in NLP",
        domain="nlp",
        report_summary="Attention mechanisms enable transformers to excel at NLP.",
        sources_found=10,
        quality_score=0.85,
        duration_seconds=120.0,
        top_sources=["https://arxiv.org/abs/1706.03762"],
        key_findings=["Self-attention is key to transformers"],
        gaps_found=["Efficient attention at scale"],
    )
    defaults.update(kwargs)
    return ResearchCase(**defaults)


# ---------------------------------------------------------------------------
# ResearchNoteStore
# ---------------------------------------------------------------------------

def test_note_store_add_and_get(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    note = make_note()
    added = store.add(note)
    retrieved = store.get(added.id)
    assert retrieved is not None
    assert retrieved.title == "Attention is All You Need"
    assert retrieved.topic == "attention mechanisms"


def test_note_store_get_missing_returns_none(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    assert store.get("nonexistent-id") is None


def test_note_store_search_by_keyword(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    store.add(make_note(title="Transformers for NLP", content="Self-attention is core."))
    store.add(make_note(title="CNN for vision", content="Convolutions excel at images.", tags=["vision"]))
    results = store.search("self-attention")
    assert any("Transformers" in r.title for r in results)


def test_note_store_search_returns_empty_for_no_match(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    store.add(make_note())
    results = store.search("quantum computing xyzzy")
    assert results == []


def test_note_store_search_top_k_limit(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    for i in range(20):
        store.add(make_note(title=f"Note {i}", content="transformers self-attention nlp"))
    results = store.search("transformers", top_k=5)
    assert len(results) <= 5


def test_note_store_auto_links_overlapping_tags(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    n1 = make_note(tags=["nlp", "transformers", "attention"], topic="transformers")
    n2 = make_note(tags=["nlp", "transformers", "bert"], topic="bert")
    added1 = store.add(n1)
    added2 = store.add(n2)
    # n2 should be auto-linked to n1 (2 overlapping tags: nlp, transformers)
    assert added1.id in added2.links or added2.id in store.get(added1.id).links


def test_note_store_no_auto_link_single_tag_overlap(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    n1 = make_note(tags=["nlp"], topic="topic-a")
    n2 = make_note(tags=["nlp", "vision"], topic="topic-b")
    added1 = store.add(n1)
    added2 = store.add(n2)
    # Only 1 overlapping tag — should NOT auto-link
    assert added1.id not in added2.links
    assert added2.id not in store.get(added1.id).links


def test_note_store_auto_links_same_topic(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    n1 = make_note(topic="transformers", tags=["a"])
    n2 = make_note(topic="transformers", tags=["b"])
    added1 = store.add(n1)
    added2 = store.add(n2)
    assert added1.id in added2.links or added2.id in store.get(added1.id).links


def test_note_store_find_by_topic(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    store.add(make_note(topic="attention mechanisms"))
    store.add(make_note(topic="convolutional networks"))
    results = store.find_by_topic("attention")
    assert len(results) == 1
    assert results[0].topic == "attention mechanisms"


def test_note_store_find_by_topic_empty(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    store.add(make_note(topic="nlp"))
    assert store.find_by_topic("robotics") == []


def test_note_store_persistence(tmp_path):
    path = tmp_path / "notes.json"
    store1 = ResearchNoteStore(store_path=path)
    note = make_note()
    added = store1.add(note)

    store2 = ResearchNoteStore(store_path=path)
    retrieved = store2.get(added.id)
    assert retrieved is not None
    assert retrieved.title == added.title
    assert retrieved.topic == added.topic


def test_note_store_persistence_preserves_datetimes(tmp_path):
    path = tmp_path / "notes.json"
    store1 = ResearchNoteStore(store_path=path)
    note = make_note()
    added = store1.add(note)

    store2 = ResearchNoteStore(store_path=path)
    retrieved = store2.get(added.id)
    assert isinstance(retrieved.created_at, datetime)
    assert isinstance(retrieved.updated_at, datetime)


def test_note_store_update(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    note = store.add(make_note(confidence=0.5))
    updated = store.update(note.id, confidence=0.95, title="Updated Title")
    assert updated is not None
    assert updated.confidence == 0.95
    assert updated.title == "Updated Title"


def test_note_store_update_sets_updated_at(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    note = store.add(make_note())
    old_updated = note.updated_at
    updated = store.update(note.id, content="New content")
    assert updated.updated_at >= old_updated


def test_note_store_update_missing_returns_none(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    assert store.update("bad-id", title="x") is None


def test_note_store_delete(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    note = store.add(make_note())
    assert store.delete(note.id) is True
    assert store.get(note.id) is None


def test_note_store_delete_missing(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    assert store.delete("nonexistent") is False


def test_note_store_get_linked(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "notes.json")
    n1 = store.add(make_note(tags=["nlp", "transformers", "attention"], topic="t1"))
    n2 = store.add(make_note(tags=["nlp", "transformers", "bert"], topic="t2"))
    linked = store.get_linked(n2.id)
    assert any(n.id == n1.id for n in linked)


def test_note_store_loads_empty_on_missing_file(tmp_path):
    store = ResearchNoteStore(store_path=tmp_path / "nonexistent.json")
    assert store.get("any-id") is None


# ---------------------------------------------------------------------------
# LocalCorpus
# ---------------------------------------------------------------------------

def test_local_corpus_store_and_get(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    entry = make_corpus_entry()
    assert corpus.store(entry) is True
    retrieved = corpus.get(entry.source_id)
    assert retrieved is not None
    assert retrieved.title == entry.title
    assert retrieved.url == entry.url


def test_local_corpus_get_missing_returns_none(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    assert corpus.get("nonexistent-source") is None


def test_local_corpus_no_duplicate(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    entry = make_corpus_entry()
    assert corpus.store(entry) is True
    assert corpus.store(entry) is False  # second store returns False


def test_local_corpus_search(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    corpus.store(make_corpus_entry(source_id="s1", title="Transformer self-attention", abstract="Self-attention rocks", full_text="Details about self-attention."))
    corpus.store(make_corpus_entry(source_id="s2", title="CNN for vision", abstract="Convolutions are great", full_text="No mention of that topic here."))
    results = corpus.search("self-attention")
    assert len(results) == 1
    assert results[0].source_id == "s1"


def test_local_corpus_search_full_text(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    corpus.store(make_corpus_entry(source_id="s1", full_text="attention mechanism detail", abstract=""))
    results = corpus.search("attention mechanism detail")
    assert len(results) >= 1


def test_local_corpus_search_empty(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    corpus.store(make_corpus_entry())
    results = corpus.search("zzz-no-match-xyzzy")
    assert results == []


def test_local_corpus_count(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    assert corpus.count() == 0
    corpus.store(make_corpus_entry(source_id="s1"))
    corpus.store(make_corpus_entry(source_id="s2"))
    assert corpus.count() == 2


def test_local_corpus_list_all(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    corpus.store(make_corpus_entry(source_id="s1", source_type="paper"))
    corpus.store(make_corpus_entry(source_id="s2", source_type="repository"))
    all_entries = corpus.list_all()
    assert len(all_entries) == 2


def test_local_corpus_list_all_filtered_by_type(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    corpus.store(make_corpus_entry(source_id="s1", source_type="paper"))
    corpus.store(make_corpus_entry(source_id="s2", source_type="repository"))
    papers = corpus.list_all(source_type="paper")
    assert len(papers) == 1
    assert papers[0].source_id == "s1"


def test_local_corpus_delete(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    entry = make_corpus_entry()
    corpus.store(entry)
    assert corpus.delete(entry.source_id) is True
    assert corpus.get(entry.source_id) is None


def test_local_corpus_delete_missing(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    assert corpus.delete("nonexistent") is False


def test_local_corpus_metadata_roundtrip(tmp_path):
    corpus = LocalCorpus(db_path=tmp_path / "corpus.db")
    entry = make_corpus_entry(metadata={"year": 2023, "venue": "NeurIPS"})
    corpus.store(entry)
    retrieved = corpus.get(entry.source_id)
    assert retrieved.metadata == {"year": 2023, "venue": "NeurIPS"}


# ---------------------------------------------------------------------------
# ResearchStrategyMemory
# ---------------------------------------------------------------------------

def test_strategy_memory_save_and_retrieve(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    strategy = make_strategy()
    saved = mem.save_strategy(strategy)
    assert saved.id == strategy.id
    results = mem.get_for_topic_type("ml_paper_search")
    assert any(s.id == strategy.id for s in results)


def test_strategy_memory_best_for_domain(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    s1 = make_strategy(domain="nlp", outcome_score=0.9)
    s2 = make_strategy(domain="nlp", outcome_score=0.5)
    s3 = make_strategy(domain="cv", outcome_score=0.95)
    mem.save_strategy(s1)
    mem.save_strategy(s2)
    mem.save_strategy(s3)
    best = mem.get_best_for_domain("nlp", top_k=2)
    assert len(best) == 2
    assert best[0].outcome_score >= best[1].outcome_score
    assert all(s.domain == "nlp" for s in best)


def test_strategy_memory_best_for_domain_empty(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    results = mem.get_best_for_domain("robotics")
    assert results == []


def test_strategy_memory_get_for_topic_type(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    mem.save_strategy(make_strategy(topic_type="ml_paper_search"))
    mem.save_strategy(make_strategy(topic_type="github_repo_search"))
    results = mem.get_for_topic_type("github_repo_search")
    assert all(s.topic_type == "github_repo_search" for s in results)


def test_strategy_memory_record_outcome(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    strategy = mem.save_strategy(make_strategy(outcome_score=0.5, use_count=0))
    mem.record_outcome(strategy.id, score=0.95, lesson="Use citation count filter.")
    updated = mem.get_for_topic_type(strategy.topic_type)
    matched = next(s for s in updated if s.id == strategy.id)
    assert matched.outcome_score == 0.95
    assert matched.use_count == 1
    assert "citation" in matched.lessons_learned


def test_strategy_memory_record_outcome_missing_noop(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "strategies.json")
    # Should not raise
    mem.record_outcome("nonexistent-id", score=1.0, lesson="noop")


def test_strategy_memory_persistence(tmp_path):
    path = tmp_path / "strategies.json"
    mem1 = ResearchStrategyMemory(store_path=path)
    strategy = mem1.save_strategy(make_strategy())

    mem2 = ResearchStrategyMemory(store_path=path)
    results = mem2.get_for_topic_type(strategy.topic_type)
    assert any(s.id == strategy.id for s in results)


def test_strategy_memory_loads_empty_on_missing_file(tmp_path):
    mem = ResearchStrategyMemory(store_path=tmp_path / "nonexistent.json")
    assert mem.get_best_for_domain("nlp") == []


# ---------------------------------------------------------------------------
# SessionCaseBank
# ---------------------------------------------------------------------------

def test_case_bank_save_and_get_all(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    case = make_case()
    bank.save_case(case)
    all_cases = bank.get_all()
    assert any(c.id == case.id for c in all_cases)


def test_case_bank_get_all_filtered_by_domain(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(domain="nlp"))
    bank.save_case(make_case(domain="cv"))
    nlp_cases = bank.get_all(domain="nlp")
    assert all(c.domain == "nlp" for c in nlp_cases)
    assert len(nlp_cases) == 1


def test_case_bank_find_related(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(topic="attention mechanisms transformers", quality_score=0.9))
    bank.save_case(make_case(topic="convolutional networks vision", quality_score=0.8))
    related = bank.find_related("attention transformers")
    assert len(related) >= 1
    assert "attention" in related[0].topic or "transformers" in related[0].topic


def test_case_bank_find_related_empty(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(topic="nlp attention"))
    related = bank.find_related("quantum robotics aerospace")
    assert related == []


def test_case_bank_find_related_sorted_by_quality(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(topic="attention mechanisms nlp", quality_score=0.6))
    bank.save_case(make_case(topic="attention transformers nlp", quality_score=0.95))
    related = bank.find_related("attention nlp", top_k=2)
    if len(related) >= 2:
        assert related[0].quality_score >= related[1].quality_score


def test_case_bank_get_best(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(quality_score=0.5))
    bank.save_case(make_case(quality_score=0.9))
    bank.save_case(make_case(quality_score=0.7))
    best = bank.get_best(n=2)
    assert len(best) == 2
    assert best[0].quality_score >= best[1].quality_score


def test_case_bank_get_best_n_larger_than_total(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    bank.save_case(make_case(quality_score=0.8))
    best = bank.get_best(n=10)
    assert len(best) == 1


def test_case_bank_persistence(tmp_path):
    path = tmp_path / "cases.json"
    bank1 = SessionCaseBank(store_path=path)
    case = make_case(topic="memory systems", quality_score=0.77)
    bank1.save_case(case)

    bank2 = SessionCaseBank(store_path=path)
    all_cases = bank2.get_all()
    assert any(c.id == case.id for c in all_cases)
    matched = next(c for c in all_cases if c.id == case.id)
    assert matched.quality_score == 0.77
    assert isinstance(matched.created_at, datetime)


def test_case_bank_loads_empty_on_missing_file(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "nonexistent.json")
    assert bank.get_all() == []
