from osisoft_client import OSIsoftClient
from safe_logger import SafeLogger
from osisoft_plugin_common import get_credentials, build_select_choices, check_debug_mode
from osisoft_plugin_common import get_item_details, PerformanceTimer
from osisoft_build_tree import build_af_element_tree


logger = SafeLogger("PI System plugin", ["user", "password"])


def do(payload, config, plugin_config, inputs):
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
    parameter_name = payload.get("parameterName")
    logger.info("Running do for method '{}' / parameter '{}'".format(method, parameter_name))
    if method == "get_query_catalogs":
        return get_query_catalogs(payload, config)
    if method == "get_children_from_db":
        return get_children_from_db(client, payload, config)
    if method == "get_templates_from_db":
        return get_templates_from_db(client, payload, config)
    if method == "get_attribute_categories_from_db":
        return get_attribute_categories_from_db(client, payload, config)
    if method == "get_element_categories_from_db":
        return get_element_categories_from_db(client, payload, config)
    if method == "get_elements_for_template":
        return get_elements_for_template(client, payload, config)
    if method == "get_attribute_for_template":
        return get_attribute_for_template(client, payload, config)
    if method == "get_attributes":
        return get_attributes(client, payload, config)
    if method == "build_af_tree":
        return build_af_tree(client, payload, config)
    if method == "get_attributes_per_page":
        return get_attributes_per_page(client, payload, config)
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
    return build_select_choices()


def get_query_catalogs(payload, config):
    logger.info("Start call [get_query_catalogs] payload_keys={}".format(sorted(payload.keys())))
    user = config.get("credentials", {}).get("osisoft_basic", {}).get("user")
    password = config.get("credentials", {}).get("osisoft_basic", {}).get("password")
    result = {"choices": [user, password]}
    logger.info("End call [get_query_catalogs] payload_keys={}".format(sorted(payload.keys())))
    return result


