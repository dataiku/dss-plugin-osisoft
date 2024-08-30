import os
import copy
import time
from osisoft_constants import OSIsoftConstants
from safe_logger import SafeLogger
from datetime import datetime, timezone
import dateutil.parser as date_parser
import re


regex_iso8601 = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'
match_iso8601 = re.compile(regex_iso8601).match

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


def check_must_convert_object_to_string(config):
    return config.get('show_advanced_parameters', False) and config.get('must_convert_object_to_string', False)


def convert_schema_objects_to_string(input_schema):
    schema = copy.deepcopy(input_schema)
    if isinstance(schema, list):
        columns = schema
    else:
        columns = schema.get("columns", [])
    for column in columns:
        column_type = column.get("type")
        if column_type == "object":
            column["type"] = "string"
    return schema


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
        "start_index": "startIndex",
        "summary_type": "summaryType"
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
    if search_mode in OSIsoftConstants.SEARCHMODES_ENDTIME_INCOMPATIBLE:
        requests_params.pop("endtime")
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
    if query_elements:
        return params.update({"q": " AND ".join(query_elements)})
    else:
        return {}


char_to_escape = {
        "%": "%25",
        " ": "%20",
        "!": "%21",
        '"': "%22",
        "#": "%23",
        "$": "%24",
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


def assert_server_url_ok(server_url):
    if not server_url:
        raise ValueError("The server URL is not set")


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
    type_column = None
    if "Value" in output_row and isinstance(output_row.get("Value"), dict):
        type_column = output_row.get("Type")
        output_row = output_row.get("Value")
        output_row.pop("Good", None)
        output_row.pop("Questionable", None)
        output_row.pop("Substituted", None)
        output_row.pop("Annotated", None)
    if is_enumeration_value:
        value = output_row.pop("Value", {})
        if value is not None:
            output_row["Value"] = value.get("Name", "")
            output_row["Value_ID"] = value.get("Value", None)
    if reference_row:
        if type_column:
            reference_row["Type"] = type_column
        output_row.update(reference_row)
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


def get_max_count(config):
    # some data_type requests only returns a maximum of 1k items
    # This can be increased by using maxCount
    DATA_TYPES_REQUIRING_MAXCOUNT = ["InterpolatedData", "PlotData", "RecordedData"]
    DEFAULT_MAXCOUNT = 1000
    max_count = None
    data_type = config.get("data_type", None)
    if data_type in DATA_TYPES_REQUIRING_MAXCOUNT:
        max_count = config.get("max_count", DEFAULT_MAXCOUNT)
    return max_count


def epoch_to_iso(epoch):
    logger.info("Converting '{}' epoch to iso".format(epoch))
    iso_timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    logger.info("Iso for '{}' is '{}'".format(epoch, iso_timestamp))
    return iso_timestamp


def iso_to_epoch(iso_timestamp):
    logger.info("Converting iso timestamp '{}' to epoch".format(iso_timestamp))
    if is_epoch(iso_timestamp):
        logger.info("Timestamp is already epoch")
        return iso_timestamp
    epoch_timestamp = None
    try:
        parsed_timestamp = date_parser.parse(iso_timestamp)
        epoch_timestamp = parsed_timestamp.timestamp()
    except Exception:
        logger.error("Error when converting iso timestamp '{}' to epoch".format(iso_timestamp))
        return None
    logger.info("Timestamp is now '{}'".format(epoch_timestamp))
    return epoch_timestamp


def is_epoch(timestamp):
    if timestamp is None:
        return False
    if isinstance(timestamp, int) or isinstance(timestamp, float):
        return True
    return timestamp.replace(".", "", 1).isdigit()


def is_iso8601(timestamp):
    # https://stackoverflow.com/questions/41129921/validate-an-iso-8601-datetime-string-in-python
    if not isinstance(timestamp, str):
        return False
    try:
        if match_iso8601(timestamp) is not None:
            return True
    except Exception:
        pass
    return False


def reorder_dataframe(unnested_items_rows, first_elements):
    columns = unnested_items_rows.columns.tolist()
    for first_element in reversed(first_elements):
        if first_element in columns:
            columns.remove(first_element)
            columns.insert(0, first_element)
    unnested_items_rows = unnested_items_rows[columns]
    return unnested_items_rows


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
    """
    Mesures the time between the calls of the start and stop methods
    If start / stop are called several times,
        - adds up all start / stop intervals
        - count the number of intervals
        - compute the average event time
        - provides a lists of the NUMBER_OF_SLOWEST_EVENTS_KEPT longest events by event id, for instance url    
    """
    NUMBER_OF_SLOWEST_EVENTS_KEPT = 5

    def __init__(self):
        self.slowest_events = []
        self.slowest_times = []
        self.total_duration = 0
        self.number_events = 0
        self.current_event_id = None

    def start(self, event_id=None):
        """
        Args:
            event_id (str, optional): name of the event to measure, to be used later on to list the longest events
        """
        self.start_time = float(time.time())
        self.number_events += 1
        self.current_event_id = event_id

    def stop(self):
        duration = float(time.time()) - self.start_time
        self.total_duration += duration
        if self.current_event_id:
            self._add_to_summary(duration)

    def _add_to_summary(self, duration):
        if not self.slowest_events:
            self.slowest_events.append(self.current_event_id)
            self.slowest_times.append(duration)
        else:
            index = 0
            was_inserted = False
            for slowest_time in self.slowest_times:
                if duration > slowest_time:
                    self.slowest_times.insert(index, duration)
                    self.slowest_events.insert(index, self.current_event_id)
                    was_inserted = True
                    break
                index += 1
            if not was_inserted:
                self.slowest_times.append(duration)
                self.slowest_events.append(self.current_event_id)
            self.slowest_times = self.slowest_times[:self.NUMBER_OF_SLOWEST_EVENTS_KEPT]
            self.slowest_events = self.slowest_events[:self.NUMBER_OF_SLOWEST_EVENTS_KEPT]

    def get_report(self):
        """
        Returns:
            dict: JSON containing total_duration, number_of_events, average_time, worst_performers list
        """
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
