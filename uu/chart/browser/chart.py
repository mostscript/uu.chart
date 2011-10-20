import random
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
        cache_bust = 'cache_bust=%s' % random.randint(1,2**32)
        return '%s/%s?%s' % (
            context.absolute_url(),
            '@@chart_json',
            cache_bust,
            )
    
    def divstyle(self, context=None, width=600, height=300):
        if context is None:
            context = self.context
        width = getattr(context, 'width', None) or width
        height = getattr(context, 'height', None) or height
        base = 'width:%spx;height:%spx' % (width, height)
        return base
        if width <= 270:
            return '%s;float:left' % base
        return '%s;clear:both;' % base

