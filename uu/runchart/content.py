from datetime import datetime, date

from plone.dexterity.content import Item, Container

from zope.interface import implements

from uu.runchart.interfaces import IMultiSeriesReport, ITimeMeasureChart
from uu.runchart.interfaces import IDataPoint, ITimeDataChart


class DataPoint(object):
    implements(IDataPoint)
    
    def __init__(self, date, value):
        self.date = date
        self.value = value


class MultiSeriesReport(Container):
    implements(IMultiSeriesReport)


class TimeMeasureChart(Item):
    implements(ITimeMeasureChart)


class TimeDataChart(Item):
    implements(ITimeDataChart)

    def datapoints(self):
        """
        Convert List of DictRows into tuple of DataPoint objects, 
        return.
        """
        raw = self.data
        if not raw:
            return ()
        return tuple([DataPoint(d['date'], d['value']) for d in raw])        

