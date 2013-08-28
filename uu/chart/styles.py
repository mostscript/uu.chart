from plone.dexterity.content import Container, Item
from zope.interface import implements

from interfaces import IChartStyleBook, ILineStyle


class ChartStyleBook(Container):
    """ Style book content for a report """

    portal_type = 'uu.chart.stylebook'

    implements(IChartStyleBook)


class LineStyle(Item):
    """ Style book entry for a line on a plot """

    portal_type = 'uu.chart.linestyle'

    implements(ILineStyle)

