# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
import os
from temp_utils import CustomTmpFile
from osisoft_constants import OSIsoftConstants
import dateutil.parser
from column_name import normalise_name


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
    date = split_line[0]
    value = split_line[1]
    if value.endswith('\n'):
        value = value[:-1]
    return date, value


def get_datetime_from_string(datetime):
    try:
        _ = dateutil.parser.isoparse(datetime)
        return datetime
    except Exception:
        pass
    return None


def get_datetime_from_pandas(datetime):
    try:
        time_stamp = datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
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


def get_latest_values_at_timestamp(file_handles, seek_timestamp):
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
        if should_add_timestamps_columns:
            values.update({
                "{}{}".format(attribute_path, OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX): current_timestamps_cache[attribute_index],
                "{}{}".format(attribute_path, OSIsoftConstants.VALUE_COLUMN_SUFFIX): current_values_cache[attribute_index]
            })
        else:
            values.update({
                attribute_path: current_values_cache[attribute_index]
            })
        attribute_index = attribute_index + 1
    return values


def reorder_dataframe(unnested_items_rows, first_elements):
    columns = unnested_items_rows.columns.tolist()
    for first_element in first_elements:
        if first_element in columns:
            columns.remove(first_element)
            columns.insert(0, first_element)
    unnested_items_rows = unnested_items_rows[columns]
    return unnested_items_rows


def clean_cache(groupby_list):
    logger.info("Polling done, cleaning the cache files")
    # Close and delete all cache files
    for groupby_parameter in groupby_list:
        groupby_list[groupby_parameter].close()
        os.remove(groupby_list[groupby_parameter].name)
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

synchronize_on_identifier = config.get("synchronize_on_identifier")
groupby_column = config.get("groupby_column")
datetime_column = config.get("datetime_column")
value_column = config.get("value_column")
column_name_suffix_margin = max([
    len(OSIsoftConstants.VALUE_COLUMN_SUFFIX),
    len(OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX)
])

columns_names_normalization = config.get("columns_names_normalization", "raw")
should_make_column_names_db_compatible = config.get("show_advanced_parameters", False) and (columns_names_normalization in ["hashed", "elements"])
should_add_timestamps_columns = config.get("show_advanced_parameters", False) and config.get("should_add_timestamps_columns", False)
column_name_max_length, number_of_elements = get_column_name_specifications()
if should_make_column_names_db_compatible:
    synchronize_on_identifier = normalise_name(synchronize_on_identifier, max_length=column_name_max_length, number_of_elements=number_of_elements)

if not groupby_column:
    raise ValueError("There is no parameter column selected.")
if not synchronize_on_identifier:
    raise ValueError("There is no full path to reference attribute selected. For transposing the dataset, use the pivot recipe.")

input_parameters_dataset = dataiku.Dataset(input_dataset[0])
input_parameters_dataframe = input_parameters_dataset.get_dataframe()

results = []
time_last_request = None
client = None
previous_server_url = ""
groupby_list = {}
file_counter = 0

# Cache each attribute
logger.info("Caching all attributes in {}".format(temp_location.name))
for index, input_parameters_row in input_parameters_dataframe.iterrows():
    datetime = get_datetime_from_row(input_parameters_row, datetime_column)
    if not datetime:
        continue
    groupby_parameter = input_parameters_row.get(groupby_column)
    if should_make_column_names_db_compatible:
        groupby_parameter = normalise_name(groupby_parameter, max_length=column_name_max_length, number_of_elements=number_of_elements)
    value = input_parameters_row.get(value_column)

    if groupby_parameter in groupby_list:
        pass
    else:
        groupby_list[groupby_parameter] = open(temp_location.name + "/temp_{}".format(file_counter), "w")
        if groupby_parameter == synchronize_on_identifier:
            time_reference_file = file_counter
        file_counter = file_counter + 1
    groupby_list[groupby_parameter].writelines("{}|{}\n".format(datetime, value))

logger.info("Cached all {} attributes".format(file_counter))

# Reopen cache files from write mode to read mode
file_counter = 0
for groupby_parameter in groupby_list:
    groupby_list[groupby_parameter].close()
    groupby_list[groupby_parameter] = open(temp_location.name + "/temp_{}".format(file_counter), "r")
    current_timestamps_cache.append(None)
    current_values_cache.append(None)
    next_timestamps_cache.append(None)
    next_values_cache.append(None)
    file_counter = file_counter + 1

if len(current_timestamps_cache) == 0:
    clean_cache(groupby_list)
    raise ValueError("No timestamp was found in column '{}'".format(datetime_column))
reference_file = groupby_list.pop(synchronize_on_identifier, None)
if not reference_file:
    clean_cache(groupby_list)
    raise ValueError("The full path to reference attribute '{}' was not found in the path column '{}'".format(
        synchronize_on_identifier, groupby_column
    ))
current_timestamps_cache.pop(0)
current_values_cache.pop(0)
next_timestamps_cache.pop(0)
next_values_cache.pop(0)

# For each timestamp of synchronizer attribute, read the most up to date value of all other attributes
# Write all that, one column per attribute
first_dataframe = True
logger.info("Polling all attributes into final dataset")
with output_dataset.get_writer() as writer:
    for line in reference_file:
        unnested_items_rows = []
        timestamp, value = parse_timestamp_and_value(line)
        dictionary = get_latest_values_at_timestamp(groupby_list, timestamp)
        dictionary.update({
            OSIsoftConstants.TIMESTAMP_COLUMN_NAME: timestamp,
            synchronize_on_identifier: value
        })
        unnested_items_rows.append(dictionary)
        unnested_items_rows = pd.DataFrame(unnested_items_rows)
        unnested_items_rows = reorder_dataframe(unnested_items_rows, [synchronize_on_identifier, OSIsoftConstants.TIMESTAMP_COLUMN_NAME])
        if first_dataframe:
            output_dataset.write_schema_from_dataframe(unnested_items_rows)
            first_dataframe = False
        writer.write_dataframe(unnested_items_rows)

clean_cache(groupby_list)
