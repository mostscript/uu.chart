import csv
from datetime import datetime, date
from hashlib import md5
from StringIO import StringIO

from plone.dexterity.content import Item, Container
from five import grok
from zope.interface import implements
from plone.uuid.interfaces import IAttributeUUID

from uu.smartdate.converter import normalize_usa_date

from uu.chart.interfaces import IDataReport
from uu.chart.interfaces import ITimeSeriesChart, ITimeDataSequence
from uu.chart.interfaces import INamedSeriesChart, INamedDataSequence
from uu.chart.interfaces import TIME_DATA_TYPE, NAMED_DATA_TYPE
from uu.chart.data import TimeSeriesDataPoint, NamedDataPoint


_type_filter = lambda o,t: hasattr(o, 'portal_type') and o.portal_type == t


class BaseDataSequence(Item):
   
    POINTCLS = None
    KEYTYPE = unicode
     
    def __init__(self, id=None, *args, **kwargs):
        super(BaseDataSequence, self).__init__(id, *args, **kwargs)
        self._v_data = {}

    @property
    def data(self):
        """Parse self.input, return list of point objects"""
        if not hasattr(self, '_v_data'):
            self._v_data = {}
        cachekey = md5(self.input).hexdigest()
        if cachekey not in self._v_data:
            result = []
            reader = csv.reader(StringIO(getattr(self, 'input', u'')))
            rows = list(reader) #iterate over CSV
            for row in rows:
                note = uri = None #default empty optional values
                if len(row) < 2:
                    continue #silently ignore
                try:
                    key = row[0]
                    if self.KEYTYPE == date:
                        key = normalize_usa_date(key)
                    value = float(row[1])
                except ValueError:
                    continue #failed to type-cast value, ignore row
                if len(row) >= 3:
                    note = row[2]
                if len(row) >= 4:
                    uri = row[3]
                result.append(self.POINTCLS(key, value, note, uri))
            self._v_data[cachekey] = result
        return self._v_data[cachekey]
     
    def __iter__(self):
        """ 
        Iterable of date, number data point objects providing
        (at least) IDataPoint.
        """
        return iter(self.data)
    
    def __len__(self):
        """Return number of data points"""
        return len(self.data)


class TimeDataSequence(BaseDataSequence):
    implements(ITimeDataSequence)
    
    POINTCLS = TimeSeriesDataPoint
    KEYTYPE = date


class TimeSeriesChart(Container):
    implements(ITimeSeriesChart, IAttributeUUID)
    
    def series(self):
        """
        Return iterable of series/sequence streams providing
        ITimeDataSequence.  In this case, this returns a list of
        contained items.
        """
        _f = lambda o: _type_filter(o, TIME_DATA_TYPE) 
        return filter(_f, self.objectValues())


class NamedDataSequence(BaseDataSequence):
    implements(INamedDataSequence)

    POINTCLS = NamedDataPoint
    KEYTYPE = unicode


class NamedSeriesChart(Container):
    implements(INamedSeriesChart, IAttributeUUID)
    
    def series(self):
        """
        Return iterable of series/sequence streams providing
        INamedDataSequence.  In this case, this returns a list of
        contained items.
        """
        _f = lambda o: _type_filter(o, NAMED_DATA_TYPE) 
        return filter(_f, self.objectValues())


class DataReport(Container):
    implements(IDataReport, IAttributeUUID)


