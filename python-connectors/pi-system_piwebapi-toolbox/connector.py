from dataiku.connector import Connector
from osisoft_client import OSIsoftClient, OSIsoftWriter
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    PISystemConnectorError, RecordsLimit, get_credentials, assert_time_format, get_schema_as_arrays, normalize_af_path, get_max_count
)
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("PI System plugin", ["user", "password"])


class OSIsoftConnector(Connector):  # Search

    def __init__(self, config, plugin_config):

        Connector.__init__(self, config, plugin_config)

        logger.info("PIWebAPI toolbox v{} initialization with config={}, plugin_config={}".format(
            OSIsoftConstants.PLUGIN_VERSION, logger.filter_secrets(config), logger.filter_secrets(plugin_config)
        ))

        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)

        self.client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled)
        self.object_id = config.get("object_id")
        self.data_type = config.get("data_type", "RecordedData")
        self.start_time = config.get("start_time")
        self.end_time = config.get("end_time")
        self.interval = config.get("interval")
        self.sync_time = config.get("sync_time")
        assert_time_format(self.start_time, error_source="start time")
        assert_time_format(self.end_time, error_source="start time")
        self.item = None
        if self.client.is_resource_path(self.object_id):
            self.object_id = normalize_af_path(self.object_id)
            self.item = self.client.get_item_from_path(self.object_id)
        self.max_count = get_max_count(config)

    def get_read_schema(self):
        return None

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)

        if self.item:
            for row in self.client.get_row_from_item(
                self.item,
                self.data_type,
                start_date=self.start_time,
                end_date=self.end_time,
                interval=self.interval,
                sync_time=self.sync_time,
                max_count=self.max_count
            ):
                if limit.is_reached():
                    break
                yield row
        else:
            for row in self.client.get_row_from_webid(
                self.object_id,
                self.data_type,
                start_date=self.start_time,
                end_date=self.end_time,
                interval=self.interval,
                sync_time=self.sync_time,
                endpoint_type="AF", max_count=self.max_count
            ):
                if limit.is_reached():
                    break
                yield row

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        column_names, _ = get_schema_as_arrays(dataset_schema)
        return OSIsoftWriter(self.client, self.object_id, column_names)

    def get_partitioning(self):
        raise PISystemConnectorError("Unimplemented")

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise PISystemConnectorError("Unimplemented")

    def get_records_count(self, partitioning=None, partition_id=None):
        raise PISystemConnectorError("Unimplemented")
