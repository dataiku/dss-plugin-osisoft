# PI System Plugin

This Dataiku DSS plugin provides a read connector to retrieve data from your PI System servers.

Documentation: https://www.dataiku.com/product/plugins/pi-system/

### Transpose & Synchronize

The recipe reads input in chunks and caches values on disk. It infers each attribute's output type from all of its valid-timestamp input rows before writing output, without loading the full dataset into memory.

Numeric text is inferred as `bigint` or `double`; a later fractional value promotes the attribute to `double`, and nonnumeric text promotes it to `string`. Boolean text is inferred as `boolean`, while mixed boolean and numeric values become strings. Integers outside the signed 64-bit range remain strings. Pandas' default missing-value markers are ignored during inference, and all-null attributes default to strings.

Interpolated numeric attributes always use `double`. Interpolation of text or boolean attributes fails before output is written; missing interpolation endpoints produce null values. The reference attribute retains its own inferred type.


### Licence

Copyright 2022 Dataiku SAS

This plugin is distributed under the Apache License version 2.0
