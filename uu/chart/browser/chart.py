from plone.uuid.interfaces import IUUID


class ChartView(object):
    """Page using jqPlot to render a chart from AJAX-loaded JSON"""
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def UID(self):
        return IUUID(self.context)

    def json_url(self):
        return '%s/%s' % (self.context.absolute_url(), '@@chart_json')

