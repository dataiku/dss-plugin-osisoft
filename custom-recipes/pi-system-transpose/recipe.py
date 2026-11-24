# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from osisoft_safe_logger import SafeLogger
import os
from contextlib import ExitStack
from heapq import merge
from sys import getsizeof
from tempfile import TemporaryDirectory
from osisoft_temp_utils import CustomTmpFile
from osisoft_constants import OSIsoftConstants
import dateutil.parser
from osisoft_column_name import normalise_name
from datetime import datetime, timezone


DEFAULT_INPUT_CHUNK_SIZE = 10000
DEFAULT_OUTPUT_BATCH_SIZE = 1000
MAX_OUTPUT_BATCH_CELLS = 100000
CACHE_SORT_BATCH_BYTES = 16 * 1024 * 1024
CACHE_SORT_MERGE_FAN_IN = 32

logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

logger.info("PIWebAPI Transpose & Synchronize recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))
current_timestamps_cache = []
current_values_cache = []
next_timestamps_cache = []
next_values_cache = []

temp_cache = CustomTmpFile()
temp_location = temp_cache.get_temporary_cache_dir()


def parse_timestamp_and_value(line):
    split_line = line.split("|")
    if len(split_line) != 2:
        return None, None
    timestamp = float(split_line[0])
    value = split_line[1]
    if value.endswith('\n'):
        value = value[:-1]
    return timestamp, value


def cache_timestamp(line):
    return float(line.split("|", 1)[0])


def write_sorted_run(lines, path):
    lines.sort(key=cache_timestamp)
    with open(path, "w") as output:
        output.writelines(lines)


def sort_cache_file(cache_path):
    with TemporaryDirectory(dir=os.path.dirname(cache_path)) as run_directory:
        run_count = 0
        lines = []
        batch_bytes = 0
        with open(cache_path, "r") as source:
            for line in source:
                line_bytes = 2 * getsizeof(line) + 64
                if lines and batch_bytes + line_bytes > CACHE_SORT_BATCH_BYTES:
                    write_sorted_run(lines, os.path.join(run_directory, "0_{}".format(run_count)))
                    run_count += 1
                    lines.clear()
                    batch_bytes = 0
                lines.append(line)
                batch_bytes += line_bytes
        if lines:
            write_sorted_run(lines, os.path.join(run_directory, "0_{}".format(run_count)))
            run_count += 1
            lines.clear()

        run_pass = 0
        while run_count > 1:
            next_run_count = 0
            for start in range(0, run_count, CACHE_SORT_MERGE_FAN_IN):
                run_paths = [
                    os.path.join(run_directory, "{}_{}".format(run_pass, index))
                    for index in range(start, min(start + CACHE_SORT_MERGE_FAN_IN, run_count))
                ]
                merged_path = os.path.join(run_directory, "{}_{}".format(run_pass + 1, next_run_count))
                if len(run_paths) == 1:
                    os.replace(run_paths[0], merged_path)
                else:
                    with ExitStack() as stack:
                        runs = [stack.enter_context(open(path, "r")) for path in run_paths]
                        output = stack.enter_context(open(merged_path, "w"))
                        output.writelines(merge(*runs, key=cache_timestamp))
                    for path in run_paths:
                        os.remove(path)
                next_run_count += 1
            run_count = next_run_count
            run_pass += 1
        if run_count:
            os.replace(os.path.join(run_directory, "{}_0".format(run_pass)), cache_path)


def get_epoch_from_row(row, datetime_column):
    timestamp = row[datetime_column]
    try:
        if isinstance(timestamp, str):
            timestamp = dateutil.parser.isoparse(timestamp)
        if not isinstance(timestamp, datetime) or pd.isna(timestamp):
            return None
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def format_epoch(timestamp):
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def get_values_at_timestamp(file_handles, seek_timestamp, step_attributes):
    attribute_index = 0
    values = {}
    for attribute_path in file_handles:
        should_interpolate = step_attributes.get(attribute_path) is False
        next_cached_timestamp = next_timestamps_cache[attribute_index]
        # Continue along file till just passed the seek_timestamp - current_timestamps_cache &
        # current_values_cache should then have the values we read for the attribute at the timestamp we want
        while next_cached_timestamp is None or next_cached_timestamp <= seek_timestamp:
            current_timestamps_cache[attribute_index] = next_timestamps_cache[attribute_index]
            current_values_cache[attribute_index] = next_values_cache[attribute_index]
            line = file_handles[attribute_path].readline()
            if not line:
                break
            attribute_timestamp, attribute_value = parse_timestamp_and_value(line)
            next_timestamps_cache[attribute_index] = attribute_timestamp
            next_values_cache[attribute_index] = attribute_value
            next_cached_timestamp = next_timestamps_cache[attribute_index]
        if should_interpolate:
            calculated_value = interpolate(
                current_timestamps_cache[attribute_index],
                current_values_cache[attribute_index],
                next_timestamps_cache[attribute_index],
                next_values_cache[attribute_index],
                seek_timestamp
            )
        else:
            calculated_value = current_values_cache[attribute_index]
        if should_add_timestamps_columns:
            values.update({
                "{}{}".format(attribute_path, OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX): format_epoch(current_timestamps_cache[attribute_index]),
                "{}{}".format(attribute_path, OSIsoftConstants.VALUE_COLUMN_SUFFIX): calculated_value
            })
        else:
            values.update({
                attribute_path: calculated_value
            })
        attribute_index = attribute_index + 1
    return values


def interpolate(previous_timestamp, previous_value, next_timestamp, next_value, time_now):
    if previous_timestamp is None or next_timestamp is None or time_now is None:
        return None
    if previous_timestamp == next_timestamp or time_now == previous_timestamp:
        return previous_value
    rate_of_change = (float(next_value) - float(previous_value)) / (float(next_timestamp) - float(previous_timestamp))
    value_now = float(previous_value) + rate_of_change * (float(time_now) - float(previous_timestamp))
    return value_now


def clean_cache(paths_to_file_handles):
    logger.info("Polling done, cleaning the cache files")
    # Close and delete all cache files
    for attribute_path in paths_to_file_handles:
        paths_to_file_handles[attribute_path].close()
        os.remove(paths_to_file_handles[attribute_path].name)
    logger.info("Cleaning done, all done.")


def get_column_name_specifications():
    column_name_max_length = number_of_elements = None
    if should_make_column_names_db_compatible:
        if columns_names_normalization == "hashed":
            column_name_max_length = config.get("column_name_max_length", 31)
            if column_name_max_length < 10:
                column_name_max_length = 10
            if should_add_timestamps_columns:
                column_name_max_length -= column_name_suffix_margin
        elif columns_names_normalization == "elements":
            number_of_elements = config.get("number_of_elements", 1)
            if number_of_elements < 1:
                number_of_elements = 1
    return column_name_max_length, number_of_elements


input_dataset = get_input_names_for_role('input_dataset')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

output_names_stats = get_output_names_for_role('api_output')
output_dataset = dataiku.Dataset(output_names_stats[0])

logger.info("Initialization with config={}".format(logger.filter_secrets(config)))

reference_attribute_path = config.get("synchronize_on_identifier")
input_paths_column = config.get("groupby_column")
datetime_column = config.get("datetime_column")
value_column = config.get("value_column")
column_name_suffix_margin = max([
    len(OSIsoftConstants.VALUE_COLUMN_SUFFIX),
    len(OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX)
])

columns_names_normalization = config.get("columns_names_normalization", "raw")
show_advanced_parameters = config.get("show_advanced_parameters", False)
chunk_size = config.get("chunk_size", DEFAULT_INPUT_CHUNK_SIZE) if show_advanced_parameters else DEFAULT_INPUT_CHUNK_SIZE
should_make_column_names_db_compatible = show_advanced_parameters and (columns_names_normalization in ["hashed", "elements"])
should_add_timestamps_columns = show_advanced_parameters and config.get("should_add_timestamps_columns", False)
column_name_max_length, number_of_elements = get_column_name_specifications()
normalized_paths = {}
if should_make_column_names_db_compatible:
    normalized_reference_path = normalise_name(reference_attribute_path, max_length=column_name_max_length, number_of_elements=number_of_elements)
    normalized_paths[reference_attribute_path] = normalized_reference_path
    reference_attribute_path = normalized_reference_path

if not input_paths_column:
    raise ValueError("There is no parameter column selected.")
if not reference_attribute_path:
    raise ValueError("There is no full path to reference attribute selected. For transposing the dataset, use the pivot recipe.")

input_parameters_dataset = dataiku.Dataset(input_dataset[0])

results = []
time_last_request = None
client = None
previous_server_url = ""
paths_to_file_handles = {}
last_cache_timestamps = {}
unordered_attributes = set()
file_counter = 0
step_attributes = {}

type_of_interpolation = config.get("type_of_interpolation", "last_value")
if type_of_interpolation == "auto":
    step_column_name = config.get("step_column_name", "Step")

input_columns = list(dict.fromkeys([input_paths_column, datetime_column, value_column]))
if type_of_interpolation == "auto" and step_column_name not in input_columns:
    input_columns.append(step_column_name)

# Cache each attribute
logger.info("Caching all attributes in {}".format(temp_location.name))
for input_parameters_dataframe in input_parameters_dataset.iter_dataframes(
    chunksize=chunk_size, columns=input_columns, parse_dates=[datetime_column]
):
    datetime_index = input_parameters_dataframe.columns.get_loc(datetime_column)
    path_index = input_parameters_dataframe.columns.get_loc(input_paths_column)
    value_index = input_parameters_dataframe.columns.get_loc(value_column)
    if type_of_interpolation == "auto":
        step_index = input_parameters_dataframe.columns.get_loc(step_column_name)
    for input_parameters_row in input_parameters_dataframe.itertuples(index=False, name=None):
        row_epoch = get_epoch_from_row(input_parameters_row, datetime_index)
        if row_epoch is None:
            continue
        attribute_path = input_parameters_row[path_index]
        if should_make_column_names_db_compatible:
            if attribute_path not in normalized_paths:
                normalized_paths[attribute_path] = normalise_name(attribute_path, max_length=column_name_max_length, number_of_elements=number_of_elements)
            attribute_path = normalized_paths[attribute_path]
        value = input_parameters_row[value_index]

        if attribute_path in paths_to_file_handles:
            pass
        else:
            paths_to_file_handles[attribute_path] = open(temp_location.name + "/temp_{}".format(file_counter), "w")
            if attribute_path == reference_attribute_path:
                time_reference_file = file_counter
            file_counter = file_counter + 1
        paths_to_file_handles[attribute_path].write("{}|{}\n".format(row_epoch, value))
        if attribute_path not in unordered_attributes:
            last_timestamp = last_cache_timestamps.get(attribute_path)
            if last_timestamp is not None and row_epoch < last_timestamp:
                unordered_attributes.add(attribute_path)
                del last_cache_timestamps[attribute_path]
            else:
                last_cache_timestamps[attribute_path] = row_epoch

        if type_of_interpolation == "auto":
            is_step_attribute = input_parameters_row[step_index]
            if is_step_attribute == "True" or is_step_attribute is True:
                step_attributes[attribute_path] = True
            elif is_step_attribute == "False" or is_step_attribute is False:
                step_attributes[attribute_path] = False
        elif type_of_interpolation == "interpolation":
            step_attributes[attribute_path] = False
        elif type_of_interpolation == "last_value":
            step_attributes[attribute_path] = True
    del input_parameters_dataframe

logger.info("Cached all {} attributes".format(file_counter))

for handle in paths_to_file_handles.values():
    handle.close()

# Reorder all caches were some timestamps are not ordered
if unordered_attributes:
    logger.info("Sorting {} out-of-order attribute caches".format(len(unordered_attributes)))
    for attribute_path in unordered_attributes:
        sort_cache_file(paths_to_file_handles[attribute_path].name)
last_cache_timestamps.clear()

# Reopen cache files from write mode to read mode
for attribute_path, handle in paths_to_file_handles.items():
    paths_to_file_handles[attribute_path] = open(handle.name, "r")
    current_timestamps_cache.append(None)
    current_values_cache.append(None)
    next_timestamps_cache.append(None)
    next_values_cache.append(None)

if len(current_timestamps_cache) == 0:
    clean_cache(paths_to_file_handles)
    raise ValueError("No timestamp was found in column '{}'".format(datetime_column))
reference_values_file = paths_to_file_handles.pop(reference_attribute_path, None)
if not reference_values_file:
    clean_cache(paths_to_file_handles)
    raise ValueError("The full path to reference attribute '{}' was not found in the path column '{}'".format(
        reference_attribute_path, input_paths_column
    ))
current_timestamps_cache.pop(0)
current_values_cache.pop(0)
next_timestamps_cache.pop(0)
next_values_cache.pop(0)

logger.info("Polling all attributes into final dataset")
# For each timestamp of synchronizer attribute, read the most up to date value of all other attributes
# Write all that, one column per attribute
first_dataframe = True
output_rows = []
with output_dataset.get_writer() as writer:
    for line in reference_values_file:
        timestamp, value = parse_timestamp_and_value(line)
        output_columns_dictionary = get_values_at_timestamp(paths_to_file_handles, timestamp, step_attributes)
        output_columns_dictionary.update({
            OSIsoftConstants.TIMESTAMP_COLUMN_NAME: format_epoch(timestamp),
            reference_attribute_path: value
        })
        if first_dataframe:
            output_columns = list(dict.fromkeys([
                OSIsoftConstants.TIMESTAMP_COLUMN_NAME, reference_attribute_path
            ] + list(output_columns_dictionary)))
            output_dataset.write_schema_from_dataframe(pd.DataFrame([output_columns_dictionary], columns=output_columns))
            output_batch_size = max(1, min(DEFAULT_OUTPUT_BATCH_SIZE, MAX_OUTPUT_BATCH_CELLS // len(output_columns)))
            first_dataframe = False
        output_rows.append(output_columns_dictionary)
        if len(output_rows) >= output_batch_size:
            writer.write_dataframe(pd.DataFrame(output_rows, columns=output_columns, dtype=object))
            output_rows.clear()
    if output_rows:
        writer.write_dataframe(pd.DataFrame(output_rows, columns=output_columns, dtype=object))

clean_cache(paths_to_file_handles)
