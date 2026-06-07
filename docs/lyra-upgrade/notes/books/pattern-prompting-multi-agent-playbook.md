# Building Complex Multi-Agent Systems Using Pattern Prompting — Best Practices Playbook

## Practice 1: Treat LLMs as Badly Behaving RESTful Endpoints
- **What:** Apply all standard enterprise integration patterns (retry, circuit breaker, rate limiting, logging, failover, redundancy) to LLM calls exactly as you would to any unreliable web service. The fact that the endpoint happens to be an LLM is irrelevant to most engineering challenges.
- **Why:** LLMs are non-deterministic, high-latency, unreliable, and insecure — characteristics that traditional enterprise middleware (message queues, ESBs, reverse proxies) was designed to handle decades ago. Using these proven tools eliminates the need for bespoke reliability logic.
- **Lyra route:** §4.1 (multi-agent architecture), §4.8 (reliability), §4.9 (harness engineering)
- **Source:** Chapter 1, Chapter 8

## Practice 2: Use Message Queues as the Agent Communication Substrate
- **What:** Implement agent-to-agent communication through a message broker (RabbitMQ), not through direct HTTP calls or in-process function invocations. Every agent interaction becomes a message on a queue with explicit exchanges, routing keys, and bindings.
- **Why:** Message queues provide decoupling, buffering, retry, backpressure management, observability, and independent scalability. A ReAct agent dispatch, a RAG retrieval, or a multi-LLM scatter-gather all become queue topologies that can be reasoned about, monitored, and modified independently.
- **Lyra route:** §4.1 (multi-agent architecture), §4.4 (message routing/plugins)
- **Source:** Chapters 4, 8, 9

## Practice 3: Implement Three-Tier Dead Letter Queues
- **What:** For every agent task queue, configure a three-tier DLQ topology: Tier 1 (30s retry for transient failures like timeouts), Tier 2 (5 min retry for persistent transient failures like rate limits), and Quarantine (no retry, manual replay only, triggers immediate alert). Classify every failure as: transient, persistent-transient, permanent, poison, expired, or rejected.
- **Why:** In production agentic systems, failures are structural, not exceptional. Tool timeouts, malformed LLM output, rate limit errors, and critic rejections are all expected events. Without explicit failure classification and routing, messages are silently lost or endlessly retried.
- **Lyra route:** §4.8 (reliability), §4.9 (harness engineering)
- **Source:** Chapter 8 (Table 8.2), Chapter 9

## Practice 4: Map GenAI Workflows to GoF and EIP Patterns Before Coding
- **What:** Before implementing any "agentic pattern" (ReAct, RAG, Plan-and-Execute, Multi-Agent), decompose it into GoF and EIP patterns. ReAct maps to Command + Mediator + Process Manager + Correlation Identifier. RAG maps to Decorator + Proxy + Claim Check + Content Enricher. Document these mappings explicitly in an architecture decision record.
- **Why:** Terms like "ReAct" and "RAG" describe workflow shapes, not software design patterns. They have no canonical participants, failure modes, or deployment structures. GoF and EIP patterns do. Naming them forces precision, makes design decisions visible, and enables LLM coding assistants to generate correct implementations (since LLMs are trained extensively on these patterns).
- **Lyra route:** §4.1 (multi-agent architecture), §4.4 (workflow engine)
- **Source:** Chapter 8 (Table 8.1)

## Practice 5: Use the Four-Action Decomposition for Custom Agent Design
- **What:** When designing a custom agent architecture, decompose requirements into four atomic actions: Decision making, Summarization, Information gathering, and Generation of output. Represent each component with a distinct shape on a whiteboard. Wire them together with arrows showing data flow direction. Optimize by eliminating unnecessary LLM calls and running independent components in parallel.
- **Why:** Canned "agentic patterns" rarely fit real-world requirements. A custom microarchitecture built from first principles — considering latency, cost, unpredictability, and non-determinism constraints — is almost always a better fit than one picked from a lineup of rubber-stamped patterns.
- **Lyra route:** §4.1 (agent role taxonomy), §4.4 (routing)
- **Source:** Chapter 7

## Practice 6: Implement the LLM Abstraction Layer for Model Portability
- **What:** Introduce a thin abstraction layer between your application logic and the LLM provider's API. Expose a stable internal interface that all agent components (Gather, Decide, Summarize, Output) call. Swap providers by changing only the implementation behind that interface.
- **Why:** The LLM landscape changes faster than any other technology sector. Models are superseded within months, providers change pricing and deprecate APIs, and some cease operations. A thin custom abstraction is often better than a heavy framework dependency (LangChain/LlamaIndex), which can itself become a source of lock-in.
- **Lyra route:** §4.5 (model routing), §4.4 (plugins/adapters)
- **Source:** Chapter 7

## Practice 7: Adopt Tiered Model Routing by Component Complexity
- **What:** Evaluate each agent component independently against representative inputs. Use the smallest/cheapest model that meets the quality bar for each task. Routing/classification → small model; summarization/synthesis → large model. This tiered approach can reduce overall LLM spend by 40-70%.
- **Why:** The pricing difference between frontier and smaller models can be an order of magnitude. A Decide component choosing between three response paths does not need the same model as a Summarize component producing nuanced long-form synthesis. Faster, smaller models also reduce wall-clock latency and enable higher concurrency.
- **Lyra route:** §4.5 (model routing), cost management
- **Source:** Chapter 7

