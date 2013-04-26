from uu.chart.browser.chart import ChartView


class ReportView(ChartView):
    """Report is aggregate of charts and page (html fragment) elements"""
    
    ELEMENT_TYPES = (
        'uu.chart.timeseries',
        'uu.chart.namedseries',
        'Document',
        )

    def chart_elements(self):
        contained = self.context.contentValues()
        return [o for o in contained if o.portal_type in self.ELEMENT_TYPES]
 
