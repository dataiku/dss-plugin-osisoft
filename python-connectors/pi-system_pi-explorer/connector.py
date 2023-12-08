from dataiku.connector import Connector
from safe_logger import SafeLogger
from osisoft_constants import OSIsoftConstants
from osisoft_client import OSIsoftClient
from osisoft_plugin_common import (RecordsLimit, get_credentials, check_debug_mode)

logger = SafeLogger("PI System plugin", ["user", "password"])


class PiExplorerConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class
        logger.info("Pi Tag Search v{} initialization with config={}, plugin_config={}".format(
                OSIsoftConstants.PLUGIN_VERSION,
                logger.filter_secrets(config),
                logger.filter_secrets(plugin_config)
            )
        )
        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
        is_debug_mode = check_debug_mode(config)
        self.client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode)
        self.data_server_url = config.get("data_server_url")

    def get_read_schema(self):
        return {"columns": [
            {"name": "Id", "type": "int"},
            {"name": "Path", "type": "string"},
            {"name": "Descriptor", "type": "string"},
            {"name": "PointClass", "type": "string"},
            {"name": "PointType", "type": "string"},
            {"name": "DigitalSetName", "type": "string"},
            {"name": "EngineeringUnits", "type": "string"},
            {"name": "Span", "type": "int"},
            {"name": "Zero", "type": "int"},
            {"name": "Step", "type": "boolean"},
            {"name": "Future", "type": "boolean"},
            {"name": "DisplayDigits", "type": "int"},
            {"name": "Name", "type": "string"},
            {"name": "WebId", "type": "string"}
        ]}

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        rows = self.client.get_row_from_url(self.data_server_url)
        for row in rows:
            row.pop("Links")
            yield row
            if limit.is_reached():
                return

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise NotImplementedError

    def get_partitioning(self):
        raise NotImplementedError

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise NotImplementedError

    def get_records_count(self, partitioning=None, partition_id=None):
        raise NotImplementedError


class CustomDatasetWriter(object):
    def __init__(self):
        pass

    def write_row(self, row):
        """
        Row is a tuple with N + 1 elements matching the schema passed to get_writer.
        The last element is a dict of columns not found in the schema
        """
        raise NotImplementedError

    def close(self):
        pass
