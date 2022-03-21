class OSIsoftConnectorError(ValueError):
    pass


def get_credentials(config):
    credentials = config.get('credentials', {})
    auth_type = credentials.get("auth_type", "basic")
    osisoft_basic = credentials.get("osisoft_basic", {})
    username = osisoft_basic.get("user")
    password = osisoft_basic.get("password")
    show_advanced_parameters = config.get('show_advanced_parameters', False)
    if show_advanced_parameters:
        default_server = credentials.get("default_server")
        overwrite_server_url = config.get("server_url")
        if not overwrite_server_url:
            server_url = default_server
        else:
            server_url = overwrite_server_url
        is_ssl_check_disabled = credentials.get("can_disable_ssl_check", False) and config.get("is_ssl_check_disabled", False)
    else:
        server_url = credentials.get("default_server")
        is_ssl_check_disabled = False
    return auth_type, username, password, server_url, is_ssl_check_disabled


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
