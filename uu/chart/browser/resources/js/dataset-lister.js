
(function ($) {
  "use strict";
    
  var ns = {};

  // global state
  ns.lastUrl = '';

  ns.clearDatasets = function () {
    var datasetSelect = $('select#form-widgets-dataset'),
        existing = $('option', datasetSelect);
    existing.each(function (idx) {
      var option = $(this);
      if (option.attr('value') !== '--NOVALUE--') {
        option.remove();
      }
    }); 
  };

  ns.basePath = function () {
    var base = window.location.href.split('?')[0]
          .split('/++add++')[0]
          .split('/edit')[0];
    return base;
  };

  ns.loadDatasets = function (measurePath) {
    var url = ns.basePath() + '/@@list_datasets?measure=' + measurePath,
        onData = function (response) {
          var data = (response instanceof Array) ? response : [],
              datasetSelect = $('select#form-widgets-dataset');
          ns.clearDatasets();
          if (datasetSelect.length) {
            data.forEach(function (pair) {
              var value=pair[0],
                  title=pair[1],
                  option;
              option = $('<option>' + title + '</option>').attr('value', value);
              option.appendTo(datasetSelect);
            });
          }
          ns.lastUrl = url;
        };
    $.ajax({
      url: url,
      success: onData
    });
  };

  ns.measureChanged = function () {
    var el = $(this),
        uid = el.val();
    if (uid) {
      ns.loadDatasets(uid);
    } else {
      //clear
      ns.clearDatasets();
    }
  };

  $(document).ready(function () {
    var body = $('body'),
        add_body_classes = [
          'template-uu-chart-data-measureseries',
          'portaltype-uu-chart-timeseries'
        ],
        edit_body_classes = [
          'template-edit',
          'portaltype-uu-chart-data-measureseries',
        ],
        is_add_form = add_body_classes.every(
          function (v) { return body.hasClass(v); }
        ),
        is_edit_form = edit_body_classes.every(
          function (v) { return body.hasClass(v); }
        ),
        measureInput = $('input[name="form.widgets.measure"]');
    if (measureInput.length && is_add_form) {
      // call measureChanged once as initial poke to load datasets:
      ns.measureChanged.bind(this)();
    }
    if (is_edit_form || is_add_form) {
      measureInput.on('change', function (event) {
        ns.measureChanged.bind(this)();
      });
    }
  });


})(jQuery);

