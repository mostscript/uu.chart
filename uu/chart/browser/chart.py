from plone.uuid.interfaces import IUUID


class ChartView(object):
    """Page using jqPlot to render a chart from AJAX-loaded JSON"""
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
    
    def chart_elements(self):
        return [ self.context ]
    
    def UID(self, context=None):
        if context is None:
            context = self.context
        try:
            uid = IUUID(context)
        except TypeError:
            if hasattr(context, 'UID'):
                uid = context.UID()
            raise
        return uid
    
    def json_url(self, context=None):
        if context is None:
            context = self.context
        return '%s/%s' % (context.absolute_url(), '@@chart_json')

