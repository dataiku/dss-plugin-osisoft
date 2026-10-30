from datetime import date, datetime, timedelta

import numpy
import pandas


def normalize_input_value(value):
    if isinstance(value, dict):
        return {key: normalize_input_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, numpy.ndarray)):
        return [normalize_input_value(item) for item in value]
    if pandas.isna(value):
        return None
    if isinstance(value, (datetime, date, numpy.datetime64)):
        return pandas.Timestamp(value).value // 1000000
    if isinstance(value, (timedelta, pandas.Timedelta, numpy.timedelta64)):
        return pandas.Timedelta(value).value // 1000000
    if isinstance(value, numpy.generic):
        value = value.item()
    if isinstance(value, float) and not numpy.isfinite(value):
        return None
    return value


def input_row_to_dict(row):
    return {column: normalize_input_value(value) for column, value in row.items()}
