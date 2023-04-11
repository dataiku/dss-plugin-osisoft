import os
import copy
import time
from osisoft_constants import OSIsoftConstants
from safe_logger import SafeLogger
from datetime import datetime


logger = SafeLogger("pi-system plugin", ["Authorization", "sharepoint_username", "sharepoint_password", "client_secret"])


class PISystemConnectorError(ValueError):
    pass


def get_credentials(config, can_raise=True):
    error_message = None
    credentials = config.get('credentials', {})
    auth_type = credentials.get("auth_type", "basic")
    osisoft_basic = credentials.get("osisoft_basic", {})
    ssl_cert_path = credentials.get("ssl_cert_path")
    if ssl_cert_path:
        setup_ssl_certificate(ssl_cert_path)
    username = osisoft_basic.get("user")
    password = osisoft_basic.get("password")
    show_advanced_parameters = config.get('show_advanced_parameters', False)
    server_url = credentials.get("default_server")
    is_ssl_check_disabled = False
    if show_advanced_parameters:
        setup_ssl_certificate(config.get("ssl_cert_path"))
        default_server = credentials.get("default_server")
        overwrite_server_url = config.get("server_url")
        can_disable_ssl_check = credentials.get("can_disable_ssl_check", False)
        can_override_server_url = credentials.get("can_override_server_url", False)
        is_ssl_check_disabled = config.get("is_ssl_check_disabled", False)
        if not overwrite_server_url:
            server_url = default_server
        else:
            if not can_override_server_url:
                error_message = "You cannot override the server URL on this preset. Please refer to your Dataiku admin"
            else:
                server_url = overwrite_server_url
        if (not can_disable_ssl_check) and is_ssl_check_disabled:
            error_message = "You cannot disable SSL check on this preset. Please refer to your Dataiku admin"
        is_ssl_check_disabled = can_disable_ssl_check and is_ssl_check_disabled
    if can_raise and error_message:
        raise PISystemConnectorError(error_message)
    if can_raise:
        return auth_type, username, password, server_url, is_ssl_check_disabled
    else:
        return auth_type, username, password, server_url, is_ssl_check_disabled, error_message


def get_advanced_parameters(config):
    show_advanced_parameters = config.get('show_advanced_parameters', False)
    batch_size = 500
    use_batch_mode = False
    if show_advanced_parameters:
        use_batch_mode = config.get("use_batch_mode", False)
        batch_size = config.get("batch_size", 500)
    return use_batch_mode, batch_size


def check_debug_mode(config):
    return config.get('show_advanced_parameters', False) and config.get('is_debug_mode', False)


def get_interpolated_parameters(config):
    data_type = config.get("data_type")
    interval = None
    sync_time = None
    boundary_type = None
    if data_type == "InterpolatedData":
        interval = config.get("interval")
        sync_time = config.get("sync_time")
        if sync_time:
            boundary_type = config.get("boundary_type")
    return interval, sync_time, boundary_type


def build_select_choices(choices=None):
    if not choices:
        return {"choices": []}
    if isinstance(choices, str):
        return {"choices": [{"label": "{}".format(choices)}]}
    if isinstance(choices, list):
        return {"choices": choices}
    if isinstance(choices, dict):
        returned_choices = []
        for choice_key in choices:
            returned_choices.append({
                "label": choice_key,
                "value": choices.get(choice_key)
            })


def build_requests_params(**kwargs):
    requests_params_options = {
        "start_time": "starttime",
        "end_time": "endtime",
        "interval": "interval",
        "sync_time": "syncTime",
        "sync_time_boundary_type": "syncTimeBoundaryType",
        "name_filter": "nameFilter",
        "category_name": "categoryName",
        "template_name": "templateName",
        "referenced_element_name_filter": "referencedElementNameFilter",
        "referenced_element_template": "referencedElementTemplate",
        "severity_levels": "severity",
        "max_count": "maxCount",
        "start_index": "startIndex"
    }
    requests_params = build_query_requests_params(
        query_name=kwargs.get("query_name"),
        query_category=kwargs.get("query_category"),
        query_template=kwargs.get("query_template"),
        query_attribute=kwargs.get("query_attribute")
    )
    for kwarg in kwargs:
        requests_param_key = requests_params_options.get(kwarg)
        if requests_param_key and kwargs.get(kwarg):
            value = kwargs.get(kwarg)
            if type(value) is list:
                requests_params.update({requests_param_key: value})
            else:
                requests_params.update({requests_param_key: "{}".format(value)})
    search_mode = kwargs.get("search_mode")
    if search_mode and (kwargs.get("start_time") or kwargs.get("end_time")):
        requests_params.update({"searchMode": "{}".format(search_mode)})
    resource_path = kwargs.get("resource_path")
    if resource_path:
        requests_params.update({"path": escape(resource_path)})
    return requests_params


def build_query_requests_params(query_name=None, query_category=None, query_template=None, query_attribute=None):
    params = {}
    query_elements = []
    if query_name:
        query_elements.append("name:({})".format(query_name))
    if query_category:
        query_elements.append("afcategories:({})".format(query_category))
    if query_template:
        query_elements.append("afelementtemplate:({})".format(query_template))
    if query_attribute:
        query_elements.append("attributename:({})".format(query_attribute))
    params.update({"q": " AND ".join(query_elements)})
    return params


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


def assert_time_format(date, error_source):
    # https://docs.osisoft.com/bundle/pi-web-api-reference/page/help/topics/time-strings.html
    pass


def get_schema_as_arrays(dataset_schema):
    columns = dataset_schema.get("columns", [])
    column_names = []
    column_types = []
    for column in columns:
        column_names.append(column.get("name"))
        column_types.append(column.get("type"))
    return column_names, column_types


