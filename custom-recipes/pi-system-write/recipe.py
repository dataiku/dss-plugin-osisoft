# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
from safe_logger import SafeLogger
from osisoft_plugin_common import (
    get_credentials, normalize_af_path, check_debug_mode,
    PerformanceTimer, get_max_count,
)
from osisoft_client import OSIsoftClient, OSIsoftWriter, OSIsoftBatchWriter
from osisoft_constants import OSIsoftConstants
from requests import models


logger = SafeLogger("pi-system plugin", forbiden_keys=["token", "password"])

logger.info("PIWebAPI Assets values writer recipe v{}".format(
    OSIsoftConstants.PLUGIN_VERSION
))


def analyse_response(response):
    status_code = None
    error = None
    if isinstance(response, models.Response):
        status_code = response.status_code
    else:
        error = "Issue with server's response"
    return status_code, error


def write_responses(responses, output):
    if not responses:
        return
    status_code = responses[0]
    path_used = responses[1]
    responses = responses[2]
    for response in responses:
        output.write_row_dict(
            {
                "Path": "{}".format(path_used),
                "Timestamp": response.get("Timestamp"),
                "Value": response.get("Value"),
                "Result": status_code
            }
        )


input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("Initialization with config config={}".format(logger.filter_secrets(config)))

auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
is_debug_mode = check_debug_mode(config)
max_count = get_max_count(config)
summary_type = config.get("summary_type")

use_server_url_column = config.get("use_server_url_column", False)
if not server_url and not use_server_url_column:
    raise ValueError("Server domain not set")

path_column = config.get("path_column", "")
webid_column = config.get("webid_column", "")
if not path_column and not webid_column:
    raise ValueError("There is no parameter column selected.")

time_column = config.get("time_column", "")
if not time_column:
    raise ValueError("There is no time column selected.")

value_column = config.get("value_column", "")
if not value_column:
    raise ValueError("There is no value column selected.")

server_url_column = config.get("server_url_column")

network_timer = PerformanceTimer()
processing_timer = PerformanceTimer()
processing_timer.start()

input_parameters_dataset = dataiku.Dataset(input_dataset[0])
output_dataset = dataiku.Dataset(output_names_stats[0])
input_parameters_dataframe = input_parameters_dataset.get_dataframe()

results = []
time_last_request = None
client = None
pi_writer = None
previous_server_url = ""
time_not_parsed = True

input_columns = list(input_parameters_dataframe.columns)

output_schema = []
output_schema.append({'name': 'Path', 'type': 'string'})
output_schema.append({'name': 'Timestamp', 'type': 'string'})
output_schema.append({'name': 'Value', 'type': 'string'})
output_schema.append({'name': 'Result', 'type': 'string'})
output_schema.append({'name': 'Error', 'type': 'string'})
output_dataset.write_schema(output_schema)

with output_dataset.get_writer() as output_writer:
    first_dataframe = True
    previous_path = None
    pi_writer = None
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        time = input_parameters_row.get(time_column)
        value = input_parameters_row.get(value_column)

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
                time = client.parse_pi_time(time)
            if not pi_writer:
                pi_writer = OSIsoftBatchWriter(client)

        if webid_column:
            object_id = input_parameters_row.get(webid_column)
        else:
            object_id = input_parameters_row.get(path_column)

        if client.is_resource_path(object_id):
            object_id = normalize_af_path(object_id)
        row = (time, value)
        responses = pi_writer.write_row(object_id, time, value)
        write_responses(responses, output_writer)
    responses = pi_writer.close()
    write_responses(responses, output_writer)

processing_timer.stop()
logger.info("Overall timer:{}".format(processing_timer.get_report()))
logger.info("Network timer:{}".format(network_timer.get_report()))
