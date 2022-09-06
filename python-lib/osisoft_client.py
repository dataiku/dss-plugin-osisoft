import requests
import logging
import copy
import json
import simplejson
from datetime import datetime
from requests_ntlm import HttpNtlmAuth
from osisoft_constants import OSIsoftConstants
from osisoft_endpoints import OSIsoftEndpoints
from osisoft_plugin_common import build_requests_params, is_filtered_out, is_server_throttling
from safe_logger import SafeLogger


logger = SafeLogger("PI System", ["username", "password"])


class PISystemClientError(ValueError):
    pass


class OSIsoftClient(object):

    def __init__(self, server_url, auth_type, username, password, is_ssl_check_disabled=False, can_raise=True, is_debug_mode=False):
        self.session = requests.Session()
        self.session.auth = self.get_auth(auth_type, username, password)
        self.session.verify = (not is_ssl_check_disabled)
        logger.info("Initialization server_url={}, is_ssl_check_disabled={}".format(server_url, is_ssl_check_disabled))
        self.endpoint = OSIsoftEndpoints(server_url)
        self.next_page = None
        self.can_raise = can_raise
        self.is_debug_mode = is_debug_mode

    def get_auth(self, auth_type, username, password):
        if auth_type == "basic":
            return (username, password)
        elif auth_type == "ntlm":
            return HttpNtlmAuth(username, password)
        else:
            return None

    def get_row_from_webid(self, webid, data_type, start_date=None, end_date=None,
                           interval=None, sync_time=None, boundary_type=None, selected_fields=None,
                           can_raise=True, endpoint_type="event_frames"):

        url = self.endpoint.get_data_from_webid_url(endpoint_type, data_type, webid)
        has_more = True
        while has_more:
            json_response, has_more = self.get_paginated(
                self.generic_get,
                url,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                selected_fields=selected_fields,
                can_raise=can_raise
            )
            if OSIsoftConstants.DKU_ERROR_KEY in json_response:
                json_response['object_id'] = "{}".format(webid)
                yield json_response
            items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
            for item in items:
                yield item

    def generic_get(self, url, start_date=None, end_date=None, interval=None, sync_time=None, boundary_type=None, selected_fields=None, can_raise=None):
        headers = self.get_requests_headers()
        params = self.get_requests_params(
            start_date,
            end_date,
            interval=interval,
            sync_time=sync_time,
            boundary_type=boundary_type,
            selected_fields=selected_fields
        )
        json_response = self.get(
            url=url,
            headers=headers,
            params=params,
            can_raise=can_raise
        )
        return json_response

    def get_row_from_item(self, item, data_type, start_date=None, end_date=None, interval=None, sync_time=None, boundary_type=None, can_raise=True):
        has_more = True
        while has_more:
            json_response, has_more = self.get_paginated(
                self.get_link_from_item,
                item,
                data_type,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                sync_time=sync_time,
                boundary_type=boundary_type,
                can_raise=can_raise
            )
            if OSIsoftConstants.DKU_ERROR_KEY in json_response:
                json_response['object_id'] = "{}".format(item)
                yield json_response
            items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [json_response])
            for item in items:
                yield self.loop_sub_items(item)

    def get_link_from_item(self, item, data_type, start_date, end_date, interval=None, sync_time=None, boundary_type=None, can_raise=True):
        url = self.extract_link_with_key(item, data_type)
        if not url:
            error_message = "This object does not have {} data type".format(data_type)
            if can_raise:
                raise PISystemClientError(error_message)
            return {OSIsoftConstants.DKU_ERROR_KEY: error_message}
        headers = self.get_requests_headers()
        params = build_requests_params(start_time=start_date, end_time=end_date, interval=interval, sync_time=sync_time, sync_time_boundary_type=boundary_type)
        json_response = self.get(
            url=url,
            headers=headers,
            params=params
        )
        return json_response

    def get_row_from_url(self, url=None, start_date=None, end_date=None, interval=None, sync_time=None):
        has_more = True
        while has_more:
            json_response, has_more = self.get_paginated(
                self.get_link_from_url,
                url, start_date=start_date, end_date=end_date, interval=interval, sync_time=sync_time
            )
            items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [json_response])
            for item in items:
                if OSIsoftConstants.API_ITEM_KEY in item:
                    rets = self.loop_sub_items(item)
                    for ret in rets:
                        yield ret
                else:
                    yield item

    def get_row_from_urls(self, links=None, data_type=None, start_date=None, end_date=None, interval=None, sync_time=None):
        links = links or []
        for link in links:
            url = link
            rows = self.get_row_from_url(url, start_date=start_date, end_date=end_date, interval=interval, sync_time=sync_time)
            for row in rows:
                yield row

    def get_link_from_url(self, url, start_date=None, end_date=None, interval=None, sync_time=None):
        if not url:
            url = self.endpoint.get_base_url()
        headers = self.get_requests_headers()
        params = build_requests_params(start_time=start_date, end_time=end_date, interval=interval, sync_time=sync_time)
        json_response = self.get(
            url=url,
            headers=headers,
            params=params
        )
        return json_response

    def get_paginated(self, calling_function, *args, **kwargs):
        if self.next_page:
            json_response = self.get(self.next_page, headers=self.get_requests_headers(), params={})
            self.next_page = None
        else:
            json_response = calling_function(*args, **kwargs)
        self.next_page = json_response.get("Links", {}).get("Next", None)
        if self.next_page:
            has_more = True
            logging.info("Next page is {}".format(self.next_page))
        else:
            has_more = False
        if OSIsoftConstants.API_ITEM_KEY in json_response:
            items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
            if not items:
                has_more = False
        return json_response, has_more

    def is_resource_path(self, reference):
        if isinstance(reference, str):
            return reference.startswith("\\")
        else:
            return False

    def get_web_id(self, resource_path):
        url = self.endpoint.get_resource_path_url()
        headers = self.get_requests_headers()
        params = self.get_resource_path_params(resource_path)
        json_response = self.get(
            url=url,
            headers=headers,
            params=params,
            can_raise=False,
            error_source="get_web_id"
        )
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            logging.warning("Path {} not found by resource path search, trying by traversing")
            json_response = self.traverse_path(resource_path)
        return json_response.get("WebId")

    def get_item_from_path(self, item_path):
        url = self.endpoint.get_resource_path_url()
        headers = self.get_requests_headers()
        params = self.get_resource_path_params(item_path)
        json_response = self.get(
            url=url,
            headers=headers,
            params=params,
            can_raise=False,
            error_source="get_item_from_path"
        )
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            json_response = self.traverse_path(item_path)
        return json_response

    def get_item_from_url(self, url):
        headers = self.get_requests_headers()
        params = {}
        json_response = self.get(
            url=url,
            headers=headers,
            params=params,
            can_raise=False,
            error_source="get_item_from_url"
        )
        return json_response

    def get(self, url, headers, params, can_raise=True, error_source=None):
        error_message = None
        url = build_query_string(url, params)
        logger.info("Trying to connect to {}".format(url))
        try:
            response = None
            while is_server_throttling(response):
                response = self.session.get(
                    url=url,
                    headers=headers
                )
                if self.is_debug_mode:
                    logger.info("response={}".format(response.content)[:1000])
        except Exception as err:
            error_message = "Could not connect. Error: {}{}".format(formatted_error_source(error_source), err)
            logger.error(error_message)
            if can_raise:
                raise PISystemClientError(error_message)
        if not error_message:
            error_message = self.assert_valid_response(response, can_raise=can_raise, error_source=error_source)
        if error_message:
            return {OSIsoftConstants.DKU_ERROR_KEY: error_message}
        json_response = simplejson.loads(response.content)
        return json_response

    def post_stream_value(self, webid, data):
        url = self.endpoint.get_stream_value_url(webid)
        headers = OSIsoftConstants.WRITE_HEADERS
        params = {}
        response = self.post(
            url=url,
            headers=headers,
            params=params,
            data=data
        )
        return response

    def post_value(self, url, data):
        headers = OSIsoftConstants.WRITE_HEADERS
        params = {}
        response = self.post(
            url=url,
            headers=headers,
            params=params,
            data=data
        )
        return response

    def post(self, url, headers, params, data, can_raise=True, error_source=None):
        url = build_query_string(url, params)
        response = self.session.post(
            url=url,
            headers=headers,
            json=data
        )
        self.assert_valid_response(response, can_raise=can_raise, error_source=error_source)
        return response

    def get_resource_path_params(self, resource_path):
        return {
            "path": escape(resource_path)
        }

    def get_requests_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br"
        }

    def get_requests_params(self, start_date=None, end_date=None, interval=None, sync_time=None, boundary_type=None, selected_fields=None):
        params = {}
        if start_date:
            params.update({"starttime": start_date})
        if end_date:
            params.update({"endtime": end_date})
        if interval:
            params.update({"interval": interval})
        if sync_time:
            params.update({"syncTime": sync_time})
        if boundary_type:
            params.update({"syncTimeBoundaryType": boundary_type})
        if selected_fields:
            params.update({"selectedFields": selected_fields})
        return params

    def assert_valid_response(self, response, can_raise=True, error_source=None):
        if response.status_code >= 400:
            error_message = "Error {}{}".format(formatted_error_source(error_source), response.status_code)
            try:
                json_response = simplejson.loads(response.content)
                if OSIsoftConstants.DKU_ERROR_KEY in json_response:
                    error_message = error_message + " {}".format(json_response.get(OSIsoftConstants.DKU_ERROR_KEY))
                if "Message" in json_response:
                    error_message = error_message + " {}".format(json_response.get("Message"))
            except Exception as err:
                logger.error("{}".format(err))
            logger.error(error_message)
            logger.error("response.content={}".format(response.content))
            if can_raise:
                raise PISystemClientError(error_message)
            return error_message

    def loop_sub_items(self, base_row):
        base_row.pop("Links", None)
        if OSIsoftConstants.API_ITEM_KEY in base_row:
            sub_items = base_row.pop(OSIsoftConstants.API_ITEM_KEY, [])
            new_rows = []
            for sub_item in sub_items:
                new_row = copy.deepcopy(base_row)
                new_row.update(sub_item)
                new_rows.append(new_row)
            return new_rows
        else:
            return unnest(base_row)

    def get_asset_servers(self, can_raise=True):
        asset_servers = []
        asset_servers_url = self.endpoint.get_asset_servers_url()
        headers = self.get_requests_headers()
        json_response = self.get(url=asset_servers_url, headers=headers, params={}, error_source="get_asset_servers", can_raise=can_raise)
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            return [{
                "label": json_response.get(OSIsoftConstants.DKU_ERROR_KEY)
            }]
        items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
        for item in items:
            asset_servers.append({
                "label": item.get("Name"),
                "value": item.get("Links").get("Databases")
            })
        return asset_servers

    def get_next_choices(self, next_url, next_key, params=None, use_name_as_link=False, filter=None):
        params = params or {}
        next_choices = []
        headers = self.get_requests_headers()
        json_response = self.get(url=next_url, headers=headers, params=params, error_source="get_next_choices")
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            return [{
                "label": json_response.get(OSIsoftConstants.DKU_ERROR_KEY)
            }]
        items = json_response.get(OSIsoftConstants.API_ITEM_KEY)
        for item in items:
            if not is_filtered_out(item, filter):
                next_choices.append({
                    "label": item.get("Name"),
                    "value": item.get("Name") if use_name_as_link else item.get("Links").get(next_key)
                })
        return next_choices

    def get_next_choices_as_json(self, next_url, next_key, params=None, use_name_as_link=False):
        params = params or {}
        next_choices = []
        headers = self.get_requests_headers()
        json_response = self.get(url=next_url, headers=headers, params=params, error_source="get_next_choices")
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            return [{
                "label": json_response.get(OSIsoftConstants.DKU_ERROR_KEY)
            }]
        items = json_response.get(OSIsoftConstants.API_ITEM_KEY)
        for item in items:
            next_choices.append({
                "label": item.get("Name"),
                "value": json.dumps({"url": item.get("Links").get(next_key), "label": item.get("Name")})
            })
        return next_choices

    def search_attributes(self, database_webid, **kwargs):
        search_attributes_base_url = self.endpoint.get_attribute_url()
        query = "Element:{{{}}} {}".format(
            self.build_element_query(**kwargs),
            self.build_attribute_query(**kwargs)
        )
        headers = self.get_requests_headers()
        params = {
            "query": query,
            "databaseWebId": database_webid
        }
        json_response = self.get(url=search_attributes_base_url, headers=headers, params=params)
        if OSIsoftConstants.DKU_ERROR_KEY in json_response:
            yield json_response
        items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
        for item in items:
            yield item

    def build_element_query(self, **kwargs):
        element_query_keys = {
            "element_name": "Name:'{}'",
            "search_root_path": "Root:'{}'",
            "element_template": "Template:'{}'",
            "element_type": "Type:'{}'",
            "element_category": "CategoryName:'{}'"
        }
        output_tokens = []
        for argument in kwargs:
            value = kwargs.get(argument)
            if value and argument in element_query_keys:
                template = element_query_keys.get(argument)
                output_tokens.append(template.format(value))
        return " ".join(output_tokens)

    def build_attribute_query(self, **kwargs):
        attribute_query_keys = {
            "attribute_name": "Name:'{}'",
            "attribute_category": "CategoryName:'{}'",
            "attribute_value_type": "Type:'{}'"
        }
        output_tokens = []
        for argument in kwargs:
            value = kwargs.get(argument)
            if value and argument in attribute_query_keys:
                template = attribute_query_keys.get(argument)
                output_tokens.append(template.format(value))
        return " ".join(output_tokens)

    def traverse(self, path_elements):
        # traversing:
        # piwebapi AssetServers Databases Items[].name="Well" Elements Items[].name=Assets Elements Items[].name=TX511 Attributes

        # Loading piwebapi initial page
        # next_url = self.get_web_api_base_url()
        next_url = self.endpoint.get_base_url()
        headers = self.get_requests_headers()
        json_response = self.get(url=next_url, headers=headers, params={}, error_source="traverse")

        # Asset server page
        next_url = self.extract_link_with_key(json_response, "AssetServers")
        json_response = self.get(url=next_url, headers=headers, params={}, error_source="traverse")

        item = self.extract_item_with_name(json_response, path_elements.pop(0))
        next_url = self.extract_link_with_key(item, "Databases")
        json_response = self.get(url=next_url, headers=headers, params={}, error_source="traverse")

        # get the database
        item = self.extract_item_with_name(json_response, path_elements.pop(0))
        next_url = self.extract_link_with_key(item, "Elements")
        json_response = self.get(url=next_url, headers=headers, params={}, error_source="traverse")

        # Looping through elements
        for path_element in path_elements:
            element, attribute = self.split_element_attribute(path_element)
            item = self.extract_item_with_name(json_response, element)
            if attribute:
                next_url = self.extract_link_with_key(item, "Attributes")
            else:
                next_url = self.extract_link_with_key(item, "Elements")
            json_response = self.get(url=next_url, headers=headers, params={}, error_source="traverse")
            if attribute:
                item = self.extract_item_with_name(json_response, attribute)

        return item

    def split_element_attribute(self, path_element):
        attribute = None
        path_elements = path_element.split("|")
        if len(path_elements) > 1:
            attribute = path_elements[1]
        return path_elements[0], attribute

    def extract_item_with_name(self, json_response, name):
        items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
        for item in items:
            item_name = item.get("Name", "")
            if item_name == name:
                return item
        return {}

    def extract_link_with_key(self, item, key):
        links = item.get("Links", {})
        return links.get(key, "")

    def traverse_path(self, path):
        elements = path.split("\\")
        elements.pop(0)  # Server name
        elements.pop(0)  # Database name
        json_response = self.traverse(elements)
        return json_response

    def unnest_row(self, row):
        rows_to_append = [row]
        if OSIsoftConstants.API_ITEM_KEY in row:
            items = row.pop(OSIsoftConstants.API_ITEM_KEY, [])
            for item in items:
                base_row = copy.deepcopy(row)
                base_row.update(item)
                rows_to_append.append(base_row)
            return rows_to_append
        else:
            if OSIsoftConstants.API_VALUE_KEY in row:
                base_row = copy.deepcopy(row)
                value = base_row.pop(OSIsoftConstants.API_VALUE_KEY)
                if isinstance(value, dict):
                    base_row.update(value)
                    return [base_row]
            return rows_to_append


