/** uu.chart.js -- javascript for rendering uu.chart chart types from
  * JSON chart API into jqplot charts.
  */

// global namspaces:
var $ = jQuery;  // For jqPlot, somehow needed for MSIE8

var uu = (function (ns, $) {
    "use strict";

    // uu namespace functions:

    /* return a new sorted array from original */
    ns.sorted = function (arr, cmp) {
        if (cmp) {
            return arr.slice().sort(cmp);
        }
        return arr.slice().sort();
    };

    ns.has_value = function (v) {
        return ($.inArray(v, [null, undefined]) !== -1);
    };

    /**  array max/min for any data-type (req. EC5 Array.prototype.reduce)
      *  prefers non-null values over any null values in sequence always
      *  for both max and min.
      */
    ns.maxcmp = function (a, b) { return ((a && (a > b)) || !b) ? a : b; };
    ns.mincmp = function (a, b) { return ((a && (a < b)) || !b) ? a : b; };
    ns.max = function (seq) { return seq.reduce(uu.maxcmp); };
    ns.min = function (seq) { return seq.reduce(uu.mincmp); };

    return ns;

}(uu || {}, jQuery));  // uu namespace, loose-augmented


uu.chart = (function (ns, $) {
    "use strict";

    ns.custom_labels = ns.custom_labels || {};

    // All keys for series, de-duplicated
    ns.uniquekeys = function (data) {
        var rset = {};      // Object as fake set-of-names type
        (data.series || []).forEach(function (s) {
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
            (s.data || []).forEach(function (pair) {
                var key = pair[0],
                    point = pair[1],
                    value = point.value;
                if (isNaN(value)) {
                    // null object {} is JSON sentinel for NaN ==> null
                    value = null;
                }
                if (data.x_axis_type === 'date') {
                    s_rep.push([(Date.parse(key) || key), value]);
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
        var min = null,
            max = null;
        (data.series || []).forEach(function (s) {
            min = (uu.has_value(s.range_min)) ? Math.min(min, s.range_min) : min;
            max = (uu.has_value(s.range_max)) ? Math.max(max, s.range_max) : max;
        });
        return [min, max];
    };

    ns.series_colors = function (data) {
        var i = 0,
            r = $.jqplot.config.defaultColors.slice(); //copy defaults
        (data.series || []).forEach(function (s) {
            // overwrite default only if color specified:
            r[i] = s.color || r[i];
            i += 1;
        });
        return r;
    };

    ns.seriesoptions = function (data) {
        var r = [];
        (data.series || []).forEach(function (s) {
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
                        formatString: "%.1f",
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
        r.max_points = uu.max(data.series.map(function (series) {
            return (series.data || []).length;
        }));
        r.width = Math.min(r.width, Math.max(5, (((chart_width * 0.8) / (r.max_points + 1)) / (r.series_length + 1))));
        return r;
    };

    /* timeseries_range(data):
     * Returns actual time-series range, not including any padding as an
     * array of [min, max] (each element is a Date object).
     */
    ns.timeseries_range = function (data) {
        var pointkey = function (a) { return a[0]; },
            min = data.start,
            max = data.end;    // start,end may be null or undefined in JSON
            
        if (!min) {
            // no explicit start date, calculate earliest date in data
            (data.series || []).forEach(function (s) {
                if (s.data instanceof Array) {
                    min = uu.min([min, uu.min(s.data.map(pointkey))]);
                }
            });
        }
        if (!max) {
            // no explicit end date, calculate latest date in data
            (data.series || []).forEach(function (s) {
                if (s.data instanceof Array) {
                    max = uu.max([max, uu.max(s.data.map(pointkey))]);
                }
            });
        }
        return [new Date(min), new Date(max)];  // RFC 2822 dates to native Date
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

    /* padded_timeseries_range():
     * Return timeseries_range with appropriate, equal padding equivalent to
     * one interval on each side of graph.
     * Intervals can be of type:
     *   millisecond, second, minute, hour, day, week, month, year
     * Intervals are array of [N, type] where N is a number, type is string.
     */
    ns.padded_timeseries_range = function (data) {
        var r = ns.timeseries_range(data),
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
        min = new Date(min.getTime());
        max = new Date(max.getTime());
        return [min, max];
    };

    ns.savelabels = function (divid, labels) {
        var k, m = {};
        ns.custom_labels[divid] = m;
        for (k in labels) {
            if (labels.hasOwnProperty(k)) {
                m[parseInt(k, 10)] = labels[k];
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
                min: (uu.has_value(range[0])) ? range[0] : undefined,
                max: (uu.has_value(range[1])) ? range[1] : undefined
            };
        if ((data.y_label) && (data.units)) {
            y_axis.label += ' ( ' + data.units + ' )';
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

    ns.fillchart = function (divid, data) {
        var legend = { show: false }, //default is none
            legend_placement = 'outsideGrid',
            goal_color = "#333333",
            x_axis = {},
            stack = false,
            series_defaults = {},
            series_colors = $.jqplot.config.defaultColors,
            interval,
            range,
            barwidth,
            line_width,
            marker_color;
        if (data.labels) {
            ns.savelabels(divid, data.labels);
        }
        if ((data.chart_type === "bar") || (data.chart_type === "stacked")) {
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
            range = ns.padded_timeseries_range(data);
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
        if ((data.legend_location) && (data.series.length > 1)) {
            if (data.legend_placement) {
                legend_placement = data.legend_placement;
            }
            legend = {
                show: true,
                location: data.legend_location,
                placement: legend_placement,
                marginTop: '2em'
            };
        }
        x_axis.label = data.x_label || undefined;
        $.jqplot.config.enablePlugins = true;
        $.jqplot(divid, ns.seriesdata(data), {
            stackSeries: stack,
            axes: {
                xaxis: x_axis,
                yaxis: ns.jqplot_yaxis_config(data)
            },
            axesDefaults: {tickOptions: {fontSize: '7pt'}},
            series: ns.seriesoptions(data),
            seriesDefaults: series_defaults,
            legend: legend,
            seriesColors : series_colors
        });
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

    ns.custom_label = function (plotid, value) {
        var k, m, lkeys, padding;
        k = value.toString();
        m = uu.chart.custom_labels[plotid];
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

    ns.loadcharts = function () {
        var new_draw;
        // copy original tick-label draw method on CanvasAxisTickRenderer
        // prototype, to make available to a monkey patched method:
        $.jqplot.CanvasAxisTickRenderer.prototype.orig_draw = $.jqplot.CanvasAxisTickRenderer.prototype.draw;

        // wrapper tick-label draw method supporting custom labels:
        new_draw = function (ctx, plot) {
            // use plot.target[0].id (plot div id), this.value for custom label
            var custom_label = ns.custom_label(plot.target[0].id, this.value);
            this.label = (custom_label !== null) ? custom_label : this.label;
            return this.orig_draw(ctx, plot);  // call orig in context of this
        };

        //monkey patch original tick-label draw method with wrapper
        $.jqplot.CanvasAxisTickRenderer.prototype.draw = new_draw;

        $('.chartdiv').each(function () {
            var div = $(this),
                json_url = $('a[type="application/json"]', div).attr('href'),
                divid = div.attr('id');
            $.ajax({
                url: json_url,
                success: function (responseText) { /*callback*/
                    ns.saved_data = ns.saved_data || {};
                    ns.saved_data[divid] = responseText;
                    ns.fillchart(divid, responseText);
                }
            });
        });
    };

    // return module namespace
    return ns;

}(uu.chart || {}, jQuery));  // uu.chart namespace, loose-augmented


jQuery('document').ready(function () {
    "use strict";

    uu.chart.loadcharts();
});

