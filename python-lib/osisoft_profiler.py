import datetime


class Profiler(object):
    def __init__(self):
        self.last_start_time = None
        self.last_performance = None
        self.timings = []
        self.number_of_records = 0

    def start(self):
        self.last_start_time = datetime.datetime.now()

    def end(self):
        end_time = datetime.datetime.now()
        self.last_performance = timing(self.last_start_time, end_time)
        self.timings.append(self.last_performance)
        self.number_of_records += 1

    def time(self):
        return self.last_performance

    def total(self):
        total_time = 0
        for timing in self.timings:
            total_time += timing
        return total_time

    def average(self):
        if not self.number_of_records:
            return None
        total_time = self.total()
        average = total_time / self.number_of_records
        return average


def timing(start, end):
    duration = end - start
    return duration.microseconds/1000000 + duration.seconds
