/* Date.js loaded in Plone resources for TeamSpace integrations (uu.smartdate dependency)
 * has some issues breaking Date.now vs standard JS behavior.  This breaks D3.  We work
 * around this by fixing what Date.js screws up (at least until we can eliminate Date.js
 * use on this page or in our date-widgets).  SDU 2015-07-13.
 */

Date.now = function() { return +new Date; };
