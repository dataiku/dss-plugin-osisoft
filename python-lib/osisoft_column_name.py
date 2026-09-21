def add_chars(input_string):
    total = 0
    for char in input_string:
        total += ord(char)
    return total


def number_to_base(number, base):
    # from https://stackoverflow.com/questions/2267362/how-to-convert-an-integer-to-a-string-in-any-base
    if number == 0:
        return [0]
    digits = []
    while number:
        digits.append(int(number % base))
        number //= base
    return digits[::-1]


def digits_to_string(digits):
    output_string = ""
    for digit in digits:
        output_string += chr(97 + digit)
    return output_string


def get_hash(input_string):
    count = add_chars(input_string)
    digits = number_to_base(count, 25)
    output_string = digits_to_string(digits)
    return output_string


def shrink_name(name_to_shrink, max_length):
    if not name_to_shrink:
        return None
    if len(name_to_shrink) <= max_length:
        return name_to_shrink
    kept_string_length = max_length - 2  # start here as no point in hashing just one char
    while True:
        kept_section_of_name = name_to_shrink[-kept_string_length:]
        section_of_name_to_hash = name_to_shrink[:-kept_string_length]
        hash = "{}_".format(get_hash(section_of_name_to_hash))
        hash_length = len(hash)
        if hash_length + kept_string_length <= max_length:
            return "{}{}".format(hash, kept_section_of_name)
        kept_string_length -= 1
        # unlikely - would need to have a super long attribute path, but ensures termination
        if kept_string_length == 0 or hash_length >= max_length:
            return hash[:max_length]


def keep_number_of_elements(path_to_shrink, number_of_elements=None):
    tokens = path_to_shrink.split("|")
    attribute_name = "_".join(tokens[1:])
    if not number_of_elements or number_of_elements == 1:
        return attribute_name
    elements = tokens[:-1][0].split("\\")
    backward_number = 1 - number_of_elements
    output = elements[backward_number:] + [attribute_name]
    return "_".join(output)


def normalise_string(input_string):
    if not input_string:
        return None
    output_string = ""
    for char in input_string:
        ord_char = ord(char)
        # Allowed chars are a-z, A-Z, 1-9, _
        if (96 < ord_char < 123) or (64 < ord_char < 91) or (47 < ord_char < 58) or ord_char == 95:
            output_string += char
        else:
            output_string += "_"
    return output_string


def normalise_name(input_name, max_length=None, number_of_elements=None):
    if max_length is not None:
        return shrink_name(normalise_string(input_name), max_length)
    else:
        attribute_name = keep_number_of_elements(input_name, number_of_elements=number_of_elements)
        return normalise_string(attribute_name)
