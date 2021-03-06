import datetime
import math

from zope.interface import implements

from uu.chart.interfaces import INamedDataPoint, ITimeSeriesDataPoint


def non_numeric(value):
    return value is None or math.isnan(value)


class BaseDataPoint(object):
    def __init__(
            self,
            value,
            note=None,
            uri=None,
            sample_size=None,
            distribution=None):
        self.value = value
        self.note = note
        self.uri = uri
        if non_numeric(sample_size):
            sample_size = None
        if sample_size is not None:
            sample_size = int(sample_size)
        self.sample_size = sample_size
        self.distribution = distribution

    def identity(self):
        raise NotImplementedError('base class does not provide')


class NamedDataPoint(BaseDataPoint):
    implements(INamedDataPoint)

    def __init__(
            self,
            name,
            value,
            note=None,
            uri=None,
            sample_size=None,
            distribution=None):
        self.name = name
        super(NamedDataPoint, self).__init__(
            value,
            note,
            uri,
            sample_size,
            distribution
            )

    def identity(self):
        return self.name


class TimeSeriesDataPoint(BaseDataPoint):
    implements(ITimeSeriesDataPoint)

    def __init__(
            self,
            date,
            value,
            note=None,
            uri=None,
            sample_size=None,
            distribution=None):
        if isinstance(date, datetime.datetime):
            date = date.date()
        if not isinstance(date, datetime.date):
            raise ValueError('date must be datetime.date object')
        self.date = date
        super(TimeSeriesDataPoint, self).__init__(
            value,
            note,
            uri,
            sample_size,
            distribution
            )

    def identity(self):
        return self.date
