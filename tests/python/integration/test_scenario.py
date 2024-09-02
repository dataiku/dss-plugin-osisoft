from dku_plugin_test_utils import dss_scenario

TEST_PROJECT_KEY = "PLUGINTESTPISYSTEM"


def test_run_pisystem_authentication_modes(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="AuthenticationModes")


def test_run_pisystem_ssl_certificate(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SSLCERTIFICATE")


def test_run_pisystem_asset_search_and_download(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ASSETSSEARCHDOWNLOAD")


def test_run_pisystem_event_frame_search_and_download(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="EVENT_FRAME_SEARCH_DOWNLOAD")


def test_run_pisystem_write_to_asset(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="WRITE_TO_ASSET_TEST")


def test_run_pisystem_sync_and_transpose_test(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="SYNC_AND_TRANSPOSE_TEST")


def test_run_pisystem_check_sc_116617(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="CHECK_SC_116617")


def test_run_pisystem_beyond_maxcount(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="BEYONDMAXCOUNT")


def test_run_pisystem_assets_values_download_with_404(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="ASSETS_VALUES_DOWNLOAD_WITH_404")


def test_run_pisystem_tag_with_spaces(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="TAG_WITH_SPACES")
