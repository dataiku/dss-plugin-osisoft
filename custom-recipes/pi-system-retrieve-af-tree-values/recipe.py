# -*- coding: utf-8 -*-
import dataiku
import json
import copy
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, get_base_for_data_type, check_debug_mode,
    PerformanceTimer, get_max_count, check_must_convert_object_to_string,
    get_advanced_parameters,
    get_batch_parameters
)
from osisoft_client import OSIsoftClient
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

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


def assert_necessary_columns_in_dataset(input_columns):
    NECESSARY_COLUMNS = ["id", "data_type", "summary_type", "boundary_type", "record_boundary_type", "summary_duration"]
    for necessary_column in NECESSARY_COLUMNS:
        if necessary_column not in input_columns:
            raise Exception("Column '{}' in missing from the input dataset".format(necessary_column))
    return True


def normalize_value(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def extract_params_from_row(row):
    data_type = normalize_value(row.get("data_type"))
    boundary_type = normalize_value(row.get("boundary_type"))
    record_boundary_type = normalize_value(row.get("record_boundary_type"))
    interval = normalize_value(row.get("interval"))
    sync_time = normalize_value(row.get("sync_time"))
    summary_type = row.get("summary_type", [])
    summary_type = normalize_value(summary_type)
    if summary_type and summary_type.startswith("["):
        summary_type = summary_type.replace("'", '"')
        summary_type = json.loads(summary_type)
        summary_type = ",".join(summary_type)
    else:
        summary_type = None
    summary_duration = normalize_value(row.get("summary_duration"))
    object_id = normalize_value(row.get("id"))
    return object_id, data_type, boundary_type, record_boundary_type, interval, sync_time, summary_type, summary_duration


def format_results(results, output_schema_data_type):
    default_columns = OSIsoftConstants.RECIPE_SCHEMA_PER_DATA_TYPE.get(output_schema_data_type)
    # todo: cache the result of this part
    columns_types = {}
    for default_column in default_columns:
        column_name = default_column.get("name")
        column_type = default_column.get("type")
        columns_types[column_name] = column_type
    formated_results = []
    for result in results:
        formated_result = {}
        for column_name in columns_types:
            formated_result[column_name] = result.get(column_name)
        formated_results.append(formated_result)
    return formated_results

def dataframe_schema(dataframe):
    from pandas.api import types as ptypes
    """Return a simplified schema for a pandas DataFrame."""
    schema = []

    for column_name, dtype in dataframe.dtypes.items():
        if ptypes.is_string_dtype(dtype):
            column_type = "string"
        elif ptypes.is_datetime64_any_dtype(dtype):
            column_type = "date"
        elif ptypes.is_bool_dtype(dtype):
            column_type = "boolean"
        elif ptypes.is_float_dtype(dtype):
            column_type = "float"
        elif ptypes.is_integer_dtype(dtype):
            column_type = "int"
        else:
            column_type = "object"
        schema.append({"name": column_name, "type": column_type})
    return schema


def combine_schemas(input_schema, pi_response_schema):
    """Combine two schemas and return the combined schema plus input renames."""
    combined_schema = [dict(column) for column in pi_response_schema]
    used_names = {column["name"] for column in combined_schema}
    renamed_columns: dict[str, str] = {}

    for column in input_schema:
        merged_column = dict(column)
        original_name = merged_column["name"]
        candidate_name = original_name
        suffix = 1

        while candidate_name in used_names:
            candidate_name = "{}_{}".format(original_name, suffix)
            suffix += 1

        merged_column["name"] = candidate_name
        if candidate_name != original_name:
            renamed_columns[original_name] = candidate_name
        combined_schema.append(merged_column)
        used_names.add(candidate_name)

    return combined_schema, renamed_columns


def schema_from_sample_data(input_schema, pi_response_schema, sample_data):
    """Build a schema from sample-data column names using schema type lookups."""
    input_types = {column["name"]: column["type"] for column in input_schema}
    pi_response_types = {column["name"]: column["type"] for column in pi_response_schema}
    output_schema = []
    added_names = set()

    if isinstance(sample_data, dict):
        rows = [sample_data]
    else:
        rows = sample_data

    for row in rows:
        if not isinstance(row, dict):
            continue
        for column_name in row:
            if column_name in added_names:
                continue

            if column_name in pi_response_types:
                output_schema.append(
                    {"name": column_name, "type": pi_response_types[column_name]}
                )
                added_names.add(column_name)
            elif column_name in input_types:
                output_schema.append({"name": column_name, "type": input_types[column_name]})
                added_names.add(column_name)

    return output_schema


input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("Initialization with config config={}".format(logger.filter_secrets(config)))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
is_debug_mode = check_debug_mode(config)
max_count = get_max_count(config)
must_convert_object_to_string = check_must_convert_object_to_string(config)

use_server_url_column = config.get("use_server_url_column", False)
if not server_url and not use_server_url_column:
    raise ValueError("Server domain not set")

path_column = config.get("path_column", "")
input_parameters_dataset = dataiku.Dataset(input_dataset[0])
input_parameters_dataframe = input_parameters_dataset.get_dataframe()
do_duplicate_input_row = config.get("do_duplicate_input_row", False)
input_columns = list(input_parameters_dataframe.columns)
input_columns_types = list(input_parameters_dataframe.dtypes)
input_schema = dataframe_schema(input_parameters_dataframe)

self_contained_mode = False
if not path_column:
    if assert_necessary_columns_in_dataset(input_columns):
        self_contained_mode = True
    else:
        raise ValueError("There is no parameter column selected.")
else:
    input_columns = list(input_parameters_dataframe.columns) if do_duplicate_input_row else []

output_schema_data_type = "All"
start_time = config.get("start_time")
end_time = config.get("end_time")
use_start_time_column = config.get("use_start_time_column", False)
start_time_column = config.get("start_time_column")
use_end_time_column = config.get("use_end_time_column", False)
end_time_column = config.get("end_time_column")
server_url_column = config.get("server_url_column")
_, batch_size = get_advanced_parameters(config)
download_strategy = config.get("download_strategy", "recursive")

max_request_size, estimated_density, maximum_points_returned = get_batch_parameters(config)
max_time_to_retrieve_per_batch = estimated_density / maximum_points_returned  # density per hour <- max time is in hour

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

output_dataset = dataiku.Dataset(output_names_stats[0])

results = []
time_last_request = None
client = None
previous_server_url = ""
time_not_parsed = True

with output_dataset.get_writer() as writer:
    first_dataframe = True
    absolute_index = 0
    batch_buffer_size = 0
    buffer = []
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        absolute_index += 1
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        start_time = input_parameters_row.get(start_time_column, start_time) if use_start_time_column else start_time
        end_time = input_parameters_row.get(end_time_column, end_time) if use_end_time_column else end_time
        row_name = input_parameters_row.get("Name")

        # if self_contained_mode:
        object_id, data_type, boundary_type, record_boundary_type, interval, sync_time, summary_type, summary_duration = extract_params_from_row(
            input_parameters_row
        )
        path_column = "id"

        duplicate_initial_row = {}
        nb_rows_to_process = input_parameters_dataframe.shape[0]
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

        step_value = None

        if download_strategy=="batch":
            buffer.append(
                {
                    "initial_index": int(absolute_index - 1),
                    "WebId": object_id, "data_type": data_type,
                    "max_count": max_count,
                    "start_date": start_time,
                    "end_date": end_time,
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
                }
            )
            batch_buffer_size += 1
            if (batch_buffer_size >= batch_size) or (absolute_index == nb_rows_to_process):
                rows = client.get_rows_from_af_trees(
                    buffer
                )
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
            if isinstance(row, list):
                for line in row:
                    base = get_base_for_data_type(data_type, object_id, Step=step_value)
                    base.update(line)
                    extention = client.unnest_row(base)
                    results.extend(extention)
            else:
                if row.get("initial_index") is not None:
                    base = json.loads(copy.deepcopy(input_parameters_dataframe.loc[row.get("initial_index")].to_json()))
                else:
                    base = json.loads(copy.deepcopy(input_parameters_dataframe.loc[absolute_index-1].to_json()))
                base.update(row)
                extention = client.unnest_row(base)
                results.extend(extention)

        unnested_items_rows = pd.DataFrame(results)
        if first_dataframe:
            pi_response_schema = dataframe_schema(unnested_items_rows)
            final_schema = schema_from_sample_data(input_schema, pi_response_schema, results[0])
            output_dataset.write_schema(final_schema)
            first_dataframe = False
        if not unnested_items_rows.empty:
            writer.write_dataframe(unnested_items_rows)
        results = []
        formated_results = []

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
