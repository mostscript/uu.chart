import math

from Acquisition import aq_parent, aq_inner
from plone.indexer.decorator import indexer
from plone.uuid.interfaces import IUUID
from zope.interface import implements

from uu.chart.content import BaseDataSequence, filter_data, computed_attribute
from uu.chart.data import NamedDataPoint, TimeSeriesDataPoint
from uu.chart.interfaces import IMeasureSeriesProvider
from uu.chart.interfaces import INamedSeriesChart
from uu.chart.interfaces import provider_measure, resolve_uid
from uu.chart.interfaces import AGGREGATE_FUNCTIONS, AGGREGATE_LABELS


DATASET_TYPE = 'uu.formlibrary.setspecifier'


class MeasureSeriesProvider(BaseDataSequence):
    
    implements(IMeasureSeriesProvider)

    @property
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
    
    def summarize(self, points):
        items = [(point.identity(), point) for point in points]
        if not items:
            return []
        keys = zip(*items)[0]
        if len(keys) == len(set(keys)):
            return points  # no duplicate points for each key
        strategy = getattr(self, 'summarization_strategy', 'AVG')
        if strategy == 'LAST':
            return dict(items).values()  # dict() picks last on collision
        if strategy == 'FIRST':
            return dict(reversed(items)).values()
        if strategy == 'IGNORE':
            # return only points without duplicated keys
            return [v for k, v in items if keys.count(k) == 1]
        if strategy in AGGREGATE_FUNCTIONS:
            sorted_uniq_keys = []
            fn = AGGREGATE_FUNCTIONS.get(strategy)
            keymap = {}
            pointmap = {}  # original points
            for k, v in items:
                if math.isnan(v.value):
                    continue  # skip NaN values
                if k not in keymap:
                    sorted_uniq_keys.append(k)  # only once
                    keymap[k] = []
                keymap[k].append(v.value)  # sequence of 1..* values per key
                pointmap[k] = v  # last point seen for key
            label = dict(AGGREGATE_LABELS).get(strategy)
            result = []
            for k in sorted_uniq_keys:
                vcount = len(keymap[k])
                if vcount == 1:
                    result.append(pointmap[k])  # original point preserved
                else:
                    note = u'%s of %s values found.' % (label, vcount)
                    result.append(self.pointcls(k, fn(keymap[k]), note=note))
            return result
        return points  # fallback

    def filter_data(self, points):
        """Pre-summarization filtering"""
        if self.pointcls is TimeSeriesDataPoint:
            return filter_data(self, points)
        return points

    def _data(self, filtered=True, excluded=False):
        measure = provider_measure(self)
        if measure is None:
            return []
        dataset_uid = getattr(self, 'dataset', None)
        dataset = resolve_uid(dataset_uid)
        if getattr(dataset, 'portal_type', None) != DATASET_TYPE:
            return []  # no dataset or wrong type
        infos = measure.dataset_points(dataset)  # list of info dicts
        if not infos:
            return []
        _key = lambda info: info.get('start')  # datetime.date
        if self.pointcls == NamedDataPoint:
            _key = lambda info: info.get('title')
        _point = lambda info: self.pointcls(
            _key(info),
            info.get('value'),
            note=measure.value_note(info),
            uri=info.get('url', None),
            )
        all_points = map(_point, infos)
        if filtered and not excluded:
            all_points = self.filter_data(all_points)
        if excluded:
            included = self.filter_data(all_points)
            all_points = [p for p in all_points if p not in included]
        return self.summarize(all_points)

    @computed_attribute(level=1)
    def data(self):
        return self._data(filtered=True)


@indexer(IMeasureSeriesProvider)
def measure_series_references(context):
    return [context.dataset, context.measure]

