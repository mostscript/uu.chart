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

from datetime import date, datetime
import operator

from collective.z3cform.datagridfield import DataGridFieldFactory, DictRow
from plone.app.textfield import RichText
from plone.directives import form
from plone.autoform import directives
from plone.uuid.interfaces import IAttributeUUID
from z3c.form.browser.textarea import TextAreaFieldWidget
from zope.interface import Interface, Invalid, invariant, implements
from zope.component.hooks import getSite
from zope.container.interfaces import IOrderedContainer
from zope.location.interfaces import ILocation
from zope import schema
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from uu.formlibrary.interfaces import is_content_uuid
from uu.formlibrary.browser.widget import CustomRootRelatedWidget
from uu.formlibrary.measure.interfaces import MEASURE_DEFINITION_TYPE
from uu.formlibrary.measure.interfaces import MeasureGroupContentSourceBinder
from uu.formlibrary.measure.interfaces import PermissiveVocabulary

from uu.chart import _  # MessageFactory for package
from uu.chart.browser.color import NativeColorFieldWidget

# type name globals:
TIMESERIES_TYPE = 'uu.chart.timeseries'
NAMEDSERIES_TYPE = 'uu.chart.namedseries'
CHART_TYPES = (TIMESERIES_TYPE, NAMEDSERIES_TYPE)
REPORT_TYPE = 'uu.chart.report'
TIMESERIES_DATA = 'uu.chart.data.timeseries'
NAMEDSERIES_DATA = 'uu.chart.data.namedseries'
MEASURESERIES_DATA = 'uu.chart.data.measureseries'
STYLEBOOK_TYPE = 'uu.chart.stylebook'
LINESTYLE_TYPE = 'uu.chart.linestyle'

# globals for vocabulary and summarization/aggregate functions

F_MEAN = lambda l: float(sum(l)) / len(l) if len(l) > 0 else float('nan')


def F_MEDIAN(l):
    """
    Return middle value of sorted sequence for an odd-sized
    list, or return the arithmetic mean of the two middle-values
    in an even-sized list.
    """
    odd = lambda v: bool(v % 2)
    s, size = sorted(l), len(l)
    middle = size / 2
    _slice = slice((middle - 1), (middle + 1))
    return s[middle] if odd(size) else F_MEAN(s[_slice])


AGGREGATE_FUNCTIONS = {
    'SUM': sum,
    'AVG': F_MEAN,
    'PRODUCT': lambda l: reduce(operator.mul, l),
    'MIN': min,
    'MAX': max,
    'MEDIAN': F_MEDIAN,
    'COUNT': len,
}

AGGREGATE_LABELS = [
    ('SUM', u'Sum'),
    ('AVG', u'Average'),
    ('PRODUCT', u'Product'),
    ('MIN', u'Minimum'),
    ('MAX', u'Maximum'),
    ('MEDIAN', u'Median'),
    ('COUNT', u'Count of occurrences'),
]

SUMMARIZATION_STRATEGIES = AGGREGATE_LABELS + [
    ('WEIGHTED_MEAN', u'Weighted mean'),
    ('FIRST', u'Pick first found value'),
    ('LAST', u'Pick last found value'),
    ('IGNORE', u'Ignore more than one value, omit on encountered duplication'),
]

VOCAB_SUMMARIZATION = SimpleVocabulary(
    [SimpleTerm(v, title=title) for v, title in SUMMARIZATION_STRATEGIES]
)

FREQ_VOCAB = SimpleVocabulary(
    [SimpleTerm(v, title=title) for v, title in [
        ('monthly', u'Monthly'),
        ('weekly', u'Weekly'),
        ('yearly', u'Yearly'),
        ('quarterly', u'Quarterly'),
        ('daily', u'Daily'),
    ]]
)

WIDTH_UNITS = SimpleVocabulary(
    [SimpleTerm(v, title=title) for v, title in [
        ('%', u'Percentage of content area'),
        ('px', u'Pixels on screen'),
    ]]
)

HEIGHT_UNITS = SimpleVocabulary(
    [SimpleTerm(v, title=title) for v, title in [
        ('%', u'Percentage of specified width (variable aspect ratio)'),
        ('px', u'Pixels: a fixed number of pixels on screen'),
        ('1:1', u'Square aspect ratio (1:1)'),
        ('2:1', u'2:1 fixed rectangular aspect ratio'),
        ('2:3', u'2:3 fixed rectangular aspect ratio'),
        ('3:5', u'3:5 fixed rectangular aspect ratio'),
        ('4:3', u'4:3 fixed rectangular aspect ratio'),
        ('16:9', u'16:9 fixed rectangular aspect ratio'),
    ]]
)

