from lyra_multilingual import MultilingualAgent
class TestMultilingual:
    def test_detect(self):
        m = MultilingualAgent(); lang = m.detect_language("这是一个测试")
        assert lang == "zh"
    def test_translate(self):
        m = MultilingualAgent(); t = m.translate("Hello", "en", "fr")
        assert t.target_lang == "fr"
