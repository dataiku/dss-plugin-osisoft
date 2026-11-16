from osisoft_constants import OSIsoftConstants


def build_af_element_tree(
        client,
        database_url,
        batch_size=100,
        page_size=1000,
        current_level_paths=None,
        incremental=False,
    ):
    """
    Retrieve the full AF element tree for a given AF database using PI Web API batch calls.

    With incremental=True, retrieve at most one batch of pages and return tree
    fragments plus current_level_paths continuation records. Each record contains
    the occurrence's true_path and WebId, and optionally a pagination URL.
    None starts a traversal; an empty list marks a completed traversal.

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

    def to_node(item):
        KEYS_TO_CHECK = {
                "Name": "title", "TemplateName": "template_name", "CategoryNames": "category_names", "Description": "description",
                "HasChildren": "has_children", "Path": "path", "Paths": "paths", "WebId": "id", "checked": "checked", "BaseTemplate": "BaseTemplate",
                "Type": "value_type",
            }  # should we stick to python naming convention or keep pi's ones throughout ?
        details = {}
        details["category_names"] = []
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
    if incremental:
        if current_level_paths is None:
            current_level_paths = [{
                "true_path": None,
                "url": (
                    f"{element_url}?selectedFields={selectedFields}"
                    f"&maxCount={page_size}&associations=Paths"
                ),
            }]
        pending = current_level_paths[:batch_size]
        remaining_paths = list(current_level_paths[batch_size:])
        resource_map = {}
        for index, parent in enumerate(pending):
            resource_map[str(index)] = parent.get("url") or (
                f"{base_url}/elements/{parent['id']}/elements"
                f"?selectedFields={selectedFields}&maxCount={page_size}&associations=Paths"
            )
        batch_response = post_batch_get(resource_map) if resource_map else {}
        tree = []
        children = []
        for index, parent in enumerate(pending):
            items, next_link = extract_items_and_next_link(
                batch_response.get(str(index), {}), parent.get("id", "database")
            )
            nodes = []
            for item in items:
                node = to_node(item)
                parent_path = parent["true_path"]
                node["true_path"] = (
                    parent_path + "\\" + node["title"] if parent_path is not None else node["path"]
                )
                node["is_weak"] = node["true_path"] != node["path"]
                nodes.append(node)
                remaining_paths.append({"true_path": node["true_path"], "id": node["id"]})
            if parent["true_path"] is None:
                tree.extend(nodes)
            else:
                children.append({"parent_path": parent["true_path"], "children": nodes})
            if next_link:
                remaining_paths.append(dict(parent, url=next_link))
        return {"tree": tree, "children": children, "current_level_paths": remaining_paths}

    root_elements = get_root_elements_paginated(element_url)
    tree = []
    node_by_true_path = {}
    current_level_paths = []

    for element in root_elements:
        node = to_node(element)
        node["true_path"] = node.get("path")
        node["is_weak"] = False
        tree.append(node)
        node_by_true_path[node["true_path"]] = node
        current_level_paths.append(node["true_path"])

    # Traverse the hierarchy level by level to preserve the tree structure.
    while current_level_paths:
        current_level_webids = [
            node_by_true_path[parent_path]["id"]
            for parent_path in current_level_paths
        ]
        unique_current_level_webids = list(dict.fromkeys(current_level_webids))
        children_map = fetch_children_batch_paginated(unique_current_level_webids)
        next_level_paths = []

        for parent_path in current_level_paths:
            parent_node = node_by_true_path[parent_path]
            parent_webid = parent_node["id"]
            parent_true_path = parent_node.get("true_path")
            child_elements = children_map.get(parent_webid, [])

            for child_element in child_elements:
                child_node = to_node(child_element)
                child_node["true_path"] = parent_true_path + "\\" + child_node.get("title")
                child_node["is_weak"] = (child_node["true_path"] != child_node["path"])
                parent_node["children"].append(child_node)
                node_by_true_path[child_node["true_path"]] = child_node
                next_level_paths.append(child_node["true_path"])

        current_level_paths = next_level_paths
    return tree
