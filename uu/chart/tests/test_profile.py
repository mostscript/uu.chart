import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.chart.tests.layers import DEFAULT_PROFILE_TESTING


class DefaultProfileTest(unittest.TestCase):
    """Test default profile's installed configuration settings"""

    layer = DEFAULT_PROFILE_TESTING
    
    FOLDERISH_TYPES = [
        'uu.chart.report',
        'uu.chart.namedseries',
        'uu.chart.timeseries',
        ]
    
    LINKABLE_TYPES = FOLDERISH_TYPES + [
        'uu.chart.data.timeseries',
        'uu.chart.data.namedseries',
        ]
    
    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
    
    def _product_fti_names(self):
        return self.LINKABLE_TYPES

    def test_browserlayer(self):
        """Test product layer interface is registered for site"""
        from uu.chart.interfaces import IChartProductLayer
        from plone.browserlayer.utils import registered_layers
        self.assertTrue(IChartProductLayer in registered_layers())
    
    def test_ftis(self):
        types_tool = getToolByName(self.portal, 'portal_types')
        typenames = types_tool.objectIds()
        for name in self._product_fti_names():
            self.assertTrue(name in typenames)
   
    def test_creation(self):
        """
        from uu.chart.tests.fixtures import CreateContentFixtures
        CreateContentFixtures(self, self.layer).create()
        """
        pass #TODO implement fixtures for content with which to test
    
    def test_tinymce_settings(self):
        tool = self.portal.portal_tinymce
        folderish = tool.containsobjects.strip().split('\n')
        linkable = tool.linkable.strip().split('\n')
        ## test for regressions from base profile, defaults still set:
        self.assertTrue(tool.styles)  # non-empty === product does not touch
        base_plone_folders = (
            'Folder', 
            'Large Plone Folder',
            'Plone Site',
            )
        for portal_type in base_plone_folders:
            self.assertIn(portal_type, folderish)
        base_plone_linkable = (
            'Topic',
            'Event',
            'File',
            'Folder', 
            'Large Plone Folder',
            'Image',
            'News Item',
            'Document',
            )
        for portal_type in base_plone_linkable:
            self.assertIn(portal_type, linkable)
        ## now test for resources added by this profile:
        for portal_type in self.FOLDERISH_TYPES:
            self.assertIn(portal_type, folderish)
        for portal_type in self.LINKABLE_TYPES:
            self.assertIn(portal_type, linkable)


