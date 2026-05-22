from lyra_workflow_compiler import WorkflowCompiler
class TestWorkflowCompiler:
    def test_compile(self):
        c = WorkflowCompiler()
        r = c.compile([{"name": "search", "action": "search_web", "inputs": ["query"], "outputs": ["results"]}, {"name": "analyze", "action": "analyze", "inputs": ["results"], "outputs": ["insights"]}])
        assert len(r.steps) == 2
    def test_parallel_optimization(self):
        c = WorkflowCompiler()
        r = c.compile([{"name": "a", "action": "a", "inputs": ["x"], "outputs": ["y"]}, {"name": "b", "action": "b", "inputs": ["z"], "outputs": ["w"]}])
        assert r.steps[-1].is_parallel
