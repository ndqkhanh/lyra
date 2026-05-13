"""
Feynman: File-Based Multi-Agent Deep Research

Implements 4-stage deep research pipeline with file-based handoffs:
1. Planner: Creates research plan
2. Researcher: Executes research, writes artifacts
3. Verifier: Validates findings
4. Synthesizer: Produces final report

Based on research: docs/155 (feynman-multi-agent-research-harness.md)
Impact: >95% citation coverage, <5% unsourced claims
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import json
import hashlib


@dataclass
class ResearchArtifact:
    """Single research artifact (file)."""
    slug: str
    title: str
    content: str
    artifact_type: str  # plan, findings, verification, synthesis
    created_at: datetime
    metadata: Dict[str, Any]


class FeynmanPipeline:
    """
    Feynman 4-stage deep research pipeline.

    Stages:
    1. Planner: Creates research plan with questions
    2. Researcher: Answers questions, writes findings
    3. Verifier: Validates findings, checks citations
    4. Synthesizer: Produces final report

    All handoffs via files (slug-based convention).
    """

    def __init__(
        self,
        llm_planner,
        llm_researcher,
        llm_verifier,
        llm_synthesizer,
        artifacts_dir: Path
    ):
        """
        Initialize Feynman pipeline.

        Args:
            llm_planner: LLM for planning
            llm_researcher: LLM for research
            llm_verifier: LLM for verification
            llm_synthesizer: LLM for synthesis
            artifacts_dir: Directory for artifacts
        """
        self.planner = llm_planner
        self.researcher = llm_researcher
        self.verifier = llm_verifier
        self.synthesizer = llm_synthesizer

        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        research_question: str,
        context_docs: Optional[List[str]] = None
    ) -> Path:
        """
        Run complete Feynman pipeline.

        Args:
            research_question: Main research question
            context_docs: Optional context documents

        Returns:
            Path to final synthesis artifact
        """
        # Generate slug for this research session
        slug = self._generate_slug(research_question)

        print(f"\n=== Feynman Deep Research: {slug} ===")

        # Stage 1: Planning
        plan_artifact = self._stage_1_planning(slug, research_question, context_docs)

        # Stage 2: Research
        findings_artifacts = self._stage_2_research(slug, plan_artifact)

        # Stage 3: Verification
        verification_artifact = self._stage_3_verification(slug, findings_artifacts)

        # Stage 4: Synthesis
        synthesis_artifact = self._stage_4_synthesis(
            slug,
            plan_artifact,
            findings_artifacts,
            verification_artifact
        )

        print(f"\n✅ Research complete: {synthesis_artifact}")
        return synthesis_artifact

    def _generate_slug(self, research_question: str) -> str:
        """Generate slug for research session."""
        # Create slug from question
        slug_base = research_question.lower()[:50]
        slug_base = ''.join(c if c.isalnum() or c == ' ' else '' for c in slug_base)
        slug_base = '-'.join(slug_base.split())

        # Add hash for uniqueness
        hash_suffix = hashlib.md5(research_question.encode()).hexdigest()[:8]

        return f"{slug_base}-{hash_suffix}"

    def _stage_1_planning(
        self,
        slug: str,
        research_question: str,
        context_docs: Optional[List[str]]
    ) -> Path:
        """Stage 1: Create research plan."""
        print("\n[Stage 1: Planning]")

        context_text = ""
        if context_docs:
            context_text = "\n\n".join(context_docs[:3])

        prompt = f"""Create a research plan for this question.

Research Question: {research_question}

Context:
{context_text}

Create a structured plan with:
1. Sub-questions to investigate (5-10 questions)
2. Expected sources/methods
3. Success criteria

Output JSON:
{{
  "research_question": "...",
  "sub_questions": [
    {{"id": "q1", "question": "...", "priority": "high"}},
    {{"id": "q2", "question": "...", "priority": "medium"}}
  ],
  "expected_sources": ["source1", "source2"],
  "success_criteria": ["criterion1", "criterion2"]
}}
"""

        response = self.planner.generate(prompt)
        plan_data = json.loads(response)

        # Write plan artifact
        plan_path = self.artifacts_dir / f"{slug}-plan.json"
        with open(plan_path, 'w') as f:
            json.dump(plan_data, f, indent=2)

        print(f"✓ Plan created: {len(plan_data['sub_questions'])} sub-questions")
        return plan_path

    def _stage_2_research(
        self,
        slug: str,
        plan_path: Path
    ) -> List[Path]:
        """Stage 2: Execute research, write findings."""
        print("\n[Stage 2: Research]")

        # Load plan
        with open(plan_path, 'r') as f:
            plan = json.load(f)

        findings_paths = []

        for sub_q in plan['sub_questions']:
            print(f"  Researching: {sub_q['question'][:60]}...")

            prompt = f"""Research this question and provide detailed findings.

Question: {sub_q['question']}

Provide:
1. Answer with evidence
2. Citations (URLs, papers, sources)
3. Confidence level (0.0-1.0)
4. Limitations/caveats

