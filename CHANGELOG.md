# Changelog

## [Version 1.2.4](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.4) - Feature  and bug release - 2024-12-12

- Add boundary type selector to recorded data type
- Add boundary type selector to attribute search connector
- *Assets values downloader* Add option to copy each input row into output dataset
- Fix issue with recorded data type
- *Assets values downloader* Time range pagination when using webids
- *Assets values downloader* Time can be selected from a column of the input dataset

## [Version 1.2.3](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.3) - Feature release - 2024-09-26

- Add summaryDuration input (duration of each summary interval)
- Fix issue when using `Starting After` search option in browse PI event frames
- Fix issue with `Value` and `End value` data types in Search attributes dataset
- Add pagination on element retrieval

## [Version 1.2.2](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.2) - Feature release - 2023-12-11

- Time range pagination - no more `maxCount` and / or `maxReturnedItemsPerCall` limitation
- Add type selector for summary reports
- Fix time drift when using PI-system time strings as start / end / synch time
- Add manual input to template selector

## [Version 1.2.1](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.1) - Feature and bug release - 2023-11-08

- Updated code-env descriptor for DSS 12

## [Version 1.2.0](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.0) - Feature and bug release - 2023-03-14

- Add Tag Search custom dataset
- Fix Toolbox issue with tags and paths containing spaces
- Fix Toolbox result consistency when using web IDs.
- Add option to change max count value
- Add performance timers
- Add option to parse object columns as string
- Transpose & Synchronization recipe output made DB friendly
- Add Event Frames Search Full Hierarchy
- Add time span search modes to Event Frame search connector
- Fix write issue when Value column contains empty cells

## [Version 1.0.2](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.0.2) - Bugfix release - 2023-04-25

- Updated code-env descriptor for DSS 12

## [Version 1.0.1](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.0.1) - Feature release - 2023-01-05

- Add batch mode for metric retrieval with the event frames
- Disable by default server URL override
- Fix pagination for Event Frames Search connector
- Fix Transpose & Synchronize recipe with rows containing no timestamp
- Fix nested value object when batch mode is not activated on Event Frames Search connector
- Fix presence of NaNs in last line produced by Transpose & Synchronize recipe
- Fix Event Frame WebId consistency in batch mode

## [Version 1.0.0](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.0.0) - Initial release - 2022-08-04

- PI System PIWebAPI plugin initial release
- PiWebAPI ToolBox custom dataset, for read/write access to any asset path / webid
- Attribute search custom dataset (DSS v10.0.7 minimum)
- Event frames search custom dataset (DSS v10.0.7 minimum)
- Attribute metrics retrieval recipe
- Event frames metrics retrieval recipe
- Attribute metrics synchronization and transposition recipe
