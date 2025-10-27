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
        self.use_batch_mode = config.get("use_batch_mode", False)
        self.batch_size = config.get("batch_size", 500)

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit = -1):
        limit = RecordsLimit(records_limit)

        headers = self.client.get_requests_headers()
        json_response = self.client.get(url=self.database_endpoint, headers=headers, params={}, error_source="traverse")

        if self.use_batch_mode:
            for item in self.batch_next_item(json_response, type="Database"):
                if limit.is_reached():
                    break
                yield item
        else:
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

    def batch_next_item(self, next_item, parent=None, type=None):
        todo_list = []
        todo_list.append(
            {
                "url": self.client.extract_link_with_key(next_item, "Elements"),
                "parent": next_item.get("Name"),
                "type": "Database"
            }
        )
        batch_requests_parameters= []
        while todo_list:
            item = todo_list.pop()
            request_kwargs = {
                "url": item.get("url"),
                "headers": self.client.get_requests_headers()
            }
            batch_requests_parameters.append(request_kwargs)
            if not todo_list or len(batch_requests_parameters) > self.batch_size:
                json_responses = self.client._batch_requests(batch_requests_parameters)
                batch_requests_parameters = []
                for json_response in json_responses:
                    response_content = json_response.get("Content", {})
                    links = response_content.get("Links", {})
                    next_link = links.get("Next", {})
                    # do something if there is a next link...
                    if next_link:
                        todo_list.append(
                            {
                                "url": next_link
                            }
                        )
                    retrieved_items = response_content.get(OSIsoftConstants.API_ITEM_KEY, [])
                    for retrieved_item in retrieved_items:
                        retrieved_item_path = retrieved_item.get("Path")
                        elements_url = self.client.extract_link_with_key(retrieved_item, "Elements")
                        attributes_url = self.client.extract_link_with_key(retrieved_item, "Attributes")
                        if elements_url:
                            todo_list.append(
                                {
                                    "url": elements_url,
                                    "type": "Element",
                                    "parent": retrieved_item_path
                                }
                            )
                        if attributes_url:
                            todo_list.append(
                                {
                                    "url": attributes_url,
                                    "type": "Attribute",
                                    "parent": retrieved_item_path
                                }
                            )
                        yield {
                            "ItemType": type,
                            "Name": retrieved_item.get("Name"),
                            "Type": retrieved_item.get("Type"),
                            "Description": retrieved_item.get("Description"),
                            "Path": retrieved_item.get("Path"),
                            "Parent": parent,
                            "DefaultUnitsName": retrieved_item.get("DefaultUnitsName"),
                            "TemplateName": retrieved_item.get("TemplateName"),
                            "CategoryNames": retrieved_item.get("CategoryNames"),
                            "ExtendedProperties": retrieved_item.get("ExtendedProperties"),
                            "Step": retrieved_item.get("Step"),
                            "WebId": retrieved_item.get("WebId"),
                            "Id": retrieved_item.get("Id")
                        }


    def batch_recurse_next_item(self, next_items, parents=None, type=None):
        # logger.info("batch_recurse_next_item")
        if not isinstance(next_items, list):
            next_items = [next_items]
        if not isinstance(parents, list):
            parents = [parents]
        batch_requests_parameters= []
        types = []
        items_parents_names =  []
        for next_item in next_items:
            next_item_name = next_item.get("Path")
            next_elements_url = self.client.extract_link_with_key(next_item, "Elements")
            if next_elements_url:
                request_kwargs = {
                    "url": next_elements_url,
                    "headers": self.client.get_requests_headers()
                }
                batch_requests_parameters.append(request_kwargs)
                types.append("Element")
                items_parents_names.append(next_item_name)
            next_attributes_url = self.client.extract_link_with_key(next_item, "Attributes")
            if next_attributes_url:
                request_kwargs = {
                    "url": next_attributes_url,
                    "headers": self.client.get_requests_headers()
                }
                batch_requests_parameters.append(request_kwargs)
                types.append("Attribute")
                items_parents_names.append(next_item_name)
        if batch_requests_parameters:
            json_responses = self.client._batch_requests(batch_requests_parameters)
            # for json_response in json_responses:
            #     # Here we process recurse based on each response in the batch
            #     # Instead we could process all responses and batch all of them in one go...
            #     response_content = json_response.get("Content", {})
            #     if OSIsoftConstants.DKU_ERROR_KEY in response_content:
            #         # Do something ?
            #         pass
            #     items = response_content.get(OSIsoftConstants.API_ITEM_KEY, [])
            #     batched_items = self.batch_recurse_next_item(items)
            #     for item in batched_items:
            #         yield item
            # approach 2:
            next_batch_items = []
            for json_response  in json_responses:
                response_content = json_response.get("Content", {})
                links = response_content.get("Links", {})
                next_link = links.get("Next", {})
                # do something if there is a next link...
                items = response_content.get(OSIsoftConstants.API_ITEM_KEY, [])
                next_batch_items.extend(items)
            batched_items = self.batch_recurse_next_item(next_batch_items, parents=items_parents_names)
            for item in batched_items:
                yield item

        for item, parent in zip(next_items, parents):
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
