
from collective.z3cform.datagridfield import DataGridFieldFactory, DictRow
from plone.directives import form, dexterity
from plone.app.textfield import RichText
from zope.interface import Interface, Invalid, invariant
from zope import schema
from zope.container.interfaces import IOrderedContainer
from zope.location.interfaces import ILocation
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from collective.z3cform.colorpicker.colorpicker import ColorpickerFieldWidget


from uu.runchart import _ #MessageFactory for package


class IDataPoint(Interface):
    
    date = schema.Date(
        title=_(u'Date'),
        required=True,
        )
    
    value = schema.Float(
        title=_(u'Number value'),
        description=_(u'Decimal number value.'),
        default=0.0,
        )


class IDataPoints(Interface):
    """Iterable of IDataPoint objects"""
    
    def __iter__():
        """
        Return iterable of date, number data point objects providing
        IDataPoints
        """
    
    def __len__():
        """Return number of data points"""


class ISeriesDisplayLine(form.Schema):
    """
    Mixin interface for display-line configuration metadata for series line.
    """
    
    form.widget(line_color=ColorpickerFieldWidget)
    line_color = schema.TextLine(
        title=_(u'Line color'),
        default=u'#666666',
        )
    
    line_width = schema.Int(
        title=_(u'Line width'),
        description=_(u'Width/thickness of line in pixel units.'),
        default=2,
        )
    
    marker_style = schema.Choice(
        title=_(u'Marker style'),
        description=_(u''),
        vocabulary=SimpleVocabulary([
            SimpleTerm(value=u'diamond', title=u'Diamond'),
            SimpleTerm(value=u'circle', title=u'Circle'),
            SimpleTerm(value=u'square', title=u'Square'),
            SimpleTerm(value=u'x', title=u'X'),
            SimpleTerm(value=u'plus', title=u'Plus sign'),
            SimpleTerm(value=u'dash', title=u'Dash'),
            SimpleTerm(value=u'filledDiamond', title=u'Filled diamond'),
            SimpleTerm(value=u'filledCircle', title=u'Filled circle'),
            SimpleTerm(value=u'filledSquare', title=u'Filled square'),
            ]),
        default=u'square',
        )
    
    marker_width = schema.Int(
        title=_(u'Marker width'),
        description=_(u'Line width of marker in pixel units.'),
        default=2,
        )
    
    form.widget(marker_color=ColorpickerFieldWidget)
    marker_color = schema.TextLine(
        title=_(u'Marker color'),
        required=False,
        default=u'#666666',
        )
    
    show_trend = schema.Bool(
        title=_(u'Show trend-line?'),
        description=_(u'Display a linear trend line?  If enabled, uses '\
                      u'configuration options specified.'),
        default=False,
        )
    
    trend_width = schema.Int(
        title=_(u'Trend-line width'),
        description=_(u'Line width of trend-line in pixel units.'),
        default=2,
        )
    
    form.widget(trend_color=ColorpickerFieldWidget)
    trend_color = schema.TextLine(
        title=_(u'Trend-line color'),
        required=False,
        default=u'#CCCCCC',
        )
    
    show_goal = schema.Bool(
        title=_(u'Show goal-line?'),
        description=_(u'If defined, show (constant horizontal) goal line?'),
        default=True,
        )
    
    form.widget(goal_color=ColorpickerFieldWidget)
    goal_color = schema.TextLine(
        title=_(u'Goal-line color'),
        required=False,
        default=u'#333333',
        )

    legend_location = schema.Choice(
        title=_(u'Legend display'),
        description=_(u'Select a position for legend.'),
        vocabulary=SimpleVocabulary((
            SimpleTerm(value=None, token=str(None), title=u'Disabled'),
            SimpleTerm(value='nw',title=_(u'Top left')),
            SimpleTerm(value='n', title=_(u'Top')),
            SimpleTerm(value='ne', title=_(u'Top right')),
            SimpleTerm(value='e', title=_(u'Right')),
            SimpleTerm(value='se', title=_(u'Bottom right')),
            SimpleTerm(value='s', title=_(u'Bottom')), 
            SimpleTerm(value='sw', title=_(u'Bottom left')),
            SimpleTerm(value='w', title=_(u'Left')),
            )),
        required=False,
        default=None, # legend disabled
        )