VOCAB_PLOT_TYPES = SimpleVocabulary([
    SimpleTerm(value=u'line', title=u'Line chart'),
    SimpleTerm(value=u'bar', title=u'Bar chart'),
    ])


def resolve_uid(uid):
    catalog = getSite().portal_catalog
    r = catalog.unrestrictedSearchResults({'UID': str(uid)})
    if not r:
        return None
    return r[0]._unrestrictedGetObject()


def provider_measure(context):
    """Given measure-provider for data sequence, get its bound measure"""
    # IMeasureSeriesProvider['measure'] field:
    measure_uid = getattr(context, 'measure', None)
    if measure_uid is None:
        return None
    return resolve_uid(measure_uid)


class MeasureGroupParentBinder(MeasureGroupContentSourceBinder):
    """
    Source binder for listing items contained in measure group parent of
    a measure context, filtered by type.
    """

    implements(IContextSourceBinder)

    def __call__(self, context):
        measure = provider_measure(context)
        if measure is None:
            return PermissiveVocabulary([])  # likely on add-form
        # get a context (indirection) of measure bound, use that to get
        # group and contained content in superclass implementation:
        return super(MeasureGroupParentBinder, self).__call__(measure)


# constants for use in package:

TIME_DATA_TYPE = 'uu.chart.data.timeseries'     # portal types should
NAMED_DATA_TYPE = 'uu.chart.data.namedseries'   # match FTIs
MEASURE_DATA_TYPE = 'uu.chart.data.measureseries'


# sorting data-point identities need collation/comparator function
def cmp_point_identities(a, b):
    """
    Given point identities a, b (may be string, number, date, etc),
    collation algorithm compares:

      (a) strings case-insensitively

      (b) dates and datetimes compared by normalizing date->datetime.

      (c) all other types use __cmp__(self, other) defaults from type.

    """
    dt = lambda d: datetime(*d.timetuple()[0:6])  # date|datetime -> datetime
    if isinstance(a, basestring) and isinstance(b, basestring):
        return cmp(a.upper(), b.upper())
    if isinstance(a, date) or isinstance(b, date):
        return cmp(dt(a), dt(b))
    return cmp(a, b)


class IChartProductLayer(Interface):
    """Marker interface for product layer"""


class IAggregateDescription(Interface):
    """
    Mixin of fields related to aggregating multiple data points into
    a single descriptive aggretate point.  All fields optional, and
    only considered relevant to aggregation of data from multiple
    sources or samples.

    'distribution' attribute would have values that look like:
    [{ "value": 75.0, "sample_size": 8 }, { "value": 80, "sample_size": 10}]

    This data is sufficient to compute:

        - The sum of sample sizes.
        - The weighted mean.
        - The original numerator values as value/100.0 * sample_size
          - Presuming the value looks like a percentage.
        - The arithmetic mean.
        - Distribution plot.
        - Median, quartile boundary, and therefore box plot.
    """

    distribution = schema.List(
        title=_(u'Distribution data'),
        description=_(u'List of dict containing value, sample size for each '
                      u'sample in aggregation.'),
        required=False,
        value_type=schema.Dict(
            key_type=schema.BytesLine(),
            value_type=schema.Object(
                schema=Interface,
                description=u'Value, may be int or float'
                )
            )
        )


class IDataPoint(IAggregateDescription):
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

    uri = schema.BytesLine(
        title=_(u'URI'),
        description=_(u'URI/URL or identifier to source of data'),
        required=False,
        )

    sample_size = schema.Int(
        title=_(u'Sample size (N)'),
        description=u'Sample size, may be computed denominator of a '
                    u'population or subpopulation sampled.',
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


# --- series and collection interfaces:


class IDataSeries(form.Schema):
    """Iterable of IDataPoint objects"""

    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Name of data series; may be displayed as a label.'),
        required=True,
        )

    def __iter__():
        """
        Return iterable of date, number data point objects providing
        (at least) IDataPoint.
        """

    def __len__():
        """Return number of data points"""

    def display_value(point):
        """Return normalized string display value for point"""

    def excluded():
        """
        If applicable, return a list of data points that were
        excluded from consideration by relevant filtering process.

        If not applicable, return empty list.
        """


