from Acquisition import aq_parent, aq_inner
from plone.dexterity.content import Item
from plone.uuid.interfaces import IUUID
from zope.component.hooks import getSite
from zope.interface import implements

from uu.chart.data import NamedDataPoint, TimeSeriesDataPoint
from uu.chart.interfaces import IMeasureSeriesProvider
from uu.chart.interfaces import INamedSeriesChart
from uu.chart.interfaces import provider_measure, resolve_uid


class MeasureSeriesProvider(Item):
    
    implements(IMeasureSeriesProvider)
    
    def pointcls(self):
        """
        Use re-acquisition of self via catalog to ensure proper 
        acquisition wrapping, get point class to use based on the
        acquisition parent (chart) type containing this provider.
        """
        own_uid = IUUID(self)
        wrapped = resolve_uid(own_uid)
        if wrapped is None:
            return TimeSeriesDataPoint  # fallback!
        parent = aq_parent(aq_inner(self))
        if INamedSeriesChart.providedBy(parent):
            return NamedDataPoint
        return TimeSeriesDataPoint
    
    @property
    def data(self):
        measure = provider_measure(self)
        if measure is None:
            return []
        group = measure.group()
        dataset_uid = getattr(self, 'dataset', None)
        topic = resolve_uid(dataset_uid)
        if getattr(topic, 'portal_type', None) != 'Topic':
            return []  # no topic or wrong type
        infos = measure.dataset_points(topic)  # list of info dicts
        if not infos:
            return []
        pointcls = self.pointcls()
        _key = lambda info: info.get('start')  # datetime.date
        if pointcls == NamedDataPoint:
            _key = lambda info: info.get('title')
        _point = lambda info: pointcls(
            _key(info),
            info.get('value'),
            note=measure.value_note(info),
            uri=info.get('uri', None),
            )
        return map(_point, infos)

