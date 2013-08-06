import datetime

from Acquisition import aq_base
from plone.dexterity.utils import addContentToContainer, createContent
from plone.app.uuid.utils import uuidToObject
from Products.statusmessages.interfaces import IStatusMessage

from uu.chart.interfaces import TIMESERIES_TYPE, NAMEDSERIES_TYPE
from uu.chart.interfaces import MEASURESERIES_DATA

try:
    from uu.qiext.utils import workspace_stack
    HAS_QIEXT = True
except ImportError:
    HAS_QIEXT = False


class Naming(object):
    def __init__(self, title):
        self.title = title


class ReportPopulateView(object):

    def __init__(self, context, request):
        self.context = context   # report
        self.request = request
        self.status = IStatusMessage(self.request)

    def _measureinfo(self, uid):
        raw = self.request.form
        r = {'uid': uid}
        chart_type = raw.get('charttype-%s' % uid, 'runchart-line')
        fti = TIMESERIES_TYPE if 'runchart' in chart_type else NAMEDSERIES_TYPE
        r['portal_type'] = fti
        if fti == TIMESERIES_TYPE:
            measure = uuidToObject(uid)
            if measure.value_type == 'percentage':
                r['range_min'] = 0
                r['range_max'] = 100
            r['label_default'] = 'abbr+year'
            if HAS_QIEXT:
                w_end = raw.get('use_project_end_date', [])
                if uid in w_end:
                    workspaces = workspace_stack(self.context)
                    for workspace in reversed(workspaces):
                        end = getattr(aq_base(workspace), 'end', None)
                        if isinstance(end, datetime.date):
                            r['end'] = end
                            break
        r['chart_type'] = 'bar' if chart_type.endswith('bar') else 'line'
        goal = raw.get('goal-%s' % uid, None)
        if goal:
            r['goal'] = float(goal)
            r['show_goal'] = True
            r['goal_color'] = '#ff0000'
        if uid in raw.get('tabular_legend', []):
            r['legend_placement'] = 'tabular'
            r['point_labels'] = 'omit'
        r['title'] = raw.get('title-%s' % uid, None)
        return r

    def _datasetinfo(self, uid):
        raw = self.request.form
        r = {'uid': uid, 'portal_type': MEASURESERIES_DATA}
        r['title'] = raw.get('title-%s' % uid, None)
        return r

    def extract(self):
        # extract lists of info dicts for components to create:
        measures = []
        datasets = []
        raw = self.request.form
        dataset_uids = raw.get('selected_datasets', [])
        measure_uids = raw.get('selected_measures', [])
        if not len(dataset_uids) or not len(measure_uids):
            msg = u'You must select at least one of each: data-set, measure.'
            self.status.addStatusMessage(msg, type='info')
        else:
            measures = map(self._measureinfo, measure_uids)
            datasets = map(self._datasetinfo, dataset_uids)
        return measures, datasets

    def populate(self, charts, series):
        """Given lists of charts, series for each, create content"""
        _ignore = ('portal_type', 'uid')
        for m_info in charts:
            kw = dict((k, v) for k, v in m_info.items() if k not in _ignore)
            chart = createContent(
                m_info.get('portal_type', TIMESERIES_TYPE),
                **kw
                )
            chart = addContentToContainer(self.context, chart)
            for ds_info in series:
                kw = dict(
                    (k, v) for k, v in ds_info.items() if k not in _ignore
                    )
                mseries = createContent(MEASURESERIES_DATA, **kw)
                mseries = addContentToContainer(chart, mseries)
                mseries.measure = m_info.get('uid')
                mseries.dataset = ds_info.get('uid')
                mseries.reindexObject()
        self.status.addStatusMessage(
            'Created %s charts (per-measure), containing %s series each.' % (
                len(charts),
                len(series),
                ),
            type='info',
            )
 
    def update(self, *args, **kwargs):
        req = self.request
        if "create.plots" in req:
            charts, series = self.extract()
            if not charts:
                return
            self.populate(charts, series)
            req.response.redirect(self.context.absolute_url())
    
    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # provided by template/framework