class IDataCollection(Interface):
    """
    Collection of one or more (related) data series and associated metadata.
    Usually the logical component of a chart with multiple data series.
    """

    title = schema.TextLine(
        title=_(u'Title'),
        description=_(u'Data collection name or title; may be displayed '
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
        description=_(u'Common set of units of measure for the data '
                      u'series in this collection.  If the units '
                      u'for series are not shared, then define '
                      u'respective units on the series themselves. '
                      u'May be displayed as part of Y-axis label.'),
        required=False,
        )

    goal = schema.Float(
        title=_(u'Goal'),
        description=_(u'Common goal value as decimal number.  If each '
                      u'series has different respective goals, edit '
                      u'those goals on each series.'),
        required=False,
        )

    range_min = schema.Float(
        title=_(u'Range minimum'),
        description=_(u'Minimum anticipated value of any data point '
                      u'(optional).'),
        required=False,
        )

    range_max = schema.Float(
        title=_(u'Range maximum'),
        description=_(u'Maximum anticipated value of any data point '
                      u'(optional).'),
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

    frequency = schema.Choice(
        title=u'Chart frequency',
        vocabulary=FREQ_VOCAB,
        default='monthly',
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

    width = schema.Int(
        title=_(u'Width'),
        description=_(u'Display width of chart, including Y-axis labels, '
                      u'grid, and legend (if applicable) in units '
                      u'configured.'),
        default=100,
        )

    width_units = schema.Choice(
        title=_(u'Units of width'),
        vocabulary=WIDTH_UNITS,
        default='%',
        )

    height = schema.Int(
        title=_(u'Height'),
        description=_(u'Display height of chart in units configured '
                      u'(either as percentage of width, or in pixels).'),
        default=50,
        )

    height_units = schema.Choice(
        title=_(u'Units of height'),
        vocabulary=HEIGHT_UNITS,
        default='2:1',
        )

    show_goal = schema.Bool(
        title=_(u'Show goal-line?'),
        description=_(u'If defined, show (constant horizontal) goal line?'),
        default=False,
        )

    form.widget(goal_color=NativeColorFieldWidget)
    goal_color = schema.TextLine(
        title=_(u'Goal-line color'),
        description=_(u'If omitted, color will be selected from defaults.'),
        required=False,
        default=u'Auto',
        )

    form.order_after(chart_type='description')
    chart_type = schema.Choice(
        title=_(u'Chart type'),
        description=_(u'Type of chart to display.'),
        vocabulary=VOCAB_PLOT_TYPES,
        default=u'line',
        )

    legend_placement = schema.Choice(
        title=_(u'Legend placement'),
        description=_(
            u'Where to place legend in relationship to the grid.'
            u'Note: the legend is disabled for less than two '
            u'series/line unless the tabular legend is selected.'
            ),
        vocabulary=SimpleVocabulary((
            SimpleTerm(value=None, token=str(None), title=u'Legend disabled'),
            SimpleTerm(
                value='outside',
                title=_(u'Basic legend, outside grid')
                ),
            SimpleTerm(value='tabular', title=_(
                u'Tabular legend with data, below plot')),
            )),
        required=False,
        default='tabular',
        )

    legend_location = schema.Choice(
        title=_(u'Legend location'),
        description=_(u'Select a directional position for legend. '
                      u'This setting is ignored if either the tabular '
                      u'legend placement is selected or if the '
                      u'legend is hidden (for less than two series).'),
        vocabulary=SimpleVocabulary((
            SimpleTerm(value='n', title=_(u'Top')),
            SimpleTerm(value='e', title=_(u'Right')),
            )),
        required=False,
        default='e',  # right hand side
        )

    x_label = schema.TextLine(
        title=_(u'X axis label'),
        default=u'',
        required=False,
        )

    y_label = schema.TextLine(
        title=_(u'Y axis label'),
        default=u'',
        required=False,
        )

    form.widget(chart_styles=TextAreaFieldWidget)
    chart_styles = schema.Bytes(
        title=_(u'Chart styles'),
        description=_(u'CSS stylesheet rules for chart (optional).'),
        required=False,
        )

    point_labels = schema.Choice(
        title=u'Show point labels?',
        description=u'Show labels above data-point markers?  '
                    u'This may be overridden on individual lines/series.',
        default='show',
        vocabulary=SimpleVocabulary([
                SimpleTerm('show', title=u'Show labels'),
                SimpleTerm('omit', title=u'Omit labels'),
            ])
        )


class ISeriesDisplay(form.Schema):
    """
    Common display settings for visualizing a series as either a bar
    or line chart.
    """

    form.widget(color=NativeColorFieldWidget)
    color = schema.TextLine(
        title=_(u'Series color'),
        description=_(u'If omitted, color will be selected from defaults.'),
        required=False,
        default=u'Auto',
        )

    show_trend = schema.Bool(
        title=_(u'Show trend-line?'),
        description=_(u'Display a linear trend line?  If enabled, uses '
                      u'configuration options specified.'),
        default=False,
        )

    trend_width = schema.Int(
        title=_(u'Trend-line width'),
        description=_(u'Line width of trend-line in pixel units.'),
        default=2,
        )

    form.widget(trend_color=NativeColorFieldWidget)
    trend_color = schema.TextLine(
        title=_(u'Trend-line color'),
        description=_(u'If omitted, color will be selected from defaults.'),
        required=False,
        default=u'Auto',
        )

    display_precision = schema.Int(
        title=u'Digits after decimal point (display precision)?',
        description=u'When displaying a decimal value, how many places '
                    u'beyond the decimal point should be displayed in '
                    u'output?  Default: two digits after the decimal point.',
        default=1,
        )

    point_labels = schema.Choice(
        title=u'Show point labels?',
        description=u'Show labels above data-point markers for this series?',
        default='defer',
        vocabulary=SimpleVocabulary([
                SimpleTerm('defer', title=u'Defer to chart default'),
                SimpleTerm('show', title=u'Show labels'),
                SimpleTerm('omit', title=u'Omit labels'),
            ])
        )


class ILineDisplayCore(form.Schema, ISeriesDisplay):
    """
    Mixin interface for display-line configuration metadata for series line.
    """

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
            SimpleTerm(value=u'triangle-up', title=u'Triangle (upward)'),
            SimpleTerm(value=u'triangle-down', title=u'Triangle (downward)'),
            ]),
        default=u'square',
        )

    marker_size = schema.Float(
        title=_(u'Marker size'),
        description=_(u'Size of the marker (diameter or circle, length of '
                      u'edge of square, etc) in decimal pixels.'),
        required=False,
        default=9.0,
        )

    marker_width = schema.Int(
        title=_(u'Marker line width'),
        description=_(u'Line width of marker in pixel units for '
                      u'non-filled markers.'),
        required=False,
        default=2,
        )

    form.widget(marker_color=NativeColorFieldWidget)
    marker_color = schema.TextLine(
        title=_(u'Marker color'),
        description=_(u'If omitted, color will be selected from defaults.'),
        required=False,
        default=u'Auto',
        )

    break_lines = schema.Bool(
        title=u'Break lines?',
        description=u'When a value is missing for name or date on the '
                    u'X axis, should the line be broken/discontinuous '
                    u'such that no line runs through the empty/null '
                    u'value?  This defaults to True, which means that '
                    u'no line will run from adjacent values through the '
                    u'missing value.',
        default=True,
        )


