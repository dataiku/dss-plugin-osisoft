from pickle import FALSE
import sys

from dku_config.stl_config import STLConfig
from dku_input_validator.decomposition_input_validator import DecompositionInputValidator
from dku_timeseries import ExtremaExtractorParams
from dku_timeseries import IntervalRestrictorParams
from dku_timeseries import ResamplerParams
from dku_timeseries import WindowAggregator, WindowAggregatorParams
from safe_logger import SafeLogger
if sys.version_info >= (3, 0):
    from dku_timeseries.dku_decomposition.stl_decomposition import STLDecomposition

logger = SafeLogger("Time series preparation plugin")


def get_resampling_params(recipe_config):
    def _p(param_name, default=None):
        return recipe_config.get(param_name, default)

    interpolation_method = _p('interpolation_method')
    extrapolation_method = _p('extrapolation_method')
    constant_value = _p('constant_value')
    category_imputation_method = _p('category_imputation_method', 'empty')
    category_constant_value = _p('category_constant_value', '')
    time_step = _p('time_step')
    time_unit = _p('time_unit')
    time_unit_end_of_week = _p('time_unit_end_of_week')
    clip_start = _p('clip_start')
    clip_end = _p('clip_end')
    shift = _p('shift')
    time_reference_identifier = None
    if _p('advanced_activated') and _p('synchronize_on_identifier', False):
        time_reference_identifier = _p('time_reference_identifier', None)

    params = ResamplerParams(interpolation_method=interpolation_method,
                             extrapolation_method=extrapolation_method,
                             constant_value=constant_value,
                             category_imputation_method=category_imputation_method,
                             category_constant_value=category_constant_value,
                             time_step=time_step,
                             time_unit=time_unit,
                             time_unit_end_of_week=time_unit_end_of_week,
                             clip_start=clip_start,
                             clip_end=clip_end,
                             shift=shift,
                             time_reference_identifier=time_reference_identifier)
    params.check()
    return params




def check_python_version():
    if sys.version_info.major == 2:
        logger.warning(
            "You are using Python {}.{}. Python 2 is now deprecated for the Time Series preparation plugin. Please consider asking an administrator "
            "to delete the existing Python 2 code env and create a new Python 3 code environment".format(sys.version_info.major, sys.version_info.minor))


def check_time_column_parameter(recipe_config, dataset_columns):
    if recipe_config.get("datetime_column") not in dataset_columns:
        raise ValueError("Invalid time column selection: {}".format(recipe_config.get("datetime_column")))


def check_and_get_groupby_columns(recipe_config, dataset_columns):
    long_format = recipe_config.get("advanced_activated", False)
    if long_format:
        groupby_columns = _format_groupby_columns(recipe_config)
        _check_groupby_columns(groupby_columns, dataset_columns)
        return groupby_columns
    else:
        return []


def _format_groupby_columns(recipe_config):
    if recipe_config.get('advanced_activated') and recipe_config.get('groupby_column') and len(recipe_config.get('groupby_columns', [])) == 0:
        logger.warning(
            "The field `Column with identifier` is deprecated. It is now replaced with the field `Time series identifiers`, which allows for several "
            "identifiers. That is why you should preferably use the field 'Time series identifiers'. You can still use 'Column with identifier' if you "
            "have one identifier only")
        groupby_columns = [recipe_config.get('groupby_column')]
    elif recipe_config.get('advanced_activated') and recipe_config.get('groupby_columns'):
        if recipe_config.get('groupby_column'):
            logger.warning("The fields `Column with identifier` and `Time series identifiers` both contain a value. As `Column with identifiers`is deprecated, "
                           "the recipe will only consider the value of `Time series identifiers`. ")
        groupby_columns = recipe_config.get('groupby_columns')
    else:
        groupby_columns = []
    return groupby_columns


def _check_groupby_columns(groupby_columns, dataset_columns):
    if len(groupby_columns) == 0:
        raise ValueError("Long format is activated but no time series identifiers have been provided")
    if not all(identifier in dataset_columns for identifier in groupby_columns):
        raise ValueError("Invalid time series identifiers selection: {}".format(groupby_columns))
