from osisoft_client import OSIsoftClient
from safe_logger import SafeLogger
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode
from osisoft_plugin_common import get_item_details, Tree, recursive_tree_rebuild, PerformanceTimer
import dataiku

logger = SafeLogger("PI System plugin", ["user", "password"])


def do(payload, config, plugin_config, inputs):
    input_tree = None
    if len(inputs) > 0:
        input_item = inputs[0]
        input_type = input_item.get("type")
        if input_type == "DATASET":
            input_dataset_name = input_item.get("fullName")
            input_dataset = dataiku.Dataset(input_dataset_name)
            input_tree = input_dataset.get_dataframe(infer_with_pandas=False)

    if "config" in config:
        config = config.get("config")
    if "credentials" not in config:
        return {"choices": [{"label": "Requires DSS v10.0.4 or above. Please use the OSIsoft Search custom dataset instead"}]}
    elif config.get("credentials") == {}:
        return {"choices": [{"label": "Pick a credential"}]}

    auth_type, username, password, server_url, is_ssl_check_disabled, credential_error = get_credentials(config, can_raise=False)
    is_ssl_check_disabled = config.get("is_ssl_check_disabled", False)  # Because no advanced parameter switch

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

    network_timer = PerformanceTimer()

    client = OSIsoftClient(
        server_url, auth_type, username, password,
        is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode,
        network_timer=network_timer
    )

    method = payload.get("method")
    if method == "get_query_catalogs":
        return get_query_catalogs(None, config)
    if method == "get_children_from_db":
        database_name = config.get("database_name")
        parent = payload.get("parent", {})
        return get_children_from_db(client, parent, database_name=database_name)
    if method == "get_templates_from_db":
        database_name = config.get("database_name")
        parent = payload.get("parent", {})
        # ret = get_items_from_db(client, parent, "ElementTemplates", database_name=database_name)
        ret = get_template_hierarchy_from_db(client, parent, database_name=database_name)
        return ret
    if method == "get_attribute_categories_from_db":
        database_name = config.get("database_name")
        parent = payload.get("parent", {})
        ret = get_items_from_db(client, parent, "AttributeCategories", database_name=database_name)
        return ret
    if method == "get_element_categories_from_db":
        database_name = config.get("database_name")
        parent = payload.get("parent", {})
        ret = get_items_from_db(client, parent, "ElementCategories", database_name=database_name)
        return ret
    if method == "do_search":
        template_name = config.get("template", None)
        category_name = config.get("element_category", None)
        clicked_nodes = config.get("clickedNodes", [])
        if template_name == "-- Any --":
            template_name = None
        if category_name == "-- Any --":
            category_name = None
        element_category = config.get("element_category", None)
        if element_category == "-- Any --":
            element_category = None
        attribute_category = config.get("attribute_category", None)
        if attribute_category == "-- Any --":
            attribute_category = None
        database_name = config.get("database_name")
        element_name = config.get("element_name")
        attribute_name = config.get("attribute_name")
        # root_tree = payload.get("root_tree")
        root_tree = config.get("treeData", [])
        root_tree = shorten_tree(root_tree)
        attributes = []
        # https://dku-qa-osi.francecentral.cloudapp.azure.com/piwebapi/assetdatabases/F1RD3VEt1yTvt0ip6-a5yeEVsgbMcrwu_Je0qg9btcZIvPswT1NJU09GVC1QSS1TRVJWXFdFTEw
        database_webid = database_name.split("/")[-1]
        elements_max_count, attributes_max_count = get_max_counts(config)

        attributes = []
        for result in client.batched_search(database_name, element_name, attribute_name,
                                            element_category, attribute_category, template_name, clicked_nodes,
                                            elements_max_count=elements_max_count, attributes_max_count=attributes_max_count):
            # result["checked"] = True
            attributes.append(result)

        attributes = duplicate_linked_attributes(attributes)
        items = []
        for attribute in attributes:
            item = get_item_details(attribute)
            items.append(item)
        attributesCopy = items.copy()
        rebuilt_tree = rebuild_tree(client, items, root_tree)
        logger.info("Search network timer:{}".format(network_timer.get_report()))
        return {"choices": rebuilt_tree, "attributes": attributesCopy}

    parameter_name = payload.get("parameterName")

    if parameter_name == "server_name":
        choices = []
        servers = client.get_asset_servers(can_raise=False)
        choices.extend(servers)
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
    if parameter_name == "treeData":
        return {"choices": config.get("treeData")}

    return build_select_choices()


def get_query_catalogs(cnx, config):
    user = config.get("credentials", {}).get("osisoft_basic", {}).get("user")
    password = config.get("credentials", {}).get("osisoft_basic", {}).get("password")
    return {"choices": [user, password]}


def get_items_from_db(client, parent_node, link_key, database_name=None):
    default_choice = {"title": "-- Any --"}
    if isinstance(parent_node, dict):
        url = parent_node.get("url", database_name)
    else:
        url = parent_node
    this_node = next(client.get_next_item_from_url(url))
    links = this_node.get("Links", {})
    items_url = links.get(link_key)
    items = []
    items.append(default_choice)
    if items_url:
        for item in client.get_next_item_from_url(items_url):
            item = get_item_details(item)
            item["type"] = link_key
            items.append(item)
    return {"choices": items}