class ILineDisplay(ILineDisplayCore):
    """Use of Line Display in chart settings"""

    form.fieldset(
        'display',
        label=u"Display settings",
        fields=[
            'color',
            'line_width',
            'marker_style',
            'marker_size',
            'marker_width',
            'marker_color',
            'show_trend',
            'trend_width',
            'trend_color',
            'break_lines',
            'point_labels',
            'display_precision',
            ],
        )


# --- content type interfaces: ---

class IBaseChart(
        form.Schema,
        ILocation,
        IAttributeUUID,
        IDataCollection,
        IChartDisplay):
    """Base chart (content item) interface"""

    form.omitted('__name__')

    form.fieldset(
        'goal',
        label=u'Goal',
        fields=[
            'show_goal',
            'goal',
            'goal_color',
            ]
        )

    form.fieldset(
        'legend',
        label=u'Axes & Legend',
        fields=[
            'legend_placement',
            'legend_location',
            'x_label',
            'y_label',
            'units',
            ]
        )

    form.fieldset(
        'display',
        label=u"Display",
        fields=[
            'width',
            'width_units',
            'height',
            'height_units',
            'chart_styles',
            'point_labels',
            ]
        )

    form.fieldset(
        'about',
        label=u"About",
        fields=['info'],
        )

    directives.widget(
        'stylebook',
        CustomRootRelatedWidget,
        pattern_options={
            'selectableTypes': ['uu.chart.stylebook'],
            'maximumSelectionSize': 1,
            'baseCriteria': [{
                'i': 'portal_type',
                'o': 'plone.app.querystring.operation.string.is',
                'v': 'uu.chart.stylebook',
                }]
            }
        )
    stylebook = schema.BytesLine(
        title=u'Bound theme',
        description=u'If a theme is bound, any updates to that theme '
                    u'will OVER-WRITE display configuration saved '
                    u'on this chart.',
        required=False,
        constraint=is_content_uuid
        )

    info = RichText(
        title=_(u'Informative notes'),
        description=_(u'This allows any rich text and may contain free-form '
                      u'notes about this chart; displayed in report output.'),
        required=False,
        )


