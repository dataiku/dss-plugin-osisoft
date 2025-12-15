from osisoft_client import OSIsoftClient
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode
import dataiku


def do(payload, config, plugin_config, inputs):
    input_tree = None
    if len(inputs)>0:
        input_item = inputs[0]
        input_type = input_item.get("type")
        if input_type == "DATASET":
            input_dataset_name = input_item.get("fullName")
            input_dataset = dataiku.Dataset(input_dataset_name)
            input_tree = input_dataset.get_dataframe(infer_with_pandas=False)

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

    method = payload.get("method")
    if method == "get_query_catalogs":
        return get_query_catalogs(None, config)
    if method == "get_children_from_db":
        database_name = config.get("database_name")
        parent = payload.get("parent", {})
        return get_children_from_db(client, parent, database_name=database_name)
    if method == "do_search":
        database_name = config.get("database_name")
        element_name = config.get("element_name")
        attribute_name = config.get("attribute_name")
        attributes = []
        # https://dku-qa-osi.francecentral.cloudapp.azure.com/piwebapi/assetdatabases/F1RD3VEt1yTvt0ip6-a5yeEVsgbMcrwu_Je0qg9btcZIvPswT1NJU09GVC1QSS1TRVJWXFdFTEw
        database_webid = database_name.split("/")[-1]
        for attribute in client.search_attributes(
            database_webid, attribute_name=attribute_name, element_name=element_name):
            print("ALX:attribute={}".format(attribute))
            attributes.append(attribute)
        return {"choices": attributes}

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


def get_children_from_db(client, parent_node, database_name=None):
    print("ALX:parent_node={}".format(parent_node))
    # ALX:parent_node={'show_advanced_parameters': False, 'use_server_url_column': False, 'is_ssl_check_disabled': True, 'must_convert_object_to_string': False, 'is_debug_mode': False, 'credentials': {'auth_type': 'basic', 'can_disable_ssl_check': True, 'ssl_cert_path': '', 'default_server': 'dku-qa-osi.francecentral.cloudapp.azure.com', 'can_override_server_url': True, 'get_parameters': {}, 'post_parameters': {}, 'url_swap': [], 'max_request_size': 1000, 'estimated_density': 6, 'maximum_points_returned': 600, 'osisoft_basic': {'user': 'abourret', 'password': 'S58BirZjtsUDTJ3'}}}
    if isinstance(parent_node, dict):
        url = parent_node.get("url", database_name)
    else:
        url = parent_node
    print("ALX:url to search:{}".format(url))
    this_node = next(client.get_next_item_from_url(url))
    links = this_node.get("Links", {})
    attributes_url = links.get("Attributes")
    elements_url = links.get("Elements")
    children = []
    if elements_url:
        elements = client.get_next_item_from_url(elements_url)
        for element in elements:
            child = get_item_details(element)
            child["type"] = "element"
            child["children"] = []
            children.append(child)
    if attributes_url:
        attributes = client.get_next_item_from_url(attributes_url)
        for attribute in attributes:
            child = get_item_details(attribute)
            child["type"] = "attribute"
            if child.get("has_children"):
                child["children"] = []
            children.append(child)

    return {"choices": children}


def get_item_details(item):
    KEYS_TO_CHECK = {"Name": "title", "TemplateName": "template_name", "CategoryNames": "category_names", "HasChildren": "has_children", "Path": "path", "WebId": "id"}
    details = {}
    for key_to_check in KEYS_TO_CHECK:
        value = item.get(key_to_check)
        if value:
            details[KEYS_TO_CHECK.get(key_to_check)] = value
    details["url"] = item.get("Links", {}).get("Self")
    return details
