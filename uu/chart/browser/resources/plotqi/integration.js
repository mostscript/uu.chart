/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */
/*globals require, window */


(function () {
  "use strict";

  // Babel compatibility stuff:
  var _prototypeProperties = function (child, staticProps, instanceProps) { if (staticProps) Object.defineProperties(child, staticProps); if (instanceProps) Object.defineProperties(child.prototype, instanceProps); };

  var _get = function get(object, property, receiver) { var desc = Object.getOwnPropertyDescriptor(object, property); if (desc === undefined) { var parent = Object.getPrototypeOf(object); if (parent === null) { return undefined; } else { return get(parent, property, receiver); } } else if ("value" in desc && desc.writable) { return desc.value; } else { var getter = desc.get; if (getter === undefined) { return undefined; } return getter.call(receiver); } };

  var _inherits = function (subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) subClass.__proto__ = superClass; };

  var BaseRenderingPlugin = window.plotqi.BaseRenderingPlugin;

  // Integration plugin:
  var IntegrationPlugin = function IntegrationPlugin(plotter) {
    // superclass init:
    _get(Object.getPrototypeOf(IntegrationPlugin.prototype), 'constructor', this).call(this, plotter);
  };

  _inherits(IntegrationPlugin, BaseRenderingPlugin);

  _prototypeProperties(
    IntegrationPlugin,
    null,
    {
      onComplete: {
        value: function onComplete() {
          var plotters = window.plotqi.plotters,
              expected = window.plotqi.plotCount,
              completed = plotters.filter(function (p) { return p.complete; }),
              done = completed.length === expected,
              viewName = window.location.pathname.split('/').slice(-1)[0],
              doPrint = viewName === '@@print_report';
          if (done && doPrint && !window.plotqi.printPrompted) {
            window.setTimeout(function () {
              window.print();
              },
              1200
            );
            window.plotqi.printPrompted = true;  // only prompt once
          }
        },
        writable: true,
        enumerable: true,
        configurable: true
      }
    }
  );

  window.plotqi.ADDITIONAL_PLUGINS.push(IntegrationPlugin);

  window.plotqi.ready(window.plotqi.load);


}());


