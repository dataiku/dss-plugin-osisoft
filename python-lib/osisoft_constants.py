class OSIsoftConstants(object):
    API_ITEM_KEY = "Items"
    API_VALUE_KEY = "Value"
    API_TIMESTAMP_KEY = "Timestamp"
    ASSET_METRICS_EMPTY_TEMPLATE = {
        "object_id": None,
        "Errors": None,
        "Timestamp": None,
        "Value": None,
        "UnitsAbbreviation": None,
        "Annotated": None,
        "Good": None,
        "Questionable": None,
        "Substituted": None
    }
    BASE_PER_DATA_TYPE = {}
    ATTRIBUTES_PATH = "attributes"
    CHAR_TO_ESCAPE = {
        " ", "%20",
        "!", "%21",
        '"', "%22",
        "#", "%23",
        "$", "%24",
        "%", "%25",
        "&", "%26",
        "'", "%27",
        "(", "%28",
        ")", "%29",
        "*", "%2A",
        "+", "%2B",
        ",", "%2C",
        "-", "%2D",
        ".", "%2E",
        "/", "%2F",
        ":", "%3A",
        ";", "%3B",
        "<", "%3C",
        "=", "%3D",
        ">", "%3E",
        "?", "%3F",
        "@", "%40"
    }
    DEFAULT_ASSET_METRICS_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Timestamp', 'type': 'date'},
        {'name': 'Value', 'type': 'string'},
        {'name': 'IsSystem', 'type': 'boolean'},
        {'name': 'UnitsAbbreviation', 'type': 'string'},
        {'name': 'Annotated', 'type': 'boolean'},
        {'name': 'Good', 'type': 'boolean'},
        {'name': 'Questionable', 'type': 'boolean'},
        {'name': 'Substituted', 'type': 'boolean'},
        {'name': 'Errors', 'type': 'object'}
    ]
    DEFAULT_SCHEMA = []
    ELEMENTS_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Id', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Description', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'TemplateName', 'type': 'string'},
        {'name': 'HasChildren', 'type': 'boolean'},
        {'name': 'CategoryNames', 'type': 'object'},
        {'name': 'ExtendedProperties', 'type': 'object'},
        {'name': 'Errors', 'type': 'object'}
    ]
    TEMPLATE_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Id', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Description', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Type', 'type': 'string'},
        {'name': 'TypeQualifier', 'type': 'string'},
        {'name': 'DefaultUnitsName', 'type': 'string'},
        {'name': 'DefaultUnitsNameAbbreviation', 'type': 'string'},
        {'name': 'DefaultValue', 'type': 'string'},
        {'name': 'DataReferencePlugIn', 'type': 'string'},
        {'name': 'ConfigString', 'type': 'string'},
        {'name': 'IsConfigurationItem', 'type': 'boolean'},
        {'name': 'IsExcluded', 'type': 'boolean'},
        {'name': 'IsHidden', 'type': 'boolean'},
        {'name': 'IsManualDataEntry', 'type': 'boolean'},
        {'name': 'HasChildren', 'type': 'boolean'},
        {'name': 'AllowElementToExtend', 'type': 'boolean'},
        {'name': 'BaseTemplate', 'type': 'string'},
        {'name': 'InstanceType', 'type': 'string'},
        {'name': 'NamingPattern', 'type': 'string'},
        {'name': 'CategoryNames', 'type': 'object'},
        {'name': 'TraitName', 'type': 'string'},
        {'name': 'ExtendedProperties', 'type': 'object'},
        {'name': 'ProcessBook.AFDisplayBuilder.UTCChanged', 'type': 'object'},
        {'name': 'ProcessBook.AFModeler.Graphic', 'type': 'object'},
        {'name': 'Severity', 'type': 'string'},
        {'name': 'CanBeAcknowledged', 'type': 'boolean'},
        {'name': 'Errors', 'type': 'object'}
    ]
    SUMMARY_DATA_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Type', 'type': 'string'},
        {'name': 'Timestamp', 'type': 'date'},
        {'name': 'Value', 'type': 'string'},
        {'name': 'UnitsAbbreviation', 'type': 'string'},
        {'name': 'Annotated', 'type': 'boolean'},
        {'name': 'Good', 'type': 'boolean'},
        {'name': 'Questionable', 'type': 'boolean'},
        {'name': 'Substituted', 'type': 'boolean'},
        {'name': 'Errors', 'type': 'object'}
    ]
    VALUE_DATA_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Type', 'type': 'string'},
        {'name': 'IsSystem', 'type': 'boolean'},
        {'name': 'Timestamp', 'type': 'date'},
        {'name': 'Value', 'type': 'string'},
        {'name': 'UnitsAbbreviation', 'type': 'string'},
        {'name': 'Annotated', 'type': 'boolean'},
        {'name': 'Good', 'type': 'boolean'},
        {'name': 'Questionable', 'type': 'boolean'},
        {'name': 'Substituted', 'type': 'boolean'},
        {'name': 'Errors', 'type': 'object'}
    ]
    CATEGORIES_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Description', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Id', 'type': 'string'},
        {'name': 'Errors', 'type': 'object'}
    ]
    ATTRIBUTES_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Id', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Description', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'Type', 'type': 'string'},
        {'name': 'TypeQualifier', 'type': 'string'},
        {'name': 'DefaultUnitsName', 'type': 'string'},
        {'name': 'DefaultUnitsNameAbbreviation', 'type': 'string'},
        {'name': 'DisplayDigits', 'type': 'string'},
        {'name': 'DataReferencePlugIn', 'type': 'string'},
        {'name': 'ConfigString', 'type': 'string'},
        {'name': 'IsConfigurationItem', 'type': 'boolean'},
        {'name': 'IsExcluded', 'type': 'boolean'},
        {'name': 'IsHidden', 'type': 'boolean'},
        {'name': 'IsManualDataEntry', 'type': 'boolean'},
        {'name': 'HasChildren', 'type': 'boolean'},
        {'name': 'CategoryNames', 'type': 'object'},
        {'name': 'Step', 'type': 'boolean'},
        {'name': 'TraitName', 'type': 'string'},
        {'name': 'Span', 'type': 'string'},
        {'name': 'Zero', 'type': 'string'},
        {'name': 'Errors', 'type': 'object'}
    ]
    EVENT_FRAMES_SCHEMA = [
        {'name': 'object_id', 'type': 'string'},
        {'name': 'WebId', 'type': 'string'},
        {'name': 'Id', 'type': 'string'},
        {'name': 'Name', 'type': 'string'},
        {'name': 'Description', 'type': 'string'},
        {'name': 'Path', 'type': 'string'},
        {'name': 'TemplateName', 'type': 'string'},
        {'name': 'HasChildren', 'type': 'boolean'},
        {'name': 'CategoryNames', 'type': 'object'},
        {'name': 'ExtendedProperties', 'type': 'object'},
        {'name': 'StartTime', 'type': 'date'},
        {'name': 'EndTime', 'type': 'date'},
        {'name': 'Severity', 'type': 'string'},
        {'name': 'AcknowledgedBy', 'type': 'string'},
        {'name': 'AcknowledgedDate', 'type': 'date'},
        {'name': 'CanBeAcknowledged', 'type': 'boolean'},
        {'name': 'IsAcknowledged', 'type': 'boolean'},
        {'name': 'IsAnnotated', 'type': 'boolean'},
        {'name': 'IsLocked', 'type': 'boolean'},
        {'name': 'AreValuesCaptured', 'type': 'boolean'},
        {'name': 'RefElementWebIds', 'type': 'object'},
        {'name': 'Security', 'type': 'object'},
        {'name': 'Errors', 'type': 'object'}
    ]
    DEFAULT_SCHEME = "https"
    DEFAULT_WAIT_BEFORE_RETRY = 60
    DKU_ERROR_KEY = "Errors"
    LINKS = "Links"
    POSSIBLE_WEB_ID_STARTS = ["F1", "I1", "P1", "L1", "D1"]
    RECIPE_SCHEMA_PER_DATA_TYPE = {
        "InterpolatedData": DEFAULT_ASSET_METRICS_SCHEMA,
        "PlotData": DEFAULT_ASSET_METRICS_SCHEMA,
        "RecordedData": DEFAULT_ASSET_METRICS_SCHEMA,
        "Elements": ELEMENTS_SCHEMA,
        "Template": TEMPLATE_SCHEMA,
        "SummaryData": SUMMARY_DATA_SCHEMA,
        "Value": VALUE_DATA_SCHEMA,
        "EndValue": VALUE_DATA_SCHEMA,
        "Categories": CATEGORIES_SCHEMA,
        "Attributes": ATTRIBUTES_SCHEMA,
        "EventFrames": EVENT_FRAMES_SCHEMA
    }
    RECORD_PATH = "recorded"
    SCHEMA_EVENT_FRAMES = [
        "Path",
        "Name",
        "Timestamp",
        "Value",
        "UnitsAbbreviation",
        "Errors",
        "Annotated",
        "Good",
        "Questionable",
        "Substituted",
        "WebId",
        "event_frame_webid"
    ]
    SCHEMA_STREAM_RESPONSE = [
        {"name": "Timestamp", "type": "date"},
        {"name": "Value_Name", "type": "string"},
        {"name": "Value_Value", "type": "string"},
        {"name": "UnitsAbbreviation", "type": "string"},
        {"name": "Value_IsSystem", "type": "boolean"},
        {"name": "Good", "type": "boolean"},
        {"name": "Questionable", "type": "boolean"},
        {"name": "Substituted", "type": "boolean"},
        {"name": "Annotated", "type": "boolean"}
    ]
    SCHEMA_TAG_RESPONSE = [
        {"name": "Timestamp", "type": "date"},
        {"name": "Value", "type": "string"},
        {"name": "UnitsAbbreviation", "type": "string"},
        {"name": "Good", "type": "boolean"},
        {"name": "Questionable", "type": "boolean"},
        {"name": "Substituted", "type": "boolean"},
        {"name": "Annotated", "type": "boolean"}
    ]
    SCHEMA_ATTRIBUTES_RESPONSE = [
        {"name": "Name", "type": "string"},
        {"name": "Description", "type": "string"},
        {"name": "Path", "type": "string"},
        {"name": "Type", "type": "string"},
        {"name": "TypeQualifier", "type": "string"},
        {"name": "DefaultUnitsName", "type": "string"},
        {"name": "DefaultUnitsNameAbbreviation", "type": "string"},
        {"name": "DisplayDigits", "type": "int"},
        {"name": "DataReferencePlugIn", "type": "string"},
        {"name": "ConfigString", "type": "string"},
        {"name": "IsConfigurationItem", "type": "boolean"},
        {"name": "IsExcluded", "type": "boolean"},
        {"name": "IsHidden", "type": "boolean"},
        {"name": "IsManualDataEntry", "type": "boolean"},
        {"name": "HasChildren", "type": "boolean"},
        {"name": "CategoryNames", "type": "string"},
        {"name": "Step", "type": "boolean"},
        {"name": "TraitName", "type": "string"},
        {"name": "Span", "type": "float"},
        {"name": "Zero", "type": "float"},
        {"name": "Id", "type": "string"},
        {"name": "WebId", "type": "string"}
    ]
    SCHEMA_ATTRIBUTES_METRICS_RESPONSE = [
        {"name": "Name", "type": "string"},
        {"name": "Description", "type": "string"},
        {"name": "Path", "type": "string"},
        {"name": "Timestamp", "type": "date"},
        {"name": "Value", "type": "string"},
        {"name": "Value_ID", "type": "string"},
        {"name": "UnitsAbbreviation", "type": "string"},
        {"name": "DefaultUnitsName", "type": "string"},
        {"name": "DefaultUnitsNameAbbreviation", "type": "string"},
        {"name": "Good", "type": "boolean"},
        {"name": "Questionable", "type": "boolean"},
        {"name": "Substituted", "type": "boolean"},
        {"name": "Annotated", "type": "boolean"},
        {"name": "Type", "type": "string"},
        {"name": "TypeQualifier", "type": "string"},
        {"name": "DisplayDigits", "type": "int"},
        {"name": "DataReferencePlugIn", "type": "string"},
        {"name": "ConfigString", "type": "string"},
        {"name": "IsConfigurationItem", "type": "boolean"},
        {"name": "IsExcluded", "type": "boolean"},
        {"name": "IsHidden", "type": "boolean"},
        {"name": "IsManualDataEntry", "type": "boolean"},
        {"name": "HasChildren", "type": "boolean"},
        {"name": "CategoryNames", "type": "string"}, 
        {"name": "Step", "type": "boolean"},
        {"name": "TraitName", "type": "string"},
        {"name": "Span", "type": "float"},
        {"name": "Zero", "type": "float"},
        {"name": "Id", "type": "string"},
        {"name": "WebId", "type": "string"}
    ]
    SCHEMA_ATTRIBUTES_METRICS_FILTER = [
        "ConfigString", "DataReferencePlugIn", "DisplayDigits",
        "HasChildren", "Id", "IsConfigurationItem", "IsExcluded",
        "IsHidden", "IsManualDataEntry", "Links", "Span", "Step", "TraitName", "Zero",
        "Good", "Questionable", "Substituted", "Annotated"
    ]
    SCHEMA_EVENT_FRAMES_RESPONSE = [
        {"name": "Name", "type": "string"},
        {"name": "Description", "type": "string"},
        {"name": "Path", "type": "string"},
        {"name": "TemplateName", "type": "string"},
        {"name": "HasChildren", "type": "string"},
        {"name": "CategoryNames", "type": "string"},
        {"name": "ExtendedProperties", "type": "string"},
        {"name": "StartTime", "type": "string"},
        {"name": "EndTime", "type": "string"},
        {"name": "Severity", "type": "string"},
        {"name": "AcknowledgedBy", "type": "string"},
        {"name": "AcknowledgedDate", "type": "string"},
        {"name": "CanBeAcknowledged", "type": "string"},
        {"name": "IsAcknowledged", "type": "string"},
        {"name": "IsAnnotated", "type": "string"},
        {"name": "IsLocked", "type": "string"},
        {"name": "AreValuesCaptured", "type": "string"},
        {"name": "RefElementWebIds", "type": "string"},
        {"name": "WebId", "type": "string"},
        {"name": "Id", "type": "string"},
        {"name": "Errors", "type": "string"}
    ]
    SCHEMA_EVENT_FRAMES_METRICS_RESPONSE = [
        {"name": "Name", "type": "string"},
        {"name": "Description", "type": "string"},
        {"name": "Timestamp", "type": "string"},
        {"name": "Value", "type": "string"},
        {"name": "UnitsAbbreviation", "type": "string"},
        {"name": "Path", "type": "string"},
        {"name": "TemplateName", "type": "string"},
        {"name": "HasChildren", "type": "string"},
        {"name": "CategoryNames", "type": "string"},
        {"name": "ExtendedProperties", "type": "string"},
        {"name": "StartTime", "type": "string"},
        {"name": "EndTime", "type": "string"},
        {"name": "Severity", "type": "string"},
        {"name": "AcknowledgedBy", "type": "string"},
        {"name": "AcknowledgedDate", "type": "string"},
        {"name": "CanBeAcknowledged", "type": "string"},
        {"name": "IsAcknowledged", "type": "string"},
        {"name": "IsAnnotated", "type": "string"},
        {"name": "IsLocked", "type": "string"},
        {"name": "AreValuesCaptured", "type": "string"},
        {"name": "RefElementWebIds", "type": "string"},
        {"name": "Good", "type": "string"},
        {"name": "Questionable", "type": "string"},
        {"name": "Substituted", "type": "string"},
        {"name": "Annotated", "type": "string"},
        {"name": "WebId", "type": "string"},
        {"name": "Id", "type": "string"},
        {"name": "Errors", "type": "string"}
    ]
    SEARCH_PATH = "search"
    STREAM_PATH = "streams"
    STREAMSETS_PATH = "streamsets"
    PIWEBAPI_AF_ENDPOINTS = {
        "InterpolatedData": "{base_url}/streams/{webid}/interpolated",
        "RecordedData": "{base_url}/streams/{webid}/recorded",
        "PlotData": "{base_url}/streams/{webid}/plot",
        "SummaryData": "{base_url}/streams/{webid}/summary",
        "Value": "{base_url}/streams/{webid}/value",
        "EndValue": "{base_url}/streams/{webid}/end"
    }
    PIWEBAPI_ENDPOINTS = {
        "Attributes": "{base_url}/eventframes/{webid}/attributes",
        "EventFrames": "{base_url}/eventframes/{webid}/eventframes",
        "Database": "{base_url}/assetdatabases/{webid}",
        "ReferencedElements": "{base_url}/eventframes/{webid}/referencedelements",
        "PrimaryReferencedElement": "{base_url}/elements/{webid}",
        "Template": "{base_url}/elementtemplates/{webid}",
        "Categories": "{base_url}/eventframes/{webid}/categories",
        "InterpolatedData": "{base_url}/streamsets/{webid}/interpolated",
        "RecordedData": "{base_url}/streamsets/{webid}/recorded",
        "PlotData": "{base_url}/streamsets/{webid}/plot",
        "SummaryData": "{base_url}/streamsets/{webid}/summary",
        "Value": "{base_url}/streamsets/{webid}/value",
        "EndValue": "{base_url}/streamsets/{webid}/end",
        "Security": "{base_url}/eventframes/{webid}/security",
        "SecurityEntries": "{base_url}/eventframes/{webid}/securityentries"
    }
    PLUGIN_VERSION = "1.0.1-beta.7"
    WEB_API_PATH = "piwebapi"
    WRITE_HEADERS = {'X-Requested-With': 'XmlHttpRequest'}
