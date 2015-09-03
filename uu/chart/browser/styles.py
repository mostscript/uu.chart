import json

from zope.schema import getFieldsInOrder

from persistent.mapping import PersistentMapping
from plone.dexterity.utils import createContentInContainer
from plone.uuid.interfaces import IUUID
from Products.statusmessages.interfaces import IStatusMessage
from zope.annotation import IAnnotations

from uu.chart.interfaces import STYLEBOOK_TYPE, CHART_TYPES, LINESTYLE_TYPE
from uu.chart.interfaces import ILineDisplayCore
from uu.chart.interfaces import IChartStyleBook


ANNO_KEY = 'uu.chart'


def _clone_attrs(source, target, schema, exclude=()):
    for name, field in getFieldsInOrder(schema):
        if name in exclude:
            continue
        v = getattr(source, name, field.default)
        setattr(target, name, v)


def clone_line_styles(source, target):
    _clone_attrs(source, target, ILineDisplayCore)
    target.reindexObject()


def clone_chart_styles(source, target):
    """
    Clone chart styles from source to target, where either may be
    a stylebook or a chart.
    """
    _clone_attrs(
        source,
        target,
        IChartStyleBook,
        exclude=('x_label', 'y_label'),
        )
    source_lines = source.objectValues()
    target_lines = target.objectValues()
    target.reindexObject()
    for i in range(len(source_lines)):
        if i >= len(target_lines):
            break
        source_line = source_lines[i]
        target_line = target_lines[i]
        clone_line_styles(source_line, target_line)


