from uu.chart.interfaces import INamedDataSequence


class DataTableView(object):
    """
    View provides HTML table output for INamedDataSequence and
    ITimeDataSequence objects.
    """
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def fieldnames(self):
        return (self.keyname(), 'value', 'note', 'uri')
    
    def keyname(self):
        if INamedDataSequence.providedBy(self.context):
            return 'name'
        return 'date'  # assume ITimeDataSequence
    
    def field_value(self, point, name):
        if name == 'value':
            return self.context.display_value(point)
        if name == 'uri':
            url = getattr(point, name, '')
            if url:
                return '<a href="%s" target="_blank">%s</a>' % (url, url)
        return getattr(point, name, '')

