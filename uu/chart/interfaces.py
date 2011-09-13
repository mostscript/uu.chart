"""
uu.chart.interfaces -- narrative summary of components:
  
  * Reports are ordered containers (folders) of one or more charts.
  
  * Charts are made up of data collections and presentation metadata.
  
  * Data collections (and therefore charts) contain a sequence of one or
    more data series.

        Terminology: we use the word "series" in a more colloquial, not
                     strictly mathematic sense: "series" is used
                     synonymously with "sequence" -- in our case a series
                     is a labeled/named sequence, for which each label
                     provides a facet for grouping related data points.
                    
                     In strictly mathematical sense, what we call "points"
                     are relations:
                     
                        value    R           sequencename
                                  pointname
                     
                     and a "series" is a sequence of these relations. 
                    
                     We can also group all values sharing the same point
                     identity/name across multiple sequences as being
                     set members of an equivalence class for that point
                     identity/name:
                    
                        [x]
                           R
                            pointname
                     
                     This is essentially what a multi-line or bar chart
                     presents in horizontal x-axis groupings.  In a way,
                     this is a visualization of faceted classification --
                     whether such facets are dates (as in a chronological
                     time-series) or nominal classifiers.
                     
  * Each series is named and is an iterable sequence of points.
  
  * Points have a unique identity within a series, usually either a name 
    or a date.  This name/identity is does double-duty as an identifier and
    as a title.

    * It is useful to think of each point as a single key/value pair, where
      the key is usually visualized and grouped along the X-axis and the 
      value is usually treated as a Y-axis value.
  
  * Points contain one numeric value each and simple annotation metadata 
    (note, URL) fields.
  
  * Charts can contain presentation metadata for:
  
    * Display for the chart at large.
    
    * Display for one series within the chart.

  * Implementations can store data series intrinsically on the chart, or
    delegate their lookup to other components (e.g. database lookups, index
    queries, traversal to externally stored measures).

  * User experience:

    (a) User creates a report in application.
    
    (b) User visits reports and adds "chart" items to the report.
    
      * User chooses a chart type at this time:
    
        * Named-series chart 
            * May be line or bar chart, configurable.
        
        * Time-series chart:
            * May be line or bar chart, configurable.
    
      * User optionally re-orders chart position in report at creation
        time or any time thereafter.
  
    (c) User visits chart, adds "Data series" to chart:
        
        If chart is time-series, user add a "Time-series sequence"
        
            A type for an externally defined measure, might be called
            "Time-series measure" in the add menu.
        
        If chart is named-series chart, user adds "Named-series sequence"

"""
from collective.z3cform.datagridfield import DataGridFieldFactory, DictRow
from plone.directives import form, dexterity
from plone.app.textfield import RichText
from zope.interface import Interface, Invalid, invariant
from zope import schema
from zope.container.interfaces import IOrderedContainer
from zope.location.interfaces import ILocation
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from collective.z3cform.colorpicker.colorpicker import ColorpickerFieldWidget


from uu.chart import _ #MessageFactory for package


## constants for use in package:

TIME_DATA_TYPE = 'Time Data Sequence'       ## portal types should
NAMED_DATA_TYPE = 'Named Data Sequence'     ## match FTIs

## sorting data-point identities need collation/comparator function
def cmp_point_identities(a,b):
    """
    Given point identities a, b (may be string, number, date, etc),
    collation algorithm compares:
    
      (a) strings case-insensitively

      (b) dates and datetimes compared by normalizing date->datetime.
      
      (c) all other types use __cmp__(self, other) defaults from type.

    """
    dt = lambda d: datetime(*d.timetuple()[0:6]) #date|datetime -> datetime
    if isinstance(a, basestring) and isinstance(b, basestring):
        return cmp(a.upper(), b.upper())
    if isinstance(a, date) or isinstance(b, date):
        return cmp(dt(a), dt(b))
    return cmp(a,b)


class IDataPoint(Interface):
    """Data point contains single value and optional note and URI"""
    
    value = schema.Float(
        title=_(u'Number value'),
        description=_(u'Decimal number value.'),
        default=0.0,
        )
    
    note = schema.Text(
        title=_(u'Note'),
        description=_(u'Note annotating the data value for this point.'),
        required=False,
        )
    
    uri = schema.Text(
        title=_(u'URI'),
        description=_(u'URI/URL or identifier to source of data'),
        required=False,
        )
    
    def identity():
        """
        Return identity (such as a name, date, id) for the point unique
        to the series in which it is contained.
        """