class ReportStylesView(object):
    """View for report style control"""

    def __init__(self, context, request):
        self.context = context  # IDataReport
        self.request = request
        self.status = IStatusMessage(self.request)
        # uncached initial values:
        self.show_paste = False
        self._contained = None
        self._charts = None
        self._stylebooks = None

    def can_paste_stylebooks(self):
        if self.request.get('__cp', None) is not None:
            if self.context.cb_dataValid():
                try:
                    oblist = self.context.cb_dataItems()
                    if oblist:
                        return all(
                            map(
                                lambda o: IChartStyleBook.providedBy(o),
                                oblist,
                                )
                            )
                except KeyError:
                    pass  # object(s) in clipboard subsequently deleted
        return False

    @property
    def contained(self):
        if self._contained is None:
            self._contained = self.context.objectValues()
        return self._contained

    def charts(self):
        if self._charts is None:
            self._charts = filter(
                lambda o: o.portal_type in CHART_TYPES,
                self.contained,
                )
        return self._charts

    def stylebooks(self):
        if self._stylebooks is None:
            self._stylebooks = filter(
                lambda o: o.portal_type == STYLEBOOK_TYPE,
                self.contained,
                )
        return self._stylebooks

    def update_apply(self, *args, **kwargs):
        req = self.request
        do_bind = bool(req.get('bind-stylebook', False))
        _get = lambda name: self.context.get(name, None)
        stylebook = _get(req.get('selected-stylebook'))
        if stylebook is None:
            self.status.addStatusMessage('Unknonwn style book', type='info')
            return
        targets = [_get(name) for name in req.get('selected-charts', [])]
        if not targets:
            self.status.addStatusMessage(
                'No target charts selected to apply stylebook to.',
                type='info'
                )
            return
        for target in targets:
            clone_chart_styles(stylebook, target)  # copy styles now
            if do_bind:
                bookuid = IUUID(stylebook, None)
                target.stylebook = bookuid
        _listcharts = lambda s: ', '.join(['"%s"' % o.Title() for o in s])
        msg = 'Copied styles from' if not do_bind else 'Bound'
        self.status.addStatusMessage(
            '%s stylebook "%s" to %s charts: %s' % (
                msg, stylebook.Title(), len(targets), _listcharts(targets),
                ),
            type='info',
            )
        if do_bind:
            self.status.addStatusMessage(
                'IMPORTANT: subsequent changes to style book and line '
                'styles will propogate to the charts listed as bound '
                'to a style book.  To remove a binding, visit the Edit '
                'tab of a chart that has been bound to a style book this '
                'way.',
                type='info',
                )

    def _stylebook_title(self):
        """get next stylebook title"""
        base = u'Style book %s'
        books = self.stylebooks()
        if not books:
            return base % 1
        titles = [o.Title() for o in books]
        isdigit = lambda s: s in [str(i) for i in range(0, 10)]
        autonames = sorted(
            [title for title in titles
             if title.startswith(base[:-2]) and
             isdigit(title[-1])])
        if not autonames:
            return base % 1
        lastnum = int(autonames[-1].split(' ')[-1])
        return base % (lastnum + 1)

    def update_mimic(self, *args, **kwargs):
        req = self.request
        mimic = req.get('existing-charts', None)
        mimic = self.context.get(mimic, None)
        if not mimic:
            self.status.addStatusMessage(
                'Unable to locate existing chart',
                type='warning'
                )
            return
        linecount = len(mimic.objectIds())
        title = self._stylebook_title()
        stylebook = createContentInContainer(
            self.context,
            STYLEBOOK_TYPE,
            title=title,
            )
        for i in range(linecount):
            createContentInContainer(
                stylebook,
                LINESTYLE_TYPE,
                title=u'Line style %s' % i + 1,
                )
        clone_chart_styles(source=mimic, target=stylebook)
        self._contained = self._stylebooks = None  # un-cache now outdated
        self.status.addStatusMessage(
            'Created a new stylebook "%s" based on styles of existing chart '
            '"%s".' % (title, mimic.Title()),
            type='info',
            )

    def update(self, *args, **kwargs):
        self.show_paste = self.can_paste_stylebooks()
        req = self.request
        if req.get('REQUEST_METHOD', 'GET') == 'POST':
            if 'apply-stylebook' in req.form or 'bind-stylebook' in req.form:
                self.update_apply(*args, **kwargs)
            if 'existing-mimic' in req.form:
                self.update_mimic(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # provided by template via Five


class MeasureGroupStyles(object):
    """
    ad-hoc measure group adapter for style book enumeration,
    get/set of default.
    """

    def __init__(self, context):
        self.context = context  # IMeasureGroup

    def stylebooks(self):
        """enumerate"""
        if not getattr(self, '_stylebooks', None):
            self._stylebooks = filter(
                lambda o: IChartStyleBook.providedBy(o),
                self.context.objectValues()
                )
        return self._stylebooks

    def _save_default(self, name):
        if name in [o.getId() for o in self.stylebooks()]:
            anno = IAnnotations(self.context)
            if ANNO_KEY not in anno:
                anno[ANNO_KEY] = PersistentMapping()
            anno[ANNO_KEY]['default_stylebook'] = name

    def _default_stylebook(self):
        if not getattr(self, '_default', None):
            if not [o.getId() for o in self.stylebooks()]:
                return None
            anno = IAnnotations(self.context).get(ANNO_KEY, {})
            self._default = anno.get('default_stylebook', None)
        return self._default

    default_stylebook = property(_default_stylebook, _save_default)


class MeasureGroupStylesView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.status = IStatusMessage(self.request)
        self.adapter = MeasureGroupStyles(self.context)

    def save_default(self):
        name = self.request.get('default_stylebook')
        self.adapter.default_stylebook = name
        if self.adapter.default_stylebook == name:
            # success saving
            title = self.context[name].Title()
            msg = 'Saved default style book of: %s' % title
            self.status.addStatusMessage(msg, type='info')

    def default_stylebook(self):
        return self.adapter.default_stylebook

    def can_paste_stylebooks(self):
        if self.request.get('__cp', None) is not None:
            if self.context.cb_dataValid():
                try:
                    oblist = self.context.cb_dataItems()
                    if oblist:
                        return all(
                            map(
                                lambda o: IChartStyleBook.providedBy(o),
                                oblist,
                                )
                            )
                except KeyError:
                    pass  # object(s) in clipboard subsequently removed
        return False

    def update(self, *args, **kwargs):
        self.stylebooks = self.adapter.stylebooks()  # template enumerates...
        self.show_paste = self.can_paste_stylebooks()
        req = self.request
        if req.get('REQUEST_METHOD', 'GET') == 'POST' and 'savebtn' in req:
            # save default stylebook name
            self.save_default()

    def json(self):
        """JSON output"""
        setHeader = self.request.response.setHeader
        _info = lambda o: {'uid': IUUID(o), 'name': o.getId(), 'title': o.title}
        stylebooks = [_info(o) for o in self.stylebooks]
        result = {
            'default_stylebook': self.default_stylebook(),
            'stylebooks': stylebooks,
            'length': len(stylebooks)
        }
        msg = json.dumps(result)
        setHeader('Content-type', 'application/json')
        setHeader('Content-length', len(msg))
        return msg

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        if self.request.get('json', False):
            return self.json()
        return self.index(*args, **kwargs)  # provided by template via Five

