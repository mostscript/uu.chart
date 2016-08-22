// base namespaces
var uu = uu || {};
uu.chart = uu.chart || {};

uu.chart.populate = (function ($, ns) {

  ns.GROUP_TYPE = 'uu.formlibrary.measuregroup';
  ns.MEASURE_TYPE = 'uu.formlibrary.measure';
  ns.STYLEBOOK_TYPE = 'uu.chart.stylebook';
  ns.DATASET_TYPE = 'uu.formlibrary.setspecifier';

  ns.DEFAULT_COLORS = [
    '#393960',
    '#8AA9C9',
    '#5F9EA0',
    '#9370DB',
    '#4682B4',
    '#2E8B57',
    '#FF7F50',
    '#FFD700',
    '#DA70D6',
    '#008080'
  ];

  ns.DEFAULT_THEME = {
    linespec: ns.DEFAULT_COLORS.map(
      function (c) {
        return { color: c, marker_style: 'square' };
    })
  };

  ns.BASE = window.location.href.split('?')[0].split('@@')[0];
  ns.GROUP_QS = 'root=1&portal_type=' + ns.GROUP_TYPE;
  ns.GROUP_JSON_URL = ns.BASE + '/@@finder?' + ns.GROUP_QS;

  // module-scoped globals:
  ns.GROUPS = [];
  ns.themes = [];  // list of theme objects with uid, id, title properties
  ns.default_stylebook = null;  // to be UID of default, once loaded

  // snippets:

  ns.html = {};
  ns.html.mCheck = '<input name="selected_measures:list" ' +
           '     class="selected-measures" ' +
           '     type="checkbox" />';
  ns.html.mTitleInput = '<input class="chart_title" />';
  ns.html.chartTypeInput = String() + 
    '<select>' +
    ' <option value="runchart-line">Time-series, line</option>' +
    ' <option value="runchart-bar">Time-series, bar</option>' +
    '</select>';
  ns.html.chartGoalInput = '<input class="chart_goal" />';
  ns.html.dCheck = '<input name="selected_datasets:list" ' +
           '     class="selected-datasets" ' +
           '     type="checkbox" />';
  ns.html.dsLabelInput = '<input class="legend_label" />';
  ns.html.rowcontrol = String() +
    ' <td class="rowcontrol">' +
    '  <a href="javascript:void(0)" class="moveup" title="Move up">' +
    ' &#x25b2;' +
    '  </a><br />' +
    '  <a href="javascript:void(0)" class="movedown" title="Move down">' +
    ' &#x25bc;' +
    '  </a>' +
    ' </td>';
  ns.html.measureHeadings = String() + 
    '<tr>' +
    ' <th class="rowcontrol">&#x21c5;</th>' +
    ' <th>' +
    ' &nbsp; Measure name <br />' +
    ' &nbsp; <a href="javascript:void(0)" class="measure-selectall">[All]</a>' +    
    ' </th>' +
    ' <th>Chart title</th>' +
    ' <th>Plot type</th>' +
    ' <th>Goal</th>' +
    '</tr>';
  ns.html.datasetHeadings = String() + 
    '<tr>' +
    ' <th class="rowcontrol">&#x21c5;</th>' +
    ' <th>' +
    ' &nbsp; Data-set name <br />' +
    ' &nbsp; <a href="javascript:void(0)" class="dataset-selectall">[All]</a>' +    
    ' </th>' +
    ' <th>Legend label</th>' +
    '</tr>';

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

  ns.makeGroupInputItem = function (uid, title, path) {
    var input = $('<input name="group-choice" type="radio" />')
        .attr('value', uid)
        .attr('id', uid),
      label = $('<label />').attr('for', uid).text(title),
      li = $('<li />');
    if (path) {
      $('<span class="context">').text(' in ' + path).appendTo(label);
    }
    input.appendTo(li);
    label.appendTo(li);
    return li;
  };

  ns.displayGroupChoices = function () {
    var form = $('#group-selector'),
      target = $('#group-selector-choices');
    ns.GROUPS.forEach(function (group) {
      var path = group.path.split('/').slice(2,-1).join('/'),
        li = ns.makeGroupInputItem(group.uid, group.title, path);
      target.append(li);
    });
  };

  ns.hookupMoveButtons = function (table) {
    $('a.movedown', table).click(function () {
      var row = $($(this).parents('tr')[0]),
        next = row.next('tr');
      if (!next.length) {
        return;
      }
      row.insertAfter(next).animate(
        {'background-color': 'orange'},
        {
          duration: 650,
          complete: function () {
            $(this).css('background-color', '');
          }
        });
    });
    $('a.moveup', table).click(function () {
      var row = $($(this).parents('tr')[0]),
        prior = row.prev('tr');
      if (!prior.length) {
        return;
      }
      row.insertBefore(prior).animate(
        {'background-color': 'orange'},
        {
          duration: 650,
          complete: function () {
            $(this).css('background-color', '');
          }
        });
    });
  };

  ns.lineSwatch = function (line, idx) {
    var shape = line.marker_style || 'square',
        color = line.color || 'Auto',
        swatch = $('<div>')
          .addClass('swatch')
          .addClass(shape);
    $('<span>X</span>').appendTo(swatch);  // content, will be replaced by css
    color = (color === 'Auto') ? ns.DEFAULT_COLORS[idx] : color;
    swatch.css('color', color); 
    return swatch;
  };

  ns.previewTheme = function (chooser, val) {
    var theme,
        swatches = $('<div class="swatches">');
    theme = ns.themes.filter(function (o) { return o.uid === val; })[0];
    if (!theme) {
      theme = ns.DEFAULT_THEME;
    }
    $('.swatches', chooser).remove();
    swatches.appendTo(chooser);
    theme.linespec.map(ns.lineSwatch).forEach(function (swatch) {
      swatch.appendTo(swatches);
    });
  };

  ns.displayThemes = function (form) {
    var chooser = $('#themepicker .chooser', form),
        select;
    // Empty UI:
    chooser.empty();
    // append select:
    select = $('<select class="themechoice" name="theme">').appendTo(chooser);
    // append auto/null option:
    $('<option value="auto">No theme / automatic</option>').appendTo(select);
    // append options:
    ns.themes.forEach(function (info) {
      var option = $('<option>').appendTo(select);
      option.attr('value', info.uid);
      option.text(info.title);
    });
    // Set default, if applicable:
    if (ns.default_stylebook !== null) {
      select.val(ns.default_stylebook);
    }
    // hook up preview for load, change:
    ns.previewTheme(chooser, select.val());
    select.unbind().change(function () {
      ns.previewTheme(chooser, select.val());
    });
  };

  ns.loadThemes = function (form, groupURL) {
    var groupThemesURL = groupURL + '/@@styles?json=1',
        reportThemesURL = ns.BASE + '/@@styles?json=1',
        loadThemes = function (data) {
            ns.themes = ns.themes.concat(data.stylebooks);
            ns.displayThemes(form);
        },
        loadDefault = function (data) {
          var defaultName = data.default_stylebook || null,
              defaultStyle = (data.stylebooks || []).filter(function (o) {
                return o.name === defaultName;
              })[0] || {},
              defaultUID = defaultStyle.uid || null;
          ns.default_stylebook = defaultUID;
        };
    // Empty global (merged) state of theme enumeration, default:
    ns.themes = [];
    ns.default_stylebook = null;
    // Chained load of state via: group, report enumeration; default;
    // these calls are chained to avoid race conditions modifying ns.themes;
    // display once all are complete.
    $.ajax({
      url: groupThemesURL,
      success: function (data) {
        loadDefault(data);
        loadThemes(data);
        $.ajax({
          url: reportThemesURL,
          success: loadThemes
        });
      }
    });
  };

  ns.loadStep2 = function (groupUID) {
    var form = $('#component-selection'),
      mSel = $('#measure-selection', form),
      dSel = $('#dataset-selection', form),
      groupURL = ns.groupURL(groupUID),
      groupListingURL = groupURL + '/@@listing?portal_type=',
      reportListingURL = ns.BASE + '/@@listing?portal_type=',
      dsURL = groupListingURL + ns.DATASET_TYPE,
      measureURL = groupListingURL + ns.MEASURE_TYPE;
    if (!groupUID) {
      return;
    }
    mSel.empty();
    mSel.append($(ns.html.measureHeadings));
    dSel.empty();
    dSel.append($(ns.html.datasetHeadings));
    // trigger theme loading
    ns.loadThemes(form, groupURL);
    // load measures:
    $.ajax({
      url: measureURL,
      success: function (data) {
        var items = data.items,
          plotdefault = form.attr('data-defaultplot') || 'line',
          selectall = {};
        items.forEach(function (info) {
          var uid = info.uid,
            check = $(ns.html.mCheck).attr('value', uid),
            tr = $('<tr />'),
            rowControl = $(ns.html.rowcontrol).appendTo(tr),
            titleNode = $('<label>').text(info.title),
            titleCell = $('<td />').append(check).append(titleNode),
            titleInput = $(ns.html.mTitleInput)
              .attr('name', 'title-' + uid)
              .attr('value', info.title),
            titleInputCell = $('<td />').append(titleInput),
            chartTypeInput = $(ns.html.chartTypeInput)
              .attr('name', 'charttype-' + uid)
              .attr('value', 'runchart-' + plotdefault),
            chartTypeInputCell = $('<td />').append(chartTypeInput),
            goalInput = $(ns.html.chartGoalInput)
              .attr('name', 'goal-' + uid),
            goalCell = $('<td />').append(goalInput);
          tr.append(titleCell);
          tr.append(titleInputCell);
          tr.append(chartTypeInputCell);
          tr.append(goalCell);
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
        ns.hookupMoveButtons(mSel);
      }
    });
    // load datasets:
    $.ajax({
      url: dsURL,
      success: function (data) {
        var items = data.items;
        items.forEach(function (info) {
          var uid = info.uid,
            check = $(ns.html.dCheck).attr('value', uid),
            tr = $('<tr />'),
            rowControl = $(ns.html.rowcontrol).appendTo(tr),
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
        ns.hookupMoveButtons(dSel);
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

  ns.hookupReorderButton = function () {
    var form = $('#component-selection'),
      button = $('div.button-reorder a', form);
    button.click(function () {
      form.toggleClass('reorder');
    });
  };

  ns.hookupOneChartSelection = function () {
    var form = $('#component-selection'),
      perMeasureInput = $('#type-chart-per-measure', form),
      multiMeasureInput = $('#type-multi-measure-chart', form),
      configDiv = $('.onechart-config', form);
    multiMeasureInput.change(function () {
      form.toggleClass('onechart');
    });
    perMeasureInput.change(function () {
      form.toggleClass('onechart');
    });
  };

  $(document).ready(function () {
    ns.loadGroups();
    ns.hookupReorderButton();
    ns.hookupOneChartSelection();
  });

  return ns;

}(jQuery, uu.chart.populate || {}));
