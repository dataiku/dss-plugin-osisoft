from osisoft_client import OSIsoftClient
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode


def do(payload, config, plugin_config, inputs):
    config["is_ssl_check_disabled"] = True
    print("ALX:af explorer do, payload={}, config={}, plugin_config={}, inputs={}".format(payload, config, plugin_config, inputs))
    if "config" in config:
        config = config.get("config")
    if "credentials" not in config:
        return {"choices": [{"label": "Requires DSS v10.0.4 or above. Please use the OSIsoft Search custom dataset instead"}]}
    elif config.get("credentials") == {}:
        return {"choices": [{"label": "Pick a credential"}]}

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
    is_ssl_check_disabled = True
    print("ALX:is_ssl_check_disabled={}".format(is_ssl_check_disabled))

    client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode)
    print("ALX:2")

    method = payload.get("method")
    if method == "get_query_catalogs":
        return get_query_catalogs(None, config)

    parameter_name = payload.get("parameterName")

    if parameter_name == "server_name":
        choices = []
        print("ALX:do function")
        servers = client.get_asset_servers(can_raise=False)
        print("ALX:servers={}".format(servers))
        choices.extend(servers)
        print("ALX:server choices={}".format(choices))
        return build_select_choices(choices)

    if parameter_name == "data_server_url":
        choices = []
        choices.extend(client.get_data_servers(can_raise=False))
        return build_select_choices(choices)

    if parameter_name == "database_name":
        choices = []
        next_url = config.get("server_name")
        if next_url:
            choices.extend(client.get_next_choices(next_url, "Self"))
            return build_select_choices(choices)
        else:
            return build_select_choices()

    return build_select_choices()


def get_query_catalogs(cnx, config):
    print("ALX:def get_query_catalogs")
    print("ALX:cnx={}, config={}".format(cnx, config))
    user = config.get("credentials", {}).get("osisoft_basic", {}).get("user")
    password = config.get("credentials", {}).get("osisoft_basic", {}).get("password")
    return {"choices": [user, password]}


def get_children(username, password, source_item_url):
    pass
