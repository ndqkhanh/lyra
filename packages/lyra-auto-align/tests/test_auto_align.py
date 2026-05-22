from lyra_auto_align import AutoAlignmentResearcher

class TestAutoAlignmentResearcher:
    def test_discover_improvements(self):
        a = AutoAlignmentResearcher(num_copies=3)
        import asyncio
        improvements = asyncio.run(a.discover_improvements())
        assert len(improvements) == 3
    
    def test_filter_valid(self):
        a = AutoAlignmentResearcher(num_copies=2)
        import asyncio
        asyncio.run(a.discover_improvements())
        valid = a.filter_valid()
        assert isinstance(valid, list)
