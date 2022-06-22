from osisoft_client import OSIsoftClient
from osisoft_plugin_common import get_credentials, build_select_choices, build_requests_params


def do(payload, config, plugin_config, inputs):
    if "config" in config:
        config = config.get("config")
    if "credentials" not in config:
        return build_select_choices("Requires DSS v10.0.4 or above. Please use the OSIsoft Search custom dataset instead")
    elif config.get("credentials") == {}:
        return build_select_choices("Pick a credential")

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
    client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled)

    parameter_name = payload.get("parameterName")

    if parameter_name == "server_name":
        choices = []
        choices.extend(client.get_asset_servers())
        return build_select_choices(choices)

    if parameter_name == "database_name":
        choices = []
        next_url = config.get("server_name")
        if next_url:
            choices.extend(client.get_next_choices(next_url, "Self"))
            return build_select_choices(choices)
        else:
            return build_select_choices()

    if parameter_name == "category_name":
        choices = [{
            "label": "<All>",
            "value": None
        }]
        next_links = config.get("database_name")
        if not next_links:
            return build_select_choices()
        next_url = next_links + "/elementcategories"
        choices.extend(client.get_next_choices(next_url, "Self", use_name_as_link=True))
        return build_select_choices(choices)

    if parameter_name == "template_name":
        choices = [{
            "label": "<All>",
            "value": None
        }]
        next_links = config.get("database_name")
        if not next_links:
            return build_select_choices()
        next_url = next_links + "/elementtemplates"
        next_choices = client.get_next_choices(next_url, "Self", use_name_as_link=True, filter={'InstanceType': 'EventFrame'})
        choices.extend(next_choices)
        return build_select_choices(choices)

    if parameter_name == "event_frame_to_retrieve":
        choices = []
        next_links = config.get("database_name")
        if not next_links:
            return build_select_choices(choices)
        next_url = next_links + "/eventframes"
        params = build_requests_params(
            **config
        )
        endpoint_name = "Self"
        if config.get("must_download_data"):
            endpoint_name = config.get("data_type", "Self")
        choices.extend(client.get_next_choices(next_url, endpoint_name, params=params))
        return build_select_choices(choices)

    # if parameter_name == "data_type":
    #     event_frame_to_retrieve = config.get("event_frame_to_retrieve", [])
    #     if not event_frame_to_retrieve:
    #         return build_select_choices()
    #     next_url = event_frame_to_retrieve[0]
    #     choices = []
    #     links = client.get_item_from_url(next_url).get('Links', {})
    #     for link in links:
    #         choices.append({
    #             "label": link,
    #             "value": links[link]
    #         })
    #     return build_select_choices(choices)

    return build_select_choices()
# https://localhost/piwebapi/assetdatabases/{webid}/eventframes?startTime=*-10d
# categoryName
# templateName
# severity None Information Warning Minor Major Critical
