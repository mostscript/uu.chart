import random

from plone.uuid.interfaces import IUUID
from zope.component.hooks import getSite
from zope.security import checkPermission


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
    
    def _fixedheight(self, context):
        """return fixed height in pixels or None"""
        height = getattr(context, 'height', None) or height
        height_units = getattr(context, 'height_units', None)
        if height_units == 'px':
            return height
        return None
    
    def can_manage(self):
        return checkPermission('cmf.ModifyPortalContent', self.context)

    def can_add(self):
        return checkPermission('cmf.AddPortalContent', self.context)
    
    def addable(self, typename):
        return typename in getSite().portal_types.objectIds()
    
    def divstyle(self, context=None, width=100, height=50):
        """
        Get width, possibly height styles for chart div.  Note that the
        height should be set in JavaScript (not here) when the height
        is specified as anything other than fixed pixels (that is, the
        JavaScript gets an aspect ratio W:H as array in JSON, and
        applies it when it is specified -- the JSON API should omit
        aspect ratio height is specified in pixels).
        """
        if context is None:
            context = self.context
        width = getattr(context, 'width', None) or width
        width_units = getattr(context, 'width_units', None)
        height = self._fixedheight(context)
        if width and not width_units:
            # backward compatibility for old charts, set to 100%
            width = 100
        width_units = width_units or '%'
        base = 'width:%s%s;' % (width, width_units)
        if height:
            base += 'height:%spx;' % (height,)
        return base

