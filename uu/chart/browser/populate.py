import datetime
import itertools

from persistent.dict import PersistentDict
from Acquisition import aq_base
from plone.dexterity.utils import createContentInContainer
from plone.app.uuid.utils import uuidToObject
from Products.statusmessages.interfaces import IStatusMessage

from uu.chart.interfaces import TIMESERIES_TYPE, NAMEDSERIES_TYPE
from uu.chart.interfaces import DATE_AXIS_LABEL_CHOICES
from uu.chart.interfaces import MEASURESERIES_DATA
from uu.chart.interfaces import resolve_uid

from uu.chart.browser.styles import clone_chart_styles


try:
    from collective.teamwork.utils import get_workspaces
    HAS_WORKSPACES = True
except ImportError:
    try:
        from uu.qiext.utils import get_workspaces
        HAS_WORKSPACES = True
    except ImportError:
        HAS_WORKSPACES = False


class Naming(object):
    def __init__(self, title):
        self.title = title


class ReportPopulateView(object):

    DATE_LABEL_CHOICES = DATE_AXIS_LABEL_CHOICES

    def __init__(self, context, request):
        self.context = context   # report
        self.request = request
        self.status = IStatusMessage(self.request)

    def _workspace_end(self):
        if HAS_WORKSPACES:
            workspaces = get_workspaces(self.context)
            for workspace in reversed(workspaces):
                end = getattr(aq_base(workspace), 'end', None)
                if isinstance(end, datetime.date):
                    return end
        return None

    def _date(self, stamp):
        if not stamp:
            return None
        # assume ISO 8601 via type-a-date/pickadate pattern (Plone/Mockup):
        parts = stamp.strip()[:10].split('-')  # y, m, d
        parts = map(int, parts)
        return datetime.date(*parts)

    def _set_date_settings(self, chart):
        start_date = self._date(self.request.get('start-date', None))
        end_date = self._date(self.request.get('end-date', None))
        use_baseline = self.request.get('use-baseline', False)
        chart.force_crop = self.request.get('force-crop', False)
        if use_baseline:
            label = 'Baseline'
            chart.label_overrides = PersistentDict([(start_date, label)])
        if start_date:
            chart.start = start_date
        if end_date:
            chart.end = end_date

    def _measureinfo(self, uid):
        raw = self.request.form
        r = {'uid': uid}
        chart_type = raw.get('charttype-%s' % uid, 'runchart-line')
        fti = TIMESERIES_TYPE if 'runchart' in chart_type else NAMEDSERIES_TYPE
        r['portal_type'] = fti
        r['display_precision'] = 0  # default, assumes count
        if fti == TIMESERIES_TYPE:
            measure = uuidToObject(uid)
            if measure.value_type == 'percentage':
                r['range_min'] = 0
                r['range_max'] = 100
                r['display_precision'] = 1
            r['label_default'] = raw.get('datelabel-choices', 'abbr+year')
            if HAS_WORKSPACES:
                w_end = raw.get('use_workspace_end_date', [])
                if uid in w_end:
                    r['end'] = self._workspace_end()
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

    def _multi_measure_chart_info(self):
        _value = lambda key: self.request.get(key)
        measure_uid = _value('selected_measures')[0]
        defaults = self._measureinfo(measure_uid)
        extend = bool(_value('onechart-enddate'))
        chart_type = _value('onechart-type') or 'runchart-line'
        fti = TIMESERIES_TYPE if 'runchart' in chart_type else NAMEDSERIES_TYPE
        goal = _value('onechart-goal')
        defaults.update({
            'portal_type': fti,
            'title': _value('onechart-title'),
            'goal': float(goal) if goal else None,
            'show_goal': bool(goal),
            'goal_color': '#ff0000',
            'legend_placement': 'tabular',
            'point_labels': 'omit',
            'end': self._workspace_end() if extend else None,
            'chart_type': 'bar' if chart_type.endswith('bar') else 'line',
            })
        return defaults

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

    def populate(self, measures, datasets):
        """
        Given lists of measures, datasets for each, create content: one
        chart per each measure containing one series for each respective
        dataset.
        """
        charts = []
        _ignore = ('portal_type', 'uid')
        for m_info in measures:
            kw = dict((k, v) for k, v in m_info.items() if k not in _ignore)
            chart = createContentInContainer(
                self.context,
                m_info.get('portal_type', TIMESERIES_TYPE),
                **kw
                )
            self._set_date_settings(chart)
            for ds_info in datasets:
                kw = dict(
                    (k, v) for k, v in ds_info.items() if k not in _ignore
                    )
                mseries = createContentInContainer(
                    chart,
                    MEASURESERIES_DATA,
                    **kw
                    )
                mseries.measure = m_info.get('uid')
                mseries.dataset = ds_info.get('uid')
                mseries.display_precision = m_info.get('display_precision', 1)
                mseries.reindexObject()
            charts.append(chart)
        self.status.addStatusMessage(
            'Created %s charts (per-measure), containing %s series each.' % (
                len(measures),
                len(datasets),
                ),
            type='info',
            )
        return charts

    def populate_multimeasure_chart(self, measures, datasets):
        """
        Given UID lists of measures, datasets, create one multi-measure
        chart.
        """
        _value = lambda key: self.request.get(key)
        title = _value('onechart-title')
        if title is None:
            msg = u'You must provide a title for a multi-measure chart.'
            self.status.addStatusMessage(msg, type='error')
            return
        if not measures:
            msg = u'You must select at least one measure'
            self.status.addStatusMessage(msg, type='error')
            return
        kw = self._multi_measure_chart_info()
        chart = createContentInContainer(
            self.context,
            **kw
            )
        self._set_date_settings(chart)
        for measure_uid, ds_uid in itertools.product(measures, datasets):
            m_title = _value('title-%s' % measure_uid)
            ds_title = _value('title-%s' % ds_uid)
            if not m_title and ds_title:
                msg = u'You must provide legend label information for measure'\
                      u'and dataset.'
                self.status.addStatusMessage(msg, type='error')
                return
            legend_label = '%s -- %s' % (ds_title, m_title)
            series_info = {
                'title': legend_label,
                'portal_type': MEASURESERIES_DATA,
                }
            mseries = createContentInContainer(
                chart,
                **series_info
                )
            mseries.measure = measure_uid
            mseries.dataset = ds_uid
            mseries.display_precision = kw.get('display_precision', 1)
            mseries.reindexObject()
        self.status.addStatusMessage(
            'Created a multi-measure chart with %s series and %s '
            'data-sets' % (len(measures), len(datasets)),
            type='info',
            )
        return chart

    def get_theme(self):
        uid = self.request.get('theme', None)
        if uid is None:
            return None  # sentinel for defaults
        return resolve_uid(uid)

    def apply_theme(self, charts):
        """
        Get theme, if appropriate, and apply to all charts passed.
        """
        theme = self.get_theme()
        if theme is None:
            return   # use defaults, do not apply a stylebook
        for chart in charts:
            clone_chart_styles(
                theme,
                chart,
                exclude=['chart_type', 'show_goal']
                )
        self.status.addStatusMessage(
            'Applied theme "%s" to chart(s).' % theme.Title(),
            type='info'
            )

    def update(self, *args, **kwargs):
        req = self.request
        if "create.plots" in req:
            if req.get('chart-type', None) == 'multi-measure-chart':
                chart = self.populate_multimeasure_chart(
                    req.get('selected_measures', []),
                    req.get('selected_datasets', []),
                    )
                self.apply_theme([chart])
            else:
                measures, datasets = self.extract()
                if not measures:
                    return
                charts = self.populate(measures, datasets)
                self.apply_theme(charts)
            req.response.redirect(self.context.absolute_url())

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # provided by template/framework

