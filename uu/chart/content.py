from datetime import datetime, date

from plone.dexterity.content import Item, Container

from zope.interface import implements

from uu.chart.interfaces import IDataReport
from uu.chart.interfaces import ITimeSeriesChart, ITimeDataSequence
from uu.chart.interfaces import INamedSeriesChart, INamedDataSequence
from uu.chart.interfaces import TIME_DATA_TYPE, NAMED_DATA_TYPE
from uu.chart.data import TimeSeriesDataPoint, NamedDataPoint


_type_filter = lambda o,t: hasattr(o, 'portal_type') and o.portal_type == t


class TimeDataSequence(Item):
    implements(ITimeDataSequence)
    
    def __iter__(self):
        """ 
        Iterable of date, number data point objects providing
        (at least) IDataPoint.
        """
        raw = self.data # from data grid
        if not raw:
            return iter(())
        return iter([TimeSeriesDataPoint(**d) for d in raw])
    
    def __len__(self):
        """Return number of data points"""
        raw = self.data # from data grid
        if not raw:
            return 0
        return len(raw) #number of items in data grid


class TimeSeriesChart(Container):
    implements(ITimeSeriesChart)
    
    def series(self):
        """
        Return iterable of series/sequence streams providing
        ITimeDataSequence.  In this case, this returns a list of
        contained items.
        """
        _f = lambda o: _type_filter(o, TIME_DATA_TYPE) 
        return filter(_f, self.objectValues())


class NamedDataSequence(Item):
    implements(INamedDataSequence)
    
    def __iter__(self):
        """ 
        Iterable of name, number data point objects providing
        (at least) IDataPoint.
        """
        raw = self.data # from data grid
        if not raw:
            return iter(())
        return iter([NamedDataPoint(**d) for d in raw])
    
    def __len__(self):
        """Return number of data points"""
        raw = self.data # from data grid
        if not raw:
            return 0
        return len(raw) #number of items in data grid


class NamedSeriesChart(Container):
    implements(INamedSeriesChart)
    
    def series(self):
        """
        Return iterable of series/sequence streams providing
        INamedDataSequence.  In this case, this returns a list of
        contained items.
        """
        _f = lambda o: _type_filter(o, NAMED_DATA_TYPE) 
        return filter(_f, self.objectValues())


class DataReport(Container):
    implements(IDataReport)


