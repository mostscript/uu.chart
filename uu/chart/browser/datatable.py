from datetime import date

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
            return 'ame'
        return 'date' # assume ITimeDataSequence
 
