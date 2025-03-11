import copy
import datetime
from dataiku.connector import Connector
from osisoft_client import OSIsoftClient
from osisoft_constants import OSIsoftConstants
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    PISystemConnectorError, RecordsLimit, get_credentials,
    build_requests_params, assert_time_format, get_advanced_parameters, check_debug_mode,
    PerformanceTimer, get_max_count, get_summary_parameters, get_interpolated_parameters
)


logger = SafeLogger("PI System plugin", ["user", "password"])


class OSIsoftConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)  # pass the parameters to the base class

        logger.info("Event frame search v{} initialization with config={}, plugin_config={}".format(
                OSIsoftConstants.PLUGIN_VERSION,
                logger.filter_secrets(config),
                logger.filter_secrets(plugin_config)
            )
        )

        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
        is_debug_mode = check_debug_mode(config)
        self.network_timer = PerformanceTimer()
        self.yields_timer = PerformanceTimer()
        self.client = OSIsoftClient(
            server_url, auth_type, username, password,
            is_ssl_check_disabled=is_ssl_check_disabled,
            is_debug_mode=is_debug_mode, network_timer=self.network_timer
        )
        self.object_id = config.get("event_frame_to_retrieve", None)
        self.data_type = config.get("data_type", "SummaryData")
        if self.object_id is None:
            self.object_id = config.get("next_element", None)
        self.start_time = config.get("start_time")
        self.start_time = self.client.parse_pi_time(self.start_time)
        if self.start_time:
            config["start_time"] = self.start_time
        self.end_time = config.get("end_time")
        self.end_time = self.client.parse_pi_time(self.end_time)
        if self.end_time:
            config["end_time"] = self.end_time
        self.interval, self.sync_time, self.boundary_type = get_interpolated_parameters(config)
        self.search_mode = config.get("search_mode", None)
        self.output_type = config.get("output_type")
        assert_time_format(self.start_time, error_source="start time")
        assert_time_format(self.end_time, error_source="end time")
        self.database_endpoint = config.get("database_name")
        if not self.database_endpoint:
            raise PISystemConnectorError("No endpoint selected")
        self.must_retrieve_metrics = config.get("must_retrieve_metrics")
        self.search_full_hierarchy = None
        if self.must_retrieve_metrics:
            self.search_full_hierarchy = config.get("search_full_hierarchy", None)
        self.data_type = config.get("data_type", "Recorded")
        self.max_count = get_max_count(config)
        self.config = config
        self.use_batch_mode, self.batch_size = get_advanced_parameters(config)
        self.summary_type, self.summary_duration = get_summary_parameters(config)

    def get_read_schema(self):
        return {
            "columns": OSIsoftConstants.SCHEMA_EVENT_FRAMES_METRICS_RESPONSE
        } if self.must_retrieve_metrics else {
            "columns": OSIsoftConstants.SCHEMA_EVENT_FRAMES_RESPONSE
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                      partition_id=None, records_limit=-1):
        limit = RecordsLimit(records_limit)
        use_batch_mode = self.use_batch_mode and (records_limit == -1 or records_limit >= 500)
        start_time = datetime.datetime.now()
        if self.object_id:
            for event_frame in self.client.get_rows_from_urls(
                        self.object_id, self.data_type, start_date=self.start_time,
                        end_date=self.end_time, interval=self.interval, sync_time=self.sync_time,
                        boundary_type=self.boundary_type, max_count=self.max_count):
                self.yields_timer.start()
                yield event_frame
                self.yields_timer.stop()
                if limit.is_reached():
                    return
        else:
            params = build_requests_params(
                **self.config
            )
            headers = self.client.get_requests_headers()
            next_page_url = self.database_endpoint + "/eventframes"
            is_first = True
            while next_page_url:
                if is_first:
                    json_response = self.client.get(
                        next_page_url,
                        headers=headers, params=params, error_source="generate_rows"
                    )
                else:
                    json_response = self.client.get(
                        next_page_url,
                        headers=None, params=None, error_source="generate_rows"
                    )
                is_first = False
                next_page_url = json_response.get("Links", {}).get("Next", None)
                event_frames = json_response.get(OSIsoftConstants.API_ITEM_KEY, [json_response])
                if self.must_retrieve_metrics:
                    if use_batch_mode:
                        batch_rows = self.client.get_rows_from_webids(
                                event_frames, self.data_type,
                                search_full_hierarchy=self.search_full_hierarchy,
                                can_raise=False,
                                batch_size=self.batch_size,
                                summary_type=self.summary_type,
                                summary_duration=self.summary_duration,
                                boundary_type=self.boundary_type,
                                interval=self.interval,
                                sync_time=self.sync_time,
                                max_count=self.max_count
                            )
                        for batch_row in batch_rows:
                            value = batch_row.pop(OSIsoftConstants.API_VALUE_KEY, {})
                            if not value:
                                items = batch_row.pop(OSIsoftConstants.API_ITEM_KEY, [])
                                for item in items:
                                    batch_row.pop("Links", None)
                                    batch_row.update(item)
                                    if isinstance(batch_row.get("Value"), dict):
                                        value = batch_row.pop("Value", {})
                                        batch_row.update(value)
                                    self.yields_timer.start()
                                    yield batch_row
                                    self.yields_timer.stop()
                                    if limit.is_reached():
                                        return
                            else:
                                batch_row.pop("Links", None)
                                batch_row.update(value)
                                self.yields_timer.start()
                                yield batch_row
                                self.yields_timer.stop()
                                if limit.is_reached():
                                    return
                    else:
                        for event_frame in event_frames:
                            event_frame_id = event_frame.get("WebId")
                            event_frame_metrics = self.client.get_rows_from_webid(
                                event_frame_id, self.data_type, summary_type=self.summary_type, summary_duration=self.summary_duration,
                                interval=self.interval, sync_time=self.sync_time, boundary_type=self.boundary_type,
                                search_full_hierarchy=self.search_full_hierarchy, max_count=self.max_count,
                                can_raise=False
                            )
                            for event_frame_metric in event_frame_metrics:
                                event_frame_copy = copy.deepcopy(event_frame)
                                event_frame_copy.pop("Links", None)
                                event_frame_copy.pop("Security", None)
                                event_frame_copy.update(event_frame_metric)
                                if OSIsoftConstants.API_ITEM_KEY in event_frame_copy:
                                    items = event_frame_copy.pop(OSIsoftConstants.API_ITEM_KEY)
                                    for item in items:
                                        row = copy.deepcopy(event_frame_copy)
                                        row.update(item)
                                        row.pop("Links", None)
                                        if isinstance(row.get("Value"), dict):
                                            value = row.pop("Value", {})
                                            row.update(value)
                                        row["event_frame_webid"] = event_frame_id
                                        self.yields_timer.start()
                                        yield row
                                        self.yields_timer.stop()
                                        if limit.is_reached():
                                            return
                                else:
                                    event_frame_copy.pop("Links", None)
                                    value = event_frame_copy.pop("Value", {})
                                    event_frame_copy.update(value)
                                    event_frame_copy["event_frame_webid"] = event_frame_id
                                    self.yields_timer.start()
                                    yield event_frame_copy
                                    self.yields_timer.stop()
                                    if limit.is_reached():
                                        return
                else:
                    for event_frame in event_frames:
                        event_frame_copy = copy.deepcopy(event_frame)
                        event_frame_copy.pop(OSIsoftConstants.API_ITEM_KEY, None)
                        event_frame_copy.pop("Security", None)
                        event_frame_copy.pop("Links", None)
                        self.yields_timer.start()
                        yield event_frame_copy
                        self.yields_timer.stop()
                        if limit.is_reached():
                            return
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info("generate_rows overall duration = {}s".format(duration.microseconds/1000000 + duration.seconds))
        logger.info("Network timer:{}".format(self.network_timer.get_report()))
        logger.info("DSS ingress:{}".format(self.yields_timer.get_report()))

    def get_writer(self, dataset_schema=None, dataset_partitioning=None,
                   partition_id=None):
        raise PISystemConnectorError("Unimplemented")

    def get_partitioning(self):
        raise PISystemConnectorError("Unimplemented")

    def list_partitions(self, partitioning):
        return []

    def partition_exists(self, partitioning, partition_id):
        raise PISystemConnectorError("Unimplemented")

    def get_records_count(self, partitioning=None, partition_id=None):
        """
        Returns the count of records for the dataset (or a partition).

        Implementation is only required if the corresponding flag is set to True
        in the connector definition
        """
        raise PISystemConnectorError("Unimplemented")
