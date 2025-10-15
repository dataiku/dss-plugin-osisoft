import requests


class RequestRecorderSession(requests.Session):
    def __init__(self, server, api_key, client_id):
        super().__init__()
        print("Starting recording session on server {} for cliebt {}".format(server, client_id))
        self.server = server.strip("/") if server else "http://localhost:3002"
        self.api_key = api_key
        self.client_id = client_id.strip("/") if client_id else "0"
        self.session = requests.Session()

    def get(self, url, **kwargs):
        requests_parameters = dict(kwargs)
        requests_parameters["method"] = "GET"
        requests_parameters["url"] = url
        response = super().get(url, **kwargs)
        self._send(requests_parameters, response)
        return response

    def post(self, url, data=None, json=None, **kwargs):
        requests_parameters = dict(kwargs)
        requests_parameters["method"] = "POST"
        requests_parameters["url"] = url
        requests_parameters["data"] = data
        requests_parameters["json"] = json
        response = super().post(url, data=data, json=json, **kwargs)
        self._send(requests_parameters, response)
        return response

    def request(self, method,
            url,
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=None,
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,):
        response = super().request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,)
        requests_parameters = {}
        requests_parameters["method"] = method
        requests_parameters["url"] = url
        requests_parameters["params"] = params
        requests_parameters["data"] = data
        requests_parameters["headers"] = headers
        requests_parameters["cookies"] = cookies
        requests_parameters["files"] = files
        requests_parameters["auth"] = auth
        requests_parameters["timeout"] = timeout
        requests_parameters["allow_redirects"] = allow_redirects
        requests_parameters["proxies"] = proxies
        requests_parameters["hooks"] = hooks
        requests_parameters["stream"] = stream
        requests_parameters["verify"] = verify
        requests_parameters["cert"] = cert
        requests_parameters["json"] = json
        self._send(requests_parameters, response)
        return response

    def _send(self, data, response):
        endpoint = "{}/{}/record".format(
            self.server,
            self.client_id
        )
        if isinstance(response, requests.Response):
            data["_response"] = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.content
            }
        try:
            self.session.post(endpoint, json=data)
        except Exception as error:
            print("Error {} while sending {}".format(error, data))
