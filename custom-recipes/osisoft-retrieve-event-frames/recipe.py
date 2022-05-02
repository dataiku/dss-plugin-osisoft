# -*- coding: utf-8 -*-
import dataiku
import copy
from dataiku.customrecipe import get_input_names_for_role, get_recipe_config, get_output_names_for_role
import pandas as pd
from safe_logger import SafeLogger
from osisoft_plugin_common import get_credentials, get_interpolated_parameters
from osisoft_constants import OSIsoftConstants
from osisoft_client import OSIsoftClient


logger = SafeLogger("osisoft plugin", forbiden_keys=["token", "password"])

input_dataset = get_input_names_for_role('input_dataset')
output_names_stats = get_output_names_for_role('api_output')
config = get_recipe_config()
dku_flow_variables = dataiku.get_flow_variables()

logger.info("retrieve event frames recipe config={}".format(logger.filter_secrets(config)))

osisoft_credentials = config.get("osisoft_credentials", {})
auth_type, username, password, server_url, is_ssl_check_disabled, trusted_ssl_certificate = get_credentials(config)

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

time_last_request = None
client = None
previous_server_url = ""
with output_dataset.get_writer() as writer:
    first_dataframe = True
    absolute_index = 0
    for index, input_parameters_row in input_parameters_dataframe.iterrows():
        server_url = input_parameters_row.get(server_url_column, server_url) if use_server_url_column else server_url
        start_time = input_parameters_row.get(start_time_column, start_time) if use_start_time_column else start_time
        end_time = input_parameters_row.get(end_time_column, end_time) if use_end_time_column else end_time
        event_frame_webid = input_parameters_row.get("WebId")

        if client is None or previous_server_url != server_url:
            client = OSIsoftClient(server_url, auth_type, username, password, is_ssl_check_disabled=is_ssl_check_disabled, trusted_ssl_certificate=trusted_ssl_certificate)
            previous_server_url = server_url
        object_id = input_parameters_row.get(path_column)
        item = None
        if client.is_resource_path(object_id):
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
                can_raise=False
            )
        unnested_items_rows = []
        row_count = 0
        for row in rows:
            row_count += 1
            base_row = copy.deepcopy(row)
            base_row.pop("Links", None)
            items_column = base_row.pop(OSIsoftConstants.API_ITEM_KEY, [])
            for item in items_column:
                item_row = {"event_frame_webid": event_frame_webid}
                value = item.get("Value", {})
                if isinstance(value, dict):
                    item.pop("Value")
                    item_row.update(value)
                item_row.update(base_row)
                item_row.update(item)
                unnested_items_rows.append(item_row)
            if (not item) and ("Value" in base_row):
                item_row = {"event_frame_webid": event_frame_webid}
                value = base_row.get("Value", {})
                if isinstance(value, dict):
                    base_row.pop("Value")
                    base_row.update(value)
                item_row.update(base_row)
                unnested_items_rows.append(item_row)
        unnested_items_rows = pd.DataFrame(unnested_items_rows)
        if first_dataframe:
            output_dataset.write_schema_from_dataframe(unnested_items_rows)
            first_dataframe = False
        writer.write_dataframe(unnested_items_rows)
