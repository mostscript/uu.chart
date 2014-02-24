import calendar
from datetime import date
import itertools

from Acquisition import aq_base
from persistent.dict import PersistentDict
from zope.globalrequest import getRequest
from zope.i18n.locales import locales, LoadLocaleError
from zope.publisher.browser import BrowserLanguages

from uu.chart.interfaces import DATE_AXIS_LABEL_CHOICES


def get_locale(request):
    """
    return locale based on HTTP request header ACCEPT_LANGUAGES.
    
    We need languages to get locale, and the locale on the request
    object gets this wrong (removes territory part of locale). This
    does essentially what ZPublisher.HTTPRequest does to load a
    locale, but with a fixed (predictable, correct) adapter.
    
    zope.publisher.browser.BrowserLangauges is an adapter with
    fixed behavior to correctly get languages.  Other adapters in
    Plone packages (e.g. PTSLanguages) may interfere with
    ZPublisher.HTTPRequest.locales loading territory, so we prefer
    a fixed adapter rather than an adapter looked-up by registration
    via IUserPreferredLanguages.
    """
    locale = None
    languages = BrowserLanguages(request).getPreferredLanguages()
    for lang in languages:
        parts = (lang.split('-') + [None, None])[:3]
        try:
            locale = locales.getLocale(*parts)
            break
        except LoadLocaleError:
            pass
    return locale


class DateLabelView(object):
    """View for managing date label aliases"""
    
    DEFAULT_FORMAT = 'locale'
    FORMAT_CHOICES = DATE_AXIS_LABEL_CHOICES  # vocab of terms w/title
    
    def __init__(self, context, request=None):
        self.context = context  # ITimeSeriesChart
        self.request = request or getRequest()
    
    def selected_format(self):
        return getattr(
            aq_base(self.context),
            'label_default',
            self.DEFAULT_FORMAT,
            )

    def included_dates(self):
        """
        Returns dates of unique date keys in use by all series data
        computed by chart.  Returns list of datetime.date.
        
        Template should use by iterating over dates and calling .isoformat()
        method for a label and key.
        """
        all_series = self.context.series()
        # we can de-dupe point dates since hash(datetime.date()) is reliable:
        q = itertools.chain(
            *[[p.identity() for p in series.data] for series in all_series]
            )
        return sorted(list(set(q)))  # iterate all unique point identity dates
    
    def date_to_formatted(self, d):
        usage = getattr(aq_base(self.context), 'label_default', 'locale')
        locname = 'en-US'  # default locale
        r_locale = get_locale(self.request)
        if r_locale:
            locname = '_'.join((r_locale.id.language, r_locale.id.territory))
        cal1 = calendar.LocaleTextCalendar(locale=(locname, 'UTF-8'))
        name = cal1.formatmonthname(*d.timetuple()[:2], width=0)  # month name
        if usage == 'abbr':
            return calendar.month_abbr[d.month]
        if usage == 'abbr+year':
            return '%s %s' % (calendar.month_abbr[d.month], d.year)
        if usage == 'name+year':
            return name
        if usage == 'name':
            return name.split(' ')[0]  # name, no year
        return d.strftime('%m/%d/%Y')
    
    def parse_date(self, d):
        if isinstance(d, date):
            return d
        d = str(d)
        return date(*map(int, (d[0:4], d[5:7], d[8:10])))
 
    def custom_label_for(self, d):
        """Given a date or JavaScript time key (as integer), get any label"""
        if isinstance(d, basestring):
            d = self.parse_date(d)
        store = getattr(aq_base(self.context), 'label_overrides', None)
        if store and d in store:
            return store.get(d)
        return ''

    def label_for(self, d):
        return self.custom_label_for(d) or self.date_to_formatted(d)

    def update(self, *args, **kwargs):
        req = self.request
        method = req.get('REQUEST_METHOD')
        if method == 'POST' and 'save.datelabels' in req.form:
            # save button clicked
            overrides = [
                (self.parse_date(k.replace('override.', '').strip()), v)
                for k, v in req.form.items()
                if k.startswith('override.')
                ]
            default = req.get('default', 'locale')
            self.context.label_overrides = PersistentDict(overrides)
            self.context.label_default = default
    
    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # template render by framework

