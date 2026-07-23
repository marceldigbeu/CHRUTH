import ao_config


def test_template_and_xlsm_paths_defined():
    assert ao_config.AO_TEMPLATE_XLSM.name == "AO_CHRUTH_TEMPLATE.xlsm"
    assert ao_config.AO_TEMPLATE_XLSM.parent.name == "assets"
    assert ao_config.AO_OUTPUT_XLSM.name == "AO_CHRUTH.xlsm"
    assert ao_config.AO_OUTPUT_XLSM.suffix == ".xlsm"
