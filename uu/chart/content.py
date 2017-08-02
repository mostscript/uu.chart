import csv
from datetime import date
from hashlib import md5
from StringIO import StringIO

from Acquisition import aq_base, aq_inner, aq_parent
from ComputedAttribute import ComputedAttribute
from persistent.mapping import PersistentMapping
from plone.dexterity.content import Item, Container
from zope.interface import implements
from plone.uuid.interfaces import IAttributeUUID

from uu.formlibrary.utils import normalize_usa_date

from uu.chart.interfaces import IDataReport
from uu.chart.interfaces import ITimeSeriesChart, ITimeDataSequence
from uu.chart.interfaces import ITimeSeriesCollection
from uu.chart.interfaces import INamedSeriesChart, INamedDataSequence
from uu.chart.interfaces import TIME_DATA_TYPE, NAMED_DATA_TYPE
from uu.chart.interfaces import MEASURE_DATA_TYPE
from uu.chart.data import TimeSeriesDataPoint, NamedDataPoint


_type_filter = lambda o, t: hasattr(o, 'portal_type') and o.portal_type == t


# need aq-friendly property decorator, credit to:
# http://stackoverflow.com/a/12545292/835961
def computed_attribute(level=0):
    def computed_attribute_wrapper(func):
        return ComputedAttribute(func, level)
    return computed_attribute_wrapper


def filter_data(context, points):
    parent = aq_parent(aq_inner(context))
    if ITimeSeriesCollection.providedBy(parent):
        if getattr(parent, 'force_crop', False):
            if parent.start:
                _after_start = lambda p: p.date >= parent.start
                points = filter(_after_start, points)
            if parent.end:
                _before_end = lambda p: p.date <= parent.end
                points = filter(_before_end, points)
    return points


class BaseDataSequence(Item):

    POINTCLS = None
    KEYTYPE = unicode

    def __init__(self, id=None, *args, **kwargs):
        super(BaseDataSequence, self).__init__(id, *args, **kwargs)

    def _data(self, filtered=True, excluded=False):
        """Unfiltered data"""
        if not self.input:
            return []
        result = []
        reader = csv.reader(StringIO(getattr(self, 'input', u'')))
        rows = list(reader)  # iterate over CSV
        for row in rows:
            note = uri = None  # default empty optional values
            if len(row) < 2:
                continue  # silently ignore
            try:
                key = row[0]
                if self.KEYTYPE == date:
                    key = normalize_usa_date(key)
                value = float(row[1])
            except ValueError:
                continue  # failed to type-cast value, ignore row
            if len(row) >= 3:
                note = row[2]
            if len(row) >= 4:
                uri = row[3]
            result.append(self.POINTCLS(key, value, note, uri))
        if filtered and not excluded:
            result = filter_data(self, result)
        if excluded:
            included = filter_data(self, result)
            result = [p for p in result if p not in included]
        return result

    @computed_attribute(level=1)
    def data(self):
        """Parse self.input, return list of point objects"""
        if not hasattr(self, '_v_data'):
            self._v_data = {}
        cachekey = md5(self.input).hexdigest()
        if cachekey not in self._v_data:
            self._v_data[cachekey] = self._data(filtered=True)
        return self._v_data[cachekey]

    def excluded(self):
        return self._data(excluded=True)

    def __iter__(self):
        """
        Iterable of date, number data point objects providing
        (at least) IDataPoint.
        """
        return iter(self.data)

    def __len__(self):
        """Return number of data points"""
        return len(self.data)

    def display_value(self, point):
        precision = getattr(aq_base(self), 'display_precision', 1)
        v = getattr(point, 'value', None)
        v = round(v, precision) if v is not None else v
        fmt = '%%.%if' % precision
        return fmt % v if v is not None else ''


class TimeDataSequence(BaseDataSequence):
    implements(ITimeDataSequence)

    POINTCLS = TimeSeriesDataPoint
    KEYTYPE = date

    def __init__(self, id=None, *args, **kwargs):
        super(TimeDataSequence, self).__init__(id, *args, **kwargs)
        self.label_default = 'locale'
        self.label_overrides = PersistentMapping()


class TimeSeriesChart(Container):
    implements(ITimeSeriesChart, IAttributeUUID)

    def series(self):
        """
        Return iterable of series/sequence streams providing
        ITimeDataSequence.  In this case, this returns a list of
        contained items.
        """
        contained = self.objectValues()
        _f = lambda o: _type_filter(o, TIME_DATA_TYPE)
        _f_measure = lambda o: _type_filter(o, MEASURE_DATA_TYPE)
        v1 = list(filter(_f, contained))
        return v1 + list(filter(_f_measure, contained))


class NamedDataSequence(BaseDataSequence):
    implements(INamedDataSequence)

    POINTCLS = NamedDataPoint
    KEYTYPE = unicode


class NamedSeriesChart(Container):
    implements(INamedSeriesChart, IAttributeUUID)

    def __init__(self, id=None, *args, **kwargs):
        super(NamedSeriesChart, self).__init__(id, *args, **kwargs)
        self.chart_type = u'bar'

    def series(self):
        """
        Return iterable of series/sequence streams providing
        INamedDataSequence.  In this case, this returns a list of
        contained items.
        """
        contained = self.objectValues()
        _f = lambda o: _type_filter(o, NAMED_DATA_TYPE)
        _f_measure = lambda o: _type_filter(o, MEASURE_DATA_TYPE)
        v1 = list(filter(_f, contained))
        return v1 + list(filter(_f_measure, contained))


class DataReport(Container):
    implements(IDataReport, IAttributeUUID)


