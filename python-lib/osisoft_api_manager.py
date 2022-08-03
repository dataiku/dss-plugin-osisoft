from osisoft_endpoints import OSIsoftEndpoints


class OSIsoftAPIManager():
    def __init__(self, target_server_endpoint, api_manager_url):
        self.api_manager_base_url = None
        if api_manager_url:
            api_manager_endpoint = OSIsoftEndpoints(api_manager_url)
            self.api_manager_base_url = api_manager_endpoint.get_base_url()
        self.target_server_endpoint = target_server_endpoint
        
        self.target_server_base_url = self.target_server_endpoint.get_base_url()

    def get_api_manager_url(self, target_url):
        if not self.api_manager_base_url or not target_url:
            return target_url

        if target_url.startswith(self.target_server_base_url):
            length_to_remove = len(self.target_server_base_url)
            url_s_payload = target_url[length_to_remove:].strip("/")
            ret = "/".join([
                self.api_manager_base_url,
                url_s_payload
            ])
            return ret
        return target_url
        
    def get_base_url(self):
        return "/".join([
            self.get_server_url(),
            self.web_api_path
        ])

    def get_server_url(self):
        port_number = ":{}".format(self.port) if self.port else ""
        return "{}://{}{}".format(self.scheme, self.hostname, port_number)
