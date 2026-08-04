import requests
from osisoft_constants import OSIsoftConstants


def build_af_element_tree(
        client,
        database_url,
        # pi_web_api_url,
        # af_server,
        # af_database,
        # username=None,
        # password=None,
        # verify_ssl=True,
        batch_size=100,
        page_size=1000,
    ):
    """
    Retrieve the full AF element tree for a given AF database using PI Web API batch calls.

    Returns:
        [
            {
                "web_id": "...",
                "name": "...",
                "path": "...",
                "children": [...]
            },
            ...
        ]
    """
    base_url = client.endpoint.get_base_url()
    selectedFields = "Items.WebId;Items.Name;Items.Path;Items.TemplateName;Items.CategoryNames;Items.HasChildren;Items.Paths;Links.Next;Items.Links.Self"

    # def to_node(element_json):
    #     return {
    #         "id": element_json["WebId"],
    #         "name": element_json["Name"],
    #         "path": element_json["Path"],
    #         "children": [],
    #     }

    def to_node(item):
        KEYS_TO_CHECK = {
                "Name": "title", "TemplateName": "template_name", "CategoryNames": "category_names", "Description": "description",
                "HasChildren": "has_children", "Path": "path", "Paths": "paths", "WebId": "id", "checked": "checked", "BaseTemplate": "BaseTemplate",
                "Type": "value_type",
            }  # should we stick to python naming convention or keep pi's ones throughout ?
        details = {}
        for key_to_check in KEYS_TO_CHECK:
            value = item.get(key_to_check)
            if value:
                details[KEYS_TO_CHECK.get(key_to_check)] = value
        details["url"] = item.get("Links", {}).get("Self")
        details["type"] = "attribute" if "|" in details.get("path", "") else "element"
        details["children"] = []
        return details

    def chunked(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i + size]

    def extract_items_and_next_link(batch_item, parent_webid):
        status = batch_item.get("Status", 0)
        if status < 200 or status >= 300:
            raise RuntimeError(
                f"Batch request failed for parent WebId={parent_webid}, "
                f"status={status}, body={batch_item.get('Content')}"
            )

        content = batch_item.get("Content") or {}
        items = content.get("Items") or []
        links = content.get("Links") or {}
        next_link = links.get("Next")

        return items, next_link

    def post_batch_get(resource_map):
        """
        resource_map: dict[key] = absolute URL
        returns raw batch JSON
        """
        batch_request = {
            key: {
                "Method": "GET",
                "Resource": url,
            }
            for key, url in resource_map.items()
        }
        headers = OSIsoftConstants.WRITE_HEADERS

        response = client.post(
            f"{base_url}/batch",
            data=batch_request,
            headers=headers,
            params={}
        )
        response.raise_for_status()
        return response.json()

    def get_root_elements_paginated(elements_url):
        """
        Fetch all root elements, following pagination if needed.
        """
        items = []
        next_url = (
            f"{elements_url}"
            f"?selectedFields={selectedFields}"
            f"&maxCount={page_size}&associations=Paths"
        )
        while next_url:
            content = client.get(next_url, params={}, headers={})
            items.extend(content.get("Items") or [])
            links = content.get("Links") or {}
            next_url = links.get("Next")
        return items

    def fetch_children_batch_paginated(parent_webids):
        """
        Fetch all direct children for each parent WebId, handling pagination.

        Returns:
            dict[parent_webid] = [child_json, ...]
        """
        results = {parent_webid: [] for parent_webid in parent_webids}

        for group in chunked(parent_webids, batch_size):
            pending = {}

            for parent_webid in group:
                pending[parent_webid] = (
                    f"{base_url}/elements/{parent_webid}/elements"
                    f"?selectedFields={selectedFields}"
                    f"&maxCount={page_size}&associations=Paths" # TemplateName
                )

            while pending:
                key_to_parent = {}
                resource_map = {}

                for idx, (parent_webid, url) in enumerate(pending.items(), start=1):
                    key = str(idx)
                    key_to_parent[key] = parent_webid
                    resource_map[key] = url

                batch_response = post_batch_get(resource_map)
                next_pending = {}

                for key, parent_webid in key_to_parent.items():
                    batch_item = batch_response.get(key, {})
                    page_items, next_link = extract_items_and_next_link(
                        batch_item, parent_webid
                    )

                    results[parent_webid].extend(page_items)

                    if next_link:
                        next_pending[parent_webid] = next_link

                pending = next_pending

        return results

    element_url = "/".join([database_url.strip("/"), "elements"])
    root_elements = get_root_elements_paginated(element_url)
    tree = []
    node_by_webid = {}
    current_level_webids = []

    for element in root_elements:
        node = to_node(element)
        tree.append(node)
        node_by_webid[node["id"]] = node
        current_level_webids.append(node["id"])

    # Traverse the hierarchy level by level to preserve the tree structure.
    while current_level_webids:
        children_map = fetch_children_batch_paginated(current_level_webids)
        next_level_webids = []

        for parent_webid in current_level_webids:
            parent_node = node_by_webid[parent_webid]
            child_elements = children_map.get(parent_webid, [])

            for child_element in child_elements:
                child_node = to_node(child_element)
                parent_node["children"].append(child_node)
                node_by_webid[child_node["id"]] = child_node
                next_level_webids.append(child_node["id"])

        current_level_webids = next_level_webids

    return tree
