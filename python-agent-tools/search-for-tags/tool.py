from osisoft_client import OSIsoftClient
from osisoft_plugin_common import (
    get_credentials,
    check_debug_mode,
)
from dataiku.llm.agent_tools import BaseAgentTool


class SearchTagsAgentTool(BaseAgentTool):
    def set_config(self, config, plugin_config):
        self.config = config
        auth_type, username, password, server_url, is_ssl_check_disabled = get_credentials(config)
        is_debug_mode = check_debug_mode(config)
        self.database_url = config.get("database_url")

        self.client = OSIsoftClient(
            self.database_url, auth_type, username, password,
            is_ssl_check_disabled=is_ssl_check_disabled,
            is_debug_mode=is_debug_mode
        )  # todo: remove the crashy stuff from here
        self.done_urls = {}

    def get_descriptor(self, tool):
        return {
            "description": "Search inside the hierachy of pi-system elements and attributes.",
            "inputSchema": {
                "$id": "https://example.com/agents/tools/hash/input",
                "title": "OSIsoft PI-system hierachy search tool",
                "type": "object",
                "properties": {
                    "result_format": {
                        "type": "string",
                        "description": "The type of result expected. It should be list containing any combination of 'path', 'webid', 'parent_path', 'parent_webid'"
                    },
                    "search_word": {
                        "type": "string",
                        "description": "Word to search in the comments section of elements and attributes"
                    },
                    "search_webid": {
                        "type": "string",
                        "description": "WebId to search. The WebId is base64 string."
                    },
                    "search_path": {
                        "type": "string",
                        "description": "PI-system path to search"
                    },
                    "parent": {
                        "type": "string",
                        "description": "webid or path of the parent of the item to search for"
                    },
                    "children": {
                        "type": "string",
                        "description": "webid or path of the children of the item to search for"
                    }
                },
                "required": []
            }
        }

    def recurse_in_database(self, url, parent_webid=None, parent_path=None):
        output_rows = []
        response = self.client.get_link_from_url(url)
        items = response.get("Items", [])
        if not items:
            items = [response]
        for item in items:
            links = item.pop("Links", {})
            output_rows.append(item)
            webid = item.get("WebId")
            path = item.get("Path")
            elements = links.get("Elements")
            attributes = links.get("Attributes")
            if elements and elements not in self.done_urls:
                elements_rows = self.recurse_in_database(elements)
                output = []
                for element_row in elements_rows:
                    out = {}
                    out["Parent webid"] = webid
                    out["Parent path"] = path
                    out.update(element_row)
                    output.append(out)
                output_rows += output
            if attributes and attributes not in self.done_urls:
                attributes_rows = self.recurse_in_database(attributes)
                output = []
                for attribute_row in attributes_rows:
                    out = {}
                    out["Parent webid"] = webid
                    out["Parent path"] = path
                    out.update(attribute_row)
                    output.append(out)
                output_rows += output
        return output_rows

    def invoke(self, input, trace):
        args = input["input"]
        search_word = args.get("search_word")
        parent = args.get("parent")
        parent_path, parent_webid = path_or_webid(parent)
        children = args.get("children")
        children_path, children_webid = path_or_webid(children)
        result_format = args.get("result_format", [])
        result_format = translate_keys(result_format)

        print("ALX:search_word={}, parent={}, children={}".format(
            search_word,
            parent,
            children
        ))
        tree = self.recurse_in_database(self.database_url)
        answer = []
        child_webid = None
        if children:
            child = extract_item(tree, children_path, children_webid)
            child_webid = child.get("Parent webid")

        for leaf in tree:
            keep = True
            if search_word:
                if search_word not in leaf.get("Name", "") and search_word not in leaf.get("Description", "") and search_word not in leaf.get("Path", ""):
                    keep = False
            # searching all children of X means looking for all items with parent = X
            # searching for parent of X means just returning parent key for X
            if parent_path:
                if leaf.get("Parent path", "") != parent_path:
                    keep = False
            if parent_webid:
                if leaf.get("Parent webid", "") != parent_webid:
                    keep = False
            if keep:
                answer.append(filter_dict(leaf, result_format))
            if child_webid:
                if child_webid == leaf.get("WebId"):
                    answer = [filter_dict(leaf, result_format)]
                    break
        print("ALX:there are {} elements in the tree".format(len(tree)))

        return {
            "output": answer,
            "sources":  [{
                "toolCallDescription": "{} elements were found".format(len(answer))
            }]
        }

    def load_sample_query(self, tool):
        return {"payload": "<Your payload to hash>"}


def path_or_webid(input_string):
    if not input_string:
        return None, None
    if "\\" in input_string:
        return input_string, None
    else:
        return None, input_string


def extract_item(items, path, webid):
    item = {}
    if webid:
        search_key = "WebId"
        search_value = webid
    else:
        search_key = "Path"
        search_value = path
    for item in items:
        if item.get(search_key) == search_value:
            return item
    return item


def translate_keys(llm_keys):
    TRANSLATION = {"path": "Path", "webid": "WebId", "parent_path": "Parent path", "parent_webid": "Parent webid"}
    pi_keys = []
    for llm_key in llm_keys:
        pi_key = TRANSLATION.get(llm_key)
        if pi_key:
            pi_keys.append(pi_key)
    return pi_keys


def filter_dict(dictionnary, keys):
    if not keys:
        return dictionnary
    if not dictionnary:
        return {}
    output_dictionary = {}
    for key in keys:
        output_dictionary[key] = dictionnary.get(key)
    return output_dictionary