## Practice 8: Build and Automate the Evaluation Dataset
- **What:** Create a curated evaluation dataset of 50-100 (target hundreds) (question → expected answer) pairs covering common cases, edge cases, and dangerous failure modes. Run automated evaluation pipeline in CI/CD on every prompt change, every data ingestion, and every model switch. Use multiple scoring strategies: exact match, semantic similarity, LLM-as-judge. Run each test case 5-10 times; report pass rate, not binary pass/fail.
- **Why:** Testing non-deterministic systems requires different approaches. A single test run is not sufficient. A test case that passes 9/10 times is fundamentally different from one that passes 5/10 times. Without this dataset, regressions are discovered in production.
- **Lyra route:** §4.6 (evaluation), §4.9 (observability)
- **Source:** Chapter 7

## Practice 9: Treat Prompt Changes as Code Deployments
- **What:** Store all prompts in version control with semantic versioning (v1.0.0, v2.0.0). Require PR review for prompt changes with evaluation dataset validation. Support independent prompt rollback (without code redeploy). Assign a designated prompt owner responsible for monitoring performance, responding to incidents, and managing the review process.
- **Why:** Prompts are the core logic of GenAI applications. Without versioning and governance, prompts become informal text snippets scattered across notebooks and chat messages — leading to chaos at scale when a regression needs to be traced.
- **Lyra route:** §4.5 (prompt management), §4.6 (evaluation)
- **Source:** Chapter 7

## Practice 10: Build a Security Architecture with LLM-Specific Threat Awareness
- **What:** Address prompt injection (direct and indirect), context window leakage, PII exposure, and output harm as first-class architectural concerns — not as "add later" items. Key mitigations: XML-style delimiters for untrusted input, dedicated LLM guard calls, PII shielding (pre-process anonymization + post-process re-substitution), output validation layer, document-level access controls on vector DB, and system prompts designed to be safe even if fully disclosed.
- **Why:** Security in GenAI applications is deeply entangled with architectural decisions. Retrofitting after the fact is expensive, disruptive, and sometimes impossible without fundamental redesign. The LLM introduces an entirely new class of vulnerabilities (prompt injection, indirect injection via ingested documents, context window leakage) distinct from traditional web application threats.
- **Lyra route:** §4.7 (safety), §4.2 (context management)
- **Source:** Chapter 7

## Practice 11: Manage Drift as a Deployment Event
- **What:** Treat every document ingestion, model version update, and embedding model change as a deployment event with the same quality gates as code deployment. Run the full evaluation suite after every vector database change. Sample 1% of embeddings post-ingestion and recompute similarities to detect silent corruption. Implement regression test suites specifically for drift detection.
- **Why:** New documents or model versions can shift retrieval results in ways that cascade into changed LLM outputs. "Different input will in all likelihood lead to different output." Drift is not a one-time concern — it is continuous and must be managed through automated quality gates.
- **Lyra route:** §4.6 (evaluation), §4.3 (data pipeline)
- **Source:** Chapter 5, Chapter 7

## Practice 12: Set Explicit Cost Models and Budget Controls from Day One
- **What:** Instrument every LLM call from the first prototype to log input/output token counts tagged by component (Gather, Decide, Summarize, Output). Build a cost model: average cost per request × projected volume × peak multiplier. Set daily spend alert at 150% of expected, hard cap at 200%. Require approval for any change projected to increase monthly spend >10%. Include LLM spend as a visible line item in engineering dashboards.
- **Why:** GenAI applications that feel inexpensive in prototype can become alarmingly expensive at scale. Tokens accumulate in ways that are easy to underestimate. A retry loop with missing back-off, a caching system that fails open, or a traffic spike can cause spending to spike dramatically within minutes. When cost is invisible, it is no one's responsibility.
- **Lyra route:** §4.9 (observability/monitoring), cost governance
- **Source:** Chapter 7

## Practice 13: Separate Data and Process Documents in RAG Design
- **What:** When designing RAG ingestion, distinguish between "data documents" (the content to be analyzed — financial statements, policy documents, customer records) and "process documents" (the methodology — accounting standards, analysis frameworks, evaluation rubrics). Write prompts that explicitly instruct the LLM to use the process documents to analyze the data documents.
- **Why:** This mirrors the computer science principle of separating data and functions, applied at the document level. It is an "extremely powerful paradigm" that enables a single system to handle multiple analysis methodologies by swapping the process document while keeping the same data.
- **Lyra route:** §4.3 (document ingestion), §4.2 (RAG design)
- **Source:** Chapter 5

## Practice 14: Conduct Pattern-Guided Audits of Existing Systems
- **What:** For any existing agentic system, audit the topology against established pattern requirements. Check: every queue has a DLX configured, all consumers use manual ACK, vhosts are isolated across trust boundaries, message payloads do not carry credentials (use Claim Check), correlation IDs are threaded through all messages, and failure classes are explicitly defined.
- **Why:** Most production failures in GenAI systems are integration-layer failures — messages that cannot be retried safely, agents that crash and lose in-flight work, workflows that stall on downstream timeouts. These are precisely the problems EIP patterns were designed to solve. An audit against pattern requirements surfaces these issues before they cause outages.
- **Lyra route:** §4.9 (harness engineering), §4.8 (reliability)
- **Source:** Chapter 8

## Practice 15: Use the Command Pattern for All Agent Task Messages
- **What:** Structure every agent task message as a self-contained Command: action type, all parameters, agent identity, timestamp, and correlation identifier — everything needed for replay without external context. A Command message that is NACKed and routed to the DLQ can be inspected, corrected, and replayed without any context lookup.
- **Why:** Ad hoc messages that depend on external state cannot be replayed safely because the state may have changed. This matters critically for the dead letter channel — messages in quarantine need to be replayable. The Command pattern ensures every message carries its own context.
- **Lyra route:** §4.4 (message design), §4.8 (reliability/replay)
- **Source:** Chapter 8
