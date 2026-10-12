from baseline.cluster import rules_classify


def test_rules_use_config_theme_names():
    got = rules_classify([{"url": "u", "title": "LiteLlm streaming drops thought_signature", "labels": []}])
    assert got == {"u": "Model providers and streaming"}
