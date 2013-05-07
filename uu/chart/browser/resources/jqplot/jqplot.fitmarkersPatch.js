/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

var uu = uu || {};
uu.chart = uu.chart || {};
uu.chart.fitmarkers = uu.chart.fitmarkers || {};

(function ($, ns) {
    "use strict";

    ns.behavior_loaded = false;

    ns.traverse = function (base, path, fallback) {
        var next,
            obj = fallback || undefined;
        if (base == null) {
            return fallback;
        }
        // traverse object graph by path, return undefined
        // if path remains after null, empty, undefined object
        // reference intermidary in path
        if (typeof path === 'string') {
            path = path.split('/');
        }
        next = path.shift();
        obj = base[next];
        if (!next) {
            return base;
        }
        return ns.traverse(obj, path, fallback);
    };

    // marker size in pixels
    ns.markerSize = function (plot) {
        var fallback = 9,
            mSize = function (s) {
                return ns.traverse(s, 'markerRenderer/size', fallback);
            };
        return Math.max.apply(null, plot.series.map(mSize));
    };

    // Will any line in the plot actually display point labels?
    ns.haslabels = function (plot) {
        var showlabels = Boolean(ns.traverse(
                plot,
                'options/seriesDefaults/pointLabels/show'
            )),
            seriesHasLabels = function (s) {
                var fallback = showlabels;
                if (s.pointLabels == null) {
                    return fallback;
                }
                return (s.pointLabels.show !== false);
            },
            anyTrue = function(a, b) { return Boolean(a || b); };
        if (!$.jqplot.PointLabels) {
            return false;
        }
        switch (plot.options.series.length) {
        case 0:
            return showlabels;
        case 1:
            return seriesHasLabels(plot.options.series[0]);
        default:
            return plot.options.series.map(seriesHasLabels).reduce(anyTrue);
        }
    };

    ns.additionalHeight = function (plot) {
        var elem = $('<div class="jqplot-point-label">&nbsp;</div>'),
            result = 0;
        result += ns.markerSize(plot);
        if ($.jqplot.PointLabels) {
            if (ns.haslabels(plot)) {
                // add empty label to get scrollHeight
                elem.appendTo(plot.target);
                result += elem[0].scrollHeight;
                elem.remove();
            }
        }
        return result;
    };

    ns.series_plot_refs = function (target, data, options) {
        var plot = this;
        plot.series.forEach(function (series) {
            series._plot = plot;
        });
    };

    ns.opted_in = function (plot) {
        return plot.target.hasClass('fitmarkers');
    };

    // max y value in user units for all data in plot:
    ns.max_value = function (plot) {
        var max = -Infinity;
        plot.data.forEach(
            function (series) {
                max = Math.max.apply(
                    null,
                    series.map(
                        function (point) {
                            return point[1];  // y value
                        }
                    )
                );
            }
        );
        return max;
    };

    // all series must be rendered as lines:
    ns.is_line_chart = function (plot) {
        var allTrue = function (a, b) { return Boolean(a && b); },
            seriesIsLine = function (s) {
                return (s.renderer instanceof $.jqplot.LineRenderer);
            };
        return plot.series.map(seriesIsLine).reduce(allTrue);
    };

    // Does plot qualify? Must be opted-in line plot with data near top line
    ns.qualifies = function (plot) {
        var yaxis = plot.axes.yaxis,
            additional = ns.additionalHeight(plot),
            data_range = yaxis.max - yaxis.min,
            max_data_value = ns.max_value(plot),
            max_value_distance = (yaxis.max - max_data_value) / data_range,
            max_pixel_approximation = max_value_distance * plot._height;
        // Necessary conditions to qualify for re-fitting series positioning
        // over the top-line of the graph:
        // (1) Chart is a line-chart;
        // (2) Chart is opted-in by configuration (assigned class name
        // to the chart div), then:
        // (3) is the approximate pixel offset from the top of the largest
        // data y-value sufficiently close (marker distance in px)
        // to the top line?  Pixel conversion is worst-case approximate,
        // naively assuming that grid height is 100% of plot height.
        if (!ns.is_line_chart(plot)) {
            return false;
        }
        return (ns.opted_in(plot) && max_pixel_approximation <= additional);
    };

    // pre-draw hook: overlap gird padding for qualified plots
    ns.plot_overlap_padding = function (target, data, options) {
        var plot = this,
            additionalHeight = ns.additionalHeight(plot);
        if (!ns.qualifies(plot)) {
            return;  // speific chart not eligible for behavior
        }
        plot._gridPadding = plot._gridPadding || {};
        plot._gridPadding.top = plot._gridPadding.top || 0;
        plot._gridPadding.top += additionalHeight;
    };

    // ref to original LineRenderer.setGridData used by wrapper:
    ns.origSetGridData = $.jqplot.LineRenderer.prototype.setGridData;

    // wrapper for monkey patching setGridData
    ns.setGridData = function (plot) {
        var series = this,
            additionalHeight = ns.additionalHeight(plot);
        ns.origSetGridData.call(this, plot);
        if (!ns.qualifies(plot)) {
            return;  // speific chart not eligible for behavior
        }
        series.gridData.forEach(function (point) {
            var y = point[1];
            point[1] = y + additionalHeight;
        });
        if (series._optsref) {
            // Series.prototype.draw first tries to get gridData from
            // options, which avoids a similar monkey patch to
            // $.jqplot.LineRenderer.prototype.makeGridData()
            series._optsref.gridData = series.gridData;
        }
    };

    // series pre-draw hook: series offsets, monkey patch grid data if needed
    ns.seriesDrawOverlapFixups = function (sctx, options) {
        var series = this,
            plot = this._plot,  // was bound in series_plot_refs postInitHook
            additionalHeight = ns.additionalHeight(plot),
            origTopMargin = parseInt(series.canvas._ctx.canvas.style.top, 10),
            newTopMargin = Math.max(0, origTopMargin - additionalHeight),
            eventCanvas = plot.eventCanvas;
        if (!ns.qualifies(plot)) {
            return;  // speific chart not eligible for behavior
        }
        if ($.jqplot.LineRenderer.prototype.setGridData !== ns.setGridData) {
            // monkey patch only once with wrapper to offset Y-values
            $.jqplot.LineRenderer.prototype.setGridData = ns.setGridData;
        }
        series.canvas._ctx.canvas.style.top = String(newTopMargin) + 'px';
        if (eventCanvas) {
            // adjust event canvas for plugins (e.g. highlighter)
            if (parseInt(plot.eventCanvas._ctx.canvas.style.top, 10) !== 0) {
                eventCanvas._ctx.canvas.style.top = String(newTopMargin) + 'px';
                eventCanvas._ctx.canvas.height += additionalHeight;
            }
        }
        series.canvas._ctx.canvas.height += additionalHeight;
        series._optsref = options;
    };

    ns.fixupHighlightCanvas = function () {
        var plot = this,
            series = plot.series[0],
            hlPlugin = plot.plugins.highlighter,
            hlCanvas = hlPlugin.highlightCanvas,
            additionalHeight = ns.additionalHeight(plot),
            origTopMargin = parseInt(series.canvas._ctx.canvas.style.top, 10),
            newTopMargin = Math.max(0, origTopMargin - additionalHeight),
            canvas = $(hlCanvas._ctx.canvas);
        if (ns.qualifies(plot)) {
            canvas.css('top', String(newTopMargin) + 'px');
            canvas[0].height += additionalHeight;
        }
    };

    // load behavior hooks, just once:
    ns.init_behavior = function () {
        if (!ns.behavior_loaded) {
            if ($.jqplot.Highlighter) {
                if ($.inArray(
                        $.jqplot.Highlighter.postPlotDraw,
                        $.jqplot.postDrawHooks) === -1
                    ) {
                    $.jqplot.postDrawHooks.push($.jqplot.Highlighter.postPlotDraw);
                }
                $.jqplot.postDrawHooks.push(ns.fixupHighlightCanvas);
            }
            $.jqplot.postInitHooks.push(ns.series_plot_refs);
            $.jqplot.preDrawHooks.push(ns.plot_overlap_padding);
            $.jqplot.preDrawSeriesHooks.push(ns.seriesDrawOverlapFixups);
            ns.behavior_loaded = true;
        }
    };

}(jQuery, uu.chart.fitmarkers));

