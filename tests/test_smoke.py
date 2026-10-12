import yaml


def test_config_has_all_themes():
    cfg = yaml.safe_load(open("config.yaml"))
    assert len(cfg["themes"]) == 11
    assert cfg["publish_bar"] == 0.95
