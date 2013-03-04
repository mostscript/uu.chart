from datetime import date

from Acquisition import aq_base

from uu.chart.interfaces import INamedDataSequence, ITimeDataSequence


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
        return 'date' # assume ITimeDataSequence
    
    def field_value(self, point, name):
        if name == 'value':
            precision = getattr(
                aq_base(self.context),
                'display_precision',
                1,
                )
            v = getattr(point, name, None)
            v = round(v, precision) if v is not None else v
            fmt = '%%.%if' % precision
            return fmt % v if v is not None else ''
        return getattr(point, name, '')

