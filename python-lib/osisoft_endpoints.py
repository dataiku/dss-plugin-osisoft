from osisoft_constants import OSIsoftConstants
from urllib.parse import urlparse


class OSIsoftEndpoints():
    def __init__(self, server_url):
        self.scheme, self.hostname, self.port, path = self.parse_server_url(server_url)
        self.web_api_path = path or OSIsoftConstants.WEB_API_PATH

    def parse_server_url(self, server_url):
        parsed = urlparse(server_url)
        scheme = parsed.scheme or OSIsoftConstants.DEFAULT_SCHEME
        hostname = parsed.hostname
        port = parsed.port
        path = parsed.path.strip('/')
        if not hostname and path:
            # urlparse parses one segment server names as being path with empty hostname
            # In intranets its more likely to be a server name with custom DNS, so we fix it here
            return scheme, path, port, ""
        return scheme, hostname, port, path

    def get_server_url(self):
        port_number = ":{}".format(self.port) if self.port else ""
        return "{}://{}{}".format(self.scheme, self.hostname, port_number)

    def get_base_url(self):
        return "/".join([
            self.get_server_url(),
            self.web_api_path
        ])

    def get_resource_path_url(self):
        #  piwebapi/attributes?path
        return "/".join([
            self.get_base_url(),
            OSIsoftConstants.ATTRIBUTES_PATH
        ])

    def get_web_api_path(self):
        return self.web_api_path

    def get_stream_value_url(self, webid):
        url = self.get_base_url() + "/streams/{webid}/value".format(webid=webid)
        return url

    def get_asset_servers_url(self):
        url = self.get_base_url() + "/assetservers"
        return url

    def get_data_servers_url(self):
        url = self.get_base_url() + "/dataservers"
        return url

    def get_event_frames_url(self):
        url = self.get_base_url() + "/eventframes"
        return url

    def get_attribute_url(self):
        url = self.get_base_url() + "/attributes/search"
        return url

    def get_data_from_webid_url(self, endpoint_type, data_type, webid):
        url_template = OSIsoftConstants.PIWEBAPI_ENDPOINTS.get(data_type, "RecordedData")
        if endpoint_type == "AF":
            url_template = OSIsoftConstants.PIWEBAPI_AF_ENDPOINTS.get(data_type, "RecordedData")
        url = url_template.format(
            base_url=self.get_base_url(),
            webid=webid
        )
        return url

    def get_calculation_time_url(self):
        url = self.get_base_url() + "/calculation/times"
        return url

    def get_batch_endpoint(self):
        return self.get_base_url() + "/batch/"
