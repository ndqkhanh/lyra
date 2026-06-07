"""
Deep Research Pipeline (P6).

Orchestrates a five-phase research workflow:
1. query_analysis        — decompose the question into sub-queries and identify target sources.
2. parallel_search       — fan-out searches across web, code, and documentation.
3. read_and_extract      — fetch each result and extract structured observations.
4. workspace_report_synth — integrate findings via the S4 WorkspaceReport.
5. citation_verification — cross-check claims against sources.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from src.context.compaction import CompactionStrategy
from src.context.workspace_report import WorkspaceReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class SourceDomain(str, Enum):
    """Broad category of a search source."""

    WEB = "web"
    CODE = "code"
    DOCS = "docs"
    ACADEMIC = "academic"


@dataclass(frozen=True)
class SearchResult:
    """A single item returned by a search provider."""

    url: str
    title: str
    snippet: str
    domain: SourceDomain = SourceDomain.WEB
    relevance_score: float = 1.0


@dataclass(frozen=True)
class Citation:
    """A verified citation linking a claim to a source."""

    claim: str
    source_url: str
    source_snippet: str
    verified: bool = True
    confidence: float = 1.0


@dataclass
class ResearchReport:
    """
    Final output of a deep research run.

    Attributes:
        query: Original research query.
        report: Synthesised workspace report (markdown).
        key_findings: Consolidated list of key findings.
        citations: Verified citations backing the findings.
        total_sources_consulted: Number of unique sources retrieved.
        total_citations: Number of citations produced.
        duration_seconds: Total wall-clock time.
        sub_query_breakdown: Number of sub-queries generated from analysis.
        created_at: Timestamp of completion.
        metadata: Additional metadata (errors, warnings, etc.).
    """

    query: str
    report: str
    key_findings: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    total_sources_consulted: int = 0
    total_citations: int = 0
    duration_seconds: float = 0.0
    sub_query_breakdown: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Provider type aliases
# ---------------------------------------------------------------------------

# f(query) -> list[SearchResult]
SearchProvider = Callable[[str], "list[SearchResult] | asyncio.Future[list[SearchResult]]"]

# f(url) -> str (the fetched page text)
FetchProvider = Callable[[str], "str | asyncio.Future[str]"]

# f(text) -> list[str] (extracted observations / claims)
ExtractProvider = Callable[[str], "list[str] | asyncio.Future[list[str]]"]

# f(claim, source_url) -> Citation
VerifyProvider = Callable[[str, str], "Citation | asyncio.Future[Citation]"]

# f(prompt) -> str (general LLM call for analysis / synthesis)
LLMProvider = Callable[[str], "str | asyncio.Future[str]"]


# ---------------------------------------------------------------------------
# DeepResearchPipeline
# ---------------------------------------------------------------------------


class DeepResearchPipeline:
    """
    Five-phase deep research pipeline.

    Phases
    ------
    1. **query_analysis** — decompose the user query into 1..N sub-queries and
       identify the target domains (web / code / docs / academic).
    2. **search** — fan out parallel searches across all identified sources.
    3. **read_and_extract** — fetch each search-result URL and extract
       structured observations.
    4. **synthesize** — feed observations into a ``WorkspaceReport`` (S4)
       to produce a compressed markdown report with key findings.
    5. **verify_citations** — cross-check each extracted claim against its
       source URL.

    Usage::

        pipeline = DeepResearchPipeline(
            search_fn=my_search,
            fetch_fn=my_fetch,
            extract_fn=my_extract,
            verify_fn=my_verify,
            llm_fn=my_llm,
        )
        report = await pipeline.run("What is the impact of X on Y?")
    """

    def __init__(
        self,
        search_fn: SearchProvider | None = None,
        fetch_fn: FetchProvider | None = None,
        extract_fn: ExtractProvider | None = None,
        verify_fn: VerifyProvider | None = None,
        llm_fn: LLMProvider | None = None,
        max_concurrent_fetches: int = 5,
        compaction_strategy: CompactionStrategy = CompactionStrategy.BALANCED,
        max_sub_queries: int = 6,
    ) -> None:
        """
        Args:
            search_fn: ``(query: str) -> list[SearchResult]``.
            fetch_fn: ``(url: str) -> str`` (raw page text).
            extract_fn: ``(text: str) -> list[str]`` (observations / claims).
            verify_fn: ``(claim: str, source_url: str) -> Citation``.
            llm_fn: ``(prompt: str) -> str``.  Used for query analysis and
                workspace synthesis when the extract/verify aren't enough.
            max_concurrent_fetches: Limit on parallel HTTP fetches.
            compaction_strategy: Compression aggressiveness for S4.
            max_sub_queries: Maximum number of sub-queries to generate.
        """
        self._search_fn = search_fn
        self._fetch_fn = fetch_fn
        self._extract_fn = extract_fn
        self._verify_fn = verify_fn
        self._llm_fn = llm_fn
        self._max_concurrent_fetches = max_concurrent_fetches
        self._compaction_strategy = compaction_strategy
        self._max_sub_queries = max_sub_queries

        self._semaphore = asyncio.Semaphore(max_concurrent_fetches)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, query: str, metadata: dict[str, Any] | None = None) -> ResearchReport:
        """
        Execute the full five-phase deep research pipeline.

        Args:
            query: The research question or topic.
            metadata: Optional metadata (e.g. ``{"user_id": ...}``).

        Returns:
            ``ResearchReport`` with synthesised findings and citations.
        """
        start = time.monotonic()
        wrapped_meta = metadata or {}

        logger.info("P6 pipeline start: %s", query)

        # Phase 1 — Analyse query
        sub_queries = await self._phase_query_analysis(query)
        domains = self._infer_domains(query, sub_queries)
        logger.info("Phase 1 complete: %d sub-queries, domains=%s", len(sub_queries), domains)

        # Phase 2 — Parallel search
        search_results = await self._phase_search(sub_queries, domains)
        logger.info("Phase 2 complete: %d search results", len(search_results))

        # Phase 3 — Read & extract
        observations = await self._phase_read_and_extract(search_results)
        logger.info("Phase 3 complete: %d observations extracted", len(observations))

        # Phase 4 — Synthesise (S4)
        workspace_report = await self._phase_synthesize(query, observations)
        logger.info(
            "Phase 4 complete: %d steps, %d findings",
            workspace_report.step_count,
            len(workspace_report.key_findings),
        )

        # Phase 5 — Verify citations
        citations = await self._phase_verify_citations(observations, search_results)
        logger.info("Phase 5 complete: %d citations verified", len(citations))

        duration = time.monotonic() - start

        return ResearchReport(
            query=query,
            report=workspace_report.report_text,
            key_findings=workspace_report.key_findings,
            citations=citations,
            total_sources_consulted=len(search_results),
            total_citations=len(citations),
            duration_seconds=round(duration, 2),
            sub_query_breakdown=len(sub_queries),
            metadata=wrapped_meta,
        )

    # ------------------------------------------------------------------
    # Phase 1 — Query Analysis
    # ------------------------------------------------------------------

    async def _phase_query_analysis(self, query: str) -> list[str]:
        """
        Decompose the user query into 1..N focused sub-queries.

        If no ``llm_fn`` is configured, returns the original query as a single
        sub-query.
        """
        if self._llm_fn is None:
            return [query]

        prompt = (
            "You are a research query decomposer. Break the following question into "
            f"up to {self._max_sub_queries} focused sub-questions. Each sub-question "
            "should target a distinct aspect of the original question.\n\n"
            "Return one sub-question per line. No numbering, no commentary.\n\n"
            f"Question: {query}"
        )

        raw = await self._call_llm(prompt)
        sub_queries = [
            line.strip().strip("-").strip()
            for line in raw.strip().splitlines()
            if line.strip()
        ]

        # Fall back to the original query if decomposition returned nothing
        # or returned the same line as the original.
        if not sub_queries or (len(sub_queries) == 1 and sub_queries[0].lower() == query.lower()):
            return [query]

        return sub_queries[: self._max_sub_queries]

    # ------------------------------------------------------------------
    # Phase 2 — Parallel Search
    # ------------------------------------------------------------------

    async def _phase_search(
        self, sub_queries: list[str], domains: list[SourceDomain]
    ) -> list[SearchResult]:
        """
        Fan out searches across all sub-queries and all domains in parallel.

        Uses ``asyncio.gather`` so all searches run concurrently.
        """
        if self._search_fn is None:
            logger.warning("No search_fn configured — returning empty results.")
            return []

        tasks = []
        for sq in sub_queries:
            for domain in domains:
                tasks.append(self._search_domain(sq, domain))

        # Gather all results; suppress individual failures.
        nested = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[SearchResult] = []
        for item in nested:
            if isinstance(item, Exception):
                logger.warning("Search task failed: %s", item)
                continue
            if isinstance(item, list):
                results.extend(item)

        return results

    async def _search_domain(self, query: str, domain: SourceDomain) -> list[SearchResult]:
        """Call the search provider once.  Wraps sync providers in a thread."""
        tagged_query = f"[{domain.value}] {query}"
        if asyncio.iscoroutinefunction(self._search_fn):
            raw_results = await self._search_fn(tagged_query)
        else:
            loop = asyncio.get_running_loop()
            raw_results = await loop.run_in_executor(None, self._search_fn, tagged_query)

        # Tag results with the domain they came from.
        for r in raw_results:
            object.__setattr__(r, "domain", domain)
        return raw_results

    # ------------------------------------------------------------------
    # Phase 3 — Read & Extract
    # ------------------------------------------------------------------

    async def _phase_read_and_extract(
        self, search_results: list[SearchResult]
    ) -> list[str]:
        """
        Fetch each search-result URL and extract structured observations.

        Concurrency is capped by ``max_concurrent_fetches``.
        """
        if self._fetch_fn is None or self._extract_fn is None:
            logger.warning("fetch_fn or extract_fn not configured — no observations.")
            return []

        sem = asyncio.Semaphore(self._max_concurrent_fetches)

        async def fetch_one(result: SearchResult) -> list[str]:
            async with sem:
                try:
                    if asyncio.iscoroutinefunction(self._fetch_fn):
                        text = await self._fetch_fn(result.url)
                    else:
                        loop = asyncio.get_running_loop()
                        text = await loop.run_in_executor(None, self._fetch_fn, result.url)
                except Exception as exc:
                    logger.debug("Fetch failed for %s: %s", result.url, exc)
                    return []

                try:
                    if asyncio.iscoroutinefunction(self._extract_fn):
                        obs = await self._extract_fn(text)
                    else:
                        loop = asyncio.get_running_loop()
                        obs = await loop.run_in_executor(None, self._extract_fn, text)
                except Exception as exc:
                    logger.debug("Extract failed for %s: %s", result.url, exc)
                    return []

                return obs

        nested = await asyncio.gather(
            *[fetch_one(r) for r in search_results],
            return_exceptions=True,
        )

        observations: list[str] = []
        for item in nested:
            if isinstance(item, Exception):
                logger.warning("Read-and-extract task failed: %s", item)
                continue
            if isinstance(item, list):
                observations.extend(item)

        return observations

    # ------------------------------------------------------------------
    # Phase 4 — Synthesize (S4 integration)
    # ------------------------------------------------------------------

    async def _phase_synthesize(
        self, query: str, observations: list[str]
    ) -> WorkspaceReport:
        """Feed observations into S4 workspace report compression."""
        report = WorkspaceReport(
            report_text=f"Research query: {query}",
            key_findings=[],
            step_count=0,
        )

        if not observations:
            return report

        # Group observations into manageable batches and update in sequence.
        batch_size = max(1, len(observations) // 3)
        for start in range(0, len(observations), batch_size):
            batch = observations[start : start + batch_size]
            combined = "\n".join(f"- {o}" for o in batch)

            # Pre-compute the compressed text through the LLM, then wrap it
            # in a synchronous closure for S4.
            if self._llm_fn is not None:
                compressed = await self._llm_synthesize(
                    report.report_text, combined,
                    f"Batch {start // batch_size + 1} of observations",
                    report.key_findings,
                    report.step_count,
                )
                # S4 expects a sync callable; our async work is already done.
                synthesize_fn = lambda _prompt, _text=compressed: _text
            else:
                synthesize_fn = None

            report = report.update(
                new_observations=combined,
                action_outcome=f"Batch {start // batch_size + 1} of observations",
                strategy=self._compaction_strategy,
                synthesize_fn=synthesize_fn,
            )

        return report

    async def _llm_synthesize(
        self,
        current_report: str,
        new_observations: str,
        action_outcome: str,
        key_findings: list[str],
        step_count: int,
    ) -> str:
        """
        Build the S4 synthesis prompt and run it through the configured LLM.

        Returns the compressed text directly so the caller can wrap it in a
        synchronous closure for ``WorkspaceReport.update(synthesize_fn=...)``.
        """
        from src.context.compaction import COMPACTION_PROMPTS

        prompt_template = COMPACTION_PROMPTS[self._compaction_strategy]
        findings_str = "\n".join(f"- {f}" for f in key_findings) if key_findings else "_(none yet)_"

        prompt = prompt_template.format(
            current_report=current_report,
            new_observations=new_observations,
            action_outcome=action_outcome,
            key_findings=findings_str,
            step_count=step_count,
        )
        return await self._call_llm(prompt)

    # ------------------------------------------------------------------
    # Phase 5 — Citation Verification
    # ------------------------------------------------------------------

    async def _phase_verify_citations(
        self,
        observations: list[str],
        search_results: list[SearchResult],
    ) -> list[Citation]:
        """
        Cross-check each observation against the relevant source URLs.

        Uses the ``verify_fn`` provider to produce verified ``Citation``
        objects.  If no verify_fn is configured, all observations are treated
        as unverified (confidence=0.5).
        """
        if not observations:
            return []

        citations: list[Citation] = []
        verify = self._verify_fn

        # Build a simple mapping: match observations to the snippet of the
        # search result they likely came from (heuristic: first result).
        for i, obs in enumerate(observations):
            source = search_results[i % len(search_results)] if search_results else None
            source_url = source.url if source else ""
            source_snippet = source.snippet if source else ""

            if verify is not None:
                try:
                    if asyncio.iscoroutinefunction(verify):
                        citation = await verify(obs, source_url)
                    else:
                        loop = asyncio.get_running_loop()
                        citation = await loop.run_in_executor(None, verify, obs, source_url)
                except Exception as exc:
                    logger.debug("Verification failed for observation: %s", exc)
                    citation = Citation(
                        claim=obs,
                        source_url=source_url,
                        source_snippet=source_snippet,
                        verified=False,
                        confidence=0.0,
                    )
            else:
                citation = Citation(
                    claim=obs,
                    source_url=source_url,
                    source_snippet=source_snippet,
                    verified=False,
                    confidence=0.5,
                )

            citations.append(citation)

        return citations

    # ------------------------------------------------------------------
    # Domain inference
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_domains(query: str, sub_queries: list[str]) -> list[SourceDomain]:
        """
        Heuristically decide which source domains to search.

        Always includes WEB.  Includes CODE if the query smells like
        code/research.  Includes DOCS for framework-specific queries.
        Includes ACADEMIC for research-heavy queries.
        """
        domains = {SourceDomain.WEB}

        all_text = (query + " " + " ".join(sub_queries)).lower()

        code_keywords = {"code", "api", "function", "class", "library",
                         "repository", "github", "implementation", "source code"}
        if any(kw in all_text for kw in code_keywords):
            domains.add(SourceDomain.CODE)

        docs_keywords = {"documentation", "docs", "how to", "guide", "tutorial",
                         "reference", "sdk", "framework"}
        if any(kw in all_text for kw in docs_keywords):
            domains.add(SourceDomain.DOCS)

        academic_keywords = {"research", "paper", "study", "survey", "arxiv",
                             "experiment", "evaluation", "benchmark"}
        if any(kw in all_text for kw in academic_keywords):
            domains.add(SourceDomain.ACADEMIC)

        return list(domains)

    # ------------------------------------------------------------------
    # LLM helper
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider, handling sync and async variants."""
        if self._llm_fn is None:
            raise RuntimeError("No llm_fn configured.")

        if asyncio.iscoroutinefunction(self._llm_fn):
            return await self._llm_fn(prompt)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._llm_fn, prompt)
