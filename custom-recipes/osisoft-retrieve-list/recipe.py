# -*- coding: utf-8 -*-
import dataiku
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
from osisoft_plugin_common import get_credentials, get_interpolated_parameters, normalize_af_path
from osisoft_client import OSIsoftClient
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("osisoft plugin", forbiden_keys=["token", "password"])


input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("retrieve-list recipe config={}".format(logger.filter_secrets(config)))

osisoft_credentials = config.get("osisoft_credentials", {})
auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)

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
interval, sync_time, boundary_type = get_interpolated_parameters(config)


input_parameters_dataset = dataiku.Dataset(input_dataset[0])
output_dataset = dataiku.Dataset(output_names_stats[0])
input_parameters_dataframe = input_parameters_dataset.get_dataframe()

results = []
time_last_request = None
client = None
previous_server_url = ""
with output_dataset.get_writer() as writer:
    first_dataframe = True
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        start_time = input_parameters_row.get(start_time_column, start_time) if use_start_time_column else start_time
        end_time = input_parameters_row.get(end_time_column, end_time) if use_end_time_column else end_time

        if client is None or previous_server_url != server_url:
            client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled)
            previous_server_url = server_url
        object_id = input_parameters_row.get(path_column)
        item = None
        if client.is_resource_path(object_id):
            object_id = normalize_af_path(object_id)
            item = client.get_item_from_path(object_id)
        if item:
            rows = client.get_row_from_item(
                item,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                can_raise=False
            )
        else:
            rows = client.get_row_from_webid(
                object_id,
                data_type,
                start_date=start_time,
                end_date=end_time,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                can_raise=False,
                endpoint_type="AF"
            )
        for row in rows:
            base = {
                "object_id": object_id,
                OSIsoftConstants.DKU_ERROR_KEY: None,
                "Timestamp": None,
                "Value": None,
                "UnitsAbbreviation": None,
                "Annotated": None,
                "Good": None,
                "Questionable": None,
                "Substituted": None
            }
            base.update(row)
            extention = client.unnest_row(base)
            results.extend(extention)

        unnested_items_rows = pd.DataFrame(results)
        if first_dataframe:
            default_columns = OSIsoftConstants.DEFAULT_ASSET_METRICS_SCHEMA
            output_dataset.write_schema(default_columns)
            first_dataframe = False
        writer.write_dataframe(unnested_items_rows)
        results = []
