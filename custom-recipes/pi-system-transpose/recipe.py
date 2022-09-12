# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
import os
from temp_utils import CustomTmpFile


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])


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


def get_latest_data_at_timestamp(file_handles, timestamp):
    cache_index = 0
    ret = {}
    for attribute_path in file_handles:
        next_cached_timestamp = next_timestamps_cache[cache_index]
        previous_line = None
        while not next_cached_timestamp or (next_cached_timestamp <= timestamp):
            current_timestamps_cache[cache_index] = next_timestamps_cache[cache_index]
            current_values_cache[cache_index] = next_values_cache[cache_index]
            line = file_handles[attribute_path].readline()
            if not line:
                current_values_cache[cache_index] = "NaN"
                break
            if previous_line and line == previous_line:
                logger.error("Loop ! attribute_path={}, line={}".format(attribute_path, line))
                break
            previous_line = line
            attribute_timestamp, attribute_value = parse_timestamp_and_value(line)
            next_timestamps_cache[cache_index] = attribute_timestamp
            next_values_cache[cache_index] = attribute_value
            next_cached_timestamp = next_timestamps_cache[cache_index]
        ret.update({
            attribute_path: current_values_cache[cache_index]
        })
        cache_index = cache_index + 1

    return ret


input_dataset = get_input_names_for_role('input_dataset')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

output_names_stats = get_output_names_for_role('api_output')
output_dataset = dataiku.Dataset(output_names_stats[0])

logger.info("retrieve-list recipe config={}".format(logger.filter_secrets(config)))

synchronize_on_identifier = config.get("synchronize_on_identifier")
groupby_column = config.get("groupby_column")
datetime_column = config.get("datetime_column")
value_column = config.get("value_column")

if not groupby_column:
    raise ValueError("There is no parameter column selected.")

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
    datetime = input_parameters_row.get(datetime_column)
    groupby_parameter = input_parameters_row.get(groupby_column)
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

# Reopen cache files from write to read
file_counter = 0
for groupby_parameter in groupby_list:
    groupby_list[groupby_parameter].close()
    groupby_list[groupby_parameter] = open(temp_location.name + "/temp_{}".format(file_counter), "r")
    current_timestamps_cache.append(None)
    current_values_cache.append(None)
    next_timestamps_cache.append(None)
    next_values_cache.append(None)
    file_counter = file_counter + 1

reference_file = groupby_list.pop(synchronize_on_identifier)
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
        dictionary = get_latest_data_at_timestamp(groupby_list, timestamp)
        dictionary.update({
            synchronize_on_identifier: value,
            "timestamp": timestamp
        })
        unnested_items_rows.append(dictionary)
        unnested_items_rows = pd.DataFrame(unnested_items_rows)
        if first_dataframe:
            output_dataset.write_schema_from_dataframe(unnested_items_rows)
            first_dataframe = False
        writer.write_dataframe(unnested_items_rows)

logger.info("Polling done, cleaning the cache files")
# Close and delete all cache files
for groupby_parameter in groupby_list:
    groupby_list[groupby_parameter].close()
    os.remove(groupby_list[groupby_parameter].name)

logger.info("Cleaning done, all done.")
