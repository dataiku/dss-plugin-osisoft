# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from osisoft_safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, get_interpolated_parameters, normalize_af_path,
    get_combined_description, get_base_for_data_type, check_debug_mode,
    PerformanceTimer, get_max_count, check_must_convert_object_to_string,
    convert_schema_objects_to_string, get_summary_parameters, get_advanced_parameters,
    get_batch_parameters
)
from osisoft_client import OSIsoftClient
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])
INPUT_CHUNK_SIZE = 10000
OUTPUT_CHUNK_SIZE = 10000

logger.info("PIWebAPI Assets values downloader recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))


def get_step_value(item):
    if item and "Step" in item:
        if item.get("Step") is True:
            return "True"
        else:
            return "False"
    return None


def iter_input_rows(dataset):
    previous_row = None
    for dataframe in dataset.iter_dataframes(chunksize=INPUT_CHUNK_SIZE):
        for index, row in dataframe.iterrows():
            if previous_row is not None:
                yield previous_row, False
            previous_row = row
    if previous_row is not None:
        yield previous_row, True


def write_results(writer, results, first_dataframe):
    unnested_items_rows = pd.DataFrame(results)
    if first_dataframe:
        default_columns = OSIsoftConstants.RECIPE_SCHEMA_PER_DATA_TYPE.get(data_type)
        if must_convert_object_to_string:
            default_columns = convert_schema_objects_to_string(default_columns)
        combined_columns_description = get_combined_description(default_columns, unnested_items_rows)
        output_dataset.write_schema(combined_columns_description)
    if not unnested_items_rows.empty:
        writer.write_dataframe(unnested_items_rows)
    results.clear()
    return False


input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("Initialization with config config={}".format(logger.filter_secrets(config)))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
is_debug_mode = check_debug_mode(config)
max_count = get_max_count(config)
summary_type = config.get("summary_type")
must_convert_object_to_string = check_must_convert_object_to_string(config)

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
use_batch_mode, batch_size = get_advanced_parameters(config)
batch_max_count, estimated_density, maximum_points_returned = get_batch_parameters(config)
if "max_request_size" not in config.get("credentials", {}):
    batch_max_count = max_count
interval, sync_time, boundary_type = get_interpolated_parameters(config)
record_boundary_type = config.get("record_boundary_type") if data_type == "RecordedData" else None
summary_type, summary_duration = get_summary_parameters(config)
do_duplicate_input_row = config.get("do_duplicate_input_row", False)

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

input_parameters_dataset = dataiku.Dataset(input_dataset[0])
output_dataset = dataiku.Dataset(output_names_stats[0])

results = []
time_last_request = None
client = None
previous_server_url = ""
time_not_parsed = True

input_columns = [column["name"] for column in input_parameters_dataset.read_schema()] if do_duplicate_input_row else []

with output_dataset.get_writer() as writer:
    first_dataframe = True
    batch_buffer_size = 0
    buffer = []
    input_rows_cache = {}
    absolute_index = 0
    for input_parameters_row, is_last_input_row in iter_input_rows(input_parameters_dataset):
        absolute_index += 1
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        start_time = input_parameters_row.get(start_time_column, start_time) if use_start_time_column else start_time
        end_time = input_parameters_row.get(end_time_column, end_time) if use_end_time_column else end_time
        row_name = input_parameters_row.get("Name")
        duplicate_initial_row = {}
        for input_column in input_columns:
            duplicate_initial_row[input_column] = input_parameters_row.get(input_column)

        if client is None or previous_server_url != server_url:
            client = OSIsoftClient(
                server_url, auth_type, username, password,
                is_ssl_check_disabled=is_ssl_check_disabled,
                is_debug_mode=is_debug_mode, network_timer=network_timer
            )
            previous_server_url = server_url
            if time_not_parsed:
                # make sure all OSIsoft time string format are evaluated at the same time
                # rather than at every request, at least for start / end times set in the UI
                time_not_parsed = False
                start_time = client.parse_pi_time(start_time)
                end_time = client.parse_pi_time(end_time)
                sync_time = client.parse_pi_time(sync_time)

        object_id = input_parameters_row.get(path_column)
        item = None
        if client.is_resource_path(object_id):
            object_id = normalize_af_path(object_id)
            item = client.get_item_from_path(object_id)
        step_value = get_step_value(item)
        if item:
            rows = client.recursive_get_rows_from_item(
                item,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                record_boundary_type=record_boundary_type,
                max_count=max_count,
                can_raise=False,
                object_id=object_id,
                summary_type=summary_type,
                summary_duration=summary_duration
            )
        elif use_batch_mode:
            input_rows_cache[absolute_index] = (row_name, object_id, duplicate_initial_row)
            buffer.append({
                "WebId": object_id,
                "initial_index": absolute_index,
                "data_type": data_type,
                "max_count": batch_max_count,
                "start_date": client.parse_pi_time(start_time),
                "end_date": client.parse_pi_time(end_time),
                "interval": interval,
                "sync_time": sync_time,
                "boundary_type": boundary_type,
                "record_boundary_type": record_boundary_type,
                "can_raise": False,
                "batch_size": batch_size,
                "object_id": object_id,
                "summary_type": summary_type,
                "summary_duration": summary_duration,
                "endpoint_type": "AF",
                "estimated_density": estimated_density,
                "maximum_points_returned": maximum_points_returned
            })
            batch_buffer_size += 1
            if (batch_buffer_size >= batch_size) or is_last_input_row:
                rows = client.get_rows_from_af_trees(buffer)
                batch_buffer_size = 0
                buffer = []
            else:
                continue
        else:
            rows = client.recursive_get_rows_from_webid(
                object_id,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                record_boundary_type=record_boundary_type,
                max_count=max_count,
                can_raise=False,
                endpoint_type="AF",
                summary_type=summary_type,
                summary_duration=summary_duration
            )
        for row in rows:
            initial_index = row.pop("initial_index", None) if isinstance(row, dict) else None
            if initial_index is not None:
                row_name, object_id, duplicate_initial_row = input_rows_cache[initial_index]
            row["Name"] = row_name
            row[path_column] = object_id
            if isinstance(row, list):
                for line in row:
                    base = get_base_for_data_type(data_type, object_id, Step=step_value)
                    base.update(line)
                    extention = client.unnest_row(base)
                    for output_row in extention:
                        results.append(output_row)
                        if len(results) >= OUTPUT_CHUNK_SIZE:
                            first_dataframe = write_results(writer, results, first_dataframe)
            else:
                base = get_base_for_data_type(data_type, object_id, Step=step_value)
                if duplicate_initial_row:
                    base.update(duplicate_initial_row)
                base.update(row)
                extention = client.unnest_row(base)
                for output_row in extention:
                    results.append(output_row)
                    if len(results) >= OUTPUT_CHUNK_SIZE:
                        first_dataframe = write_results(writer, results, first_dataframe)

        if results or first_dataframe:
            first_dataframe = write_results(writer, results, first_dataframe)
        if not buffer:
            input_rows_cache.clear()

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