class ITimeSeriesData(Interface):
    """
    Time series interface for configured range of time with iterable data
    points and basic display-agnostic configuration.
    """
    
    identifier = schema.TextLine(
        title=_(u'Series identifier'),
        description=_(u'Series identifier (text short name); may be '\
                      u'prefixed with a namespace.'),
        required=False,
        )
    
    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Name or series title; may be displayed in legend.'),
        required=False,
        )
    
    description = schema.Text(
        title=_(u'Description'),
        description=_(u'Textual description of the time series.'),
        required=False,
        )
    
    start = schema.Date(
        title=_(u'Start date'),
        required=False,
        )
    
    end = schema.Date(
        title=_(u'End date'),
        required=False,
        )
    
    units = schema.TextLine(
        title=_(u'Units'),
        description=_(u'Units of measure for the series.'),
        required=False,
        )
    
    goal = schema.Float(
        title=_(u'Goal'),
        description=_(u'Goal value as floating point / decimal number'),
        required=False,
        )
    
    def datapoints():
        """
        return a iterable of IDataPoint objects.
        """
    
    @invariant
    def validate_start_end(obj):
        if not (obj.start is None or obj.end is None) and obj.start > obj.end:
            raise Invalid(_(u"Start date cannot be after end date."))


class ITimeSeriesChart(form.Schema,
                       ITimeSeriesData,
                       ISeriesDisplayLine,
                       ILocation):
    """Base chart content item/component interface"""
    
    form.omitted('__name__')
    
    form.fieldset(
        'display',
        label=u"Display settings",
        fields=['line_width',
                'line_color',
                'marker_style',
                'marker_width',
                'marker_color',
                'chart_styles',
                'show_trend',
                'trend_width',
                'trend_color',
                'show_goal',
                'goal_color',
                'legend_location',]
        )
    
    form.fieldset(
        'about',
        label=u"About",
        fields=['info'],
        )
    
    info = RichText(
        title=_(u'Series information'),
        description=_(u'Series information is rich text and may be '\
                      u'displayed in report output.'),
        required=False,
        )
    
    chart_styles = schema.Bytes(
        title=_(u'Chart styles'),
        description=_(u'CSS stylesheet rules for chart (optional).'),
        required=False,
        )


class ITimeDataChart(ITimeSeriesChart, IDataPoints):
    """
    A time series chart for which data points are retrieved by datapoints()
    are stored locally, and as such, the content object provides the
    IDataPoints interface.
    """
    
    form.fieldset(
        'data',
        label=u"Data",
        fields=['data'],
        )
    
    form.widget(data=DataGridFieldFactory)
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points for time series: date, value; values are '\
                      u'either whole/integer or decimal numbers.'),
        value_type=DictRow(
            title=_(u'tablerow'),
            schema=IDataPoint,
            ),
        )


class ITimeMeasureChart(ITimeSeriesChart):
    """
    A time series chart for which data points are retrieved by datapoints()
    via delegation to adaptation of context to IDataPoints object.
    """
    
    form.fieldset(
        'data',
        label=u"Data",
        fields=['measure_name', 'measure_namespace'],
        )
    
    measure_name = schema.TextLine(
        title=_(u'Measure name'),
        description=_(u'Measure name for chart to subscribe to.'),
        required=False,
        )
    
    measure_namespace = schema.TextLine(
        title=_(u'Measure namespace'),
        description=_(u'Measure namespace or qualifier for name.'),
        required=False,
        )


class IMultiSeriesReport(form.Schema, IOrderedContainer):
    """
    Ordered container/folder of contained charts providing ITimeSeriesChart.
    """
    
    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Report title; may be displayed in output.'),
        required=False,
        )
    
    description = schema.Text(
        title=_(u'Description'),
        description=_(u'Textual description of the report.'),
        required=False,
        )

