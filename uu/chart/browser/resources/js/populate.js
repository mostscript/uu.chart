// base namespaces
var uu = uu || {};
uu.chart = uu.chart || {};

uu.chart.populate = (function ($, ns) {

    ns.GROUP_TYPE = 'uu.formlibrary.measuregroup';
    ns.MEASURE_TYPE = 'uu.formlibrary.measure';
    ns.DATASET_TYPE = 'uu.formlibrary.setspecifier';

    ns.BASE = $('base').attr('href');
    ns.GROUP_QS = 'root=1&portal_type=' + ns.GROUP_TYPE;
    ns.GROUP_JSON_URL = ns.BASE + '/@@finder?' + ns.GROUP_QS;

    // module-scoped globals:
    ns.GROUPS = [];

    // snippets:

    ns.html = {};
    ns.html.mCheck = '<input name="selected_measures:list" ' +
                     '       class="selected-measures" ' +
                     '       type="checkbox" />';
    ns.html.mTitleInput = '<input class="chart_title" />';
    ns.html.chartTypeInput = String() + 
        '<select>' +
        ' <option value="runchart-line">Time-series, line</option>' +
        ' <option value="runchart-bar">Time-series, bar</option>' +
        '</select>';
    ns.html.chartGoalInput = '<input class="chart_goal" />';
    ns.html.dCheck = '<input name="selected_datasets:list" ' +
                     '       class="selected-datasets" ' +
                     '       type="checkbox" />';
    ns.html.dsLabelInput = '<input class="legend_label" />';
    ns.html.measureHeadings = String() + 
        '<tr>' +
        ' <th>' +
        '   &nbsp; Measure name <br />' +
        '   &nbsp; <a href="javascript:void(0)" class="measure-selectall">[All]</a>' +    
        ' </th>' +
        ' <th>Chart title</th>' +
        ' <th>Plot type</th>' +
        ' <th>Goal</th>' +
        ' <th class="center-check">' + 
        '   Use tabular legend? <br />' +
        '   <a href="javascript:void(0)" class="tabular-selectall">[All]</a>' +    
        ' </th>' +
        ' <th class="center-check">' +
        '   Extend to workspace end-date? <br />' +
        '   <a href="javascript:void(0)" class="enddate-selectall">[All]</a>' +    
        ' </th>' +
        '</tr>';
    ns.html.datasetHeadings = String() + 
        '<tr>' +
        ' <th>' +
        '   &nbsp; Data-set name <br />' +
        '   &nbsp; <a href="javascript:void(0)" class="dataset-selectall">[All]</a>' +    
        ' </th>' +
        ' <th>Legend label</th>' +
        '</tr>';
    ns.html.tabularLegendCheck = String() +
        '<input name="tabular_legend:list" type="checkbox" class="tabular-check" />';
    ns.html.workspaceEndCheck = String() +
        '<input name="use_workspace_end_date:list" type="checkbox" class="end-check" />';

    // namespaced functions:

    ns.groupURL = function (uid) {
        var result = null;
        // lame linear search
        ns.GROUPS.forEach(function (group) {
            if (group.uid === uid) {
                result = group.url;
            }
        });
        return result;
    };

    ns.makeGroupInputItem = function (uid, title) {
        var input = $('<input name="group-choice" type="radio" />')
                .attr('value', uid)
                .attr('id', uid),
            label = $('<label />').attr('for', uid).text(title),
            li = $('<li />');
        input.appendTo(li);
        label.appendTo(li);
        return li;
    };

    ns.displayGroupChoices = function () {
        var form = $('#group-selector'),
            target = $('#group-selector-choices');
        ns.GROUPS.forEach(function (group) {
            var li = ns.makeGroupInputItem(group.uid, group.title);
            target.append(li);
        });
    };

    ns.loadStep2 = function (groupUID) {
        var form = $('#component-selection'),
            mSel = $('#measure-selection', form),
            dSel = $('#dataset-selection', form),
            groupURL = ns.groupURL(groupUID),
            dsURL = groupURL + '/@@listing?portal_type=' + ns.DATASET_TYPE,
            measureURL = groupURL + '/@@listing?portal_type=' + ns.MEASURE_TYPE;
        if (!groupUID) {
            return;
        }
        mSel.empty();
        mSel.append($(ns.html.measureHeadings));
        dSel.empty();
        dSel.append($(ns.html.datasetHeadings));
        $.ajax({
            url: measureURL,
            success: function (data) {
                var items = data.items,
                    selectall = {};
                items.forEach(function (info) {
                    var uid = info.uid,
                        check = $(ns.html.mCheck).attr('value', uid),
                        tr = $('<tr />'),
                        titleNode = $('<label>').text(info.title),
                        titleCell = $('<td />').append(check).append(titleNode),
                        titleInput = $(ns.html.mTitleInput)
                            .attr('name', 'title-' + uid)
                            .attr('value', info.title),
                        titleInputCell = $('<td />').append(titleInput),
                        chartTypeInput = $(ns.html.chartTypeInput)
                            .attr('name', 'charttype-' + uid),
                        chartTypeInputCell = $('<td />').append(chartTypeInput),
                        goalInput = $(ns.html.chartGoalInput)
                            .attr('name', 'goal-' + uid),
                        goalCell = $('<td />').append(goalInput),
                        tabularLegendCheck = $(ns.html.tabularLegendCheck)
                            .attr('value', uid),
                        legendCheckCell = $('<td />')
                            .addClass('center-check')
                            .append(tabularLegendCheck),
                        workspaceEndCheck = $(ns.html.workspaceEndCheck)
                            .attr('value', uid),
                        workspaceEndCheckCell = $('<td />')
                            .addClass('center-check')
                            .append(workspaceEndCheck);
                    tr.append(titleCell);
                    tr.append(titleInputCell);
                    tr.append(chartTypeInputCell);
                    tr.append(goalCell);
                    tr.append(legendCheckCell);
                    tr.append(workspaceEndCheckCell);
                    if (info.subject && info.subject.length) {
                        info.subject.forEach(function(tag) {
                            if (tag.substring(0, 11) === 'goal_value_') {
                                goalInput.val(
                                    parseFloat(tag.split('goal_value_')[1])
                                );
                            }
                        });
                    }
                    check.click(function () {
                        tr.toggleClass('selected');
                    });
                    titleInput.change(function () {
                        $(this).addClass('modified');
                    });
                    goalInput.change(function () {
                        $(this).addClass('modified');
                    });
                    tabularLegendCheck.click(function () {
                        if (!tr.hasClass('selected')) {
                            check.click();
                        }
                    });
                    workspaceEndCheck.click(function () {
                        if (!tr.hasClass('selected')) {
                            check.click();
                        }
                    });
                    mSel.append(tr);
                });
                $('a.measure-selectall').click(function () {
                    var inputs = $('input.selected-measures');
                    if (!selectall.measures) {
                        inputs.attr('checked', 'CHECKED');
                        inputs.parents('tr').addClass('selected');
                        selectall.measures = true;
                        $(this).text('[Uncheck all]');
                    } else {
                        inputs.attr('checked', false);
                        inputs.parents('tr').removeClass('selected');
                        selectall.measures = false;
                        $(this).text('[All]');
                    }
                });
                $('a.dataset-selectall').click(function () {
                    var inputs = $('input.selected-datasets');
                    if (!selectall.datasets) {
                        inputs.attr('checked', 'CHECKED');
                        inputs.parents('tr').addClass('selected');
                        selectall.datasets = true;
                        $(this).text('[Uncheck all]');
                    } else {
                        inputs.attr('checked', false);
                        inputs.parents('tr').removeClass('selected');
                        selectall.datasets = false;
                        $(this).text('[All]');
                    }
                });
                $('a.tabular-selectall').click(function () {
                    var inputs = $('input.tabular-check');
                    if (!selectall.tabular) {
                        inputs.attr('checked', 'CHECKED');
                        if (!selectall.measures) {
                            $('a.measure-selectall').click();
                        }
                        selectall.tabular = true;
                        $(this).text('[Uncheck all]');
                    } else {
                        inputs.attr('checked', false);
                        selectall.tabular = false;
                        $(this).text('[All]');
                    }
                });
                $('a.enddate-selectall').click(function () {
                    var inputs = $('input.end-check');
                    if (!selectall.end) {
                        inputs.attr('checked', 'CHECKED');
                        if (!selectall.measures) {
                            $('a.measure-selectall').click();
                        }
                        selectall.end = true;
                        $(this).text('[Uncheck all]');
                    } else {
                        inputs.attr('checked', false);
                        selectall.end = false;
                        $(this).text('[All]');
                    }
                });
            }
        });
        $.ajax({
            url: dsURL,
            success: function (data) {
                var items = data.items;
                items.forEach(function (info) {
                    var uid = info.uid,
                        check = $(ns.html.dCheck).attr('value', uid),
                        tr = $('<tr />'),
                        titleNode = $('<label>').text(info.title),
                        titleCell = $('<td />').append(check).append(titleNode),
                        titleInput = $(ns.html.dsLabelInput)
                            .attr('name', 'title-' + uid)
                            .attr('value', info.title),
                        titleInputCell = $('<td />').append(titleInput);
                    tr.append(titleCell);
                    tr.append(titleInputCell);
                    check.click(function () {
                        tr.toggleClass('selected');
                    });
                    titleInput.change(function () {
                        $(this).addClass('modified');
                    });
                    dSel.append(tr);
                });
            }
        });
        $('#group-selector .detail').slideToggle();
        form.slideDown();
    };
   
    ns.activateGroupChoiceButton = function () {
        var form = $('#group-selector'),
            target = $('#group-selector-choices'),
            button = $('#button-select-group', form);
        button.click(function (evt) {
            var groupUID = $('input[name="group-choice"]:checked').val();
            ns.loadStep2(groupUID);
        });
    };
 
    ns.loadGroups = function () {
        $.ajax({
            url: ns.GROUP_JSON_URL,
            success: function (data) {
                var target = $('#group-selector'),
                    detail = $('.detail', target);
                ns.GROUPS = data.items;
                ns.displayGroupChoices();
                ns.activateGroupChoiceButton();
                $('#group-selector h4 a').click(function () {
                    $(this).css('cursor', 'pointer');
                    detail.slideToggle();
                });
            }
        });
    };

    $(document).ready(function () {
        ns.loadGroups();
    });

    return ns;

}(jQuery, uu.chart.populate || {}));
