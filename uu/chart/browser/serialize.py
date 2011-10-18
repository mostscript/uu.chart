"""
chart views for generating JSON representation of chart data

JSON structure pseudo-UML
-------------------------

Note: properties marked with multiplicity [0..1] either have a typed
      value or are null.  These properties with optional values may 
      also be omitted from the JSON payload.

      Rendering code should have suitable defaults for ommited
      configuration and optional metadata.

      Date values will be formatted to ISO 8601 with microseconds removed.
      (jqplot understands this format, as do many other parsers).

 _________________________________
| Multi-series chart              | ,    ___________________
+---------------------------------+/|___| Time-series chart |   subclass adds
| title : String                  |\|   +-------------------+   string date
| description : String      [0..1]| `   | start : String    |   start, end 
| css : String              [0..1]|     | end : String      |   fields
| x_label : String          [0..1]|     '-------------------'
| y_label : String          [0..1]|    
| chart_type : String       [0..1]|   enum: ('line' (default), 'bar')
| units : String            [0..1]|
| goal : Number             [0..1]|   Common goal; omit if None or hidden.
| goal_color : String       [0..1]|   include IFF configured, goal not hidden
| x_axis_type : String      [0..1]|   Either 'date' or omitted.
| legend_location : String  [0..1]|   null ==> hide legend
| legend_placement : String [0..1]|   enum: ('inside', 'outside')
'---------------------------------'
       1 /%\ 
         \%/  series                  (Array of objects)
          Y   
          |   
    0..*  |
 _________!___________________
|  Data series                |   
+-----------------------------+
| title : String              |   
| description : String  [0..1]|
| units  : String       [0..1]|
| line_width : Number   [0..1]|       (note: line_width=0 : do not show line,
| color : String        [0..1]|               however, markers may be shown).
| marker_color : Number [0..1]|
| marker_width : Number [0..1]|       (integer value)
| marker_size : Number  [0..1]|       (floating point value)
| marker_style : String [0..1]|
| range_min : Number    [0..1]|       (y-axis min/max)
| range_max : Number    [0..1]|
| show_trend : String   [0..1]|     'true' or 'false' in JSON
| trend_width : Number  [0..1]| 
| trend_color : String  [0..1]|     if empty, default same as color
| goal : Number         [0..1]|
'-----------------------------'
       1 /%\ 
         \%/  data                  Mapping of objects by key
          Y                         
          |   
    0..*  |
 _________!_____________
| Data point Object     |
+-----------------------+
| key : String          |       (key is either name or Date representation)
| value : Number        |   
| title : String  [0..1]|       Label for key, may be same as key.
| note : String   [0..1]|
| uri : String    [0..1]|
'-----------------------'

"""

from datetime import date, datetime
import json

from uu.chart.interfaces import ITimeSeriesChart, ITimeDataSequence


def isodate(dt):
    if isinstance(dt, date):
        dt = datetime(*dt.timetuple()[0:6])
    return dt.isoformat().split('.')[0] #microseconds removed


class ChartJSON(object):
    """Adapter to create JSON for use by view"""

    def __init__(self, context):
        self.context = context
    
    def _series_list(self):
        """Get all series represented as dict"""
        r = []
        for seq in self.context.series():
            series = {}
            # series data is mapping of keys to point objects
            series['data'] = dict(
                [(p['key'], p) for p in map(self._datapoint, seq.data)]
                )
            for name in (
                'title',
                'description',
                'units',
                'line_width',
                'color',
                'marker_color',
                'marker_size',
                'marker_width',
                'marker_style',
                'range_min',
                'range_max',
                'show_trend',
                'trend_width',
                'trend_color',
                'goal',
                ):
                v = getattr(seq, name, None)
                if v is not None and v != '':
                    if not (name.endswith('color') and
                            str(v).upper() == 'AUTO'):
                        series[name] = v
            r.append(series)
        return r
    
    def _datapoint(self, point):
        r = {}
        r['key'] = key = point.identity()
        if isinstance(key, date) or isinstance(key, datetime):
            r['key'] = key = isodate(key)
        r['title'] = unicode(point.identity()).title()
        r['value'] = point.value
        if point.note is not None:
            r['note'] = point.note
        if point.uri is not None:
            r['uri'] = point.uri
        return r

    def _chart(self):
        context = self.context
        r = {}
        r['series'] = self._series_list()
        if context.chart_styles:
            r['css'] = context.chart_styles
        for name in (
            'title',
            'description',
            'chart_type',
            'units',
            'goal',
            'goal_color',
            'x_label',
            'y_label',
            'legend_placement',
            'legend_location',
            'width',
            'height',
            ):
            v = getattr(self.context, name, None)
            if v is not None and v != '':
                if not (name.endswith('color') and
                        str(v).upper() == 'AUTO'):
                    r[name] = v
        if ITimeSeriesChart.providedBy(context):
            for name in ('start', 'end'):
                v = getattr(self.context, name, None)
                if v is not None:
                    r[name] = isodate(v)
            r['x_axis_type'] = 'date';
        if not self.context.show_goal and r.get('goal', None):
            del(r['goal']) #omit if show_goal is false
        if not self.context.show_goal and r.get('goal_color', None):
            del(r['goal_color']) #superfluous if show_goal is false
        return r
    
    def render(self):
        return json.dumps(self._chart(), indent=2)


class ChartJSONView(object):
    """Browser view for JSON representation of chart context"""
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
   
    def __call__(self, *args, **kwargs):
        self.request.response.setHeader('Content-type', 'application/json')
        return ChartJSON(self.context).render()


