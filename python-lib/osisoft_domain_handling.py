class DomainHandler():
    def __init__(self, config):
        credentials = config.get('credentials', {})
        self.old_domain = credentials.get("old_domain")
        self.new_domain = credentials.get("new_domain")

    def ui_side_url(self, input):
        if not self.old_domain:
            return input
        if isinstance(input, list):
            return swap_in_list(input, self.new_domain, self.old_domain)
        input = swap(input, self.new_domain, self.old_domain)
        return input

    def client_side_url(self, url):
        if not self.old_domain:
            return url
        url = swap(url, self.old_domain, self.new_domain)
        return url


def swap_in_list(items, domain_to_replace, domain_to_replace_with):
    new_items = []
    for item in items:
        value = item.get("value")
        label = item.get("label")
        value = swap(value, domain_to_replace, domain_to_replace_with)
        new_items.append(
            {
                "value": "{}".format(value),
                "label": "{}".format(label)
            }
        )
    return new_items


def swap(url, domain_to_replace, domain_to_replace_with):
    if not url:
        return url
    if domain_to_replace in url:
        return url.replace(domain_to_replace, domain_to_replace_with)
    return url
