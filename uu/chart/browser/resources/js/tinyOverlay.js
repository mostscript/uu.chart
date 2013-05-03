// tinyOverlay.js -- a minimal JavaScript overlay library.
// Author: Sean Upton <sean.upton@hsc.utah.edu>
// (c) 2013 University of Utah / MIT-licensed, text at:
//          https://teamspace.upiq.org/trac/wiki/Copyright


/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

var tinyOverlay = tinyOverlay || {};

(function ($, ns) {
    "use strict";

    // uuid function via http://stackoverflow.com/a/2117523/835961
    ns.uuid4_tmpl = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    ns.uuid4 = function () {
        return ns.uuid4_tmpl.replace(/[xy]/g, function(c) {
            var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
            return v.toString(16);
        });
    };

    ns.snippets = ns.snippets || {};

    // Default CSS for overlay
    ns.snippets.STYLE = String() +
        'div.tinyOverlay {' +
        '  position:absolute; '+
        '  border-radius:0.4em; ' +
        '  border:0.1em solid rgba(0,0,0,0.5); ' +
        '  box-shadow:0.1em 0.2em 0.5em #999; ' +
        '  background-color:white; ' +
        '  padding:0.3em 1em 0.3em 0.3em; ' +
        '}\n' +
        '.olControlBtn {' +
        '  background-color:rgba(255,255,255,0.85); ' +
        '  font-weight:bold; ' +
        '  font-size:140%; ' +
        '  display:block; ' +
        '  float:right; ' +
        '  width:0.9em; ' +
        '  margin-right:-1.1em; ' +
        '  margin-top:-0.6em; ' +
        '  text-align:center; ' +
        '  line-height:100%; ' +
        '  border-radius:0.5em; ' +
        '  box-shadow:0.1em 0.2em 0.5em #999; ' +
        '}\n' +
        '.olControlBtn a.close {' +
        '  color:#006; ' +
        '  cursor:pointer; ' +
        '  text-decoration:none !important; ' +
        '}\n';

    ns.snippets.CONTROL = String() +
        '<div class="olControl">' +
        '  <span class="olControlBtn">' +
        '   <a class="close" title="close">&times;</a>' +
        '  </span>' +
        '</div>';

    ns.STYLE = $('<style data-ident="tinyOverlay" />').text(ns.snippets.STYLE);

    // singleton global <style> tag for overlays
    ns.getStyle = function () {
        var style = $('head style[data-ident="tinyOverlay"]');
        return (style.length) ? style : ns.STYLE.appendTo($('head'));
    };

    ns.Overlay = function Overlay(html, options, onclose) {

        this.init = function (html, options, onclose) {
            var self = this,
                global_style = ns.getStyle(),
                body = $('body'),
                wrapper = $('<div class="overlayInner" />'),
                overlayDiv = $('<div class="tinyOverlay" />'),
                control = $(ns.snippets.CONTROL);
            this.html = $(html);
            this.options = options || {};
            this.options.style = this.options.style || {width:120};
            this.id = this.options.id || ns.uuid4();
            this.onclose = onclose || [];
            if (onclose && !(onclose instanceof Array)) {
                this.onclose = [onclose];  // array of callbacks
            }
            this.container = this.options.container || $(document);
            // detached overlay div tag; later attached/shown by open()
            this.overlayDiv = overlayDiv;
            this.styleTag = this.getStyle();
            overlayDiv.addClass(this.options.classname).attr('id', this.id);
            control.appendTo(overlayDiv);
            if (!this.html.length && html) {
                this.html = $('<p />').text(html);
            }
            wrapper.html(this.html);
            wrapper.appendTo(overlayDiv);
            Object.keys(this.options.style || {}).forEach(function (k) {
                var v = self.options.style[k];
                self.overlayDiv.css(k, v);
            });
        };

        // warning: raw styles are unscoped, so caller creating an overlay
        // should scope the CSS selectors (which likely means constructing an
        // overlay with known identifier and using templated CSS).
        this.getStyle = function () {
            var ident = 'tinyOverlay-' + this.id,
                style = $('head style[data-id="' + ident + '"]'),
                mkstyle = function (source) {
                    var style = $('<style>').attr('data-id', ident).text(source);
                    return style.appendTo($('head'));
                };
            return (style.length) ? style : mkstyle(this.options.css || '');
        };

        this.open = function () {
            var self = this,
                closebtn,
                offset = this.container.offset() || {left: 0, top: 0};
            // close any already open overlays on page:
            $('span.olControlBtn a.close').click();
            // then append this overlay
            this.overlayDiv.appendTo($('body'));
            closebtn = $('span.olControlBtn a.close', this.overlayDiv);
            closebtn.click(function () { self.close(); });
            if (!this.options.style.left) {
                this.overlayDiv.css('left', (
                    (this.container.width() / 2) -
                    (0.5 * this.overlayDiv.width())
                    ) + offset.left
                );
            }
            if (!this.options.style.top) {
                this.overlayDiv.css('top', (
                    (this.container.height() / 2) -
                    (0.5 * (this.overlayDiv.height() || 120))
                    ) + offset.top
                );
            }
            this.overlayDiv.slideDown(200);
        };

        this.close = function () {
            var self = this;
            this.overlayDiv.slideUp(200, function () { $(this).remove(); });
            this.onclose.forEach(function (callback) { callback.call(self); });
        };

        this.init(html, options, onclose);
    };

}(jQuery, tinyOverlay));
