from osisoft_constants import OSIsoftConstants


def build_af_element_tree(
        client,
        database_url,
        page_size=1000,
        current_level_paths=None,
    ):
    """
    Retrieve at most one batch of AF element pages using PI Web API batch calls.

    Return tree fragments plus only newly discovered current_level_paths records.
    The caller owns the queue and controls the number of records sent per call.
    Each record contains the occurrence's true_path and WebId, and optionally a
    pagination URL. None starts a traversal; an empty list requests no pages.
    Traversal is complete once the caller's queue is empty.

    Returns:
        A dict with root nodes in tree, child groups in children, and newly
        discovered continuation records in current_level_paths.
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

    element_url = "/".join([database_url.strip("/"), "elements"])
    if current_level_paths is None:
        current_level_paths = [{
            "true_path": None,
            "url": (
                f"{element_url}?selectedFields={selectedFields}"
                f"&maxCount={page_size}&associations=Paths"
            ),
        }]
    pending = current_level_paths
    remaining_paths = []
    resource_map = {}
    key_by_resource = {}
    parent_keys = []
    for parent in pending:
        resource = parent.get("url") or (
            f"{base_url}/elements/{parent['id']}/elements"
            f"?selectedFields={selectedFields}&maxCount={page_size}&associations=Paths"
        )
        if resource not in key_by_resource:
            key = str(len(resource_map))
            key_by_resource[resource] = key
            resource_map[key] = resource
        parent_keys.append(key_by_resource[resource])
    batch_response = post_batch_get(resource_map) if resource_map else {}
    tree = []
    children = []
    for key, parent in zip(parent_keys, pending):
        items, next_link = extract_items_and_next_link(
            batch_response.get(key, {}), parent.get("id", "database")
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
