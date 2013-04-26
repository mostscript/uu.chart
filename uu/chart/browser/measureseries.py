import json

from plone.uuid.interfaces import IUUID
from zope.component.hooks import getSite
from Products.CMFCore.utils import getToolByName

from uu.formlibrary.measure.interfaces import IMeasureDefinition


DATASET_TYPE = 'uu.formlibrary.setspecifier'


class DatasetListerView(object):
    """
    A tiny API for returning JSON lists of datasets, given
    a request containing the UID or path of a measure.  Returns JSON
    array-of-arrays, where each item tuple is a UID, Title pair.
    Datasets returned are always in same group as the measure.
    
    The purpose of this is to enable the add/edit forms for a Measure
    Data Sequence to look up data-sets contingent on measure choice,
    without additional form visit/load.  Javascript should GET or POST
    to this view with the UID (string) of the measure listed
    """
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = getSite()
    
    def _datasets(self, group):
        return filter(
            lambda o: o.portal_type == DATASET_TYPE,
            group.objectValues(),
            )
    
    def ispath(self, id):
        return (
            id.startswith('/') and
            self.portal.getId() in id.split('/')
            )
    
    def __call__(self, *args, **kwargs):
        req = self.request
        req.response.setHeader('Content-type', 'application/json')
        measure_uid = self.request.get('measure', None)
        catalog = getToolByName(self.portal, 'portal_catalog')
        if self.ispath(measure_uid):
            r = catalog.search({'path': {'query': measure_uid, 'depth': 0}})
            measure_uid = r[0].UID if r else None  # value from catalog brain
        r = catalog.search({'UID': measure_uid})
        if not measure_uid or not r:
            req.response.setHeader('Content-Length', 2)
            return '[]'   # empty
        measure = r[0]._unrestrictedGetObject()
        if not IMeasureDefinition.providedBy(measure):
            req.response.setHeader('Content-Length', 2)
            return '[]'   # empty
        group = measure.__parent__
        _info = lambda o: (IUUID(o), o.Title())
        msg = json.dumps(map(_info, self._datasets(group)))
        req.response.setHeader('Content-Length', len(msg))
        return msg