def normalize_af_path(af_path):
    return "\\\\" + af_path.strip("\\")


def setup_ssl_certificate(ssl_cert_path):
    if ssl_cert_path:
        if os.path.isfile(ssl_cert_path):
            os.environ['REQUESTS_CA_BUNDLE'] = ssl_cert_path
            os.environ['CURL_CA_BUNDLE'] = ssl_cert_path


def remove_unwanted_columns(row):
    for unwated_column in OSIsoftConstants.SCHEMA_ATTRIBUTES_METRICS_FILTER:
        row.pop(unwated_column, None)


def format_output(input_row, reference_row=None, is_enumeration_value=False):
    output_row = copy.deepcopy(input_row)
    if reference_row:
        output_row.update(reference_row)
    if is_enumeration_value:
        value = output_row.pop("Value", {})
        output_row["Value"] = value.get("Name", "")
        output_row["Value_ID"] = value.get("Value", None)
    return output_row


def filter_columns_from_schema(schema_columns, columns_to_remove):
    output_schema = []
    for column in schema_columns:
        if column.get("name") not in columns_to_remove:
            output_schema.append(column)
    return output_schema


def is_filtered_out(item, filters=None):
    if not filters:
        return False
    for filter_key in filters:
        if filter_key not in item:
            return True
        filter_value = filters.get(filter_key)
        item_value = item.get(filter_key)
        if filter_value != item_value:
            return True
    return False


def is_server_throttling(response):
    if response is None:
        return True
    if response.status_code in [409, 429, 503]:
        logger.warning("Error {}, headers = {}".format(response.status_code, response.headers))
        seconds_before_retry = decode_retry_after_header(response)
        logger.warning("Sleeping for {} seconds".format(seconds_before_retry))
        time.sleep(seconds_before_retry)
        return True
    return False


def decode_retry_after_header(response):
    seconds_before_retry = OSIsoftConstants.DEFAULT_WAIT_BEFORE_RETRY
    raw_header_value = response.headers.get("Retry-After", str(OSIsoftConstants.DEFAULT_WAIT_BEFORE_RETRY))
    if raw_header_value.isdigit():
        seconds_before_retry = int(raw_header_value)
    else:
        # Date format, "Wed, 21 Oct 2015 07:28:00 GMT"
        try:
            datetime_now = datetime.now()
            datetime_header = datetime.strptime(raw_header_value, '%a, %d %b %Y %H:%M:%S GMT')
            if datetime_header.timestamp() > datetime_now.timestamp():
                # target date in the future
                seconds_before_retry = (datetime_header - datetime_now).seconds
        except Exception as err:
            logger.error("decode_retry_after_header error {}".format(err))
            seconds_before_retry = OSIsoftConstants.DEFAULT_WAIT_BEFORE_RETRY
    return seconds_before_retry


def is_child_attribute_path(path):
    if not path:
        return False
    reversed_path = path[::-1]
    has_one_pipe = False
    for char in reversed_path:
        if char == '|':
            if has_one_pipe:
                return True
            has_one_pipe = True
        if char == '\\':
            return False
    return False


def get_combined_description(default_columns, actual_columns):
    default_column_names = []
    output_columns = []
    for default_column in default_columns:
        default_column_name = default_column.get("name")
        default_column_names.append(default_column_name)
        output_columns.append(default_column)
    for actual_column in actual_columns:
        if actual_column not in default_column_names:
            output_columns.append({
                "name": actual_column,
                "type": "string"
            })
    return output_columns


def get_base_for_data_type(data_type, object_id):
    schema = OSIsoftConstants.RECIPE_SCHEMA_PER_DATA_TYPE.get(data_type)
    base = {}
    for item in schema:
        item_name = item.get("name")
        base[item_name] = None
    base['object_id'] = object_id
    ret = copy.deepcopy(base)
    return ret


class RecordsLimit():
    def __init__(self, records_limit=-1):
        self.has_no_limit = (records_limit == -1)
        self.records_limit = records_limit
        self.counter = 0

    def is_reached(self):
        if self.has_no_limit:
            return False
        self.counter += 1
        return self.counter > self.records_limit


class PerformanceTimer():
    def __init__(self):
        self.slowest_events = []
        self.slowest_times = []
        self.total_duration = 0
        self.number_events = 0
        self.current_event = None

    def start(self, event_id=None):
        self.start_time = float(time.time())
        self.number_events += 1
        self.current_event = event_id

    def stop(self):
        self.stop_time = float(time.time())
        duration = self.stop_time - self.start_time
        self.total_duration += duration
        if self.current_event:
            self.add_to_record(duration)

    def add_to_record(self, duration):
        if not self.slowest_events:
            self.slowest_events.append(self.current_event)
            self.slowest_times.append(duration)
        else:
            index = 0
            was_inserted = False
            for slowest_time in self.slowest_times:
                if duration > slowest_time:
                    self.slowest_times.insert(index, duration)
                    self.slowest_events.insert(index, self.current_event)
                    was_inserted = True
                    break
                index += 1
            if not was_inserted:
                self.slowest_times.append(duration)
                self.slowest_events.append(self.current_event)
            self.slowest_times = self.slowest_times[:5]
            self.slowest_events = self.slowest_events[:5]

    def get_report(self):
        report = {
            "total_duration": self.total_duration,
            "number_of_events": self.number_events,
            "average_time": self.get_average()
        }
        if self.slowest_events:
            report["worst_performers"] = self.get_worst_performers()
        return report

    def get_average(self):
        if not self.number_events:
            return None
        return self.total_duration / self.number_events

    def get_worst_performers(self):
        worst_performers = []
        for slowest_event, slowest_time in zip(self.slowest_events, self.slowest_times):
            worst_performers.append("{}: {}s".format(slowest_event, slowest_time))
        return worst_performers
