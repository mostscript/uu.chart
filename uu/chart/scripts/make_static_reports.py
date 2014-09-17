"""
make_static_reports.py -- make static reports for all UPIQ (and only UPIQ
projects).  Purpose is use in making reference/mocks for development.

Static reports will have HTML, JavaScript, JSON, and CSS in a well-organized
directory structure:

    - index.html
    - resources/
        jqplot/
        js/
        css/
    - content/
        {PROJECT_ID}/
            index.html
            {REPORT_UID}/
                index.html
                chart-{CHART1UID}.html
                chart-{CHART2UID}.html
                report.json
                chart-{CHART1UID}.json
                chart-{CHART2UID}.json

"""

from datetime import date
import os
import shutil
import sys
import tempfile
import zipfile

from zope.component.hooks import setSite
from plone.uuid.interfaces import IUUID
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

import uu.chart
from uu.chart.interfaces import REPORT_TYPE, IBaseChart
from uu.chart.browser.serialize import ReportJSON, ChartJSON
from uu.chart.browser.chart import ChartView as BaseChartView
from uu.chart.browser.report import ReportView as BaseReportView
from uu.qiext.utils import get_projects
from uu.formlibrary.utils import local_query
from uu.formlibrary.tests import test_request


PKG_PATH = uu.chart.__path__[0]

SITENAME = 'qiteamspace'

README = """
UPIQ Data visualization examples, September 2014.

To use:

  * Firefox: visit index.html (local file)

  * Chrome:

    (a) from root of directory containing main index, run:

        $ python -m SimpleHTTPServer 8888

    (b) Visit http://localhost:8888

Notes:

  * Batching of data-fetch for report on page load does not work;
    instead ALL data is returned (from STATIC JSON file), but this
    only has the detrimental side-effect of a slight delay and some
    minor duplication.

  * Printing hyperlink via window.print() on page load is disabled for these
    examples.

""".strip()


class ChartView(BaseChartView):

    index = ViewPageTemplateFile(
        os.path.join(PKG_PATH, 'scripts', 'static_chart.pt')
        )

    def json_url(self, context=None):
        if context is None:
            context = self.context
        return '%s.json' % context.getId()  # local file URL

    def __call__(self, *args, **kwargs):
        return self.index(*args, **kwargs)


class ReportView(BaseReportView):

    index = ViewPageTemplateFile(
        os.path.join(PKG_PATH, 'scripts', 'static_chart.pt')
        )

    def __call__(self, *args, **kwargs):
        return self.index(*args, **kwargs)


# filters using substring match:
PROJECT_BLACKLIST = (
    'idaho',
    'training',
    'testing',
    'demo-',
    )


def ignore_project(project):
    for name in PROJECT_BLACKLIST:
        if name in project.getId():
            return True
    return False


def populate_resources(basepath):
    source_dir = os.path.join(PKG_PATH, 'browser', 'resources')
    dest_dir = os.path.join(basepath, 'resources')
    shutil.copytree(source_dir, dest_dir)  # incl js, css, jqplot dirs
    readme = open(os.path.join(basepath, 'README.txt'), 'w+')
    readme.write(README)
    readme.close()


def init_base(path, nozip):
    if nozip:
        if not os.path.isdir(path):
            if not os.path.exists(path):
                os.mkdir(path)
            else:
                raise RuntimeError('Path exists, not a directory')
        return path
    basepath = tempfile.mkdtemp()
    return basepath


def make_scaffolding(site, basepath):
    """directory structure and static assets"""
    populate_resources(basepath)
    os.mkdir(os.path.join(basepath, 'content'))


def make_project_directory(basepath, name):
    path = os.path.join(basepath, 'content', name)
    os.mkdir(path)
    return path


def project_reports(project, catalog):
    q = local_query(project, {}, types=(REPORT_TYPE,), depth=10)
    brains = catalog.unrestrictedSearchResults(q)
    return brains


def output_report_json(report, path):
    uid = IUUID(report)
    os.mkdir(os.path.join(path, uid))
    f = open(os.path.join(path, uid, 'report.json'), 'w+')
    f.write(ReportJSON(report).render())
    f.close()
    charts = [o for o in report.objectValues() if IBaseChart.providedBy(o)]
    for chart in charts:
        chart_name = '%s.json' % chart.getId()
        f = open(os.path.join(path, uid, chart_name), 'w+')
        f.write(ChartJSON(chart).render())
        f.close()
    return os.path.join(path, IUUID(report))


