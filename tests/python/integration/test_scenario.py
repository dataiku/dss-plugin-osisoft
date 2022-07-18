from dku_plugin_test_utils import dss_scenario

TEST_PROJECT_KEY = "PLUGINTESTOSISOFT"


def test_run_osisoft_authentication_modes(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="AuthenticationModes")


def test_run_osisoft_ssl_certificate(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SSLCERTIFICATE")


def test_run_osisoft_asset_search_and_download(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ASSETSSEARCHDOWNLOAD")


def test_run_osisoft_event_frame_search_and_download(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="EVENT_FRAME_SEARCH_DOWNLOAD")


def test_run_osisoft_write_to_asset(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="WRITE_TO_ASSET_TEST")


def test_run_osisoft_sync_and_transpose_test(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SYNC_AND_TRANSPOSE_TEST")
