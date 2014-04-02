/** uu.chart.js -- javascript for rendering uu.chart chart types from
  * JSON chart API into jqplot charts.
  */

/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

// global namspaces:
var $ = jQuery;  // For jqPlot, somehow needed for MSIE8

var uu = uu || {};


uu.utils = (function () {
    "use strict";

    var ns = {};

    /**
     * Is value v "empty" by common sense?
     *  - undefined OR null,
     *  - an empty object (has none of its own keys, via ES5 Object.keys()),
     *  - any non-object, non-array, non-string scalar value,
     *  - an empty string or Array,
     *  - an Array of (recursively) empty arrays?
     */
    ns.isEmpty = function (v) {
        var _alltrue = function (a, b) { return Boolean(a && b); };
        return (v === undefined || v === null) ? true : (    // null,undef
                (v instanceof String && ('' + v).length) ||  // String object
                (v instanceof Object && Object.keys(v)) ||   // Object
                (v.length === undefined),                    // non-str scalar
                (v.length === 0) ||                          // str/Array
                (v[0] instanceof Array &&
                    v.map(ns.isEmpty).reduce(_alltrue)
                )
               );
    };

    /**
     * hasValue(): is non-empty value?
     */
    ns.hasValue = function (v) {
        return (!ns.isEmpty(v));
    };

    /** 
     * any(): given a sequence, are any elements within true
     */
    ns.any = function (seq) {
        var either = function (a, b) {
                return a || b;
            };
        return seq.map(function (v) { return !!v; }).reduce(either, false);
    };

    /**
     * all(): given a sequence are all elements within true
     */
    ns.all = function (seq) {
        var both = function (a, b) {
                return a && b;
            };
        return seq.map(function (v) { return !!v; }).reduce(both, true);
    };

    /**
     *  cmp function (max a>b) for use in Array.prototype.reduce():
     */
    ns.maxcmp = function (a, b) {
        return ((ns.hasValue(a) && (a > b)) || !ns.hasValue(b)) ? a : b;
    };

    /**
     *  cmp function (min a<b) for use in Array.prototype.reduce():
     */
    ns.mincmp = function (a, b) {
        return ((ns.hasValue(a) && (a < b)) || !ns.hasValue(b)) ? a : b;
    };

    /**
      * sorted(): return a new sorted array from original
      */
    ns.sorted = function (arr, cmp) {
        return (cmp) ? arr.slice().sort(cmp) : arr.slice().sort();
    };

    /**
     * chain(): given Array of Arrays, or multiple Array arguments,
     * construct a single array of all contained members, in order.
     */
    ns.chain = function () {
        var args = Array.prototype.slice.call(arguments),
            useArray = (args.length === 1 && args[0] instanceof Array);
        args = (useArray) ? args[0] : args;
        return [].concat.apply([], args);
    };

    /**
     * make Date object from variety of values:
     *  - A null, zero, or undefined value passed returns a Date for NOW;
     *  - An integer value is assumed milliseconds since epoch;
     *  - A string value is parsed by moment.js, assumed ISO 8601.
     *    (The latter two are constructed by moment.js).
     */
    ns.date = function (v) {
        return (!v || v === 'now') ? new Date() : moment(v).toDate();
    };


    /**
     * given a function to apply to arguments, apply to either an array or
     * sequential positional arguments.
     */
    ns.exemplar = function (fn, args, fallback) {
        return (ns.isEmpty(args)) ? (fallback || null) : fn(args);
    };

    /**
     * fallback comparison application via Array.prototype.reduce()
     */
    ns.bindcmp = function (fn) {
        var applied = function (seq) {
                return seq.reduce(fn, null);
            };
        return applied;
    };

    /** 
     * Shared implementation for tendency (max, min, etc) finding, where
     * a function to apply to a sequence or and a comparison function are
     * supplied, allong with a fallback value for empty sequence.
     */
    ns.tendency = function (fn, cmp, args, fallback) {
        var isString = function (v) { return (typeof v === 'string'); },
            useArray = (args.length === 1 && args[0] instanceof Array),
            usecmp = ns.any((useArray ? args[0] : args).map(isString));
        args = (useArray) ? args[0] : args;
        return ns.exemplar((usecmp) ? ns.bindcmp(cmp) : fn, args, fallback);
    };

    /**
     * max of either Array of values or sequential positional arguments.
     * if any arguments are strings, a reduced comparison function will
     * be used in lieu of Math.max().
     */
    ns.max = function () {
        var args = Array.prototype.slice.call(arguments),
            fn = function (seq) { return Math.max.apply(null, seq); };
        return ns.tendency(fn, ns.maxcmp, args, -Infinity);
    };

    /**
     * min of either Array of values or sequential positional arguments.
     */
    ns.min = function () {
        var args = Array.prototype.slice.call(arguments),
            fn = function (seq) { return Math.min.apply(null, seq); };
        return ns.tendency(fn, ns.mincmp, args, Infinity);
    };

    return ns;

}());


