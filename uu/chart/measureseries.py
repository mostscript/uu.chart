from Acquisition import aq_parent, aq_inner
from plone.indexer.decorator import indexer
from zope.interface import implements

from uu.chart.content import BaseDataSequence, filter_data, computed_attribute
from uu.chart.data import NamedDataPoint, TimeSeriesDataPoint
from uu.chart.data import non_numeric
from uu.chart.interfaces import IMeasureSeriesProvider
from uu.chart.interfaces import INamedSeriesChart
from uu.chart.interfaces import provider_measure, resolve_uid
from uu.chart.interfaces import AGGREGATE_FUNCTIONS, AGGREGATE_LABELS


DATASET_TYPE = 'uu.formlibrary.setspecifier'


def weighted_mean(points, default_sample_size=1):
    """
    Weight mean by sample size, use default size if data points do not
    provide.
    """
    _sample_size = lambda p: getattr(p, 'sample_size', default_sample_size)
    pairs = [(point.value, _sample_size(point)) for point in points]
    total_samples = sum(zip(*pairs)[1])
    sum_weighted_values = sum([pair[0] * pair[1] for pair in pairs])
    return sum_weighted_values / float(total_samples)


class MeasureSeriesProvider(BaseDataSequence):

    implements(IMeasureSeriesProvider)

    @computed_attribute(level=0)
    def pointcls(self):
        """
        Get point class / factory based on type of parent chart.
        """
        if not hasattr(self, '_v_pointcls'):
            self._v_pointcls = TimeSeriesDataPoint
            parent = aq_parent(aq_inner(self))
            if INamedSeriesChart.providedBy(parent):
                self._v_pointcls = NamedDataPoint
        return self._v_pointcls

    def weighted_mean_summarization(self, points):
        items = [(point.identity(), point) for point in points]
        if not items:
            return []
        keys = zip(*items)[0]
        if len(keys) == len(set(keys)):
            return points  # no duplicate points for each key
        sorted_uniq_keys = []
        keymap = {}
        for key, point in items:
            if key not in keymap:
                sorted_uniq_keys.append(key)    # only once
                keymap[key] = []
            keymap[key].append(point)
        label = 'Weighted mean'
        result = []
        for key in sorted_uniq_keys:
            keypoints = keymap[key]
            vcount = len([p for p in keypoints if not non_numeric(p.value)])
            if vcount == 0:
                # special case, only NaN values must have been found,
                # so we will append a constructed NaN point:
                point = self.pointcls(
                    date=key,
                    value=float('NaN'),
                    note='All respective forms have N/A values for point',
                    )
                result.append(point)
            if vcount == 1:
                result.append(keymap[key])  # original point preserved
            elif vcount > 1:
                value = weighted_mean(
                    [p for p in keypoints if not non_numeric(p.value)]
                    )
                distribution = [
                    {
                        'value': p.value,
                        'sample_size': p.sample_size
                    }
                    for p in keypoints
                    ]
                combined_sample_size = sum([p.sample_size for p in keypoints])
                note = u'%s of %s sources (N=%s).' % (
                    label,
                    len(keypoints),
                    combined_sample_size
                    )
                aggregate_point = self.pointcls(
                    key,
                    value,
                    note=note,
                    sample_size=combined_sample_size,
                    distribution=distribution
                    )
                result.append(aggregate_point)
        return result

    def aggregate_function_summarization(self, points, strategy='AVG'):
        items = [(point.identity(), point) for point in points]
        if not items:
            return []
        sorted_uniq_keys = []
        fn = AGGREGATE_FUNCTIONS.get(strategy)
        keymap = {}
        pointmap = {}  # original points
        for k, v in items:
            if k not in keymap:
                sorted_uniq_keys.append(k)  # only once
                keymap[k] = []
            if non_numeric(v.value):
                continue  # ignore NaN values in keymap
            keymap[k].append(v)  # sequence of 1..* values per key
            pointmap[k] = v  # last point seen for key
        label = dict(AGGREGATE_LABELS).get(strategy)
        result = []
        for k in sorted_uniq_keys:
            vcount = len(keymap[k])
            if vcount == 0:
                # special case, only NaN values must have been found,
                # so we will append a constructed NaN point:
                point = self.pointcls(
                    date=k,
                    value=float('NaN'),
                    note='All respective forms have N/A values for point',
                    )
                result.append(point)
            if vcount == 1:
                result.append(pointmap[k])  # original point preserved
            elif vcount > 1:
                note = u'%s of %s values found.' % (label, vcount)
                keypoints = keymap[k]
                value = fn([p.value for p in keymap[k]])
                distribution = [
                    {
                        'value': p.value,
                        'sample_size': p.sample_size
                    }
                    for p in keypoints
                    ]
                combined_sample_size = sum(
                    [p.sample_size for p in self.filter_data(keypoints)
                     if p.sample_size is not None]
                    )
                aggregate_point = self.pointcls(
                    k,
                    value,
                    note=note,
                    sample_size=combined_sample_size,
                    distribution=distribution
                    )
                result.append(aggregate_point)
        return result

    def summarize(self, points):
        strategy = getattr(self, 'summarization_strategy', 'AVG')
        if strategy in AGGREGATE_FUNCTIONS:
            return self.aggregate_function_summarization(points, strategy)
        if strategy == 'WEIGHTED_MEAN':
            return self.weighted_mean_summarization(points)
        items = [(point.identity(), point) for point in points]
        if not items:
            return []
        keys = zip(*items)[0]
        if len(keys) == len(set(keys)):
            return points  # no duplicate points for each key
        if strategy == 'LAST':
            return dict(items).values()  # dict() picks last on collision
        if strategy == 'FIRST':
            return dict(reversed(items)).values()
        if strategy == 'IGNORE':
            # return only points without duplicated keys
            return [v for k, v in items if keys.count(k) == 1]
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
            sample_size=info.get('raw_denominator', None),
            )
        all_points = map(_point, infos)
        if filtered and not excluded:
            all_points = self.filter_data(all_points)
        if excluded:
            included = self.filter_data(all_points)
            all_points = [p for p in all_points if p not in included]
        return self.summarize(all_points)

    @computed_attribute(level=0)
    def data(self):
        return self._data(filtered=True)


@indexer(IMeasureSeriesProvider)
def measure_series_references(context):
    return [context.dataset, context.measure]