# -- timed series chart interfaces:

class ITimeSeriesChart(IBaseChart, ITimeSeriesCollection):
    """Chart content item; container for sequences"""

    form.order_after(auto_crop='frequency')
    auto_crop = schema.Bool(
        title=u'Auto-crop to completed data?',
        description=u'If data contains sequential null values (incomplete '
                    u'or no data calculable) on the right-hand of a '
                    u'time-series plot, should that right-hand side '
                    u'be cropped to only show the latest meaningful '
                    u'data?  The default is to crop automatically.',
        default=True,
        )

    form.order_after(force_crop='auto_crop')
    force_crop = schema.Bool(
        title=u'Forced crop of data?',
        description=u'If data points are available before a specified '
                    u'start date or after a specified end-date, should '
                    u'those points be excluded from the visualization?',
        default=False,
        )

    form.omitted('label_overrides')
    label_overrides = schema.Dict(
        key_type=schema.Date(),
        value_type=schema.BytesLine(),
        required=False,
        )

    def series():
        """
        return a iterable of IDataSeries objects for all contained
        series.  Points in each series should provide ITimeSeriesDataPoint.
        """


DATE_AXIS_LABEL_CHOICES = SimpleVocabulary(
    [
        SimpleTerm(value, title=title) for value, title in (
            ('locale', u'MM/DD/YYYY'),
            ('iso8601', u'YYYY-MM-DD'),
            ('name', u'Month name only'),
            ('name+year', u'Month name and year'),
            ('abbr', u'Month abbreviation'),
            ('abbr+year', u'Month abbreviation, with year'),
        )
    ]
)


class ITimeDataSequence(form.Schema, IDataSeries, ILineDisplay):
    """Content item interface for a data series stored as content"""

    input = schema.Text(
        title=_(u'Data input'),
        description=_(u'Comma-separated records, one per line '
                      u'(date, numeric value, [note], [URL]). '
                      u'Note and URL are optional. Date '
                      u'should be in MM/DD/YYYY format.'),
        default=u'',
        required=False,
        )

    label_default = schema.Choice(
        title=_(u'Label default'),
        description=_(u'Default format for X-Axis labels.'),
        default='locale',
        vocabulary=DATE_AXIS_LABEL_CHOICES,
        )

    form.omitted('data')
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points for time series: date, value; values are '
                      u'either whole/integer or decimal numbers.'),
        value_type=schema.Object(
            schema=ITimeSeriesDataPoint,
            ),
        readonly=True,
        )


# -- named series chart interfaces:

class INamedSeriesChart(IBaseChart, IDataCollection, IChartDisplay):
    """
    Named/categorical chart: usually a bar chart with x-axis containing
    categorical enumerated names/labels, and Y-axis representing values
    for that label.
    """

    chart_type = schema.Choice(
        title=_(u'Chart type'),
        description=_(u'Type of chart to display.'),
        vocabulary=SimpleVocabulary([
            SimpleTerm(value=u'bar', title=u'Bar chart'),
            SimpleTerm(value=u'stacked', title=u'Stacked bar chart'),
            ]),
        default=u'bar',
        )

    def series():
        """
        return a iterable of IDataSeries objects for all contained
        series.  Points in each series should provide INamedSeriesDataPoint.
        """


