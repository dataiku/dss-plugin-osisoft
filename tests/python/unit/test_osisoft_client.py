from osisoft_client import format_output_row
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

    def test_format_output_row(self):
        formated_rows = list(format_output_row(self.rows_to_format))
        assert formated_rows[0] == {'a': 1, 'c': 111, 'b': 11, 'v': 1}
