from datetime import date, datetime
import json


def isodate(dt):
    if isinstance(dt, date):
        dt = datetime(*dt.timetuple()[0:6])
    return dt.isoformat().split('.')[0] #microseconds removed

def point_tuple(point):
    """
    Given IDataPoint object, convert point to tuple of serialized
    date and numeric value.
    """
    return (isodate(point.date), point.value)


class SeriesJSON(object):
    """Adapter for rendering series JSON for context"""
    
    def __init__(self, context):
        self.context = context
    
    def _display_info(self):
        context = self.context
        result = {}
        result['line_width'] = context.line_width or 2
        result['line_color'] = context.line_color or '#666666'
        result['marker_color'] = context.marker_color or '#666666'
        result['marker_width'] = context.marker_width or 2
        result['marker_style'] = context.marker_style or 'square'
        result['chart_styles'] = context.chart_styles or None
        result['info'] = context.info.output or None
        return result
    
    def render(self):
        context = self.context
        result = {}
        result['title'] = context.Title() or 'Measure'
        result['start'] = isodate(context.start)
        result['end'] = isodate(context.end)
        result['units'] = context.units or None
        result['goal'] = context.goal or None
        result['display'] = self._display_info()
        result['series'] = [point_tuple(p) for p in context.datapoints()]
        return json.dumps(result)


class SeriesJSONView(object):
    """Series JSON render view for ITimeSeriesChart content"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, *args, **kwargs):
        self.request.response.setHeader('Content-type', 'application/json')
        return SeriesJSON(self.context).render()


