// jqplot.tabularLegendRenderer.js -- tabular legend renderer plugin,
// Copyright 2013, University of Utah.  
// Licensed under MIT-style license, see:
//  https://teamspace.upiq.org/trac/wiki/Copyright
// Author: Sean Upton <sean.upton@hsc.utah.edu>  for upiq.org

/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

var colortool = colortool || {};  // ns

(function ($, ns) {
    "use strict";

    // color value normalizer
    ns.normalizeColor = function (color) {
        var two = function (s,n) { return (new Array(2+1)).join(s); },
            expandHex = function (s) { return two(s[1])+two(s[2])+two(s[3]); },
            isHex = function (s) { return s[0] === '#'; };
        if (!isHex(color)) {
            return color;
        }
        return (color.length === 7) ? color : '#' + expandHex(color);
    };

    // return array of RGB decimal for 24-bit hex color code
    ns.rgb = function (color) {
        var _c = ns.normalizeColor(color),
            r = parseInt(_c.slice(1,3), 16),
            g = parseInt(_c.slice(3,5), 16),
            b = parseInt(_c.slice(5,7), 16);
        return [r, g, b];
    };

    ns.rgbaCSS = function (color, opacity) {
        var rgba = ns.rgb(color);
        rgba.push(opacity);
        return 'rgba(' + rgba.join(', ') + ')';
    };

    ns.avgLum = function (color) {
        var _add = function (a, b) { return a + b; },
            _sum = function (seq) { return seq.reduce(_add); },
            _avg = function (seq) { return _sum(seq) / seq.length; };
        return _avg(ns.rgb(color));
    };

}(jQuery, colortool));


