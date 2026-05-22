from lyra_edge import EdgeRuntime
class TestEdgeRuntime:
    def test_register(self): r = EdgeRuntime(); d = r.register_device("phone", 256, 512); assert d.name == "phone"
    def test_can_run(self): r = EdgeRuntime(); r.register_device("watch", 64, 128); assert not r.can_run("watch", 128)
    def test_offline(self): r = EdgeRuntime(); r.register_device("phone"); r.go_offline("phone"); assert not r.devices["phone"].is_online