def format_output_row(row):
    # Duplicates the row for each element of the Items key
    # Do that recursively (streamsets contains items in items)
    # Unnest the Value key if it is an object
    if OSIsoftConstants.API_ITEM_KEY in row:
        items = row.get(OSIsoftConstants.API_ITEM_KEY, [])
        for item in items:
            initial_row = copy.deepcopy(row)
            initial_row.pop(OSIsoftConstants.API_ITEM_KEY, None)
            initial_row.update(item)
            initial_row.pop("Links", None)
            new_rows = format_output_row(initial_row)
            for new_row in new_rows:
                yield new_row
    elif "Value" in row and isinstance(row.get("Value"), dict):
        initial_row = copy.deepcopy(row)
        value = initial_row.pop("Value", None)
        initial_row.update(value)
        yield initial_row
    else:
        yield row


class OSIsoftWriter(object):
    def __init__(self, client, path, column_names, value_url=False):
        self.client = client
        if value_url:
            self.webid = path
        else:
            self.webid = self.client.get_web_id(path)
        self.free_timing = "Timestamp" in column_names
        self.timestamp_rank, self.value_rank = self.get_column_rank(column_names)
        self.value_url = value_url
        self.path = path

    def get_column_rank(self, column_names):
        if "Timestamp" in column_names:
            logger.info("'Timestamp' column found")
            timestamp_rank = column_names.index("Timestamp")
        else:
            logger.info("No 'Timestamp' column found. Using current time")
            timestamp_rank = None
        if "Value" in column_names:
            value_rank = column_names.index("Value")
        else:
            raise PISystemClientError("The 'Value' column cannot be found in the input dataset")
        return timestamp_rank, value_rank

    def write_row(self, row):
        """
        Row is a tuple with N + 1 elements matching the schema passed to get_writer.
        The last element is a dict of columns not found in the schema
        """
        if self.timestamp_rank is not None:
            timestamp = self.timestamp_convertion(row[self.timestamp_rank])
        else:
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = {
            "Timestamp": timestamp,
            "Value": row[self.value_rank]
        }
        if self.value_url:
            self.client.post_value(self.path, data)
        else:
            self.client.post_stream_value(self.webid, data)

    def timestamp_convertion(self, timestamp):
        return timestamp

    def close(self):
        pass

    # https://eme/piwebapi/streams/{{webid}}}}/value
    # body:
    # {
    #   "Timestamp": "2015-04-03T18:46:10.39135 -7",
    #   "Value": 42.0,
    # }


