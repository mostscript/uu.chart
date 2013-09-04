// jqplot.tabularLegendRenderer.js -- tabular legend renderer plugin,
// Copyright 2013, University of Utah.  
// Licensed under MIT-style license, see:
//  https://teamspace.upiq.org/trac/wiki/Copyright
// Author: Sean Upton <sean.upton@hsc.utah.edu>  for upiq.org

/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

var colortool = colortool || {};  // ns


// auto-wrap contents of jQuery-wrapped cell in wrapper div, if:
//  (a) more than one child node, OR
//  (b) only text node
// Returns wrapper element.
function autoWrap(cell) {
    var outer = $(cell),
        contents = outer.contents(),    // all nodes
        children = outer.children(),    // element nodes only
        inner = $('<div class="content-wrap" />'),
        empty = (contents.length === 0),
        alreadyWrapped = (children.length === 1 && children[0].tagName === 'div');
    if (empty) {
        return inner.appendTo(outer);
    }
    if (alreadyWrapped) {
        return $(children[0]);  // use existing singular element
    }
    inner.appendTo(outer);
    // reparent each node within outer inside inner div
    contents.each(function () { inner.append($(this)); });
    return inner;
}

// given a specified width, wrap cell contents and adjust font-size to fit
function autofitTextSize(cell, width) {
    var tableCell = $($(cell)[0]),  // cell is singular && jquery object
        innerDiv = autoWrap(tableCell),
        fontSize = parseInt(innerDiv.css('font-size'), 10),
        minSize = 6;
    while (innerDiv[0].scrollWidth > width) {
        fontSize *= 0.95;
        if (fontSize <= minSize) {
            break;
        }
        innerDiv.css('font-size', fontSize);
    }
    return fontSize;
}


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

    var round = Math.round;

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
        if (plot.legend && plot.legend.renderer) {
            if (plot.legend.renderer instanceof $.jqplot.tabularLegendRenderer) {
                styleTag.text(axisCss);
                styleTag.appendTo($('head'));
                if (plot._gridPadding && plot._gridPadding.left != null) {
                    plot._gridPadding.left = ns.LABEL_WIDTH + 10;
                }
            }
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

    ns.syncColumnCount = function (plot, legend) {
        var xaxis = plot.axes.xaxis,
            u2p = xaxis.series_u2p,
            ticks = xaxis._ticks,
            rows = $('tr', legend._elem),
            seriesIndex = -1;
        rows.each(function () {
            var row = $(this),
                columns = $('td,th', row),
                added = 0,
                cellTag = (row.hasClass('legend-headings')) ? 'th' : 'td class="value"',
                s = plot.series[seriesIndex],
                colorLight = '#fff';
            if (s) {
                colorLight = colortool.rgbaCSS(s.color, 0.45);
            }
            while (added < (ticks.length - columns.length - 1)) {
                autoWrap(
                    $('<' + cellTag + '>&nbsp;</' + cellTag + '>')
                        .css('background-color', colorLight)
                        .appendTo(row));
                added += 1;
            }
            seriesIndex += 1;
        });
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
            th.data('key', h.key);
            th.text(h.title);
        });
        series.forEach(function (s) {
            var legendkey = $('<div class="legendkey" />'),
                keytd = $('<td class="keycell">').append(legendkey),
                tr = $('<tr>').append(keytd),
                seriesdata = {},
                keyClr = (colortool.avgLum(s.color) > 127) ? 'black' : 'white';
            s.data.forEach(function (pair) {
                var key = pair[0], value = pair[1];
                seriesdata[key] = value;
            });
            keytd.css('background-color', s.color);
            keytd.css('color', keyClr);
            legendkey.append(s.label);
            headings.forEach(function (h) {
                var v = seriesdata[h.key],
                    td = $('<td class="value" />'),
                    colorLight = colortool.rgbaCSS(s.color, 0.45);
                // RGBA opacity lightens background color:
                td.css('background-color', colorLight);
                td.css('color', '#444');
                if (v == null) {
                    td.text('--');
                    td.css('color', '#bbb');
                } else {
                    td.text($.jqplot.sprintf(s.formatString || '%.1f', v));
                }
                td.appendTo(tr);
            });
            table.append(tr);
        });
        plot.axes.xaxis.showTicks = false;
        return this._elem;
    };

    ns.fixColumnWidths = function (plot) {
        var xaxis = plot.axes.xaxis,
            u2p = xaxis.series_u2p,
            ticks = xaxis._ticks,
            gridLeft = 0,
            chartdiv = plot.target,
            padLeft = plot._gridPadding.left || 0,
            padRight = plot._gridPadding.right || 10,
            gridRight = plot._plotDimensions.width - padLeft - padRight,
            headings = ns.headingData(plot),
            dimfn = function (tick) { return [u2p(tick.value), null]; },
            gridData = ticks.slice(1).map(dimfn),
            celldim = ns.cellDimensions(gridData, gridRight, gridLeft),
            headingRow = $('tr.legend-headings', chartdiv),
            dataRows = $('tr', chartdiv).not('.legend-headings'),
            i, h, th, dim, width, padleft, padright, useWidth,
            tickCount = plot.axes.xaxis._ticks.length,
            gridWidth = $($('.jqplot-series-canvas', chartdiv)[0]).width(),
            cellWidth = gridWidth / (tickCount - 1),
            baseFontSize = Math.min(cellWidth / 2.3, 12.5);
        padleft = function () {
            var w = useWidth,
                pad = round(w * 0.5);
            $($('td', $(this))[1])
                .width(round(w))
                .css('padding-left', pad);
        };
        padright = function () {
            var w = useWidth,
                pad = round(w * 0.5);
            $($('td', $(this)).slice(-1)[0])
                .width(round(w))
                .css('padding-right', pad);
        };
        for (i=0; i < (celldim.length - 1); i += 1) {
            h = headings[i];
            th = $($('th', headingRow)[i+1]);
            dim = celldim[i];
            width = dim.width * 0.9865;
            if ($('td.value', $(dataRows[0])).length > 12) {
                width = dim.width * 0.94;
            }
            // auto-size pass 1: wrap cell contents with div
            autoWrap(th);
            if (i === 0) {
                // first cell
                if (gridData[1]) {
                    useWidth = gridData[1][0] - gridData[i][0];
                } else {
                    useWidth = width - (width * 0.3333);  // fallback
                }
                dataRows.each(padleft);
                th.width(round(useWidth) - 2)
                    .css('padding-left', round(useWidth * 0.5));
            } else if (i === celldim.length-2) {
                // last cell
                if (i !== 0) {
                    useWidth = gridData[i][0] - gridData[i-1][0];
                } else {
                    useWidth = width - (width * 0.3333);  // fallback
                }
                dataRows.each(padright);
                th.width(round(useWidth) - 2)
                    .css('padding-right', round(useWidth * 0.5));
            } else {
                // middle cells
                th.width(round(width - 1.0 - (celldim.length/26.015)));
            }
        }
        // auto-size the header cell font-size based on number of ticks:
        $('div.content-wrap', headingRow).css('font-size', baseFontSize);
        // auto-size th text pass 2: each cell in heading row consistent size:
        if (tickCount > 12) {
            $('div.content-wrap', headingRow).css(
                'font-family',
                '"Helvetica Neue","Segoe UI","Tahoma","Ubuntu Condensed"'
            );
        }
        // ad-hoc auto-size value cells based on number of cells:
        $('td.value', chartdiv).each(function () {
            autoWrap($(this)).css('font-size', baseFontSize);
        });
    };

    ns.tickIndexFor = function (plot, value) {
        var xaxis = plot.axes.xaxis,
            result = -1,
            idx = 0;
        xaxis._ticks.forEach(function (tick) {
            if (tick.value === value) {
                result = idx;
            }
            idx += 1;
        });
        return result;
    };

    ns.moveColumn = function (legend, fromIdx, toIdx) {
        var table = legend._elem,
            rows = $('tr', table);
        rows.each(function (rowIdx) {
            var row = $(this),
                cells = $('td,th', row);
            $(cells[fromIdx]).insertAfter($(cells[toIdx]));
        });
    };

    ns.columnOrderFixups = function (plot, legend) {
        var headingRow = $('tr.legend-headings', legend._elem),
            headings = $('th', headingRow),
            adjust = [];
        headings.each(function (idx) {
            var th = $(this),
                value = th.data('key'),
                tickIdx = ns.tickIndexFor(plot, value),
                filler = (tickIdx === -1),
                gap = tickIdx - idx,
                i;
            if (gap && !filler) {
                adjust.splice(0, 0, [idx, tickIdx]);
            }
        });
        adjust.forEach(function (spec) {
            ns.moveColumn(legend, spec[0], spec[1]);
        });
    };

    // pack() positions the table element in the chart div:
    $.jqplot.tabularLegendRenderer.prototype.pack = function (offsets) {
        var chartdiv = $(this._elem[0].offsetParent),
            plot = this._series[0]._plot,
            divid = chartdiv.attr('id'),
            yaxis = $('div.jqplot-yaxis', chartdiv),
            pxtop = chartdiv[0].scrollHeight,
            keytd = $('td.keycell', this._elem),
            tableHeight = this._elem.outerHeight(),
            xaxis = $('.jqplot-xaxis', chartdiv),
            headings = ns.headingData(plot),
            padLeft = plot._gridPadding.left || 0,
            padRight = plot._gridPadding.right || 10,
            gridRight = plot._plotDimensions.width - padLeft - padRight;
        // adjust number of columns to match number of ticks, which
        // can only be done in pack(), not draw() since draw of legend
        // takes place prior to draw of grid:
        ns.syncColumnCount(plot, this);
        ns.columnOrderFixups(plot, this);
        // adjust key-cell (for labels) width:
        ns.adjustKeycells(this);
        // set width for each table data column based on calculated:
        ns.fixColumnWidths(plot);
        this._elem.css('width', String() + gridRight + 'px');
        this._elem.css('left', offsets.left + 0);
        this._elem.css('margin-top', pxtop - 10);
        // adjust div size, x axis label loc
        tableHeight = this._elem.outerHeight(),
        chartdiv.height(chartdiv.height() + tableHeight);
        if (chartdiv.parents('.sizing').length) {
            chartdiv.parents('.sizing').height(chartdiv.height());
        }
    };

})(jQuery);

