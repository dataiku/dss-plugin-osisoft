from safe_logger import SafeLogger
from osisoft_constants import OSIsoftConstants


logger = SafeLogger("PI System", ["username", "password"])


class OffsetPagination():
    def __init__(self, **kwargs):
        self.offset = int(kwargs.get("offset", 0))
        self.number_of_items_per_page = int(kwargs.get("number_of_items_per_page", OSIsoftConstants.DEFAULT_MAXCOUNT))

    def get_offset_paginated(self, calling_function, *args, **kwargs):
        kwargs["start_index"] = self.offset
        kwargs["max_count"] = self.number_of_items_per_page
        json_response = calling_function(*args, **kwargs)
        self.offset += self.number_of_items_per_page
        has_more = True
        if OSIsoftConstants.API_ITEM_KEY in json_response:
            items = json_response.get(OSIsoftConstants.API_ITEM_KEY, [])
            if not items or len(items) < self.number_of_items_per_page:
                has_more = False
        return json_response, has_more
