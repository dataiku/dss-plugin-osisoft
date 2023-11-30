# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas
from safe_logger import SafeLogger
from osisoft_constants import OSIsoftConstants
from osisoft_plugin_common import reorder_dataframe, iso_to_epoch, get_datetime_from_row


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

logger.info("PIWebAPI Interpolate recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))
current_timestamps_cache = []
current_values_cache = []
next_timestamps_cache = []
next_values_cache = []


input_dataset = get_input_names_for_role('input_dataset')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

output_names_stats = get_output_names_for_role('api_output')
output_dataset = dataiku.Dataset(output_names_stats[0])

logger.info("Initialization with config={}".format(logger.filter_secrets(config)))

datetime_column = config.get("datetime_column")

column_name_suffix_margin = max([
    len(OSIsoftConstants.VALUE_COLUMN_SUFFIX),
    len(OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX)
])

input_parameters_dataset = dataiku.Dataset(input_dataset[0])
input_parameters_dataframe = input_parameters_dataset.get_dataframe()

columns_to_interpolate = []
for column in input_parameters_dataframe.columns:
    if column.endswith(OSIsoftConstants.VALUE_COLUMN_SUFFIX):
        columns_name = column.split(OSIsoftConstants.VALUE_COLUMN_SUFFIX)[0]
        # Todo: check that the timestamp is there too before adding to the list
        columns_to_interpolate.append(columns_name)

logger.info("Columns to interpolate: {}".format(columns_to_interpolate))

results = []
time_last_request = None
client = None
previous_server_url = ""
groupby_list = {}
file_counter = 0
previous_row = None
first_dataframe = True
final_row = {}

with output_dataset.get_writer() as writer:
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        output_rows = []
        this_row = input_parameters_row.to_dict()
        reference_time = iso_to_epoch(get_datetime_from_row(input_parameters_row, datetime_column))
        if previous_row is None:
            previous_row = this_row
            previous_reference_time = reference_time
            continue
        # At this stage previous_row is past, this_row is present
        for column_to_interpolate in columns_to_interpolate:
            sample_time = iso_to_epoch(previous_row.get("{}{}".format(column_to_interpolate, OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX)))
            value = previous_row.get("{}{}".format(column_to_interpolate, OSIsoftConstants.VALUE_COLUMN_SUFFIX))
            if sample_time == previous_reference_time:
                # This sample can go in output straigth away
                previous_row["{}{}".format(column_to_interpolate, OSIsoftConstants.INTERPOLATED_COLUMN_SUFFIX)] = value
            elif sample_time < previous_reference_time:
                # Sample is in the past, so next one is in the future
                future_value = this_row.get("{}{}".format(column_to_interpolate, OSIsoftConstants.VALUE_COLUMN_SUFFIX))
                future_time = iso_to_epoch(this_row.get("{}{}".format(column_to_interpolate, OSIsoftConstants.TIMESTAMP_COLUMN_SUFFIX)))
                slope = (future_value - value) / (future_time - sample_time)
                interpolated_value = value + slope * (previous_reference_time - sample_time)
                interpolated_column_name = "{}{}".format(column_to_interpolate, OSIsoftConstants.INTERPOLATED_COLUMN_SUFFIX)
                previous_row[interpolated_column_name] = interpolated_value
            elif sample_time > previous_reference_time:
                # Temporal paradox, that should never happen
                raise Exception("Time issue: On row {}, timestamp for {} is advance of the reference timestamp".format(index, column_to_interpolate))
        output_dataframe = pandas.DataFrame([previous_row])
        output_dataframe = reorder_dataframe(output_dataframe, [datetime_column])
        if first_dataframe:
            output_dataset.write_schema_from_dataframe(output_dataframe)
            first_dataframe = False
        writer.write_dataframe(output_dataframe)
        previous_row = this_row
        previous_reference_time = reference_time
