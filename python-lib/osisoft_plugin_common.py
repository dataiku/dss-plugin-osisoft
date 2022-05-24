import os
import copy
from osisoft_constants import OSIsoftConstants


class OSIsoftConnectorError(ValueError):
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
    if show_advanced_parameters:
        setup_ssl_certificate(config.get("ssl_cert_path"))
        default_server = credentials.get("default_server")
        overwrite_server_url = config.get("server_url")
        can_disable_ssl_check = credentials.get("can_disable_ssl_check", False)
        is_ssl_check_disabled = config.get("is_ssl_check_disabled", False)
        if not overwrite_server_url:
            server_url = default_server
        else:
            server_url = overwrite_server_url
        if (not can_disable_ssl_check) and is_ssl_check_disabled:
            error_message = "You cannot disable SSL check on this preset. Please refer to your DSS admin"
        is_ssl_check_disabled = can_disable_ssl_check and is_ssl_check_disabled
    else:
        server_url = credentials.get("default_server")
        is_ssl_check_disabled = False
    if can_raise and error_message:
        raise OSIsoftConnectorError(error_message)
    if can_raise:
        return auth_type, username, password, server_url, is_ssl_check_disabled
    else:
        return auth_type, username, password, server_url, is_ssl_check_disabled, error_message


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
        "severity_levels": "severity"
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
            requests_params.update({requests_param_key: "{}".format(kwargs.get(kwarg))})
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
    return


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

    def add_record(self):
        self.counter += 1