class INamedDataSequence(form.Schema, IDataSeries, ISeriesDisplay):
    """Named category seqeuence with embedded data stored as content"""

    form.fieldset(
        'display',
        label=u"Display settings",
        fields=[
            'color',
            'show_trend',
            'trend_width',
            'trend_color',
            'display_precision',
            'point_labels',
            ],
        )

    input = schema.Text(
        title=_(u'Data input'),
        description=_(u'Comma-separated records, one per line '
                      u'(name, numeric value, [note], [URL]). '
                      u'Note and URL are optional.'),
        default=u'',
        required=False,
        )

    # data field to store CSV source:
    form.omitted('data')
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points for series: name, value; values are '
                      u'either whole/integer or decimal numbers.'),
        value_type=schema.Object(
            schema=INamedDataPoint,
            ),
        readonly=True,
        )


# report container/folder interfaces:

class IDataReport(form.Schema, IOrderedContainer, IAttributeUUID):
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

    timeseries_default_type = schema.Choice(
        title=u'Default plot type for time-series',
        vocabulary=VOCAB_PLOT_TYPES,
        default=u'line',
        )


class IMeasureSeriesProvider(form.Schema, IDataSeries, ILineDisplay):

    directives.widget(
        'measure',
        CustomRootRelatedWidget,
        custom_root_query={'portal_type': 'uu.formlibrary.measurelibrary'},
        pattern_options={
            'selectableTypes': [MEASURE_DEFINITION_TYPE],
            'maximumSelectionSize': 1,
            'baseCriteria': [{
                'i': 'portal_type',
                'o': 'plone.app.querystring.operation.string.is',
                'v': MEASURE_DEFINITION_TYPE,
                }]
            }
        )
    measure = schema.BytesLine(
        title=u'Bound measure',
        description=u'Measure definition that defines a function to apply '
                    u'to a dataset of forms to obtain a computed value for '
                    u'each as a data-point.',
        constraint=is_content_uuid,
        )

    dataset = schema.Choice(
        title=u'Data set (collection)',
        description=u'Select a dataset that enumerates which forms are '
                    u'considered part of the data set to query for data. '
                    u'You must select a dataset within the same measure '
                    u'group in which the bound measure definition is '
                    u'contained.',
        source=MeasureGroupParentBinder(
            portal_type='uu.formlibrary.setspecifier',
            ),
        required=False,
        )

    summarization_strategy = schema.Choice(
        title=u'Summarization strategy',
        description=u'How should data be summarized into a single value '
                    u'when multiple competing values for date or name '
                    u'are found in the data stream provided by the measure '
                    u'and data set?  For example you may average or sum '
                    u'the multiple values, take the first or last, '
                    u'or you may choose to treat such competing values as '
                    u'a conflict, and omit any value on duplication.',
        vocabulary=VOCAB_SUMMARIZATION,
        default='AVG',
        )

    form.omitted('data')
    data = schema.List(
        title=_(u'Data'),
        description=_(u'Data points computed from bound dataset, measure '
                      u'selected.  Should return an empty list if any '
                      u'bindings are missing. '
                      u'Whether the data point key/identity type is a date '
                      u'or a name will depend on the type of chart '
                      u'containing this data provider.'),
        value_type=schema.Object(
            schema=IDataPoint,
            ),
        readonly=True,
        )


# style book content interfaces:


class ISeriesQuickStyles(form.Schema):
    """Interface for quick line styles (commonly used) for style book"""

    form.widget(color=NativeColorFieldWidget)
    color = schema.TextLine(
        title=_(u'Series color'),
        description=_(u'If omitted, color will be selected from defaults.'),
        required=False,
        default=u'Auto',
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
            SimpleTerm(value=u'triangle-up', title=u'Triangle (upward)'),
            SimpleTerm(value=u'triangle-down', title=u'Triangle (downward)'),
            ]),
        default=u'square',
        )


class IChartStyleBook(IChartDisplay):
    """
    Style book for charts, can contain (as folder) ILineStyle items,
    in an ordered manner.
    """

    form.widget(quick_styles=DataGridFieldFactory)
    quick_styles = schema.List(
        title=u'Quick series styles',
        value_type=DictRow(schema=ISeriesQuickStyles),
        )

    # hide fields that are per-chart-specific
    form.omitted('x_label')
    form.omitted('y_label')


class ILineStyle(ILineDisplayCore):
    """
    Style book entry for a specific line or bar.
    """
