# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import json
from osisoft_safe_logger import SafeLogger
import os
from osisoft_temp_utils import CustomTmpFile
from osisoft_constants import OSIsoftConstants
import dateutil.parser
from osisoft_column_name import normalise_name
from osisoft_transpose_types import AttributeType
from datetime import datetime


DEFAULT_INPUT_CHUNK_SIZE = 10000

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
    return json.loads(line)


def get_epoch_from_string(datetime_string):
    try:
        utc_time = datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M:%SZ")
        epoch_time = (utc_time - datetime(1970, 1, 1)).total_seconds()
    except Exception:
        return None
    return epoch_time


def get_datetime_from_string(datetime_string):
    try:
        _ = dateutil.parser.isoparse(datetime_string)
        return datetime_string
    except Exception:
        pass
    return None


def get_datetime_from_pandas(datetime_string):
    try:
        time_stamp = datetime_string.strftime('%Y-%m-%dT%H:%M:%SZ')
        return time_stamp
    except Exception:
        pass
    return None


def get_datetime_from_row(row, datetime_column):
    raw_datetime = row[datetime_column]
    if isinstance(raw_datetime, str):
        formated_datetime = get_datetime_from_string(raw_datetime)
    else:
        formated_datetime = get_datetime_from_pandas(raw_datetime)
    return formated_datetime


def get_values_at_timestamp(file_handles, seek_timestamp, step_attributes):
    attribute_index = 0
    values = {}
    for attribute_path in file_handles:
        next_cached_timestamp = next_timestamps_cache[attribute_index]
        previous_line = None
        # Continue along file till just passed the seek_timestamp - current_timestamps_cache &
        # current_values_cache should then have the values we read for the attribute at the timestamp we want
        while not next_cached_timestamp or (next_cached_timestamp <= seek_timestamp):
            current_timestamps_cache[attribute_index] = next_timestamps_cache[attribute_index]
            current_values_cache[attribute_index] = next_values_cache[attribute_index]
            line = file_handles[attribute_path].readline()
            if not line:
                break
            if previous_line and line == previous_line:
                logger.error("Loop ! attribute_path={}, line={}".format(attribute_path, line))
                break
            previous_line = line
            attribute_timestamp, attribute_value = parse_timestamp_and_value(line)
            next_timestamps_cache[attribute_index] = attribute_timestamp
            next_values_cache[attribute_index] = attribute_value
            next_cached_timestamp = next_timestamps_cache[attribute_index]
        if step_attributes.get(attribute_path) is False:
            calculated_value = interpolate(
                current_timestamps_cache[attribute_index],
                current_values_cache[attribute_index],
                next_timestamps_cache[attribute_index],
                next_values_cache[attribute_index],
                seek_timestamp
            )
        else:
            calculated_value = current_values_cache[attribute_index]
            calculated_value = attribute_types[attribute_path].convert(calculated_value)
        if should_add_timestamps_columns:
            values.update({
                "{}{}".format(attribute_path, OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX): current_timestamps_cache[attribute_index],
                "{}{}".format(attribute_path, OSIsoftConstants.VALUE_COLUMN_SUFFIX): calculated_value
            })
        else:
            values.update({
                attribute_path: calculated_value
            })
        attribute_index = attribute_index + 1
    return values


def interpolate(previous_timestamp, previous_value, next_timestamp, next_value, time_now):
    previous_timestamp = get_epoch_from_string(previous_timestamp)
    next_timestamp = get_epoch_from_string(next_timestamp)
    time_now = get_epoch_from_string(time_now)
    if previous_timestamp is None or next_timestamp is None or time_now is None:
        return None
    if previous_timestamp == next_timestamp or time_now == previous_timestamp:
        return previous_value
    if previous_value is None or next_value is None:
        return None
    rate_of_change = (float(next_value) - float(previous_value)) / (float(next_timestamp) - float(previous_timestamp))
    value_now = float(previous_value) + rate_of_change * (float(time_now) - float(previous_timestamp))
    return value_now


def clean_cache(paths_to_file_handles):
    logger.info("Polling done, cleaning the cache files")
    # Close and delete all cache files
    for attribute_path in paths_to_file_handles:
        handle = paths_to_file_handles[attribute_path]
        handle.close()
        if os.path.exists(handle.name):
            os.remove(handle.name)
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

show_advanced_parameters = config.get("show_advanced_parameters", False)
chunk_size = config.get("chunk_size", DEFAULT_INPUT_CHUNK_SIZE) if show_advanced_parameters else DEFAULT_INPUT_CHUNK_SIZE
columns_names_normalization = config.get("columns_names_normalization", "raw")
should_make_column_names_db_compatible = show_advanced_parameters and (columns_names_normalization in ["hashed", "elements"])
should_add_timestamps_columns = show_advanced_parameters and config.get("should_add_timestamps_columns", False)
column_name_max_length, number_of_elements = get_column_name_specifications()
if should_make_column_names_db_compatible:
    reference_attribute_path = normalise_name(reference_attribute_path, max_length=column_name_max_length, number_of_elements=number_of_elements)

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
file_counter = 0
step_attributes = {}
attribute_types = {}

