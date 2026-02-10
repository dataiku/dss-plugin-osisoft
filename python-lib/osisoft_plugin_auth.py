import requests
from requests_ntlm import HttpNtlmAuth


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        request.headers["Authorization"] = "Bearer {}".format(self.token)
        return request


def get_auth(auth_type, username, password):
    if auth_type == "basic":
        return (username, password)
    elif auth_type == "ntlm":
        return HttpNtlmAuth(username, password)
    elif auth_type == "bearer_token":
        return BearerAuth(password)
    else:
        return None
