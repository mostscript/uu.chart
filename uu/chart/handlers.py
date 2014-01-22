from Products.CMFCore.utils import getToolByName


def wfinfo(context):
    wftool = getToolByName(context, 'portal_workflow')
    chain = wftool.getChainFor(context)[0]
    if 'workspace_workflow' not in chain:
        # depends on conventions of collective.teamwork or uu.qiext workflow(s)
        raise ValueError('Context does not use known workflow: %s' % chain)
    state = wftool.getStatusOf(chain, context)['review_state']
    return state, wftool


def publish(context, message=None, ignore_states=()):
    message = 'Publishing item' + (': %s' % message if message else '')
    state, wftool = wfinfo(context)
    transition = lambda o, t: wftool.doActionFor(o, t, comment=message)
    if state == 'published' or state in ignore_states:
        return
    if state == 'collaborative_editing':
        transition(context, 'end_collaboration')
    elif state not in ('pending', 'archived', 'visible'):
        transition(context, 'share')
    transition(context, 'publish')


def unpublish(context, message):
    message = 'Un-publishing item' + (': %s' % message if message else '')
    state, wftool = wfinfo(context)
    transition = lambda o, t: wftool.doActionFor(o, t, comment=message)
    if state == 'published':
        transition(context, 'return_for_editing')


def publish_children(context, message):
    for content in context.contentValues():
        publish(content, message, ignore_states=('private',))


def unpublish_children(context, message):
    for content in context.contentValues():
        unpublish(content, message)


def after_chart_transition(context, event):
    if event.action == 'publish':
        message = 'publishing all chart series components with chart.'
        publish_children(context, message=message)
    if event.action == 'return_for_editing':
        message = 'returning any published series in chart '\
                  'to the Shared with Workgroup state.'
        unpublish_children(context, message=message)


def after_report_transition(context, event):
    """Handler for (IDataReport, IActionSucceededEvent)"""
    # note, publising children (charts) will fire its own events
    # to affect items within those charts, such as series.
    if event.action == 'publish':
        message = 'publishing report components with report.'
        publish_children(context, message=message)
    if event.action == 'return_for_editing':
        message = 'returning any published components in report '\
                  'to the Shared with Workgroup state.'
        unpublish_children(context, message=message)

