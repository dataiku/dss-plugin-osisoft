from osisoft_client import format_output_row
from osisoft_plugin_common import is_child_attribute_path
import pytest


class TestCommonMethods:
    def setup_class(self):
        self.rows_to_format = {
            'a': 1, 'Links': 'should not see that',
            'Items': [
                {'b': 11, 'Links': 'should not see that', 'Items': [
                    {'c': 111, 'Value': {'v': 1}}, {'c': 112}]}, {'b': 12, 'Items': [
                        {'c': 121}, {'c': 122}
                    ]}
                ]
            }
        self.path_to_child_attribute = "\\\\server\\database\\element1\\element2|attribute|child"
        self.path_to_attribute = "\\\\server\\database\\element1\\element2|attribute"
        self.path_to_attribute_with_pipe = "\\\\server\\database\\element1|withpipe|withsecondpipe\\element2|attribute"
        self.path_to_element = "\\\\server\\database\\element1\\element2"

    def test_format_output_row(self):
        formated_rows = list(format_output_row(self.rows_to_format))
        assert formated_rows[0] == {'a': 1, 'c': 111, 'b': 11, 'v': 1}

    def test_is_child_attribute_path(self):
        is_child_attribute = is_child_attribute_path(self.path_to_attribute)
        assert not is_child_attribute
        is_child_attribute = is_child_attribute_path(self.path_to_attribute_with_pipe)
        assert not is_child_attribute
        is_child_attribute = is_child_attribute_path(self.path_to_child_attribute)
        assert is_child_attribute
        is_child_attribute = is_child_attribute_path(self.path_to_element)
        assert not is_child_attribute
