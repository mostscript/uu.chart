from plone.dexterity.content import Container, Item
from plone.dexterity.utils import createContentInContainer
from plone.uuid.interfaces import IUUID
from zope.interface import implements
from zope.container.interfaces import IContainerModifiedEvent

from uu.formlibrary.measure.interfaces import IMeasureGroup

from interfaces import IChartStyleBook, ILineStyle, IBaseChart
from interfaces import LINESTYLE_TYPE, STYLEBOOK_TYPE
from browser.styles import clone_chart_styles, MeasureGroupStyles


class ChartStyleBook(Container):
    """ Style book content for a report """

    portal_type = 'uu.chart.stylebook'

    implements(IChartStyleBook)


class LineStyle(Item):
    """ Style book entry for a line on a plot """

    portal_type = 'uu.chart.linestyle'

    implements(ILineStyle)


def update_quick_line_styles(context, event=None):
    # on zope.container.contained.ContainerModifiedEvent, we ignore:
    if IContainerModifiedEvent.providedBy(event):
        return
    quick = context.quick_styles or []
    existing = [l for l in context.objectValues() if ILineStyle.providedBy(l)]
    val = lambda o, name, default: spec.get(name, getattr(o, name, default))
    copy_to = lambda o, name, default: setattr(o, name, val(o, name, default))
    i = -1
    for spec in quick:
        i += 1
        if i + 1 <= len(existing):
            line_style = existing[i]
            copy_to(line_style, 'color', 'Auto')
            copy_to(line_style, 'marker_style', 'square')
        else:
            line_style = createContentInContainer(
                context,
                LINESTYLE_TYPE,
                title=u'Line style %s' % (i + 1),
                **spec
                )


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


def stylebook_added(context, event):
    parent = context.__parent__
    if IMeasureGroup.providedBy(parent):
        adapter = MeasureGroupStyles(parent)
        stylebooks = adapter.stylebooks()
        style_ids = [o.getId() for o in stylebooks]
        default = adapter.default_stylebook
        first_stylebook = len(stylebooks) <= 1
        stale_or_no_default = default not in style_ids
        if first_stylebook or stale_or_no_default:
            adapter.default_stylebook = context.getId()


def measure_group_added(context, event):
    """
    When a measure group is added, auto-add a default stylebook called
    "Default theme".
    """
    createContentInContainer(
        context,
        STYLEBOOK_TYPE,
        title=u'Default theme',
        )

