from dataiku.connector import Connector
from osisoft_client import OSIsoftClient
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    RecordsLimit, get_credentials, 
    check_debug_mode, PerformanceTimer
)
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("PI System plugin", ["user", "password"])


class HierarchyConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)

        logger.info("Attribute search v{} initialization with config={}, plugin_config={}".format(
            OSIsoftConstants.PLUGIN_VERSION, logger.filter_secrets(config), logger.filter_secrets(plugin_config)
        ))

        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
        is_debug_mode = check_debug_mode(config)
        self.database_endpoint = config.get("database_name")

        self.network_timer = PerformanceTimer()
        self.client = OSIsoftClient(
            server_url, auth_type, username, password,
            is_ssl_check_disabled=is_ssl_check_disabled,
            is_debug_mode=is_debug_mode,
            network_timer=self.network_timer
        )

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit = -1):
        limit = RecordsLimit(records_limit)

        headers = self.client.get_requests_headers()
        json_response = self.client.get(url=self.database_endpoint, headers=headers, params={}, error_source="traverse")
        next_url = self.client.extract_link_with_key(json_response, "Elements")

        for item in self.recurse_next_item(next_url):
            if limit.is_reached():
                break
            yield item

    def recurse_next_item(self, next_url, parent=None, type=None):
        logger.info("recurse_next_item")
        type = type or "Elements"
        headers = self.client.get_requests_headers()
        json_response = self.client.get(url=next_url, headers=headers, params={}, error_source="recurse")
        items = json_response.get("Items")
        if not items:
            return
        for item in items:
            parent_path = item.get("Path")
            link_to_attributes = self.client.extract_link_with_key(item, "Attributes")
            if link_to_attributes:
                for attribute in self.recurse_next_item(link_to_attributes, parent=parent_path, type="Attribute"):
                    yield attribute
            link_to_elements = self.client.extract_link_with_key(item, "Elements")
            if link_to_elements:
                for element in self.recurse_next_item(link_to_elements, parent=parent_path, type="Element"):
                    yield element
            yield {
                "ItemType": type,
                "Name": item.get("Name"),
                "Type": item.get("Type"),
                "Description": item.get("Description"),
                "Path": item.get("Path"),
                "Parent": parent,
                "DefaultUnitsName": item.get("DefaultUnitsName"),
                "TemplateName": item.get("TemplateName"),
                "CategoryNames": item.get("CategoryNames"),
                "ExtendedProperties": item.get("ExtendedProperties"),
                "Step": item.get("Step"),
                "WebId": item.get("WebId"),
                "Id": item.get("Id")
            }

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                         partition_id=None, write_mode="OVERWRITE"):
        raise NotImplementedError

    def get_partitioning(self):
        raise NotImplementedError

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        raise NotImplementedError