class INamedBase(Interface):
    """Mix-in schema for name field"""
    
    name = schema.TextLine(
        title=_(u'Name'),
        description=_(u'Series-unique name or category for data point.'),
        required=True,
        )
    
    def identity():
        """return self.name"""


class IDateBase(Interface):
    """Mix-in schema with date field"""
    
    date = schema.Date(
        title=_(u'Date'),
        required=True,
        )
        
    def identity():
        """return self.date"""


class INamedDataPoint(INamedBase, IDataPoint):
    """Data point with a series-unique categorical name"""    


class ITimeSeriesDataPoint(IDateBase, IDataPoint):
    """Data point with a distinct date"""


#--- series and collection interfaces:


class IDataSeries(Interface):
    """Iterable of IDataPoint objects"""
    
    name = schema.TextLine(
        title=_(u'Name'),
        description=_(u'Name of data series; may be displayed as a label.'),
        required=True,
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
    
    range_min = schema.Float(
        title=_(u'Range minimum'),
        description=_(u'Minimum anticipated value of any data point '\
                      u'(optional).'),
        required=False,
        )
    
    range_max = schema.Float(
        title=_(u'Range maximum'),
        description=_(u'Maximum anticipated value of any data point '\
                      u'(optional).'),
        required=False,
        )
    
    def __iter__():
        """
        Return iterable of date, number data point objects providing
        (at least) IDataPoint.
        """
    
    def __len__():
        """Return number of data points"""


class IDataCollection(Interface):
    """
    Collection of one or more (related) data series and associated metadata.
    Usually the logical component of a chart with multiple data series.
    """
    
    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Data collection name or title; may be displayed '\
                      u'in legend.'),
        required=False,
        )
    
    description = schema.Text(
        title=_(u'Description'),
        description=_(u'Textual description of the data collection.'),
        required=False,
        )
    
    units = schema.TextLine(
        title=_(u'Units'),
        description=_(u'Common set of units of measure for the data '\
                      u'series in this collection.  If the units '\
                      u'for series are not shared, then define '\
                      u'respective units on the series themselves.'),
        required=False,
        )
    
    goal = schema.Float(
        title=_(u'Goal'),
        description=_(u'Common goal value as decimal number.  If each '\
                      u'series has different respective goals, edit '\
                      u'those goals on each series.'),
        required=False,
        )
    
    def series():
        """
        return a iterable of IDataSeries objects.
        """
    
    def identities():
        """
        Return a sequence of sorted point identities (names, dates, etc)
        for all points contained in all series.  These identities are 
        effectively faceted classifiers for points.
        """


class ITimeSeriesCollection(IDataCollection):
    """
    Time series interface for configured range of time for all data
    series contained.  Adds date range configuration to collection.
    """
    
    start = schema.Date(
        title=_(u'Start date'),
        required=False,
        )
    
    end = schema.Date(
        title=_(u'End date'),
        required=False,
        )
    
    @invariant
    def validate_start_end(obj):
        if not (obj.start is None or obj.end is None) and obj.start > obj.end:
            raise Invalid(_(u"Start date cannot be after end date."))


# -- presentation and content interfaces:

class IChartDisplay(form.Schema):
    """
    Display configuration for chart settings (as a whole).
    """
    
    form.fieldset(
        'display',
        label=u"Display settings",
        fields=['show_goal',
                'goal_color',]
        )
    
    show_goal = schema.Bool(
        title=_(u'Show goal-line?'),
        description=_(u'If defined, show (constant horizontal) goal line?'),
        default=False,
        )
    
    form.widget(goal_color=ColorpickerFieldWidget)
    goal_color = schema.TextLine(
        title=_(u'Goal-line color'),
        required=False,
        default=u'#333333',
        )
    
    chart_type = schema.Choice(
        title=_(u'Chart type'),
        description=_(u'Type of chart to display.'),
        vocabulary=SimpleVocabulary([
            SimpleTerm(value=u'line', title=u'Line chart'),
            #SimpleTerm(value=u'bar', title=u'Bar chart'),
            #SimpleTerm(value=u'barline', title=u'Two-measure bar plus line.'),
            ]),
        default=u'line',
        )