def get_children_from_db(client, payload, config):
    database_name = config.get("database_name")
    parent_node = payload.get("parent", {})
    logger.info(
        "Start call [get_children_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    result = get_children_node(client, parent_node, database_name=database_name)
    logger.info(
        "End call [get_children_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    return result


def get_children_node(client, parent_node, database_name=None):
    if isinstance(parent_node, dict):
        url = parent_node.get("url", database_name)
    else:
        url = parent_node
    this_node = next(client.get_next_item_from_url(url, params={"associations": "Paths"}))
    links = this_node.get("Links", {})
    attributes_url = links.get("Attributes")
    elements_url = links.get("Elements")
    children = []
    if attributes_url:
        attributes = client.get_next_item_from_url(attributes_url, params={"associations": "Paths"})
        templates_urls = []
        for attribute in attributes:
            # templates_urls are processed in batch for speed
            templates_urls.append(extract_attribute_template_url(attribute))
            child = get_item_details(attribute)
            # child["title"] = "🏷️{}".format(child.get("title"))
            child["type"] = "attribute"
            if child.get("has_children"):
                child["children"] = []
            children.append(child)
        templates_names = client.get_attributes_templates_names(templates_urls)
        # post processing the batch response
        for child, template_name in zip(children, templates_names):
            if template_name:
                child["template_name"] = template_name
    if elements_url:
        elements = client.get_next_item_from_url(elements_url, params={"associations": "Paths"})
        for element in elements:
            child = get_item_details(element)
            # child["title"] = "🧩{}".format(child.get("title"))
            child["type"] = "element"
            child["children"] = []
            children.append(child)
    return {"choices": children}


def get_templates_from_db(client, payload, config):
    database_name = config.get("database_name")
    parent_node = payload.get("parent", {})
    logger.info(
        "Start call [get_templates_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    result = get_template_hierarchy_from_db(client, parent_node, database_name=database_name)
    logger.info(
        "End call [get_templates_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    return result


def get_attribute_categories_from_db(client, payload, config):
    database_name = config.get("database_name")
    parent_node = payload.get("parent", {})
    logger.info(
        "Start call [get_attribute_categories_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    result = get_items_from_db(client, parent_node, "AttributeCategories", database_name=database_name)
    logger.info(
        "End call [get_attribute_categories_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    return result


def get_element_categories_from_db(client, payload, config):
    database_name = config.get("database_name")
    parent_node = payload.get("parent", {})
    logger.info(
        "Start call [get_element_categories_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    result = get_items_from_db(client, parent_node, "ElementCategories", database_name=database_name)
    logger.info(
        "End call [get_element_categories_from_db] database_name={}, parent_node={}".format(database_name, parent_node)
    )
    return result


def get_elements_for_template(client, payload, config):
    database_name = config.get("database_name")
    template_name = payload.get("template_name", None)
    logger.info(
        "Start call [get_elements_for_template] database_name={}, template_name={}".format(
            database_name, template_name
        )
    )
    elements = []
    for element in client.search_elements(database_name, name=None, description=None, category=None, template=template_name, full_search=True):
        elements.append(get_item_details(element))
    result = {"choices": [], "elements": elements}
    logger.info(
        "End call [get_elements_for_template] database_name={}, template_name={}".format(
            database_name, template_name
        )
    )
    return result


def get_attributes(client, payload, config):
    database_url = config.get("database_name")
    database_name = database_url.split("/")[-1]
    element_name = payload.get("element_name", None)
    attribute_categories = payload.get("element_category", None)
    attribute_value_type =  payload.get("attribute_value_type", None)
    if not element_name:
        element_name = "*"
    attribute_name = payload.get("attribute_name", None)
    logger.info(
        "Start call [get_attributes] database_name={}, element_name={}, attribute_name={}".format(
            database_name, element_name, attribute_name
        )
    )
    raw_attributes = list(client.search_attributes(
        database_name,
        attribute_name=attribute_name,
        element_name=element_name,
        attribute_category=attribute_categories,
        attribute_value_type=attribute_value_type,
        search_associations="Paths",
        full_search=True
    ))
    attributes = [get_item_details(attribute) for attribute in raw_attributes]
    template_urls = [
        extract_attribute_template_url(attribute)
        for attribute in raw_attributes
    ]
    template_names = client.get_attributes_templates_names(template_urls)
    for attribute, template_name in zip(attributes, template_names):
        if template_name:
            attribute["template_name"] = template_name

    result = {"choices": [], "attributes": attributes}
    logger.info(
        "End call [get_attributes] database_name={}, element_name={}, attribute_name={}".format(
            database_name, element_name, attribute_name
        )
    )
    return result

def get_attributes_per_page(client, payload, config):
    next_page = payload.get("next_page", None)
    if next_page:
        logger.info(
            "Start call [get_attributes_per_page] next_page={}".format(
                next_page
            )
        )
        raw_attributes, next_page = client.get_next_page(next_page)
    else:
        database_url = config.get("database_name")
        database_name = database_url.split("/")[-1]
        element_name = payload.get("element_name", None)
        attribute_categories = payload.get("element_category", None)
        attribute_value_type =  payload.get("attribute_value_type", None)
        if not element_name:
            element_name = "*"
        attribute_name = payload.get("attribute_name", None)
        logger.info(
            "Start call [get_attributes_per_page] database_name={}, element_name={}, attribute_name={}".format(
                database_name, element_name, attribute_name
            )
        )
        raw_attributes, next_page = client.search_attributes_first_page(
            database_name,
            attribute_name=attribute_name,
            element_name=element_name,
            attribute_category=attribute_categories,
            attribute_value_type=attribute_value_type,
            search_associations="Paths",
            full_search=True
        )
    attributes = [get_item_details(attribute) for attribute in raw_attributes]
    template_urls = [
        extract_attribute_template_url(attribute)
        for attribute in raw_attributes
    ]
    template_names = client.get_attributes_templates_names(template_urls)
    for attribute, template_name in zip(attributes, template_names):
        if template_name:
            attribute["template_name"] = template_name

    result = {"choices": [], "attributes": attributes, "next_page": next_page}
    logger.info(
        "End call [get_attributes_per_page] "
    )
    return result


def build_af_tree(client, payload, config):
    database_url = config.get("database_name")
    if not database_url:
        return {}
    logger.info(
        "Start call [build_af_element_tree] database_url={}".format(
            database_url
        )
    )
    tree = build_af_element_tree(client, database_url)
    result = {"choices": [], "tree": tree}
    logger.info(
        "End call [build_af_element_tree] database_url={}".format(
            database_url
        )
    )
    return result


def get_attribute_for_template(client, payload, config):
    database_name = config.get("database_name")
    template_name = payload.get("template_name", None)
    logger.info(
        "Start call [get_attribute_for_template] database_name={}, template_name={}".format(
            database_name, template_name
        )
    )
    if template_name is None:
        result = {"choices": [], "attributes": []}
        logger.info(
            "End call [get_attribute_for_template] database_name={}, template_name={}".format(
                database_name, template_name
            )
        )
        return result
    attributes = []
    for attribute in client.search_element_attributes(
        database_name, template=template_name, full_search=True,
        selected_fields=[
            "Links.Next", "Items.WebId", "Items.Name", "Items.Description",
            "Items.Path", "Items.Paths", "Items.Type", "Items.CategoryNames", "Items.Links.Self"
        ]
    ):
        attribute["TemplateName"] = template_name
        attributes.append(get_item_details(attribute))
    result = {"choices": [], "attributes": attributes}
    logger.info(
        "End call [get_attribute_for_template] database_name={}, template_name={}".format(
            database_name, template_name
        )
    )
    return result


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


def extract_attribute_template_url(attribute):
    return attribute.get("Links", {}).get("Template")


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
            if is_event_frame_template(element_template):
                continue
            child = get_item_details(element_template)
            child["type"] = "template"
            child["children"] = []
            children.append(child)
        rebuilt_tree = nest_children(children)
    return {"choices": rebuilt_tree}


def is_event_frame_template(element_template):
    if not isinstance(element_template, dict):
        return False
    return element_template.get("InstanceType", "") == "EventFrame"


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
            parent["has_children"] = True
    return tree


def is_sub_attribute_item(item):
    if not isinstance(item, dict):
        return False
    return len(item.get("Path").split("|")) > 2
