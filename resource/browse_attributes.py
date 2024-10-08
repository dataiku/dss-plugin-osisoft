import json
import dataiku
from osisoft_client import OSIsoftClient
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode


def do(payload, config, plugin_config, inputs):
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

    client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode)

    parameter_name = payload.get("parameterName")

    if parameter_name == "server_name":
        choices = []
        choices.extend(client.get_asset_servers(can_raise=False))
        return build_select_choices(choices)

    if parameter_name == "database_name":
        choices = []
        next_url = config.get("server_name")
        if next_url:
            choices.extend(client.get_next_choices(next_url, "Self"))
            return build_select_choices(choices)
        else:
            return build_select_choices()

    if parameter_name == "element_category":
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

    if parameter_name == "element_template":
        choices = [{
            "label": "<All>",
            "value": None
        }]
        next_links = config.get("database_name")
        if not next_links:
            return build_select_choices()
        next_url = next_links + "/elementtemplates"
        choices.extend(client.get_next_choices(next_url, "Self", use_name_as_link=True, filter={'InstanceType': 'Element'}))
        choices.append({"label": "✍️ Enter manually", "value": "_DKU_manual_input"})
        choices.append({"label": "🗄️ Use a variable", "value": "_DKU_variable_select"})
        return build_select_choices(choices)

    if parameter_name == "element_template_variable_select":
        choices = []
        variables = dataiku.get_custom_variables()
        for variable in variables:
            choices.append(
                {
                    "label": variable,
                    "value": variable
                }
            )
        if not choices:
            return build_select_choices("No variable available")
        return build_select_choices(choices)

    if parameter_name == "attribute_category":
        choices = [{
            "label": "<All>",
            "value": None
        }]
        next_links = config.get("database_name")
        if not next_links:
            return build_select_choices()
        next_url = next_links + "/attributecategories"
        choices.extend(client.get_next_choices(next_url, "Self", use_name_as_link=True))
        return build_select_choices(choices)

    if parameter_name == "element_1":
        choices = []
        next_url = config.get("database_name", None)
        if next_url:
            choices.extend(client.get_next_choices_as_json(next_url+"/elements", "Elements"))
            return build_select_choices(choices)
        else:
            return build_select_choices()

    for element_number in range(2, 10):
        if parameter_name == "element_{}".format(element_number):
            choices = []
            json_string = config.get("element_{}".format(element_number - 1), "{}")
            json_choice = json.loads(json_string)
            next_url = json_choice.get("url")
            if next_url:
                choices.extend(client.get_next_choices_as_json(next_url, "Elements"))
                return build_select_choices(choices)
            else:
                return build_select_choices()

    if parameter_name == "attribute_1":
        choices = []
        json_string = get_latest_config(config)
        json_string = json_string or "{}"
        json_choice = json.loads(json_string)
        next_url = json_choice.get("url")
        if next_url:
            choices.extend(client.get_next_choices(
                next_url.replace("/elements", "/attributes").replace("/{}/attributes".format(client.endpoint.get_web_api_path()), "/{}/elements".format(client.endpoint.get_web_api_path())),
                "Self")
            )
            return build_select_choices(choices)
        else:
            return build_select_choices()

    if parameter_name == "analysis_1":
        choices = []
        json_string = get_latest_config(config)
        json_string = json_string or "{}"
        json_choice = json.loads(json_string)
        next_url = json_choice.get("url")
        if next_url:
            choices.extend(client.get_next_choices(
                next_url.replace("/elements", "/eventframes").replace("/{}/eventframes".format(client.endpoint.get_web_api_path()), "/{}/elements".format(client.endpoint.get_web_api_path())),
                "Self")
            )
            return build_select_choices(choices)
        else:
            return build_select_choices()

    if parameter_name == "data_type":
        json_string = get_latest_config(config)
        json_string = json_string or "{}"
        json_choice = json.loads(json_string)
        url_candidate = json_choice.get("url")
        if url_candidate:
            next_url = config.get(
                "attribute_1",
                url_candidate.replace("/elements", "/attributes").replace("/{}/attributes".format(client.endpoint.get_web_api_path()), "/{}/elements".format(client.endpoint.get_web_api_path()))
            )
        else:
            return build_select_choices()
        choices = []
        item = client.get_item_from_url(next_url)
        links = item.get("Links", {})
        for link in links:
            choices.append({
                "label": link,
                "value": links[link]
            })
        return build_select_choices(choices)

    return build_select_choices()


def get_latest_config(config):
    latest_config = None
    for element_number in range(10, 1, -1):
        latest_config = config.get("element_{}".format(element_number), None)
        if latest_config:
            return latest_config
    return None
