from osisoft_constants import OSIsoftConstants
from urllib.parse import urlparse


class OSIsoftEndpoints():
    def __init__(self, server_url):
        self.scheme, self.hostname, self.port = self.parse_server_url(server_url)

    def parse_server_url(self, server_url):
        parsed = urlparse(server_url)
        scheme = parsed.scheme
        if scheme:
            hostname = parsed.hostname
        else:
            scheme = "https"
            hostname = parsed.path.split("/")[0]
        port = parsed.port
        return scheme, hostname, port

    def get_server_url(self):
        port_number = ":{}".format(self.port) if self.port else ""
        return self.scheme + "://" + self.hostname + port_number

    def get_base_url(self):
        return "/".join([
            self.get_server_url(),
            OSIsoftConstants.WEB_API_PATH
        ])

    def get_resource_path_url(self):
        #  piwebapi/attributes?path
        return "/".join([
            self.get_server_url(),
            OSIsoftConstants.WEB_API_PATH,
            OSIsoftConstants.ATTRIBUTES_PATH
        ])

    def get_stream_value_url(self, webid):
        url = self.get_base_url() + "/streams/{webid}/value".format(webid=webid)
        return url

    def get_asset_servers_url(self):
        url = self.get_base_url() + "/assetservers"
        return url

    def get_attribute_url(self):
        url = self.get_base_url() + "/attributes/search"
        return url

    def get_data_from_webid_url(self, endpoint_type, data_type, webid):
        url_template = OSIsoftConstants.PIWEBAPI_ENDPOINTS.get(data_type, "RecordedData")
        if endpoint_type == "AF":
            url_template = OSIsoftConstants.PIWEBAPI_AF_ENDPOINTS.get(data_type, "RecordedData")
        url = url_template.format(
            base_url=self.get_server_url(),
            webid=webid
        )
        return url
