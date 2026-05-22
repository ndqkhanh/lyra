from lyra_distill import DistillPipeline
class TestDistillPipeline:
    def test_create_target(self):
        p = DistillPipeline(); dt = p.create_target("llama-70b", 140000, 7000)
        assert dt.compression_ratio == 20.0
    def test_distill(self):
        p = DistillPipeline(); dt = p.create_target("model", 1000, 100)
        r = p.distill(dt)
        assert r["compression"] == "10.0x"
    def test_quantize(self):
        p = DistillPipeline(); r = p.quantize(1000, 8)
        assert r["quantized_mb"] == 250.0
