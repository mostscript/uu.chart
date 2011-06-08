from datetime import datetime, date

from plone.dexterity.content import Item, Container

from zope.interface import implements

from uu.runchart.interfaces import IMultiSeriesReport, ITimeMeasureChart, ITimeDataChart


class MultiSeriesReport(Container):
    implements(IMultiSeriesReport)


class TimeMeasureChart(Item):
    implements(ITimeMeasureChart)


class TimeDataChart(Item):
    implements(ITimeDataChart)


