# Changelog

## [Version 1.2.0](https://github.com/dataiku/dss-plugin-pi-server/releases/tag/v1.2.0) - Feature and bug release - 2023-03-14

- Add Tag Search custom dataset
- Fix Toolbox issue with tags and paths containing spaces
- Fix Toolbox result consistency when using web IDs.
- Add option to change max count value
- Add performance timers
- Add option to parse object columns as string

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
