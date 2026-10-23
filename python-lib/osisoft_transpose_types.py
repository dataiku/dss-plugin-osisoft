import math
import re
import pandas


class AttributeType:
    def __init__(self):
        self.kind = None

    def observe(self, value):
        if pandas.isna(value):
            return None
        text = str(value)
        stripped = text.strip()
        if stripped.lower() in ("true", "false"):
            kind = "boolean"
        elif re.fullmatch(r"[+-]?[0-9]+", stripped):
            integer = int(stripped)
            kind = "bigint" if -(2 ** 63) <= integer < 2 ** 63 else "string"
        else:
            try:
                kind = "double" if math.isfinite(float(stripped)) else "string"
            except ValueError:
                kind = "string"
        if self.kind is None:
            self.kind = kind
        elif self.kind != kind:
            if {self.kind, kind} <= {"bigint", "double"}:
                self.kind = "double"
            else:
                self.kind = "string"
        return text

    def finalize(self, interpolate=False):
        if interpolate and self.kind is not None:
            if self.kind not in ("bigint", "double"):
                raise ValueError("Cannot interpolate {} values".format(self.kind))
            self.kind = "double"
        return self.kind or "string"

    def convert(self, value):
        if value is None:
            return None
        if self.kind == "bigint":
            return int(value)
        if self.kind == "double":
            return float(value)
        if self.kind == "boolean":
            return value.strip().lower() == "true"
        return value
