import copy
from dataiku.connector import Connector
from osisoft_client import OSIsoftClient
from osisoft_constants import OSIsoftConstants
from safe_logger import SafeLogger
from osisoft_plugin_common import OSIsoftConnectorError, RecordsLimit, get_credentials, build_requests_params, assert_time_format


logger = SafeLogger("OSIsoft plugin", ["user", "password"])


class OSIsoftConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class

        logger.info("Event frame search v1.0.0 initialization with config={}, plugin_config={}".format(
                logger.filter_secrets(config),
                logger.filter_secrets(plugin_config)
            )
        )

        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)

        self.client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled)
        self.object_id = config.get("event_frame_to_retrieve", None)
        self.data_type = config.get("data_type", "SummaryData")
        if self.object_id is None:
            self.object_id = config.get("next_element", None)
        self.start_time = config.get("start_time")
        self.end_time = config.get("end_time")
        self.output_type = config.get("output_type")
        assert_time_format(self.start_time, error_source="start time")
        assert_time_format(self.end_time, error_source="end time")
        self.database_endpoint = config.get("database_name")
        if not self.database_endpoint:
            raise OSIsoftConnectorError("No endpoint selected")
        self.must_retrieve_metrics = config.get("must_retrieve_metrics")
        self.data_type = config.get("data_type", "Recorded")
        self.config = config

    def get_read_schema(self):
        return {
            "columns": OSIsoftConstants.SCHEMA_EVENT_FRAMES_METRICS_RESPONSE
        } if self.must_retrieve_metrics else {
            "columns": OSIsoftConstants.SCHEMA_EVENT_FRAMES_RESPONSE
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        if self.object_id:
            for event_frame in self.client.get_row_from_urls(self.object_id, self.data_type, start_date=self.start_time, end_date=self.end_time):
                if limit.is_reached():
                    break
                yield event_frame
        else:
            params = build_requests_params(
                **self.config
            )
            headers = self.client.get_requests_headers()
            json_response = self.client.get(url=self.database_endpoint + "/eventframes", headers=headers, params=params, error_source="generate_rows")
            event_frames = json_response.get(OSIsoftConstants.API_ITEM_KEY, [json_response])
            for event_frame in event_frames:
                if self.must_retrieve_metrics:
                    event_frame_id = event_frame.get("WebId")
                    event_frame_metrics = self.client.get_row_from_webid(
                        event_frame_id, self.data_type,
                        can_raise=False
                    )
                    for event_frame_metric in event_frame_metrics:
                        ret = copy.deepcopy(event_frame)
                        ret.pop("Links", None)
                        ret.pop("Security", None)
                        ret.update(event_frame_metric)
                        # yield self.client.unnest_row(ret)
                        if OSIsoftConstants.API_ITEM_KEY in ret:
                            items = ret.pop(OSIsoftConstants.API_ITEM_KEY)
                            for item in items:
                                rett = copy.deepcopy(ret)
                                rett.update(item)
                                rett.pop("Links", None)
                                yield rett
                                limit.add_record()
                        else:
                            ret.pop("Links", None)
                            yield ret
                            limit.add_record()
                else:
                    ret = copy.deepcopy(event_frame)
                    ret.pop(OSIsoftConstants.API_ITEM_KEY, None)
                    ret.pop("Security", None)
                    ret.pop("Links", None)
                    yield ret
                    limit.add_record()
                if limit.is_reached():
                    break

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise OSIsoftConnectorError("Unimplemented")

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