def get_children_from_db(client, parent_node, database_name=None):
    if isinstance(parent_node, dict):
        url = parent_node.get("url", database_name)
    else:
        url = parent_node
    this_node = next(client.get_next_item_from_url(url))
    links = this_node.get("Links", {})
    attributes_url = links.get("Attributes")
    elements_url = links.get("Elements")
    children = []
    if elements_url:
        elements = client.get_next_item_from_url(elements_url)
        for element in elements:
            child = get_item_details(element)
            # child["title"] = "🧩{}".format(child.get("title"))
            child["type"] = "element"
            child["children"] = []
            children.append(child)
    if attributes_url:
        attributes = client.get_next_item_from_url(attributes_url)
        for attribute in attributes:
            child = get_item_details(attribute)
            # child["title"] = "🏷️{}".format(child.get("title"))
            child["type"] = "attribute"
            if child.get("has_children"):
                child["children"] = []
            children.append(child)
    return {"choices": children}


def get_template_hierarchy_from_db(client, parent_node, database_name=None):
    if isinstance(parent_node, dict):
        url = parent_node.get("url", database_name)
    else:
        url = parent_node
    default_choice = {"title": "-- Any --", "id:": ""}
    this_node = next(client.get_next_item_from_url(url))
    links = this_node.get("Links", {})
    element_templates_url = links.get("ElementTemplates")
    children = [default_choice]
    rebuilt_tree = []
    if element_templates_url:
        element_templates = client.get_next_item_from_url(element_templates_url)
        for element_template in element_templates:
            child = get_item_details(element_template)
            child["type"] = "template"
            child["children"] = []
            children.append(child)
        rebuilt_tree = nest_children(children)
    return {"choices": rebuilt_tree}


def nest_children(items):
    name_to_item = {item["title"]: item for item in items}
    tree = []
    for item in items:
        parent_name = item.get("BaseTemplate")
        if parent_name is None or parent_name not in name_to_item:
            tree.append(item)
        else:
            parent = name_to_item[parent_name]
            if "children" not in parent:
                parent["children"] = []
            parent["children"].append(item)
    return tree


def rebuild_tree(client, items, root_tree=None):
    # builds an active tree containing all the items and their parent up to the root
    tree = Tree(root_tree=root_tree)
    # tree.print()
    while len(items) > 1:
        item = items.pop()
        if item is None:
            break
        find_all_ancestors(client, item, tree)
        update_item(item, tree)
    result = recursive_tree_rebuild(tree.get_tree(), tree.get_records())
    result = drop_first_levels(result)
    return result


def drop_first_levels(result):
    # recursively removes the 2 first levels of the returned tree
    # (server and DB)
    output_result = []
    for item in result:
        path = item.get("path", "")
        path_length = len(path.split("\\"))
        if path_length >= 5:
            output_result.append(item)
        else:
            children = item.get("children", [])
            output_result = drop_first_levels(children)
    return output_result


def find_all_ancestors(client, item, tree):
    # Find all the ancestors of an item
    elements_paths_tokens, attributes_paths_tokens = path_to_list(item.get("path"))
    client.traverse_and_cache(elements_paths_tokens, attributes_paths_tokens, tree)


def combine_trees(final_tree, all_item_s_ancestors):
    # combine two trees with partial overlap and common root ancestor
    return final_tree


# elements, attributes
def path_to_list(path):
    if not path:
        return []
    return path.split('|')[0].split('\\')[2:], (path.split('|')[1:])


def shorten_tree(tree):
    if isinstance(tree, list):
        for node in tree:
            if "expanded" in node:
                # node.pop("expanded", None)
                node["expanded"] = False
            if "children" in node:
                shorten_tree(node.get("children", []))
    return tree


def duplicate_linked_attributes(attributes):
    duplicated_attributes = []
    for attribute in attributes:
        paths = attribute.pop("Paths", [attribute.get("Path")])
        for path in paths:
            this_attribute = attribute.copy()
            this_attribute["Path"] = path
            this_attribute["type"] = "attribute" if "|" in path else "element"
            duplicated_attributes.append(this_attribute)
    return duplicated_attributes


def set_as_selected(items):
    for item in items:
        item["checked"] = True
    return items


def update_item(item, tree):
    elements_paths_tokens, attributes_paths_tokens = path_to_list(item.get("path"))
    tree.put(elements_paths_tokens + attributes_paths_tokens, item)


def get_max_counts(config):
    show_advanced_parameters = config.get("show_advanced_parameters", False)
    if not show_advanced_parameters:
        return 100, 100

    def parse_max_count(value, default):
        if value is None or value == "":
            return default
        try:
            value = int(value)
        except (TypeError, ValueError):
            return default
        if value <= 0:
            return None
        return value

    elements_max_count = parse_max_count(config.get("elements_max_count"), 100)
    attributes_max_count = parse_max_count(config.get("attributes_max_count"), 100)
    return elements_max_count, attributes_max_count
