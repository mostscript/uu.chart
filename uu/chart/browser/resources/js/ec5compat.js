/** partial ECMAScript 5 compatibility for MSIE<9 and MSIE9+ document
  * compatibility modes <IE8
  *
  * Implemented:
  *     * Object.keys
  *     * Array.prototype.reduce
  *     * Array.prototype.map
  */


// Object.keys -- via moz dev: http://goo.gl/mN0cO
if(!Object.keys) Object.keys = function(o){
  if (o !== Object(o))
    throw new TypeError('Object.keys called on non-object');
  var ret=[],p;
  for(p in o) if(Object.prototype.hasOwnProperty.call(o,p)) ret.push(p);
  return ret;
}

// Array.prototype.reduce -- via moz dev: http://goo.gl/pF3mW
if ( !Array.prototype.reduce ) {
  Array.prototype.reduce = function reduce(accumulator){
    var i, l = this.length, curr;
    if(typeof accumulator !== "function") // ES5 : "If IsCallable(callbackfn) is false, throw a TypeError exception."
      throw new TypeError("First argument is not callable");
    if((l == 0 || l === null) && (arguments.length <= 1))// == on purpose to test 0 and false.
      throw new TypeError("Array length is 0 and no second argument");
    if(arguments.length <= 1){
      curr = this[0]; // Increase i to start searching the secondly defined element in the array
      i = 1; // start accumulating at the second element
    } else {
      curr = arguments[1];
    }
    for(i = i || 0 ; i < l ; ++i){
      if(i in this)
        curr = accumulator.call(undefined, curr, this[i], i, this);
    }
    return curr;
  };
}

// Array.prototype.map -- via moz dev, algorithm from es5.github.com:
//   http://goo.gl/cmEVv
if (!Array.prototype.map) {
  Array.prototype.map = function(callback, thisArg) {
    var T, A, k;
    if (this == null) {
      throw new TypeError(" this is null or not defined");
    }   
    var O = Object(this);
    var len = O.length >>> 0;
    if ({}.toString.call(callback) != "[object Function]") {
      throw new TypeError(callback + " is not a function");
    }   
    if (thisArg) {
      T = thisArg;
    }   
    A = new Array(len);
    k = 0;
    while(k < len) {
      var kValue, mappedValue;
      if (k in O) {
        kValue = O[ k ];
        mappedValue = callback.call(T, kValue, k, O); 
        A[ k ] = mappedValue;
      }   
      k++;
    }   
    return A;
  };          
}

// Array.prototype.forEach via mozdev: http://goo.gl/GXKkL
if ( !Array.prototype.forEach ) {
  Array.prototype.forEach = function(fn, scope) {
    for(var i = 0, len = this.length; i < len; ++i) {
      fn.call(scope, this[i], i, this);
    }
  }
}

// Array.prototype.filter via mozdev: http://goo.gl/9meKG
if (!Array.prototype.filter)
{
  Array.prototype.filter = function(fun /*, thisp */)
  {
    "use strict";
 
    if (this == null)
      throw new TypeError();
 
    var t = Object(this);
    var len = t.length >>> 0;
    if (typeof fun != "function")
      throw new TypeError();
 
    var res = [];
    var thisp = arguments[1];
    for (var i = 0; i < len; i++)
    {
      if (i in t)
      {
        var val = t[i]; // in case fun mutates this
        if (fun.call(thisp, val, i, t))
          res.push(val);
      }
    }
 
    return res;
  };
}
