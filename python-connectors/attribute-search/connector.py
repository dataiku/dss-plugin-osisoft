import json
from dataiku.connector import Connector
from osisoft_client import OSIsoftClient
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    OSIsoftConnectorError, RecordsLimit, get_credentials, assert_time_format,
    remove_unwanted_columns, format_output, filter_columns_from_schema, is_child_attribute_path
)
from osisoft_constants import OSIsoftConstants

logger = SafeLogger("OSIsoft plugin", ["user", "password"])


class OSIsoftConnector(Connector):  # Browse

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class

        logger.info("Attribute search v1.0.0 initialization with config={}, plugin_config={}".format(logger.filter_secrets(config), logger.filter_secrets(plugin_config)))

        auth_type, username, password, server_url, is_ssl_check_disabled, api_manager_url = get_credentials(config)

        self.client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, api_manager_url=api_manager_url)
        self.start_time = config.get("start_time")
        self.end_time = config.get("end_time")
        is_interpolated_data = config.get("data_type", "").endswith("InterpolatedData")
        self.interval = config.get("interval") if is_interpolated_data else None
        self.sync_time = config.get("sync_time") if is_interpolated_data else None
        assert_time_format(self.start_time, error_source="start time")
        assert_time_format(self.end_time, error_source="end time")
        self.attribute_name = config.get("attribute_name")  # todo: check if next_element has an url first
        self.element_name = config.get("element_name")
        database_endpoint = config.get("database_name")
        self.database_webid = self.extract_database_webid(database_endpoint)
        self.search_root_path = None
        if config.get("specify_search_root_element", False):
            self.search_root_path = self.build_path_from_config(config)
        self.must_retrieve_metrics = config.get("must_retrieve_metrics", False)
        self.data_type = config.get("data_type")
        self.maximum_results = config.get("maximum_results", 1000)
        self.attribute_value_type = config.get("attribute_value_type")
        self.must_filter_child_attributes = not (config.get("must_keep_child_attributes", False))
        self.config = config

    def extract_database_webid(self, database_endpoint):
        return database_endpoint.split("/")[-1]

    def build_path_from_config(self, config):
        # Wont work.
        # Instead: take the last url, remove the /elements and get the "Path" key from the retrieved object
        path_elements = []
        for index in range(1, 10):
            json_string = config.get("element_{}".format(index), None)
            json_string = json_string or "{}"
            json_choice = json.loads(json_string)
            path_element = json_choice.get("label")
            if path_element:
                path_elements.append(path_element)
            else:
                break
        return "\\".join(path_elements)

    def get_read_schema(self):
        return {
            "columns": filter_columns_from_schema(
                OSIsoftConstants.SCHEMA_ATTRIBUTES_METRICS_RESPONSE,
                OSIsoftConstants.SCHEMA_ATTRIBUTES_METRICS_FILTER
            )
        } if self.must_retrieve_metrics else {
            "columns": filter_columns_from_schema(
                OSIsoftConstants.SCHEMA_ATTRIBUTES_RESPONSE,
                OSIsoftConstants.SCHEMA_ATTRIBUTES_METRICS_FILTER
            )
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        if self.must_retrieve_metrics:
            for attribute in self.client.search_attributes(
                    self.database_webid, search_root_path=self.search_root_path,
                    **self.config):
                attribute_webid = attribute.pop("WebId")
                attribute.pop("Id", None)
                is_enumeration_value = attribute.get("Type") == "EnumerationValue"
                remove_unwanted_columns(attribute)
                if "Errors" in attribute:
                    yield attribute
                else:
                    for row in self.client.get_row_from_webid(
                        attribute_webid,
                        self.data_type,
                        start_date=self.start_time,
                        end_date=self.end_time,
                        interval=self.interval,
                        sync_time=self.sync_time,
                        endpoint_type="AF",
                        selected_fields="Links;Items.Timestamp;Items.Value"
                        # boundary_type=self.boundary_type
                    ):
                        if limit.is_reached():
                            return
                        output_row = format_output(row, attribute, is_enumeration_value=is_enumeration_value)
                        yield output_row
        else:
            for row in self.client.search_attributes(
                    self.database_webid, search_root_path=self.search_root_path,
                    **self.config):
                if limit.is_reached():
                    break
                if self.must_filter_child_attributes:
                    path = row.get("Path", "")
                    if is_child_attribute_path(path):
                        continue
                remove_unwanted_columns(row)
                output_row = format_output(row)
                yield output_row

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise Exception("Unimplemented")

    def get_partitioning(self):
        raise OSIsoftConnectorError("Unimplemented")

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise OSIsoftConnectorError("Unimplemented")

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise OSIsoftConnectorError("Unimplemented")
