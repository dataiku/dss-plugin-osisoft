class OSIsoftConstants(object):
    API_ITEM_KEY = "Items"
    API_VALUE_KEY = "Value"
    API_TIMESTAMP_KEY = "Timestamp"
    ATTRIBUTES_PATH = "attributes"
    DEFAULT_WAIT_BEFORE_RETRY = 60
    DKU_ERROR_KEY = "error"
    LINKS = "Links"
    POSSIBLE_WEB_ID_STARTS = ["F1", "I1", "P1", "L1", "D1"]
    RECORD_PATH = "recorded"
    SEARCH_PATH = "search"
    STREAM_PATH = "streams"
    STREAMSETS_PATH = "streamsets"
    WEB_API_PATH = "piwebapi"
    # CHAR_TO_ESCAPE = '+ - && || ! ( ) { } [ ] ^ " ~ * ? : \\'
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
    WRITE_HEADERS = {'X-Requested-With': 'XmlHttpRequest'}
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
    PIWEBAPI_ENDPOINTS = {
        "Attributes": "{base_url}/piwebapi/eventframes/{webid}/attributes",
        "EventFrames": "{base_url}/piwebapi/eventframes/{webid}/eventframes",
        "Database": "{base_url}/piwebapi/assetdatabases/{webid}",
        "ReferencedElements": "{base_url}/piwebapi/eventframes/{webid}/referencedelements",
        "PrimaryReferencedElement": "{base_url}/piwebapi/elements/{webid}",
        "Template": "{base_url}/piwebapi/elementtemplates/{webid}",
        "Categories": "{base_url}/piwebapi/eventframes/{webid}/categories",
        "InterpolatedData": "{base_url}/piwebapi/streamsets/{webid}/interpolated",
        "RecordedData": "{base_url}/piwebapi/streamsets/{webid}/recorded",
        "PlotData": "{base_url}/piwebapi/streamsets/{webid}/plot",
        "SummaryData": "{base_url}/piwebapi/streamsets/{webid}/summary",
        "Value": "{base_url}/piwebapi/streamsets/{webid}/value",
        "EndValue": "{base_url}/piwebapi/streamsets/{webid}/end",
        "Security": "{base_url}/piwebapi/eventframes/{webid}/security",
        "SecurityEntries": "{base_url}/piwebapi/eventframes/{webid}/securityentries"
      }
    PIWEBAPI_AF_ENDPOINTS = {
        "InterpolatedData": "{base_url}/piwebapi/streams/{webid}/interpolated",
        "RecordedData": "{base_url}/piwebapi/streams/{webid}/recorded",
        "PlotData": "{base_url}/piwebapi/streams/{webid}/plot",
        "SummaryData": "{base_url}/piwebapi/streams/{webid}/summary",
        "Value": "{base_url}/piwebapi/streams/{webid}/value",
        "EndValue": "{base_url}/piwebapi/streams/{webid}/end"
    }
