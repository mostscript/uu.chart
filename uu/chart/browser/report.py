from AccessControl.SecurityManagement import getSecurityManager

from uu.chart.browser.chart import ChartView


def batch(items, b_start=0, b_size=None):
    """
    Simple batching that does not try to avoid loading objects from
    ZODB; rather, the win (for report loading via ReportJSON view),
    is from avoiding the overhead of getting data.  There is benefit
    in pre-loading the content for the report; batching should not
    try to avoid that.
    """
    if b_size is None and not b_start:
        return items  # no batching specified
    if b_start and not b_size:
        b_size = len(items) - b_start
    idx = b_start + b_size
    return items[b_start:idx]


class ReportView(ChartView):
    """Report is aggregate of charts and page (html fragment) elements"""

    PLOT_TYPES = [
        'uu.chart.timeseries',
        'uu.chart.namedseries',
        ]

    ELEMENT_TYPES = PLOT_TYPES + [
        'Document',
        ]

    def __init__(self, context, request):
        super(ReportView, self).__init__(context, request)

    def size(self):
        return len([o for o in self.chart_elements(types=self.PLOT_TYPES)])

    def chart_elements(self, types=None, b_start=0, b_size=None):
        if not hasattr(self, '_content'):
            sm = getSecurityManager()
            self._content = filter(
                lambda o: sm.checkPermission('View', o),
                filter(
                    lambda o: o.portal_type in self.ELEMENT_TYPES,
                    self.context.contentValues(),
                    )
                )
        content = self._content
        if types:
            content = filter(
                lambda o: o.portal_type in types,
                content,
                )
        return batch(content, b_start, b_size)

