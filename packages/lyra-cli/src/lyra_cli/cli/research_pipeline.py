"""Real Deep Research Engine for Lyra.

Multi-hop web retrieval + LLM synthesis + citation grounding.

Pipeline (GPT-Researcher / STORM inspired):
  Phase 1 · Decompose    — LLM generates 4-6 targeted sub-questions
  Phase 2 · Search       — parallel web search for each sub-question
  Phase 3 · Scrape       — fetch full content for top sources
  Phase 4 · Extract      — LLM distills key facts per source with [N] markers
  Phase 5 · Gap detect   — LLM identifies missing angles → follow-up queries
  Phase 6 · Follow-up    — targeted searches to fill gaps
  Phase 7 · Synthesize   — LLM writes full report with inline [N] citations
  Phase 8 · Cite         — build verified Sources section
  Phase 9 · Store        — archive session summary in ArchivalStore
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator

from .search_tools import SearchResult, build_provider


# Legacy dataclass kept for tui.py status bars that reference RESEARCH_PHASES
@dataclass
class ResearchPhase:
    name: str
    description: str
    weight: float


RESEARCH_PHASES = [
    ResearchPhase("Decompose",  "Breaking topic into sub-questions",    0.08),
    ResearchPhase("Search",     "Parallel web search",                  0.15),
    ResearchPhase("Scrape",     "Fetching full source content",         0.15),
    ResearchPhase("Extract",    "Distilling facts + citations",         0.18),
    ResearchPhase("Gap detect", "Identifying missing angles",           0.08),
    ResearchPhase("Follow-up",  "Targeted gap-fill searches",           0.10),
    ResearchPhase("Synthesize", "Writing report with citations",        0.16),
    ResearchPhase("Cite",       "Verifying & grounding citations",      0.05),
    ResearchPhase("Store",      "Archiving session to memory",          0.05),
]

# Max sources to scrape fully (keeps cost down)
_MAX_SCRAPE_PER_QUERY = 2
_MAX_QUERIES = 6
_SCRAPE_CHARS = 4000


class RealResearchPipeline:
    """End-to-end deep research with real web retrieval and citation grounding."""

    def __init__(
        self,
        client: Any,
        provider: str,          # "anthropic" | "openai"
        model_name: str,
        cred_mgr: Any = None,
    ) -> None:
        self._client = client
        self._provider = provider
        self._model_name = model_name
        self._cred_mgr = cred_mgr
        self._search: Any = None  # lazy — resolved on first run()

        self._sources: list[SearchResult] = []
        self._facts: list[str] = []         # "[N] fact text"
        self._report: str = ""

    # ── Public entry point ────────────────────────────────────────────────

    async def run(self, topic: str) -> AsyncIterator[dict]:
        """Stream progress events through all 9 phases.

        Yields dicts: {type: "phase"|"finding"|"progress"|"done"|"error", ...}
        Raises no exceptions — provider errors are yielded as {"type": "error"}.
        """
        if self._search is None:
            try:
                self._search = build_provider(self._cred_mgr)
            except RuntimeError as e:
                yield {"type": "error", "content": str(e)}
                return

        total = 0.0

        for phase in RESEARCH_PHASES:
            yield {"type": "phase", "phase": phase.name,
                   "progress": total, "content": phase.description}
            async for event in self._run_phase(phase.name, topic):
                yield event
            total += phase.weight
            yield {"type": "progress", "phase": phase.name,
                   "progress": min(total, 1.0), "content": f"{phase.name} complete"}

        yield {"type": "done", "phase": "Complete",
               "progress": 1.0, "content": self._report}

    # ── Phase dispatch ─────────────────────────────────────────────────────

    async def _run_phase(self, name: str, topic: str) -> AsyncIterator[dict]:
        if name == "Decompose":
            async for e in self._phase_decompose(topic): yield e
        elif name == "Search":
            async for e in self._phase_search(): yield e
        elif name == "Scrape":
            async for e in self._phase_scrape(): yield e
        elif name == "Extract":
            async for e in self._phase_extract(): yield e
        elif name == "Gap detect":
            async for e in self._phase_gap_detect(topic): yield e
        elif name == "Follow-up":
            async for e in self._phase_followup(): yield e
        elif name == "Synthesize":
            async for e in self._phase_synthesize(topic): yield e
        elif name == "Cite":
            async for e in self._phase_cite(): yield e
        elif name == "Store":
            async for e in self._phase_store(topic): yield e

    # ── Phase 1: Decompose ────────────────────────────────────────────────

    async def _phase_decompose(self, topic: str) -> AsyncIterator[dict]:
        yield {"type": "finding", "content": f"Decomposing: {topic!r}"}

        prompt = (
            f"Research topic: {topic}\n\n"
            "Generate exactly 5 focused sub-questions that together cover the topic comprehensively. "
            "Each sub-question should address a distinct angle: background, current state, "
            "technical details, key players, and practical implications.\n\n"
            "Respond with a JSON array of strings only. Example:\n"
            '["question 1", "question 2", "question 3", "question 4", "question 5"]'
        )
        raw = await self._llm(prompt, max_tokens=400)
        try:
            # Extract JSON array from response
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            questions: list[str] = json.loads(match.group()) if match else []
        except Exception:
            questions = []

        if not questions:
            questions = [
                f"What is {topic}?",
                f"What are the latest developments in {topic}?",
                f"What are the key technical aspects of {topic}?",
                f"Who are the main players or researchers in {topic}?",
                f"What are the practical applications and implications of {topic}?",
            ]

        questions = questions[:_MAX_QUERIES]
        self._pending_queries: list[str] = questions
        self._gap_queries: list[str] = []

        for i, q in enumerate(questions, 1):
            yield {"type": "finding", "content": f"  Sub-question {i}: {q}"}

    # ── Phase 2: Search ───────────────────────────────────────────────────

    async def _phase_search(self) -> AsyncIterator[dict]:
        provider_name = self._search.name
        yield {"type": "finding",
               "content": f"Searching via {provider_name} ({len(self._pending_queries)} queries in parallel)…"}

        tasks = [
            self._search.search(q, num_results=6)
            for q in self._pending_queries
        ]
        results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        for results in results_per_query:
            if not isinstance(results, list):
                continue
            for r in results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    r.source_idx = len(self._sources) + 1
                    self._sources.append(r)

        yield {"type": "finding",
               "content": f"Found {len(self._sources)} unique sources across {len(self._pending_queries)} queries"}

    # ── Phase 3: Scrape ───────────────────────────────────────────────────

    async def _phase_scrape(self) -> AsyncIterator[dict]:
        # Pick the top N sources per query (by score or order) for full scraping
        to_scrape = self._sources[:_MAX_SCRAPE_PER_QUERY * len(self._pending_queries)]
        to_scrape = to_scrape[:12]  # Hard cap

        yield {"type": "finding", "content": f"Scraping {len(to_scrape)} sources for full content…"}

        async def _fetch_one(src: SearchResult) -> None:
            if src.content and len(src.content) > 800:
                return  # Already have content from search
            text = await self._search.scrape(src.url, max_chars=_SCRAPE_CHARS)
            if text:
                src.content = text

        await asyncio.gather(*[_fetch_one(s) for s in to_scrape], return_exceptions=True)

        content_count = sum(1 for s in self._sources if len(s.content) > 100)
        yield {"type": "finding", "content": f"Full content available for {content_count} sources"}

    # ── Phase 4: Extract facts ────────────────────────────────────────────

    async def _phase_extract(self) -> AsyncIterator[dict]:
        sources_with_content = [s for s in self._sources if len(s.content) > 100]
        yield {"type": "finding",
               "content": f"Extracting facts from {len(sources_with_content)} sources…"}

        async def _extract_one(src: SearchResult) -> list[str]:
            content_preview = src.content[:2000]
            prompt = (
                f"Source [{src.source_idx}]: {src.title}\n"
                f"URL: {src.url}\n\n"
                f"{content_preview}\n\n"
                f"Extract 3-5 key facts from this source. "
                f"Each fact must end with the citation [{src.source_idx}]. "
                f"Be specific and concrete — include numbers, dates, names where present. "
                f"One fact per line, no bullet points."
            )
            raw = await self._llm(prompt, max_tokens=300)
            facts = [
                line.strip()
                for line in raw.strip().splitlines()
                if line.strip() and f"[{src.source_idx}]" in line
            ]
            return facts if facts else [
                f"{src.snippet[:200]} [{src.source_idx}]"
            ]

        tasks = [_extract_one(s) for s in sources_with_content[:10]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for batch in results:
            if isinstance(batch, list):
                self._facts.extend(batch)

        yield {"type": "finding", "content": f"Extracted {len(self._facts)} cited facts"}

    # ── Phase 5: Gap detect ───────────────────────────────────────────────

    async def _phase_gap_detect(self, topic: str) -> AsyncIterator[dict]:
        if not self._facts:
            yield {"type": "finding", "content": "No facts to analyse for gaps"}
            return

        facts_sample = "\n".join(self._facts[:30])
        prompt = (
            f"Topic: {topic}\n\n"
            f"Facts gathered so far:\n{facts_sample}\n\n"
            "Identify 2-3 important angles that are NOT covered by the facts above. "
            "For each gap, write a specific search query that would fill it. "
            "Respond as a JSON array of query strings only. "
            "If coverage is already comprehensive, respond with []."
        )
        raw = await self._llm(prompt, max_tokens=200)
        try:
            match = re.search(r'\[.*?\]', raw, re.DOTALL)
            self._gap_queries = json.loads(match.group()) if match else []
        except Exception:
            self._gap_queries = []

        self._gap_queries = self._gap_queries[:3]
        if self._gap_queries:
            yield {"type": "finding",
                   "content": f"Identified {len(self._gap_queries)} coverage gaps — running follow-up searches"}
        else:
            yield {"type": "finding", "content": "Coverage is comprehensive — no gaps detected"}

    # ── Phase 6: Follow-up ────────────────────────────────────────────────

    async def _phase_followup(self) -> AsyncIterator[dict]:
        if not self._gap_queries:
            yield {"type": "finding", "content": "No gap queries — skipping follow-up"}
            return

        yield {"type": "finding",
               "content": f"Running {len(self._gap_queries)} gap-fill searches…"}

        tasks = [self._search.search(q, num_results=4) for q in self._gap_queries]
        results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls = {s.url for s in self._sources}
        new_count = 0
        for results in results_per_query:
            if not isinstance(results, list):
                continue
            for r in results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    r.source_idx = len(self._sources) + 1
                    self._sources.append(r)
                    new_count += 1

        if new_count:
            # Extract facts from the new sources too
            new_sources = [s for s in self._sources if s.source_idx > len(self._sources) - new_count]
            for src in new_sources[:6]:
                if len(src.content) < 100:
                    src.content = await self._search.scrape(src.url, max_chars=_SCRAPE_CHARS)
                if src.content:
                    prompt = (
                        f"Source [{src.source_idx}]: {src.title}\n{src.content[:1500]}\n\n"
                        f"Extract 2-3 key facts. Each must end with [{src.source_idx}]. One per line."
                    )
                    raw = await self._llm(prompt, max_tokens=200)
                    for line in raw.strip().splitlines():
                        if line.strip() and f"[{src.source_idx}]" in line:
                            self._facts.append(line.strip())

        yield {"type": "finding",
               "content": f"Added {new_count} new sources, {len(self._facts)} total facts"}

    # ── Phase 7: Synthesize ───────────────────────────────────────────────

    async def _phase_synthesize(self, topic: str) -> AsyncIterator[dict]:
        yield {"type": "finding", "content": "Synthesizing report with inline citations…"}

        facts_block = "\n".join(f"• {f}" for f in self._facts[:60])
        sources_block = "\n".join(
            f"[{s.source_idx}] {s.title} — {s.url}"
            for s in self._sources[:25]
        )

        prompt = (
            f"You are a research analyst. Write a comprehensive research report on:\n"
            f"**{topic}**\n\n"
            f"Use the following cited facts as your evidence base:\n"
            f"{facts_block}\n\n"
            f"Available sources (use [N] notation for inline citations):\n"
            f"{sources_block}\n\n"
            "Write the report in this structure:\n"
            "## Executive Summary\n"
            "3-4 sentences covering the most important findings.\n\n"
            "## Background\n"
            "Context and why this topic matters.\n\n"
            "## Key Findings\n"
            "Detailed findings with inline [N] citations for every claim.\n\n"
            "## Current State & Trends\n"
            "What is happening today, with dates and specifics.\n\n"
            "## Analysis\n"
            "Synthesis, patterns, implications.\n\n"
            "## Recommendations\n"
            "Actionable takeaways.\n\n"
            "Rules: cite every factual claim with [N], use markdown headers, "
            "be specific (numbers, names, dates), do not fabricate — only use provided facts."
        )

        self._report = await self._llm(prompt, max_tokens=2000)
        yield {"type": "finding", "content": f"Report generated ({len(self._report)} chars)"}

    # ── Phase 8: Cite ─────────────────────────────────────────────────────

    async def _phase_cite(self) -> AsyncIterator[dict]:
        # Find which [N] citations are actually used in the report
        used_idxs = set(int(m) for m in re.findall(r'\[(\d+)\]', self._report))

        sources_section = "\n\n## Sources\n\n"
        cited_sources = [s for s in self._sources if s.source_idx in used_idxs]
        uncited = [s for s in self._sources if s.source_idx not in used_idxs]

        for src in sorted(cited_sources, key=lambda s: s.source_idx):
            pub = f" ({src.published})" if src.published else ""
            sources_section += f"[{src.source_idx}] [{src.title}]({src.url}){pub}\n"

        if uncited:
            sources_section += "\n*Additional sources consulted (not directly cited):*\n"
            for src in uncited[:5]:
                sources_section += f"- [{src.title}]({src.url})\n"

        self._report += sources_section

        yield {"type": "finding",
               "content": (
                   f"{len(cited_sources)} citations verified · "
                   f"{len(self._sources)} total sources · "
                   f"provider: {self._search.name}"
               )}

    # ── Phase 9: Store ────────────────────────────────────────────────────

    async def _phase_store(self, topic: str) -> AsyncIterator[dict]:
        try:
            from .memory_manager import MemoryManager
            mm = MemoryManager()
            import hashlib, time
            session_id = f"research_{hashlib.md5(topic.encode()).hexdigest()[:8]}_{int(time.time())}"
            summary = (
                f"Deep research on '{topic}'. "
                f"{len(self._sources)} sources, {len(self._facts)} facts. "
                f"Provider: {self._search.name}. "
                f"Key findings: {' '.join(self._facts[:3])[:300]}"
            )
            mm.archive_session(session_id, summary, tags=["research", topic.split()[0]])
            yield {"type": "finding", "content": f"Session archived to memory (id: {session_id[:20]})"}
        except Exception as e:
            yield {"type": "finding", "content": f"Memory store skipped: {e}"}

    # ── LLM helper ────────────────────────────────────────────────────────

    async def _llm(self, prompt: str, max_tokens: int = 800) -> str:
        """Single non-streaming LLM call for pipeline orchestration."""
        messages = [{"role": "user", "content": prompt}]
        try:
            if self._provider == "anthropic":
                resp = await self._client.messages.create(
                    model=self._model_name,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                return resp.content[0].text if resp.content else ""
            else:  # openai / deepseek
                resp = await self._client.chat.completions.create(
                    model=self._model_name,
                    max_tokens=max_tokens,
                    messages=messages,
                )
                return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[LLM error: {e}]"
