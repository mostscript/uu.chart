import datetime

from zope.interface import implements

from uu.chart.interfaces import INamedDataPoint, ITimeSeriesDataPoint


class BaseDataPoint(object):
    def __init__(self, value, note=None, uri=None):
        self.value = value
        self.note = note
        self.uri = uri

    def identity(self):
        raise NotImplementedError('base class does not provide')


class NamedDataPoint(BaseDataPoint):
    implements(INamedDataPoint)

    def __init__(self, name, value, note=None, uri=None):
        self.name = name
        super(NamedDataPoint, self).__init__(value, note, uri)

    def identity(self):
        return self.name


class TimeSeriesDataPoint(BaseDataPoint):
    implements(ITimeSeriesDataPoint)

    def __init__(self, date, value, note=None, uri=None):
        if isinstance(date, datetime.datetime):
            date = date.date()
        if not isinstance(date, datetime.date):
            raise ValueError('date must be datetime.date object')
        self.date = date
        super(TimeSeriesDataPoint, self).__init__(value, note, uri)

    def identity(self):
        return self.date

