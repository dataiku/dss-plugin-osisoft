# Changelog

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
