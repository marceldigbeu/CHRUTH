import ao_config


def test_recolte_config():
    assert ao_config.AO_LOOKBACK_DAYS == 14
    assert ao_config.AO_MAX_EXPORT_ROWS == 100
    assert ao_config.AO_MAX_PAGES >= 100
