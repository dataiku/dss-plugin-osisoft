from osisoft_client import OSIsoftClient
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode
from osisoft_domain_handling import DomainHandler


def do(payload, config, plugin_config, inputs):
    if "config" in config:
        config = config.get("config")
    if "credentials" not in config:
        return {"choices": [{"label": "Requires DSS v10.0.4 or above. Please use the OSIsoft Search custom dataset instead"}]}
    elif config.get("credentials") == {}:
        return {"choices": [{"label": "Pick a credential"}]}
    domain_handler = DomainHandler(config)

    auth_type, username, password, server_url, is_ssl_check_disabled, credential_error = get_credentials(config, can_raise=False)

    if credential_error:
        return build_select_choices(credential_error)

    if not (auth_type and username and password):
        return build_select_choices("Pick a credential")

    if not username or not password:
        return build_select_choices(
            "Incorrect credential. "
            + "Go to you profile page > Credentials > Your preset, click the edit button and fill in you username and password details."
        )

    if not server_url:
        return build_select_choices("Fill in the server address")

    is_debug_mode = check_debug_mode(config)

    client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode)

    parameter_name = payload.get("parameterName")

    if parameter_name == "data_server_url":
        choices = []
        choices.extend(
            domain_handler.ui_side_url(
                client.get_data_servers(can_raise=False)
            )
        )
        return build_select_choices(choices)

    return build_select_choices()
