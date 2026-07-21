import dataiku
from dataiku.customrecipe import get_recipe_config, get_output_names_for_role
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, PerformanceTimer
)
from osisoft_constants import OSIsoftConstants
from osisoft_client import OSIsoftClient


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

logger.info("PIWebAPI AF selector recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))


def get_step_value(item):
    if item and "Step" in item:
        if item.get("Step") is True:
            return "True"
        else:
            return "False"
    return None


def next_tree_item(tree_data):
    if not isinstance(tree_data, list):
        return
    for item in tree_data:
        children = item.pop("children", [])
        if children:
            for child in next_tree_item(children):
                yield child
        yield item


def filter_dictionary_keys(input_dict, keys_to_filter):
    filtered_dict = input_dict or []
    for key_to_filter in keys_to_filter:
        filtered_dict[key_to_filter] = "{} elements".format(len(filtered_dict.get(key_to_filter, [])))
    return filtered_dict


output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
filtered_config = logger.filter_secrets(config)
filtered_config = filter_dictionary_keys(filtered_config, [
       "attributeList", "outputSelectedAttributes", "loadedAttributes",
       "attribute_categories", "element_categories", "clickedNodes"
    ]
)

logger.info("Initialization with config config={}".format(filtered_config))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
is_ssl_check_disabled = config.get("is_ssl_check_disabled", False)  # Because no advanced parameter switch

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

output_dataset = dataiku.Dataset(output_names_stats[0])
schema = [
    {'name': 'title', 'type': 'string'},
    {'name': 'template_name', 'type': 'string'},
    {'name': 'category_names', 'type': 'string'},
    {'name': 'path', 'type': 'string'},
    {'name': 'paths', 'type': 'string'},
    {'name': 'id', 'type': 'string'},
    {'name': 'url', 'type': 'string'},
    {'name': 'endpoint_url', 'type': 'string'},
    {'name': 'data_type', 'type': 'string'},
    {'name': 'summary_type', 'type': 'string'},
    {'name': 'boundary_type', 'type': 'string'},
    {'name': 'record_boundary_type', 'type': 'string'},
    {'name': 'summary_duration', 'type': 'string'},
    {'name': 'max_count', 'type': 'int'},
    {'name': 'interval', 'type': 'string'},
    {'name': 'sync_time', 'type': 'string'},

]
output_dataset.write_schema(schema)

selectedAttributes = config.get("outputSelectedAttributes", [])

client = OSIsoftClient(
    server_url, auth_type, username, password,
    is_ssl_check_disabled=is_ssl_check_disabled,
    network_timer=network_timer
)

with output_dataset.get_writer() as writer:
    while selectedAttributes:
        selectedAttribute = selectedAttributes.pop()
        selectedAttribute["url"] = None
        selected_attribute_url = selectedAttribute.get("url")
        if selected_attribute_url:
            kwarg = {
                "url": "{}?associations=Paths".format(selected_attribute_url),
            }
        else:
            attribute_path = selectedAttribute.get("path")
            search_url = client.endpoint.get_base_url() + "/attributes?associations=Paths&path={}".format(attribute_path)
            # https://server/piwebapi/attributes?path=\\server\factory\INST-001-Temperature|InstrumentType
            kwarg = {
                "url": search_url,
            }
        # last one is never pushed
        response = client.push_to_batch(selectedAttribute, **kwarg)
        if not selectedAttributes:
            # Reached the last element, forcing the flush
            for selectedAttribute_back, reply in response:
                data_type = selectedAttribute_back.get("data_type")
                selectedAttribute_back["endpoint_url"] = reply.get("Content", {}).get("Links", {}).get(data_type)
                selectedAttribute_back["paths"] = reply.get("Paths")
                selectedAttribute_back["id"] = reply.get("WebId")
                writer.write_row_dict(selectedAttribute_back)
            response = client.flush_batch()

        for selectedAttribute_back, reply in response:
            data_type = selectedAttribute_back.get("data_type")
            selectedAttribute_back["endpoint_url"] = reply.get("Content", {}).get("Links", {}).get(data_type)
            selectedAttribute_back["paths"] = reply.get("Content", {}).get("Paths")
            selectedAttribute_back["id"] = reply.get("Content", {}).get("WebId")
            writer.write_row_dict(selectedAttribute_back)

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