(function ($) {
    "use strict";

    /** Class: $jqplot.tabularLegendRenderer
      * Renders a tabular legend, color coded, something like:
      *
      *     100 +---------------------------+  
      *         |       '     '     '       |
      *     75  |       '.-#-.'     '       |
      *         |     ,-'     `-,  ..---#   |
      *     50  |    #  '     '  #' '       |
      *         |       '     '     '       |
      *     25  |    @. '     '     ' .-@   |
      *         |      `-     '    ,-'      |
      *     0   +-------+`@~~~=~~@'-+-------+
      *         :   Jun : Jul : Aug : Sep   :
      *     .................................
      *     [#] :   50  : 75  : 50  :  62   :
      *     [@] :   25  :  0  :  0  :  25   :
      *     `````````````````````````````````
      */

    var ns = {};  // namespace for internal functions

    ns.LABEL_WIDTH = 120;  // px

    ns.snippets = {};

    ns.snippets.AXISCSS = String() +
        'div.jqplot-yaxis {' +
        '   margin-left:0 !important; ' +
        '   left:0 !important; ' +
        '   width:' + ns.LABEL_WIDTH + 'px !important; ' +
        '}';

    if ($.jqplot === undefined) {
        return;
    }

    ns.seriesPlotRefs = function (target, data, options) {
        var plot = this;
        plot.series.forEach(function (series) {
            series._plot = plot;
        });
    };

    $.jqplot.postInitHooks.push(ns.seriesPlotRefs);

    // post-init hook function injects fixed y-axis width CSS as
    // a style tag in the <head> of the document, specifically
    // constrained by selector to only the specific plot.
    ns.adjustLeftGridPadding = function (target, data, options) {
        var plot = this,
            getLabelSize = function (s) { return s.label.length; },
            labelSizes = plot.series.map(getLabelSize),
            maxLabelSize = Math.max.apply(null, labelSizes),
            pxApprox = (maxLabelSize * 8) + 20,
            pxAdjusted = Math.min(pxApprox, 120),
            baseLeftGridPadding = plot._gridPadding.left || 0,
            axisCss = '#' + plot.target[0].id + ' ' + ns.snippets.AXISCSS,
            styleTag = $('<style />');
        styleTag.text(axisCss);
        styleTag.appendTo($('head'));
        if (plot._gridPadding && plot._gridPadding.left != null) {
            plot._gridPadding.left = ns.LABEL_WIDTH + 10;
        }
    };

    ns.xDistances = function (gridData, gridRight, gridLeft) {
        var _x = function (coord) { return coord[0]; },
            _distance = function (pair) { return pair[1] - pair[0];},
            xCoordinates = gridData.map(_x),
            boundaries = [gridLeft||0].concat(xCoordinates, [gridRight]),
            windows = [],
            i;
        for (i=0; i<boundaries.length-1; i+=1) {
            windows.push([boundaries[i], boundaries[i+1]]);
        }
        return windows.map(_distance);
    };

    ns.cellDimensions = function (gridData, gridRight, gridLeft) {
        var left, right, multLeft, multRight, segment, cell,
            distances = ns.xDistances(gridData, gridRight, gridLeft),
            prev = gridLeft || 0,
            r = [];
        for (segment=0; segment < distances.length - 1; segment += 1) {
            multLeft = 0.5;
            multRight = 0.5;
            if (segment === 0) {
                // first segment, do not divide left side width in half
                multLeft = 1.0;
            }
            if (segment === distances.length-2) {
                // last segment, do not divide right side width in half
                multRight = 1.0;
            }
            left = distances[segment];
            right = distances[segment+1];
            cell = {};
            cell.left = prev;
            cell.width = (multLeft * left) + (multRight * right);
            r.push(cell);
            prev = cell.left + cell.width;
        }
        return r;
    };

    $.jqplot.postInitHooks.push(ns.adjustLeftGridPadding);

    // resize keycell according to content, approximate reasonable
    // width, then adjust grid to match (with replot)
    ns.adjustKeycells = function (legend) {
        var series = legend._series,
            plot = series[0]._plot,
            yaxis = plot.axes.yaxis,
            yaxisWidth = $(yaxis._elem[0]).outerWidth(),
            table = $('table.tabular-legend', plot.target),
            keycells = $('td.keycell', table),
            pxAdjusted = yaxisWidth;
        keycells.css('width', pxAdjusted);
    };

    ns.mergedColumnHeadings = function (plot) {
        var series = plot.series,
            headings = [],
            ncmp = function (a, b) { return a - b; };
        series.forEach(function (s) {
            s.data.forEach(function (pair) {
                var key = pair[0];
                if ($.inArray(key, headings) === -1) {
                    headings.push(key);
                }
            });
        });
        if (plot.axes.xaxis.renderer === $.jqplot.DateAxisRenderer) {
            headings.sort(ncmp);  // numerical order ms values
        }
        return headings;
    };

    ns.headingData = function (plot) {
        var headings = ns.mergedColumnHeadings(plot),
            data = [],
            u2p = plot.series[0]._xaxis.series_u2p;
        headings.forEach(function (k) {
            var h = {};
            if (u2p) {
                h.x = u2p(k);
            }
            h.key = k;
            h.title = k;
            if (plot.data[0][0][0] instanceof Date) {
                if (uu.chart.custom_label) {
                    h.title = uu.chart.custom_label(plot.target[0].id, k);
                } else {
                    h.title = (new Date(k)).toISOString().split('T')[0];
                }
            }
            data.push(h);
        });
        return data;
    };

    ns.mergedGridData = function (plot) {
        var series = plot.series,
            data = [],
            headings = [],
            ncmp = function (a, b) { return a - b; };
        series.forEach(function (s) {
            var rowdata = {};
            rowdata.label = s.label;  // copy label
            s.gridData.forEach(function (pair) {
                var key = pair[0],
                    yValue = pair[1];
                rowdata[key] = yValue;
                if ($.inArray(key, headings) === -1) {
                    headings.push(key);
                }
            });
            data.push(rowdata);
        });
        if (plot.axes.xaxis.renderer === $.jqplot.DateAxisRenderer) {
            headings.sort(ncmp);  // numerical order ms values
        }
        return {
            headings: headings,
            data: data
        };
    };

    $.jqplot.tabularLegendRenderer = function () {};
    $.jqplot.tabularLegendRenderer.prototype.init = function (options) {
        $.extend(true, this, options);
    };

    // draw() renders the table element using options, series data:
    $.jqplot.tabularLegendRenderer.prototype.draw = function (options) {
        var series = this._series,
            plot = series[0]._plot,
            headings = ns.headingData(plot),
            table,
            firstTh = $('<th class="keycell">&nbsp;</th>'),
            headingRow;
        this._elem = $('<table class="tabular-legend" />');
        table = this._elem;
        table.css('table-layout', 'fixed');
        headingRow = $('<tr class="legend-headings">').appendTo(table);
        firstTh.appendTo(headingRow);
        firstTh.width(125);
        headings.forEach(function (h) {
            var th = $('<th />').appendTo(headingRow);
            th.addClass(h.key);
            th.text(h.title);
        });
        series.forEach(function (s) {
            var legendkey = $('<div class="legendkey" />'),
                keytd = $('<td class="keycell">').append(legendkey),
                tr = $('<tr>').append(keytd),
                seriesdata = s.data,
                keyClr = (colortool.avgLum(s.color) > 127) ? 'black' : 'white';
            keytd.css('background-color', s.color);
            keytd.css('color', keyClr);
            legendkey.append(s.label);
            seriesdata.forEach(function (pair) {
                var v = pair[1],
                    td = $('<td class="value" />').append(v),
                    colorLight = colortool.rgbaCSS(s.color, 0.45);
                // RGBA opacity lightens background color:
                td.css('background-color', colorLight);
                td.css('color', '#444');
                td.appendTo(tr);
            });
            table.append(tr);
        });
        plot.axes.xaxis.showTicks = false;
        return this._elem;
    };

    ns.fixColumnWidths = function (plot) {
        var gridLeft = 0,
            chartdiv = plot.target,
            padLeft = plot._gridPadding.left || 0,
            padRight = plot._gridPadding.right || 10,
            gridRight = plot._plotDimensions.width - padLeft - padRight,
            headings = ns.headingData(plot),
            gridData = headings.map(function (h) { return [h.x, null]; }),
            celldim = ns.cellDimensions(gridData, gridRight, gridLeft),
            headingRow = $('tr.legend-headings', chartdiv),
            dataRows = $('tr', chartdiv).not('.legend-headings'),
            i, h, th, dim, width, padleft, padright;
        padleft = function () {
            $($('td', $(this))[1]).width(width - width*0.3333).css('padding-left', width*0.3333);
        };
        padright = function () {
            $($('td', $(this)).slice(-1)[0]).width(width - width*0.3333).css('padding-right', width*0.3333);
        };
        for (i=0; i < celldim.length; i += 1) {
            h = headings[i];
            th = $($('th', headingRow)[i+1]);
            dim = celldim[i];
            width = dim.width * 0.98;
            th.width(width);
            if (i===0) {
                dataRows.each(padleft);
                th.width(width - width*0.3333).css('padding-left', width*0.3333);
            }
            if (i===celldim.length-1) {
                dataRows.each(padright);
                th.width(width - width*0.3333).css('padding-right', width*0.3333);
            }
        }
    };

    // pack() positions the table element in the chart div:
    $.jqplot.tabularLegendRenderer.prototype.pack = function (offsets) {
        var chartdiv = $(this._elem[0].offsetParent),
            plot = this._series[0]._plot,
            divid = chartdiv.attr('id'),
            yaxis = $('div.jqplot-yaxis', chartdiv),
            pxtop = chartdiv[0].scrollHeight,
            //keywidth = yaxis.outerWidth(true),
            keytd = $('td.keycell', this._elem),
            tableHeight = this._elem.outerHeight(),
            xaxis = $('.jqplot-xaxis', chartdiv),
            headings = ns.headingData(plot),
            padLeft = plot._gridPadding.left || 0,
            padRight = plot._gridPadding.right || 10,
            gridRight = plot._plotDimensions.width - padLeft - padRight;
        // adjust key-cell (for labels) width:
        ns.adjustKeycells(this);
        // set width for each table data column based on calculated:
        ns.fixColumnWidths(plot);

        this._elem.css('width', String() + gridRight + 'px');
        this._elem.css('left', offsets.left + 0);
        this._elem.css('margin-top', pxtop - 10);
        // adjust div size, x axis label loc
        chartdiv.height(chartdiv.height() + tableHeight);
    };

})(jQuery);

