from osisoft_client import OSIsoftClient, PISystemClientError, format_output_row
from osisoft_plugin_common import epoch_to_iso
from osisoft_plugin_common import is_child_attribute_path, get_element_name_from_path


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

    def test_get_element_name_from_path(self):
        assert get_element_name_from_path("\\osisoft-pi-serv\\Well\\Assets\\TX532|Current") == 'TX532'
        assert get_element_name_from_path("\\osisoft-pi-serv\\Well\\Assets\\TX532") == 'TX532'
        assert get_element_name_from_path("TX532") == 'TX532'
        assert get_element_name_from_path("") is None
        assert get_element_name_from_path("|mknnkn") == ""
        assert get_element_name_from_path("\\something\\|mknnkn") == ""


class TestSmartGetRowsFromWebid:
    def setup_method(self):
        self.client = OSIsoftClient.__new__(OSIsoftClient)
        self.request_log = []

    def _build_fake_get_rows_from_webid(self, points, max_window_seconds=None):
        def fake_get_rows_from_webid(_self, webid, data_type, **kwargs):
            start_epoch = _self.parse_pi_time(kwargs["start_date"], to_epoch=True)
            end_epoch = _self.parse_pi_time(kwargs["end_date"], to_epoch=True)
            self.request_log.append((start_epoch, end_epoch))
            if max_window_seconds and (end_epoch - start_epoch) > max_window_seconds:
                raise PISystemClientError("Error 400 value is greater than the maximum allowed")
            rows = []
            for point_epoch in points:
                if start_epoch <= point_epoch <= end_epoch:
                    rows.append({
                        "Timestamp": epoch_to_iso(point_epoch),
                        "Value": point_epoch
                    })
            max_count = kwargs.get("max_count")
            if max_count:
                rows = rows[:max_count]
            return iter(rows)
        return fake_get_rows_from_webid.__get__(self.client, OSIsoftClient)

    def test_smart_get_rows_from_webid_uses_density_to_size_windows(self):
        points = [1000.0 + float(index * 60) for index in range(60)]
        self.client.get_rows_from_webid = self._build_fake_get_rows_from_webid(points)

        rows = list(self.client.smart_get_rows_from_webid(
            "webid",
            "RecordedData",
            start_date=epoch_to_iso(points[0]),
            end_date=epoch_to_iso(points[-1]),
            max_count=20
        ))

        assert len(rows) == len(points)
        assert [row["Value"] for row in rows] == points
        assert len(self.request_log) < 10

    def test_smart_get_rows_from_webid_halves_windows_when_server_rejects_large_ranges(self):
        points = [1000.0 + float(index * 10) for index in range(100)]
        self.client.get_rows_from_webid = self._build_fake_get_rows_from_webid(
            points,
            max_window_seconds=40
        )

        rows = list(self.client.smart_get_rows_from_webid(
            "webid",
            "RecordedData",
            start_date=epoch_to_iso(points[0]),
            end_date=epoch_to_iso(points[-1]),
            max_count=50
        ))

        assert len(rows) == len(points)
        assert [row["Value"] for row in rows] == points
        assert any((end - start) > 40 for start, end in self.request_log)
        assert any((end - start) <= 40 for start, end in self.request_log)
