from osisoft_constants import OSIsoftConstants
from osisoft_plugin_common import get_item_details, get_next_page_url


def build_af_element_tree(client, database_url, page_size=1000):
    """Retrieve the AF hierarchy and return nested nodes for each element path.

    The batch_size argument is retained for compatibility.
    """
    database_url = database_url.rstrip("/")
    next_url = f"{database_url}/elements"
    params = {
        "searchFullHierarchy": "true",
        "associations": "Paths",
        "maxCount": page_size,
        "selectedFields": (
            "Items.WebId;Items.Name;Items.Path;Items.TemplateName;Items.CategoryNames;"
            "Items.HasChildren;Items.Paths;Links.Next;Items.Links.Self"
        ),
    }
    nodes_by_path = {}
    database_paths = set()
    while next_url:
        page = client.get(next_url, params=params, headers={})
        if OSIsoftConstants.DKU_ERROR_KEY in page:
            raise RuntimeError(page[OSIsoftConstants.DKU_ERROR_KEY])
        for item in page.get("Items") or []:
            details = get_item_details(item)
            canonical_path = details.get("path")
            for path in [canonical_path, *(details.get("paths") or [])]:
                if not path or path in nodes_by_path:
                    continue
                database_paths.add("\\".join(path.split("\\", 4)[:4]))
                nodes_by_path[path] = {
                    "category_names": [],
                    **details,
                    "true_path": path,
                    "is_weak": path != canonical_path,
                    "children": [],
                }
        next_url = get_next_page_url(page)
        params = {}

    if not database_paths:
        return []
    if len(database_paths) == 1:
        database_path = database_paths.pop()
    else:
        database = client.get(database_url, params={"selectedFields": "Path"}, headers={})
        if OSIsoftConstants.DKU_ERROR_KEY in database:
            raise RuntimeError(database[OSIsoftConstants.DKU_ERROR_KEY])
        database_path = database["Path"]

    tree = []
    database_prefix = database_path + "\\"
    for path, node in nodes_by_path.items():
        if not path.startswith(database_prefix):
            continue
        parent_path = path.rsplit("\\", 1)[0]
        if parent_path == database_path:
            tree.append(node)
        elif parent_path in nodes_by_path:
            nodes_by_path[parent_path]["children"].append(node)
    return tree
