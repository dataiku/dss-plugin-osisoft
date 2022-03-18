from dku_plugin_test_utils import dss_scenario

TEST_PROJECT_KEY = "PLUGINTESTOSISOFT"


def test_run_sharepoint_online_authentication_modes(user_dss_clients):
    dss_scenario.run(user_dss_clients, project_key=TEST_PROJECT_KEY, scenario_id="AuthenticationModes")
