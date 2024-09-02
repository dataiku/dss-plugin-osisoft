# -*- coding: utf-8 -*-
import dataiku
import copy
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, get_interpolated_parameters,
    get_advanced_parameters, check_debug_mode, PerformanceTimer, get_max_count, reorder_dataframe
)
from osisoft_constants import OSIsoftConstants
from osisoft_client import OSIsoftClient


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

logger.info("PIWebAPI Event frames downloader recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))
input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("Initialization with config={}".format(logger.filter_secrets(config)))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
is_debug_mode = check_debug_mode(config)
max_count = get_max_count(config)

use_server_url_column = config.get("use_server_url_column", False)
if not server_url and not use_server_url_column:
    raise ValueError("Server domain not set")

path_column = config.get("path_column", "")
if not path_column:
    raise ValueError("There is no parameter column selected.")

data_type = config.get("data_type")
start_time = config.get("start_time")
end_time = config.get("end_time")
use_start_time_column = config.get("use_start_time_column", False)
start_time_column = config.get("start_time_column")
use_end_time_column = config.get("use_end_time_column", False)
end_time_column = config.get("end_time_column")
server_url_column = config.get("server_url_column")
search_full_hierarchy = config.get("search_full_hierarchy", None)
summary_type = config.get("summary_type")
use_batch_mode, batch_size = get_advanced_parameters(config)
interval, sync_time, boundary_type = get_interpolated_parameters(config)

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

input_parameters_dataset = dataiku.Dataset(input_dataset[0])
output_dataset = dataiku.Dataset(output_names_stats[0])

input_parameters_dataframe = input_parameters_dataset.get_dataframe()

time_last_request = None
client = None
previous_server_url = ""
time_not_parsed = True
with output_dataset.get_writer() as writer:
    first_dataframe = True
    absolute_index = 0
    batch_buffer_size = 0
    buffer = []
    nb_rows_to_process = input_parameters_dataframe.shape[0]
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        absolute_index += 1
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        start_time = input_parameters_row.get(start_time_column, start_time) if use_start_time_column else start_time
        end_time = input_parameters_row.get(end_time_column, end_time) if use_end_time_column else end_time
        event_frame_webid = input_parameters_row.get("WebId")
        event_frame_start_time = input_parameters_row.get("StartTime", "")
        event_frame_end_time = input_parameters_row.get("EndTime", "")

        if client is None or previous_server_url != server_url:
            client = OSIsoftClient(
                server_url, auth_type, username, password,
                is_ssl_check_disabled=is_ssl_check_disabled, is_debug_mode=is_debug_mode,
                network_timer=network_timer
            )
            previous_server_url = server_url
            if time_not_parsed:
                # make sure all OSIsoft time string format are evaluated at the same time
                # rather than at every request, at least for start / end times set in the UI
                time_not_parsed = False
                if not use_start_time_column:
                    start_time = client.parse_pi_time(start_time)
                if not use_end_time_column:
                    end_time = client.parse_pi_time(end_time)
                sync_time = client.parse_pi_time(sync_time)
        object_id = input_parameters_row.get(path_column)
        item = None
        if client.is_resource_path(object_id):
            item = client.get_item_from_path(object_id)
        if item:
            rows = client.get_rows_from_item(
                item,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                search_full_hierarchy=search_full_hierarchy,
                can_raise=False,
                max_count=max_count,
                summary_type=summary_type
            )
        elif use_batch_mode:
            buffer.append({"WebId": object_id, "StartTime": event_frame_start_time, "EndTime": event_frame_end_time})
            batch_buffer_size += 1
            if (batch_buffer_size >= batch_size) or (absolute_index == nb_rows_to_process):
                rows = client.get_rows_from_webids(
                    buffer, data_type, max_count,
                    search_full_hierarchy=search_full_hierarchy,
                    can_raise=False,
                    batch_size=batch_size,
                    summary_type=summary_type
                )
                batch_buffer_size = 0
                buffer = []
            else:
                continue
        else:
            rows = client.get_rows_from_webid(
                object_id,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                search_full_hierarchy=search_full_hierarchy,
                max_count=max_count,
                can_raise=False,
                summary_type=summary_type
            )
        unnested_items_rows = []
        row_count = 0
        for row in rows:
            row_count += 1
            if not use_batch_mode and event_frame_start_time:
                row["StartTime"] = event_frame_start_time
            if not use_batch_mode and event_frame_end_time:
                row["EndTime"] = event_frame_end_time
            base_row = copy.deepcopy(row)
            base_row.pop("Links", None)
            items_column = base_row.pop(OSIsoftConstants.API_ITEM_KEY, [])
            for item in items_column:
                item_row = {} if use_batch_mode else {"event_frame_webid": event_frame_webid}
                value = item.get("Value", {})
                if isinstance(value, dict):
                    item.pop("Value")
                    item_row.update(value)
                item_row.update(base_row)
                item_row.update(item)
                unnested_items_rows.append(item_row)
            if (not item) and ("Value" in base_row):
                item_row = {} if use_batch_mode else {"event_frame_webid": event_frame_webid}
                value = base_row.get("Value", {})
                if isinstance(value, dict):
                    base_row.pop("Value")
                    base_row.update(value)
                item_row.update(base_row)
                unnested_items_rows.append(item_row)
        unnested_items_rows = pd.DataFrame(unnested_items_rows)
        unnested_items_rows = reorder_dataframe(unnested_items_rows, ['Path', 'Name', 'StartTime', 'EndTime', 'Timestamp', 'Value', 'UnitsAbbreviation', 'Errors'])
        if first_dataframe:
            output_dataset.write_schema_from_dataframe(unnested_items_rows)
            first_dataframe = False
        writer.write_dataframe(unnested_items_rows)

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