def formatted_error_source(error_source):
    return "({}) ".format(error_source) if error_source else ""


def build_query_string(url, params):
    # requests doesn't handle backslash in params, so we build the query string by hand
    # Todo: extract existing query params from url
    params = params or {}
    tokens = []
    for key in params:
        value = params.get(key)
        if isinstance(value, list):
            for element in value:
                tokens.append(key+"="+str(element))
        else:
            tokens.append(key+"="+str(value))
    if len(tokens) > 0:
        return url + "?" + "&".join(tokens)
    else:
        return url


def unnest(row):
    if "Value" in row and isinstance(row.get("Value"), dict):
        value_object = row.pop("Value", {})
        if isinstance(value_object, dict):
            for key in value_object:
                row["Value_{}".format(key)] = value_object.get(key)
    return row


char_to_escape = {
        " ": "%20",
        "!": "%21",
        '"': "%22",
        "#": "%23",
        "$": "%24",
        "%": "%25",
        "&": "%26",
        "'": "%27",
        "(": "%28",
        ")": "%29",
        "*": "%2A",
        "+": "%2B",
        ",": "%2C",
        "-": "%2D",
        ".": "%2E",
        "/": "%2F",
        ":": "%3A",
        ";": "%3B",
        "<": "%3C",
        "=": "%3D",
        ">": "%3E",
        "?": "%3F",
        "@": "%40",
        "[": "%5B",
        "]": "%5D"
    }


def escape(string_to_escape):
    for char in char_to_escape:
        string_to_escape = string_to_escape.replace(char, char_to_escape.get(char))
    string_to_escape = string_to_escape.replace("\\", "%5C")
    return string_to_escape