uu.chart = (function (ns, $) {
    "use strict";

    var hasValue = uu.utils.hasValue,
        utils = uu.utils;

    // prefix constant, used in DOM ids, prefixing a [U]UID
    ns.DIVPREFIX = 'chartdiv-';

    ns.patched = false;

    ns.custom_labels = ns.custom_labels || {};

    // saved data keyed by div (chart) id
    ns.saved_data = ns.saved_data || {};

    // All keys for series, de-duplicated
    ns.uniquekeys = function (data) {
        var rset = {};      // Object as fake set-of-names type
        (data.series || []).forEach(function (s) {
            if (!(s.data && s.data.length)) {
                return;  // no data, ignore series
            }
            (s.data || []).forEach(function (pair) {
                var propname = pair[0];
                rset[propname] = 1;
            });
        });
        return Object.keys(rset);
    };

    ns.seriesdata = function (data) {
        var r = [];
        (data.series || []).forEach(function (s) {
            var s_rep = [];
            if (!(s.data && s.data.length)) {
                return;  // no/empty data, ignore series
            }
            (s.data || []).forEach(function (pair) {
                var key = pair[0],
                    point = pair[1],
                    value = point.value;
                //if (isNaN(value)) {
                //    // null object {} is JSON sentinel for NaN ==> null
                //    value = null;
                //}
                if (data.x_axis_type === 'date') {
                    s_rep.push([(utils.date(key) || key), value]);
                } else {
                    // named series elements for jqplot are Y-value onl
                    s_rep.push(value);
                }
            });
            r.push(s_rep);
        });
        return r;
    };

    /* min, max Y-values for chart for all respective data series */
    ns.range = function (data) {
        var min = (hasValue(data.range_min)) ? data.range_min : null,
            max = (hasValue(data.range_max)) ? data.range_max : null;
        (data.series || []).forEach(function (s) {
            if (!(s.data && s.data.length)) {
                return;  // no data for series, ignore
            }
            min = (hasValue(s.range_min)) ? Math.min(min, s.range_min) : min;
            max = (hasValue(s.range_max)) ? Math.max(max, s.range_max) : max;
        });
        return [min, max];
    };

    ns.series_colors = function (data) {
        var i = 0,
            r = $.jqplot.config.defaultColors.slice(); //copy defaults
        (data.series || []).forEach(function (s) {
            if (!(s.data && s.data.length)) {
                return;  // no data, ignore to avoid incorrect colors
            }
            // overwrite default only if color specified:
            r[i] = s.color || r[i];
            i += 1;
        });
        return r;
    };

    ns.showPointLabels = function (data, series) {
        var chartValue = data.point_labels,
            seriesValue = series.point_labels,
            chartDefault = (chartValue) ? (chartValue === 'show') : true,
            defer = (seriesValue) ? (seriesValue === 'defer') : true,
            optIn = (seriesValue === 'show');
        return (defer) ? chartDefault : optIn;
    };

    ns.seriesoptions = function (data) {
        var r = [];
        (data.series || []).forEach(function (s) {
            if (!(s.data && s.data.length)) {
                return;  // no data, no need for options
            }
            var options = {
                    markerOptions: {
                        style: s.marker_style || 'square',
                        lineWidth: s.marker_width || 2,
                        size: s.marker_size || 9,
                        color: s.marker_color || undefined
                    },
                    label: s.title || undefined,
                    breakOnNull: s.break_lines || undefined,
                    pointLabels: {
                        show: ns.showPointLabels(data, s),
                        formatString: s.display_format || "%.1f",
                        hideZeros: false
                    },
                    lineWidth: s.line_width || undefined,
                    trendline: {
                        show: s.show_trend || false,
                        label: (!s.show_trend) ? undefined : 'Trend',
                        lineWidth: (!s.show_trend) ? undefined : s.trend_width || 1,
                        color: (s.show_trend && s.trend_color) ? s.trend_color : undefined
                    },
                    formatString: s.display_format || undefined
                };
            if (s.units && options.label) {
                options.label += ' [&thinsp;' + s.units + '&thinsp;]';
            }
            if (s.show_trend === true) {
                options.trendline.label = 'Trend' + ((s.title) ? ': ' + s.title : '');
            }
            r.push(options);
        });
        return r;
    };

    ns.bar_config = function (data) {
        /* fitting algorithm: bars between 5 and 32 pixels wide, computed to fit */
        var r = {
                series_length: (data.series || []).length,
                max_points: 0,
                width: 32
            },
            chart_width = data.width || 600;
        r.max_points = Math.max(
            0,
            utils.max(
                data.series.map(
                    function (series) {
                        return (ns.seriesdata(data) || []).length;
                    })
            )
        );
        r.width = Math.min(r.width, Math.max(5, (((chart_width * 0.8) / (r.max_points + 1)) / (r.series_length + 1))));
        return r;
    };

    /** 
     * return start/end Date objects for x-axis domain crop or calculated
     * range with possible auto-crop; returns Array of Date objects.
     */
    ns.timeseriesDomain = function (data) {
        var keyFor = function (pair) { return utils.date(pair[0]); },
            // Data getters (raw and cropped):
            rawSeriesData = function (series) { return series.data || []; },
            nonNullSeriesData = function (series) {
                var cropfilter = function (pair) {
                    return (pair[1] && pair[1].value !== null);
                    };
                return (series.data || []).filter(cropfilter);
                },
            // select series data function on whether to crop or not:
            getData = (data.auto_crop) ? nonNullSeriesData : rawSeriesData,
            // All date keys as Date objects, mapped from series data:
            keys = utils.chain(data.series.map(getData)).map(keyFor),
            // All date keys as integer milliseconds:
            msKeys = keys.map(function (d) { return d.getTime(); }),
            // Earliest date key:
            minKey = msKeys.length ? utils.date(utils.min(msKeys)) : null,
            // Latest date key:
            maxKey = msKeys.length ? utils.date(utils.max(msKeys)) : null,
            // Configured start/end, if provided:
            specifiedStart = (data.start) ? utils.date(data.start) : null,
            specifiedEnd = (data.end) ? utils.date(data.end) : null,
            // Merged start/end from config, data (fallback start/end is NOW):
            start = (specifiedStart || minKey) || utils.date('now'),
            end = (specifiedEnd || maxKey) || start;
        return [start, end];
    };

    /* timeseries_interval():
     * Return interval as array of [N, type]
     *   - where N is a number, type is string.
     * Intervals can be of type:
     *   millisecond, second, minute, hour, day, week, month, year
     */
    ns.timeseries_interval = function (data) {
        var freqmap = {
                monthly: [1, 'month'],
                weekly: [1, 'week'],
                quarterly: [3, 'month'],
                yearly: [1, 'year']
            },
            supported_freq = Object.keys(freqmap);
        if ($.inArray(data.frequency, supported_freq) !== -1) {
            return freqmap[data.frequency];
        }
        // monthly default:
        return freqmap.monthly;
    };

    /**
     * paddedTimeseriesDomain():
     * Return timeseries domain start/end with appropriate, equal padding
     * equivalent to one interval on each side of graph.
     * Intervals can be of type:
     *   millisecond, second, minute, hour, day, week, month, year
     * Intervals are array of [N, type] where N is a number, type is string.
     */
    ns.paddedTimeseriesDomain = function (data) {
        var r = ns.timeseriesDomain(data),
            interval = ns.timeseries_interval(data),
            has_datediff = Boolean($.jsDate),
            valid_itypes = [
                'millisecond',
                'second',
                'minute',
                'hour',
                'day',
                'week',
                'month',
                'year'
            ],
            min = r[0],
            max = r[1];
        if (!has_datediff) {
            // needs http://sandbox.kendsnyder.com/date/?q=sandbox/date/
            return [min, max]; // bail out and tread water
        }
        min = new $.jsDate(min);
        max = new $.jsDate(max);
        if ($.inArray(interval[1], valid_itypes)) {
            min = min.add(-1 * interval[0], interval[1]);
            max = max.add(interval[0], interval[1]);
        }
        // finally convert jsDate instances back to native Date:
        min = utils.date(min.getTime());
        max = utils.date(max.getTime());
        return [min, max];
    };

    ns.savelabels = function (uid, labels) {
        var k, m = {};
        ns.custom_labels[uid] = m;
        for (k in labels) {
            if (labels.hasOwnProperty(k)) {
                m[utils.date(k).getTime()] = labels[k];
            }
        }
    };

    ns.label_color_fixups = function (data, divid, series_colors) {
        var i, points, labelselect,
            pointfn = function () {
                var point = $(this);
                if (data.chart_type === "stacked") {
                    if (parseInt(point.html(), 10) < 20) {
                        point.css('margin-left', '2.2em');
                    }
                    point.css('backgroundColor', series_colors[i]);
                    point.css('padding', '0 0.2em');
                    point.css('margin-top', '3em');
                } else {
                    point.css('color', series_colors[i]);
                }
            };
        for (i = 0; i < series_colors.length; i += 1) {
            labelselect = '#' + divid + ' .jqplot-series-' + i + '.jqplot-point-label';
            points = $(labelselect);
            points.each(pointfn);
        }
    };

    ns.jqplot_yaxis_config = function (data) {
        var range = uu.chart.range(data),
            y_axis = {
                label: data.y_label || undefined,
                min: (hasValue(range[0])) ? range[0] : undefined,
                max: (hasValue(range[1])) ? range[1] : undefined
            };
        if (data.y_label && data.units) {
            y_axis.label += ' ( ' + data.units + ' )';
        } else if (data.units) {
            y_axis.label = data.units;
        }
        if ($.jqplot.CanvasAxisLabelRenderer) {
            y_axis.labelRenderer = $.jqplot.CanvasAxisLabelRenderer;
            y_axis.labelOptions = {
                fontFamily: 'Helvetica,Arial,Sans Serif',
                fontSize: '12pt'
            };
        }
        return y_axis;
    };

    ns.cleardiv = function (div) {
        var chartdiv = $(div),
            apilink = $('a[rel="api"][type="application/json"]', chartdiv);
        chartdiv.empty();
        apilink.appendTo(chartdiv);
    };

    ns.getWrapper = function (div) {
        var _wrapper = div.parents('div.sizing'),
            hasWrapper = Boolean(_wrapper.length),
            w = '<div class="sizing" />',
            sizingWrapper = (hasWrapper) ? _wrapper : div.wrap(w).parent();
        return sizingWrapper;  // existing or new wrapper, only once
    };

    ns.adjustForLegend = function (data) {
        var leftLocations = ['w', 'sw', 'nw'],
            rightLocations = ['e', 'ne', 'se'],
            legendLeft = (leftLocations.indexOf(data.legend_location) >= 0),
            legendRight = (rightLocations.indexOf(data.legend_location) >= 0),
            legendSide = (legendLeft || legendRight),
            legendOutside = (data.legend_placement === 'outside');
        return (legendSide && legendOutside);
    };

    ns.sizeAdjust = function (outer, inner, data) {
        var legendWidth = 120;
        if (ns.adjustForLegend(data)) {
            inner.width(inner.width() - legendWidth);
        }
    };

    ns.sizeDiv = function (div, data) {
        var widthUnits = data.width_units || '%',
            heightUnits = data.height_units || '%',
            isRelativeHeight = (heightUnits !== 'px'),
            isFixedWidth = (widthUnits === 'px'),
            width = data.width,  // || (isFixedWidth) ? 600 : 100,
            height = data.height || 50,
            aspectRatio = data.aspect_ratio,
            aspectMultiplier = height / 100.0,
            wrapper = ns.getWrapper(div),
            chartWidth;
        // reset previous widths:
        div[0].style.width = '100%';
        // set width
        wrapper[0].style.width = String(width) + widthUnits;
        chartWidth = wrapper[0].clientWidth;
        if (data.series && !data.series.length) {
            // empty chart, trivial height:
            wrapper[0].style.height = '15px';
            wrapper.html('<em>No series data yet provided for plot.</em>');
        }
        if (!data.aspect_ratio || data.aspect_ratio.length != 2) {
            if (data.heightUnits === 'px') {
                wrapper[0].style.height = String(height) + 'px';
                return;
            }
        } else {
            aspectMultiplier = (
                1.0 / (data.aspect_ratio[0] / data.aspect_ratio[1])
            );
        }
        height = Math.round(aspectMultiplier * chartWidth);
        wrapper[0].style.height = String(height) + 'px';
        div[0].style.height = String(height) + 'px';
        ns.sizeAdjust(wrapper, div, data);
    };

    ns.overlayHookups = function (div, data) {
        var chart_div = $(div),
            divid = div.attr('id'),
            colorGen = new $.jqplot.ColorGenerator(),
            mkHTML = function (series, point, color) {
                var wrap = $('<div>'),
                    seriesLabel = series.title,
                    title = $('<h5>').appendTo(wrap),
                    detail = $('<dl>').appendTo(wrap),
                    fmt = series.display_format || '%.1f',
                    v = $.jqplot.sprintf(fmt, point.value);
                title.css('color', color);
                title.text(seriesLabel);
                $('<dt class="name">').appendTo(detail).text(point.title);
                if (point.value !== null) {
                    $('<dd class="value">').appendTo(detail).text('Value: ' + v);
                } else {
                    $('<dd class="value">').appendTo(detail).text('Value: n/a (null)');
                }
                $('<p class="note">').appendTo(wrap).text(point.note);
                if (point.uri) {
                    $('<a>').attr({
                        href: point.uri,
                        target: '_blank'
                        }
                    ).appendTo(wrap).text('View data source');
                }
                return wrap;
            };
        // hook up click handlers for data-points
        chart_div.bind('jqplotDataClick',
            function (ev, seriesIndex, pointIndex, datapair) {
                var series = data.series[seriesIndex],
                    pointData = series.data[pointIndex][1],
                    seriesLabel = series.title,
                    seriesColor = series.color || colorGen.get(seriesIndex),
                    overlay = new tinyOverlay.Overlay(
                        mkHTML(series, pointData, seriesColor),
                        {
                            classname: 'pointOverlay',
                            style: {
                                left: ev.pageX - 244,
                                top: ev.pageY - 3,
                                width: 220,
                                border: '2px solid ' + seriesColor,
                                'z-index': 10000
                            }
                        }
                    );
                $('.jqplot-highlighter-tooltip', chart_div).hide();
                overlay.open();
            }
        );
    };

    /**
     * plotid(): given value of div, divid, return uid of plot.
     */
    ns.plotid = function (v) {
        var divid = (typeof v === 'string') ? v : $(v).attr('id');
        return divid.replace(ns.DIVPREFIX, '');
    };

    /**
     * divfor(): given uid of chart/plot component, get its div as
     * jQuery-wrapped DOM node.
     */
    ns.divfor = function (uid) {
        var divid = ns.DIVPREFIX + uid;
        return $('#' + divid);
    };

    ns.fillchart = function (div, data) {
        var chart_div = $(div),
            uid = ns.plotid(chart_div),
            divid = div.attr('id'),
            seriesData = ns.seriesdata(data),
            legend = { show: false }, //default is none
            legend_placement = data.legend_placement || 'tabular',
            legend_location = data.legend_location || 'e',
            tabularLegend = (legend_placement === 'tabular'),
            tabularRenderer = $.jqplot.tabularLegendRenderer,
            legendRenderer = (tabularLegend) ? tabularRenderer : undefined,
            goal_color = "#333333",
            x_axis = {},
            stack = false,
            series_defaults = {},
            series_colors = $.jqplot.config.defaultColors,
            interval,
            range,
            barwidth,
            line_width,
            aspect_ratio,
            marker_color,
            display_format;
        if (!seriesData.length) {
            chart_div.html('<em>No available data at this time for plot.</em>');
            return;
        }
        display_format = data.series[0].display_format || '%.1f';
        ns.cleardiv(chart_div);
        ns.sizeDiv(chart_div, data);
        if (data.labels) {
            ns.savelabels(uid, data.labels);
        }
        if (data.chart_type === "bar" || data.chart_type === "stacked") {
            barwidth = ns.bar_config(data).width;
            if (data.chart_type === "stacked") {
                stack = true;
                barwidth = barwidth * data.series.length;
            }
            series_defaults = {
                renderer : $.jqplot.BarRenderer,
                rendererOptions : {
                    barWidth : barwidth
                }
            };
        } else {
            // line-rendering only config here:
            chart_div.addClass('fitmarkers');
            uu.chart.fitmarkers.init_behavior();
        }
        series_colors = ns.series_colors(data);
        line_width = 4;
        marker_color = null;
        if (data.goal) {
            goal_color = data.goal_color || undefined;
            series_defaults.thresholdLines = {
                lineColor: goal_color,
                labelColor: goal_color,
                yValues: [data.goal]
            };
        }
        if (data.x_axis_type === 'date') {
            interval = ns.timeseries_interval(data);
            range = ns.paddedTimeseriesDomain(data);
            // note:    jqplot padding causes problems with tick locations and
            //          intervals.  The pratical implications of this include:
            //          (1) we use updated DateAxisRenderer plugin from
            //              hg/bitbucket downloaded on 2013-03-05i (deac87b).
            //              This is to correctly parse interval string when min
            //              and/or max are specified.
            //          (2) we need to pad using same intervals as between
            //              the data points, and specify the tickInterval.
            //          (3) we may need to specify max for some unknown
            //              jqplot regression in latest plugin, as it does
            //              not appear to correctly infer (displays years out).
            //
            // also:    intervals of one month are tricky, we always want the
            //          min date to be the same day-of-month as each subsequent
            //          data point, when the interval is monthly.
            x_axis = {
                renderer: $.jqplot.DateAxisRenderer,
                tickInterval:  String(interval[0]) + ' ' + interval[1],
                min: range[0],
                max: range[1],
                tickRenderer: $.jqplot.CanvasAxisTickRenderer,
                tickOptions: {
                    angle: -65,
                    fontSize: '10pt',
                    fontFamily: 'Arial',
                    fontWeight: 'bold',
                    enableFontSupport: true,
                    textColor: '#00f'
                }
            };
        } else { /* named */
            x_axis.renderer = $.jqplot.CategoryAxisRenderer;
            x_axis.ticks = ns.uniquekeys(data);
        }
        if (legend_placement) {
            if (data.series.length > 1 || legend_placement === 'tabular') {
                legend = {
                    show: true,
                    location: legend_location,
                    placement: legend_placement,
                    marginTop: '2em',
                    renderer: legendRenderer
                };
            }
        }
        x_axis.label = data.x_label || undefined;
        $.jqplot.config.enablePlugins = true;

        chart_div.data('plot', $.jqplot(divid, seriesData, {
            stackSeries: stack,
            axes: {
                xaxis: x_axis,
                yaxis: ns.jqplot_yaxis_config(data)
            },
            highlighter: {
                show: true,
                sizeAdjust: 7.5,
                formatString: '%s, ' + display_format + ' <br />' +
                    '<em class="tip">Click data-point for details</em>'
            },
            axesDefaults: {tickOptions: {fontSize: '7pt'}},
            series: ns.seriesoptions(data),
            seriesDefaults: series_defaults,
            legend: legend,
            seriesColors : series_colors
        }));
        // hookup on-click overlays:
        ns.overlayHookups(chart_div, data);
        // finally, adjust label colors to match line colors using CSS/jQuery:
        ns.label_color_fixups(data, divid, series_colors);
    };

    ns.biggest_label = function (labels) {
        var k,
            v,
            biggest = 0;
        for (k in labels) {
            if (labels.hasOwnProperty(k)) {
                v = labels[k];
                biggest = (v.length > biggest) ? v.length : biggest;
            }
        }
        return biggest;
    };

    ns.timeseries_custom_label = function (uid, value, data) {
        var k, m, lkeys, padding,
            auto_crop = data.auto_crop || true,
            maxkey = ns.timeseriesDomain(data)[1];
        if (maxkey.getTime() < value) {
            // empty label === auto-cropped tick with no values
            return ' ';
        }
        k = value.toString();
        m = uu.chart.custom_labels[uid];
        if (!m) {
            return null;
        }
        lkeys = Object.keys(m);
        padding = ns.biggest_label(m);
        if ($.inArray(k, lkeys) !== -1) {
            return ('        ' + m[k]).slice(-1 * padding);
        }
        if (m) {
            return ' ';
        }
        return null;
    };

    ns.custom_label = function (uid, value) {
        var data = ns.saved_data[uid];
        if (data.x_axis_type === 'date') {
            return ns.timeseries_custom_label(uid, value, data);
        }
        return null;
    };


    ns.drawchart = function (uid, data) {
        var div = ns.divfor(uid);
        if (!div) {
            return;
        }
        ns.saved_data[uid] = data;
        ns.fillchart(div, data);
    };

    /**
     * redraw(): unlike loadcharts, redraw only loads from saved data,
     * primarily here to avoid any race conditions. 
     */
    ns.redraw = function () {
        Object.keys(ns.saved_data).forEach(function (uid) {
            var data = ns.saved_data[uid];
            ns.drawchart(uid, data);
        });
    };

    ns.geometric_batch = function (length) {
        var r = [],
            size = 1,
            pos = 0;
        while (size <= length) {
            r.push([pos, Math.min(size, length-pos)]);
            pos = pos + size;
            size += size;  // 1, 2, 4, 8, 16, 32,...N
        }
        return r;
    };

    ns.loadreport = function (url) {
        var total = $('.chartdiv').length,
            batch_spec = ns.geometric_batch(total);
        batch_spec.forEach(function (pair) {
            var pos = pair[0],
                size = pair[1],
                batchurl = url + '?b_size=' + size + '&b_start=' + pos;
            $.ajax({
                url: batchurl,
                success: function (response) {
                    response.forEach(function (info) {
                        var uid = info[0],      // uid key
                            data = info[1];     // chart data value
                        ns.drawchart(uid, data);
                    });
                }
            });
        });
    };

    ns.loadcharts = function () {
        var report_json_url = $('#report-core').attr('data-report-json');
        if (report_json_url) {
            ns.loadreport(report_json_url);
        } else {
            $('.chartdiv').each(function () {
                var div = $(this),
                    json_url = $('a[type="application/json"]', div).attr('href'),
                    uid = ns.plotid(div);
                    //divid = div.attr('id'),
                    //uid = divid.replace(ns.DIVPREFIX, '');
                if (ns.saved_data && ns.saved_data[uid]) {
                    // load (synchronously) from cache, not (async) from server
                    ns.fillchart(div, ns.saved_data[uid]);
                } else {
                    $.ajax({
                        url: json_url,
                        success: function (response) { /*callback*/
                            ns.drawchart(uid, response);
                        }
                    });
                }
            });
        }
    };

    ns.patch_jqplot = function () {
        var new_draw;

        if (ns.patched) {
            return;
        }

        // monkey-patch default colors of jqplot, new first-eight colors
        $.jqplot.config.defaultColors.splice(
            0,
            0,
            '#4682B4',
            '#9370DB',
            '#2E8B57',
            '#FF7F50',
            '#191970',
            '#FFD700',
            '#DA70D6',
            '#008080'
        );

        // copy original tick-label draw method on CanvasAxisTickRenderer
        // prototype, to make available to a monkey patched method:
        $.jqplot.CanvasAxisTickRenderer.prototype.orig_draw = $.jqplot.CanvasAxisTickRenderer.prototype.draw;

        // wrapper tick-label draw method supporting custom labels:
        new_draw = function (ctx, plot) {
            // use plot.target[0].id (plot div id), this.value for custom label
            var custom_label = ns.custom_label(ns.plotid(plot.target), this.value);
            this.label = (custom_label !== null) ? custom_label : this.label;
            return this.orig_draw(ctx, plot);  // call orig in context of this
        };

        //monkey patch original tick-label draw method with wrapper
        $.jqplot.CanvasAxisTickRenderer.prototype.draw = new_draw;

        ns.patched = true;  // only patch once!
    };

    $(window).resize($.debounce( 250, function () {
        ns.redraw();
    }));

    if ($.jqplot) {
        ns.patch_jqplot();
    }

    // return module namespace
    return ns;

}(uu.chart || {}, jQuery));  // uu.chart namespace, loose-augmented


jQuery('document').ready(function () {
    "use strict";

    uu.chart.loadcharts();
});

