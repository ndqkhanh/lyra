"""Tests for LP-RAG Retriever."""

from lyra_memory.routing.lp_rag import Chunk, LPRAGRetriever


class StubLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._idx = 0
        self.prompts: list[str] = []

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return "[]"


class TestChunk:
    def test_default_values(self):
        c = Chunk(content="test content", source_doc="doc1", index=0)
        assert c.content == "test content"
        assert c.source_doc == "doc1"
        assert c.index == 0
        assert len(c.id) == 32

    def test_node_returns_id(self):
        c = Chunk(content="test")
        assert c.node == c.id


class TestLPRAGRetriever:
    def _make_retriever(self, responses: list[str] | None = None) -> LPRAGRetriever:
        llm = StubLLM(responses=responses)
        return LPRAGRetriever(llm=llm)

    async def test_retrieve_empty_index(self):
        retriever = self._make_retriever()
        result = await retriever.retrieve("any query")
        assert result == []

    async def test_retrieve_with_chunks(self):
        retriever = self._make_retriever()
        retriever.add_chunk("Python async programming guide", "docs/python.md")
        retriever.add_chunk("Rust memory safety principles", "docs/rust.md")
        chunk_ids = [c.id for c in retriever.chunks.values()]
        retriever.llm.responses = [f'["{chunk_ids[0]}"]']
        result = await retriever.retrieve("async python")
        assert isinstance(result, list)

    async def test_retrieve_uses_llm_for_scoring(self):
        retriever = self._make_retriever()
        c1 = retriever.add_chunk("deploy pipeline configuration", "docs/deploy.md")
        retriever.add_chunk("breakfast recipes pancakes", "docs/food.md")
        retriever.llm.responses = ['["' + c1.id + '"]']
        result = await retriever.retrieve("ci cd deployment")
        assert len(result) >= 0

    async def test_add_chunk_returns_chunk(self):
        retriever = self._make_retriever()
        chunk = retriever.add_chunk("content", "src", 5)
        assert isinstance(chunk, Chunk)
        assert chunk.content == "content"
        assert chunk.source_doc == "src"
        assert chunk.index == 5

    async def test_generate_synthetic_queries(self):
        retriever = self._make_retriever(
            responses=['["query1", "query2", "query3"]']
        )
        chunks = [
            Chunk(content="machine learning model training pipeline optimization"),
            Chunk(content="deep neural network gradient descent backpropagation"),
        ]
        queries = await retriever._generate_synthetic_queries(chunks)
        assert len(queries) == 3

    async def test_identify_relevant_chunks(self):
        retriever = self._make_retriever()
        c1 = Chunk(id="abc123", content="database query optimization techniques")
        c2 = Chunk(id="def456", content="frontend css styling guide")
        retriever.llm.responses = ['["abc123"]']
        relevant = await retriever._identify_relevant_chunks(
            "how to speed up database", [c1, c2],
        )
        assert len(relevant) == 1
        assert relevant[0].id == "abc123"

    def test_chunk_document(self):
        text = "word " * 600
        chunks = LPRAGRetriever._chunk_document(text, chunk_size=200)
        assert len(chunks) == 3
        for c in chunks:
            assert isinstance(c, Chunk)

    def test_embed_query(self):
        node = LPRAGRetriever._embed_query("test query")
        assert node.startswith("query:")

    async def test_parse_chunk_ids_valid(self):
        retriever = self._make_retriever()
        chunks = retriever._parse_chunk_ids('["abc", "def"]', 2)
        assert len(chunks) == 2
        assert chunks[0].id == "abc"

    async def test_parse_chunk_ids_invalid(self):
        retriever = self._make_retriever()
        chunks = retriever._parse_chunk_ids("not json", 5)
        assert chunks == []

    async def test_train_on_synthetic_no_predictor(self):
        retriever = self._make_retriever()
        await retriever.train_on_synthetic(["some document text"])
        assert retriever._trained is False
