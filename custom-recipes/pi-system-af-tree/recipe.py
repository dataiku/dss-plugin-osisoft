import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, PerformanceTimer
)
from osisoft_constants import OSIsoftConstants


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


input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
print("ALX:config={}".format(config))
tree_data = config.get("treeData", [])

logger.info("Initialization with config config={}".format(logger.filter_secrets(config)))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

output_dataset = dataiku.Dataset(output_names_stats[0])
schema = [
    {'name': 'title', 'type': 'string'},
    {'name': 'template_name', 'type': 'string'},
    {'name': 'category_names', 'type': 'array'},
    {'name': 'path', 'type': 'string'},
    {'name': 'id', 'type': 'string'},
    {'name': 'url', 'type': 'string'},
    {'name': 'checked', 'type': 'boolean'},
    {'name': 'expanded', 'type': 'boolean'},
]
output_dataset.write_schema(schema)

with output_dataset.get_writer() as writer:
    for item in next_tree_item(tree_data):
        if item.get("checked", False) is True:
            writer.write_row_dict(item)

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