type_of_interpolation = config.get("type_of_interpolation", "last_value")
if type_of_interpolation == "auto":
    step_column_name = config.get("step_column_name", "Step")

try:
    logger.info("Caching all attributes in {}".format(temp_location.name))
    input_columns = [column["name"] for column in input_parameters_dataset.read_schema()]
    input_chunks = input_parameters_dataset.iter_dataframes_forced_types(
        names=input_columns, dtypes={value_column: str}, parse_date_columns=False, chunksize=10000
    )
    for input_parameters_dataframe in input_chunks:
        for index, input_parameters_row in input_parameters_dataframe.iterrows():
            row_datetime = get_datetime_from_row(input_parameters_row, datetime_column)
            if not row_datetime:
                continue
            attribute_path = input_parameters_row.get(input_paths_column)
            if should_make_column_names_db_compatible:
                attribute_path = normalise_name(attribute_path, max_length=column_name_max_length, number_of_elements=number_of_elements)
            if attribute_path not in paths_to_file_handles:
                cache_path = os.path.join(temp_location.name, "temp_{}".format(len(paths_to_file_handles)))
                paths_to_file_handles[attribute_path] = open(cache_path, "w", encoding="utf-8")
                attribute_types[attribute_path] = AttributeType()
            value = attribute_types[attribute_path].observe(input_parameters_row.get(value_column))
            paths_to_file_handles[attribute_path].write(json.dumps([row_datetime, value]) + "\n")

            if type_of_interpolation == "auto":
                is_step_attribute = input_parameters_row.get(step_column_name)
                if is_step_attribute == "True" or is_step_attribute is True:
                    step_attributes[attribute_path] = True
                elif is_step_attribute == "False" or is_step_attribute is False:
                    step_attributes[attribute_path] = False
            elif type_of_interpolation == "interpolation":
                step_attributes[attribute_path] = False
            elif type_of_interpolation == "last_value":
                step_attributes[attribute_path] = True
        del input_parameters_dataframe

    logger.info("Cached all {} attributes".format(len(paths_to_file_handles)))
    if not paths_to_file_handles:
        raise ValueError("No timestamp was found in column '{}'".format(datetime_column))
    if reference_attribute_path not in paths_to_file_handles:
        raise ValueError("The full path to reference attribute '{}' was not found in the path column '{}'".format(
            reference_attribute_path, input_paths_column
        ))

    output_types = {}
    for attribute_path, attribute_type in attribute_types.items():
        should_interpolate = attribute_path != reference_attribute_path and step_attributes.get(attribute_path) is False
        try:
            output_types[attribute_path] = attribute_type.finalize(interpolate=should_interpolate)
        except ValueError as error:
            raise ValueError("Attribute '{}' is incompatible with interpolation mode '{}': {}".format(
                attribute_path, type_of_interpolation, error
            )) from error

    for attribute_path, handle in paths_to_file_handles.items():
        handle.close()
        paths_to_file_handles[attribute_path] = open(handle.name, "r", encoding="utf-8")
    reference_values_file = paths_to_file_handles[reference_attribute_path]
    synchronized_handles = {
        attribute_path: handle for attribute_path, handle in paths_to_file_handles.items()
        if attribute_path != reference_attribute_path
    }
    output_schema = [
        {"name": OSIsoftConstants.TIMESTAMP_COLUMN_NAME, "type": "string"},
        {"name": reference_attribute_path, "type": output_types[reference_attribute_path]}
    ]
    for attribute_path in synchronized_handles:
        current_timestamps_cache.append(None)
        current_values_cache.append(None)
        next_timestamps_cache.append(None)
        next_values_cache.append(None)
        if should_add_timestamps_columns:
            output_schema.extend([
                {"name": attribute_path + OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX, "type": "string"},
                {"name": attribute_path + OSIsoftConstants.VALUE_COLUMN_SUFFIX, "type": output_types[attribute_path]}
            ])
        else:
            output_schema.append({"name": attribute_path, "type": output_types[attribute_path]})

    output_dataset.write_schema(output_schema)
    logger.info("Polling all attributes into final dataset")
    with output_dataset.get_writer() as writer:
        for line in reference_values_file:
            timestamp, value = parse_timestamp_and_value(line)
            output_columns_dictionary = get_values_at_timestamp(synchronized_handles, timestamp, step_attributes)
            output_columns_dictionary.update({
                OSIsoftConstants.TIMESTAMP_COLUMN_NAME: timestamp,
                reference_attribute_path: attribute_types[reference_attribute_path].convert(value)
            })
            writer.write_row_dict(output_columns_dictionary)
finally:
    clean_cache(paths_to_file_handles)
