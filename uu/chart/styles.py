from plone.dexterity.content import Container, Item
from plone.uuid.interfaces import IUUID
from zope.interface import implements

from interfaces import IChartStyleBook, ILineStyle, IBaseChart
from browser.styles import clone_chart_styles


class ChartStyleBook(Container):
    """ Style book content for a report """

    portal_type = 'uu.chart.stylebook'

    implements(IChartStyleBook)


class LineStyle(Item):
    """ Style book entry for a line on a plot """

    portal_type = 'uu.chart.linestyle'

    implements(ILineStyle)


def handle_stylebook_modified(context, event):
    """
    When stylebook is modified, find any charts in same report
    that are bound to it, and update them.
    """
    bookuid = IUUID(context)
    report = context.__parent__
    charts = [o for o in report.objectValues() if IBaseChart.providedBy(o)]
    if not charts:
        return
    bound = [o for o in charts if getattr(o, 'stylebook', None) == bookuid]
    if not bound:
        return
    for target in bound:
        clone_chart_styles(context, target)
        target.reindexObject()


def handle_line_style_modified(context, event):
    stylebook = context.__parent__
    handle_stylebook_modified(stylebook, None)