class ILineDisplay(form.Schema):
    """
    Mixin interface for display-line configuration metadata for series line.
    
    Note: while a series can have a specific goal value, only one
    goal per-chart is considered for goal-line display.  It is therefore up
    to implementation to choose reasonable aspects for display (or omission)
    of line/series specific goals.
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
        description=_(u'Shape/type of the point-value marker.'),
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
    
    legend_location = schema.Choice(
        title=_(u'Legend location'),
        description=_(u'Select a directional position for legend.'),
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
    
    legend_placement = schema.Choice(
        title=_(u'Legend placement'),
        description=_(u'Where to place legend in relationship to the grid.'),
        vocabulary=SimpleVocabulary((
            SimpleTerm(value='outside', title=_(u'Outside grid')),
            SimpleTerm(value='inside', title=_(u'Inside grid')),
            )),
        required=True,
        default='inside',
        )

# --- content type interfaces: ---

class IBaseChart(form.Schema, ILocation):
    """Base chart (content item) interface"""
    
    form.omitted('__name__')
    
    form.fieldset(
        'about',
        label=u"About",
        fields=['info'],
        )
    
    form.fieldset(
        'display',
        label=u"Display settings",
        fields=['chart_styles',]
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


# -- timed series chart interfaces:

class ITimeSeriesChart(IBaseChart,
                       ITimeSeriesCollection,
                       IChartDisplay):
    """Chart content item; container for sequences"""
    
    def series():
        """
        return a iterable of IDataSeries objects for all contained
        series.  Points in each series should provide ITimeSeriesDataPoint.
        """


class ITimeDataSequence(IDataSeries):
    """Content item interface for a data series stored as content"""
    
    form.widget(data=DataGridFieldFactory)
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points for time series: date, value; values are '\
                      u'either whole/integer or decimal numbers.'),
        value_type=DictRow(
            title=_(u'tablerow'),
            schema=ITimeSeriesDataPoint,
            ),
        )


class ITimeMeasureSequence(IDataSeries):
    """
    A time series data sequence content item interface.  Series data 
    iteration via proxy/delegation to external named adapter providing
    IDataSeries is customary (where name for adaptation uses the 
    measure name and namespace field values configured).
    
    Contained point identity() calls return date or datetime objects.
    """
    
    form.fieldset(
        'data',
        label=u"Data",
        fields=['measure_name', 'measure_namespace'],
        )
    
    measure_name = schema.TextLine(
        title=_(u'Measure name'),
        description=_(u'Measure name for sequence to subscribe to.'),
        required=False,
        )
    
    measure_namespace = schema.TextLine(
        title=_(u'Measure namespace'),
        description=_(u'Measure namespace or qualifier for name; '\
                      u'may be system or data source name.'),
        required=False,
        )


# -- named series chart interfaces:

class INamedSeriesChart(IBaseChart, IDataCollection, IChartDisplay):
    """
    Named/categorical chart: usually a bar chart with x-axis containing
    categorical enumerated names/labels, and Y-axis representing values
    for that label.
    """
    
    def series():
        """
        return a iterable of IDataSeries objects for all contained
        series.  Points in each series should provide INamedSeriesDataPoint.
        """

class INamedDataSequence(IDataSeries):
    """Named category seqeuence with embedded data stored as content"""
    
    form.widget(data=DataGridFieldFactory)
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points for series: name, value; values are '\
                      u'either whole/integer or decimal numbers.'),
        value_type=DictRow(
            title=_(u'tablerow'),
            schema=INamedDataPoint,
            ),
        )


class INamedMeasureSequence(IDataSeries):
    """
    A named-data sequence content item interface.  Series data 
    iteration via proxy/delegation to external named adapter providing
    IDataSeries is customary (where name for adaptation uses the 
    measure name and namespace field values configured).
    
    Contained point identity() calls return string names.
    """
    
    form.fieldset(
        'data',
        label=u"Data",
        fields=['measure_name', 'measure_namespace'],
        )
    
    measure_name = schema.TextLine(
        title=_(u'Measure name'),
        description=_(u'Measure name for sequence to subscribe to.'),
        required=False,
        )
    
    measure_namespace = schema.TextLine(
        title=_(u'Measure namespace'),
        description=_(u'Measure namespace or qualifier for name; '\
                      u'may be system or data source name.'),
        required=False,
        )


# report container/folder interfaces:

class IDataReport(form.Schema, IOrderedContainer):
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

