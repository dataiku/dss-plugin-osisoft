import pandas


class BufferedOutputWriter:
    def __init__(self, dataset, writer, columns_formatter, batch_size):
        if batch_size < 1:
            raise ValueError("Output batch size must be positive")
        self.dataset = dataset
        self.writer = writer
        self.columns_formatter = columns_formatter
        self.batch_size = batch_size
        self.rows = []
        self.schema_written = False

    def write_rows(self, rows):
        for row in rows:
            self.rows.append(self.columns_formatter.parse_row(row))
            if len(self.rows) >= self.batch_size:
                self.flush()

    def flush(self):
        if not self.schema_written:
            self.dataset.write_schema(self.columns_formatter.get_schema())
            self.schema_written = True
        if self.rows:
            dataframe = pandas.DataFrame(self.rows)
            self.writer.write_dataframe(dataframe)
            self.rows.clear()