def output_request(context):
    req = test_request()
    req.form['ajax_load'] = 1
    req.form['ajax_include_head'] = 1
    return req


def output_report_html(report, path):
    req = output_request(report)
    charts = [o for o in report.objectValues() if IBaseChart.providedBy(o)]
    for chart in charts:
        chart_name = os.path.join(path, '%s.html' % chart.getId())
        view = ChartView(chart, req)
        f = open(chart_name, 'w+')
        f.write(view().encode('utf-8'))
        f.close()
    report_name = os.path.join(path, 'index.html')
    view = ReportView(report, req)
    f = open(report_name, 'w+')
    f.write(view().encode('utf-8'))
    f.close()


def make_project_reports(project, brains, path):
    result = []
    for brain in brains:
        report = brain._unrestrictedGetObject()
        report_path = output_report_json(report, path)
        result.append((report_path, report.title))
        output_report_html(report, report_path)
    return result


def make_project_index(project, project_path, reports):
    project_id = project.getId()
    project_title = project.title
    output = open(os.path.join(project_path, 'index.html'), 'w+')
    output.write(
        """
<!DOCTYPE html>
<html>
  <head>
    <title>Project reports index: %s</title>
  </head>
  <body>
    <h1>Reports / index for <em>%s</em> project</h1>
    <ul>
        """.strip() % (project_id, project_title.encode('utf-8'))
        )
    for path, title in reports:
        url = './%s' % path[len(project_path) + 1:]  # rel. dir path
        url = os.path.join(url, 'index.html')  # index page appended
        html = '<li><a href="%s">%s</a></li>\n' % (url, title)
        output.write(html)
    output.write(
        """
    </ul>
  </body>
</html>
        """.strip()
        )
    output.close()


def make_master_index(basepath, paths):
    output = open(os.path.join(basepath, 'index.html'), 'w+')
    output.write(
        """
<!DOCTYPE html>
<html>
  <head>
    <title>Reports index</title>
  </head>
  <body>
    <h1>Reports / main index</h1>
    <ul>
        """.strip()
        )
    for path, title in paths:
        url = './%s' % path[len(basepath) + 1:]  # rel. dir path
        url = os.path.join(url, 'index.html')  # index page appended
        html = '<li><a href="%s">%s</a></li>\n' % (url, title)
        output.write(html)
    output.write(
        """
    </ul>
  </body>
</html>
        """.strip()
        )
    output.close()


def copy2zip(basepath, filename):
    rootlen = len(basepath) + 1
    archive = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)
    for dirpath, dirnames, filenames in os.walk(basepath):
        for name in filenames:
            path = os.path.join(dirpath, name)
            archive.write(path, path[rootlen:])
    archive.close()


def make_zip(basepath, output_dir):
    filename = 'teamspace-reports-%s.zip' % (date.today().isoformat(),)
    output_path = os.path.join(output_dir, filename)
    copy2zip(basepath, output_path)
    

def make_reports(site, nozip, output):
    paths = []
    basepath = init_base(output, nozip)
    catalog = site.portal_catalog
    make_scaffolding(site, basepath)
    all_projects = get_projects(site)
    considered_projects = [p for p in all_projects if not ignore_project(p)]
    for project in considered_projects:
        brains = project_reports(project, catalog)
        if not brains:
            print ' -- Skipping project with no reports: %s' % project.getId()
            continue
        print '%s: %s reports' % (project.getId(), len(brains))
        path = make_project_directory(basepath, project.getId())
        paths.append((path, project.title))
        reports = make_project_reports(project, brains, path)
        make_project_index(project, path, reports)
    make_master_index(basepath, paths)
    if nozip:
        return
    make_zip(basepath, output)


def main(app, args):
    nozip = args.pop(args.index('--nozip')) if '--nozip' in args else False
    if not args:
        print 'Path argument required for output destination, not given.'
        exit(0)
    output_path = args[-1]
    site = app[SITENAME]
    setSite(site)
    make_reports(site, bool(nozip), output_path)


if __name__ == '__main__' and 'app' in locals():
    main(app, sys.argv[3:])  # noqa
