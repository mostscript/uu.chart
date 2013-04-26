import calendar
from datetime import date
import time
import itertools

from Acquisition import aq_base
from persistent.dict import PersistentDict
from zope.globalrequest import getRequest
from zope.i18n.locales import locales, LoadLocaleError
from zope.publisher.browser import BrowserLanguages

from uu.chart.interfaces import DATE_AXIS_LABEL_CHOICES
from utils import withtz


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
        method for a label, and view.date_to_jstime() for an integer
        key representation equivalent to JavaScript representation of
        time as an integer in ms since the epoch.
        """
        all_series = self.context.series()
        # we can de-dupe point dates since hash(datetime.date()) is reliable:
        q = itertools.chain(
            *[[p.identity() for p in series.data] for series in all_series]
            )
        return sorted(list(set(q)))  # iterate all unique point identity dates
    
    def date_to_formatted(self, d):
        usage = getattr(aq_base(self.context), 'label_default', 'locale')
        r_locale = get_locale(self.request)
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
    
    def date_to_jstime(self, d):
        d = withtz(d)  # datetime with user, site, or system tz
        return int(time.mktime(d.timetuple())) * 1000
    
    def jstime_to_date(self, t):
        t = int(t)
        return date.fromtimestamp(t / 1000)
    
    def label_for(self, d):
        """Given a date or JavaScript time key (as integer), get any label"""
        if not isinstance(d, date):
            d = self.jstime_to_date(int(d))
        store = getattr(aq_base(self.context), 'label_overrides', None)
        if store and d in store:
            return store.get(d)
        return ''
    
    def update(self, *args, **kwargs):
        req = self.request
        method = req.get('REQUEST_METHOD')
        if method == 'POST' and 'save.datelabels' in req.form:
            # save button clicked
            _datekey = lambda k: self.jstime_to_date(int(k))
            overrides = [
                (_datekey(k.replace('override.', '')), v)
                for k, v in req.form.items()
                if k.startswith('override.')
                ]
            default = req.get('default', 'locale')
            self.context.label_overrides = PersistentDict(overrides)
            self.context.label_default = default
    
    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # template render by framework