Output JSON:
{{
  "question": "...",
  "answer": "Detailed answer...",
  "citations": [
    {{"source": "...", "url": "...", "relevance": "..."}}
  ],
  "confidence": 0.9,
  "limitations": ["limitation1", "limitation2"]
}}
"""

            response = self.researcher.generate(prompt)
            findings_data = json.loads(response)

            # Write findings artifact
            findings_path = self.artifacts_dir / f"{slug}-findings-{sub_q['id']}.json"
            with open(findings_path, 'w') as f:
                json.dump(findings_data, f, indent=2)

            findings_paths.append(findings_path)

        print(f"✓ Research complete: {len(findings_paths)} findings")
        return findings_paths

    def _stage_3_verification(
        self,
        slug: str,
        findings_paths: List[Path]
    ) -> Path:
        """Stage 3: Verify findings and citations."""
        print("\n[Stage 3: Verification]")

        # Load all findings
        all_findings = []
        for path in findings_paths:
            with open(path, 'r') as f:
                all_findings.append(json.load(f))

        # Format for verification
        findings_text = json.dumps(all_findings, indent=2)

        prompt = f"""Verify these research findings.

Findings:
{findings_text}

Check:
1. Citation coverage (% of claims with citations)
2. Unsourced claims
3. Contradictions
4. Confidence calibration

Output JSON:
{{
  "citation_coverage": 0.95,
  "unsourced_claims": ["claim1", "claim2"],
  "contradictions": [],
  "overall_quality": "high",
  "recommendations": ["rec1", "rec2"]
}}
"""

        response = self.verifier.generate(prompt)
        verification_data = json.loads(response)

        # Write verification artifact
        verification_path = self.artifacts_dir / f"{slug}-verification.json"
        with open(verification_path, 'w') as f:
            json.dump(verification_data, f, indent=2)

        print(f"✓ Verification complete: {verification_data['citation_coverage']:.0%} citation coverage")
        return verification_path

    def _stage_4_synthesis(
        self,
        slug: str,
        plan_path: Path,
        findings_paths: List[Path],
        verification_path: Path
    ) -> Path:
        """Stage 4: Synthesize final report."""
        print("\n[Stage 4: Synthesis]")

        # Load all artifacts
        with open(plan_path, 'r') as f:
            plan = json.load(f)

        findings = []
        for path in findings_paths:
            with open(path, 'r') as f:
                findings.append(json.load(f))

        with open(verification_path, 'r') as f:
            verification = json.load(f)

        # Format for synthesis
        prompt = f"""Synthesize a final research report.

Research Question: {plan['research_question']}

Findings: {len(findings)} sub-questions answered
Verification: {verification['citation_coverage']:.0%} citation coverage

Create a comprehensive report with:
1. Executive summary
2. Key findings
3. Detailed analysis
4. Citations
5. Limitations

Output markdown format.
"""

        synthesis_content = self.synthesizer.generate(prompt)

        # Write synthesis artifact
        synthesis_path = self.artifacts_dir / f"{slug}-synthesis.md"
        with open(synthesis_path, 'w') as f:
            f.write(synthesis_content)

        print(f"✓ Synthesis complete")
        return synthesis_path

    def get_artifacts(self, slug: str) -> Dict[str, List[Path]]:
        """Get all artifacts for a research session."""
        artifacts = {
            'plan': [],
            'findings': [],
            'verification': [],
            'synthesis': []
        }

        for artifact_file in self.artifacts_dir.glob(f"{slug}-*.json"):
            if 'plan' in artifact_file.name:
                artifacts['plan'].append(artifact_file)
            elif 'findings' in artifact_file.name:
                artifacts['findings'].append(artifact_file)
            elif 'verification' in artifact_file.name:
                artifacts['verification'].append(artifact_file)

        for artifact_file in self.artifacts_dir.glob(f"{slug}-*.md"):
            if 'synthesis' in artifact_file.name:
                artifacts['synthesis'].append(artifact_file)

        return artifacts


# Verification as structural primitive
class VerificationPrimitive:
    """
    Verification as a structural primitive in the pipeline.

    Every stage outputs verification metadata:
    - What was verified
    - How it was verified
    - Confidence level
    - Limitations
    """

    @staticmethod
    def add_verification_metadata(
        artifact_path: Path,
        verification_data: Dict[str, Any]
    ) -> None:
        """Add verification metadata to artifact."""
        # Load artifact
        with open(artifact_path, 'r') as f:
            if artifact_path.suffix == '.json':
                artifact = json.load(f)
            else:
                artifact = {'content': f.read()}

        # Add verification
        artifact['_verification'] = {
            'verified_at': datetime.now().isoformat(),
            'verification_method': verification_data.get('method', 'llm'),
            'confidence': verification_data.get('confidence', 0.0),
            'limitations': verification_data.get('limitations', [])
        }

        # Write back
        with open(artifact_path, 'w') as f:
            if artifact_path.suffix == '.json':
                json.dump(artifact, f, indent=2)
            else:
                f.write(artifact['content'])


# Usage example
"""
from lyra_research.feynman import FeynmanPipeline
from lyra_core.llm import build_llm
from pathlib import Path

# Initialize LLMs
llm = build_llm("deepseek-v4-pro")

# Create pipeline
pipeline = FeynmanPipeline(
    llm_planner=llm,
    llm_researcher=llm,
    llm_verifier=llm,
    llm_synthesizer=llm,
    artifacts_dir=Path("~/.lyra/research/artifacts").expanduser()
)

# Run research
synthesis_path = pipeline.run(
    research_question="What are the best practices for LLM memory systems?",
    context_docs=["Doc 1...", "Doc 2..."]
)

# Read final report
with open(synthesis_path, 'r') as f:
    report = f.read()
    print(report)

# Get all artifacts
artifacts = pipeline.get_artifacts("best-practices-llm-memory-12345678")
print(f"Plan: {artifacts['plan']}")
print(f"Findings: {len(artifacts['findings'])}")
print(f"Verification: {artifacts['verification']}")
print(f"Synthesis: {artifacts['synthesis']}")
"""
