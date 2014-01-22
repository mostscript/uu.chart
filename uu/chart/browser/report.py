from AccessControl.SecurityManagement import getSecurityManager

from uu.chart.browser.chart import ChartView


class ReportView(ChartView):
    """Report is aggregate of charts and page (html fragment) elements"""
    
    ELEMENT_TYPES = (
        'uu.chart.timeseries',
        'uu.chart.namedseries',
        'Document',
        )

    def chart_elements(self):
        sm = getSecurityManager()
        content = filter(
            lambda o: sm.checkPermission('View', o),
            filter(
                lambda o: o.portal_type in self.ELEMENT_TYPES,
                self.context.contentValues(),
                )
            )
        return content
 
