
(function ($) {
    "use strict";
    
    var ns = {};

    ns.observer_installed = false;

    ns.alltrue = function (seq, callback) {
        var fn = callback || function (v) { return new Boolean(v); },
            basev = seq.map(function (v) { return fn(v); });
        return basev.reduce(function (a,b) { return a && b; }, true);
    };

    ns.measure_radio_callback = function (radio) {
        var radio = $(radio),
            path = radio.attr('value'),
            json_url = './@@list_datasets?measure=' + path;
        if (!json_url) {
            return;
        }
        $.ajax({
            url: json_url,
            success: function (responseText) {
                var data = (responseText instanceof Array) ? responseText : [],
                    dataset_select = $('select#form-widgets-dataset'),
                    existing = $('option', dataset_select);
                    existing.each(function (idx) {
                        var option = $(this);
                        if (option.attr('value') !== '--NOVALUE--') {
                            option.remove();
                        }
                    }); 
                if (dataset_select.length) {
                    data.forEach(function (pair) {
                        var value=pair[0],
                            title=pair[1],
                            option;
                        option = $('<option>' + title + '</option>').attr('value', value);
                        option.appendTo(dataset_select);
                    });
                }
            }
        });
    };

    if (MutationObserver) {

        // handle change in measure selection via widget DOM change:
        var install_measure_observer = function () {
            var swidget = $('#form-widgets-measure-input-fields')[0],
                observer;
            if (!swidget) {
                return;
            }
            observer = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    var target = mutation.target,
                        radio = $('input#form-widgets-measure-0', $(target));
                    if (!radio.length || mutation.type !== 'childList') {
                        return;
                    }
                    ns.measure_radio_callback(radio);
                });
            });
            var config = { attributes: true, childList: true, characterData: true };
            observer.observe(swidget, config);
            ns.observer_installed = true;
        };

        $(document).ready(function () {
            var body = $('body'),
                add_body_classes = [
                    'template-uu.chart.data.measureseries',
                    'portaltype-uu-chart-timeseries'
                ],
                is_add_form = ns.alltrue(
                    add_body_classes,
                    function (v) { return body.hasClass(v); }
                ),
                edit_body_classes = [
                    'template-edit',
                    'portaltype-uu-chart-data-measureseries',
                ],
                is_edit_form = ns.alltrue(
                    edit_body_classes,
                    function (v) { return body.hasClass(v); }
                ),
                radio = $('input#form-widgets-measure-0');
            if (radio.length && is_add_form) {
                ns.measure_radio_callback(radio);
            }
            if (is_edit_form || is_add_form) {
                console.log('Measure data sequence edit or add form');
                if (!ns.observer_installed) {
                    install_measure_observer();
                }
            }
        });

    } else {
        // compatibilty, likely MSIE, fallback is setInterval polling :-(
        console.log('compatibility'); //TODO implement, remove boilerplate
    }

})(jQuery);

