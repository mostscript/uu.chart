from plone.app.uuid.utils import uuidToCatalogBrain

from uu.chart.interfaces import INamedDataSequence, IMeasureSeriesProvider
from uu.chart.interfaces import SUMMARIZATION_STRATEGIES

STRATEGIES = dict(SUMMARIZATION_STRATEGIES)


class DataTableView(object):
    """
    View provides HTML table output for INamedDataSequence and
    ITimeDataSequence objects.
    """
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def strategy(self):
        """Summarization strategy, if applicable"""
        if IMeasureSeriesProvider.providedBy(self.context):
            strategy = self.context.summarization_strategy or 'AVG'
            return STRATEGIES.get(strategy)  # label
        return None

    def links(self):
        """Named links for context, if applicable"""
        result = []
        _get = lambda uid: uuidToCatalogBrain(uid)
        if IMeasureSeriesProvider.providedBy(self.context):
            measure_uid = self.context.measure
            dataset_uid = self.context.dataset
            if measure_uid:
                brain = _get(measure_uid)
                if brain:
                    result.append((
                        'Measure: %s' % brain.Title,
                        brain.getURL()
                        ))
            if dataset_uid:
                brain = _get(dataset_uid)
                if brain:
                    result.append((
                        'Data set: %s' % brain.Title,
                        brain.getURL()
                        ))
        return result

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

