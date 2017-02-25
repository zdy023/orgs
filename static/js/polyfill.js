(function () {
  "use strict";
  if (String.prototype.startsWith) {
    return;
  }
  String.prototype.startsWith = function startsWith(searchString) {
    var err = check(this, searchString, "startsWith");
    if (err !== null) {
      throw new TypeError(err);
    }
    var a = "" + this, b = "" + searchString, c = +arguments[1];
    a = String(this), b = String(searchString);
    c = c > 0 ? Math.min(c | 0, a.length) : 0;
    return a.lastIndexOf(b, c) === c;
  };
  if (String.prototype.endsWith) {
    return;
  }
  String.prototype.endsWith = function endsWith(searchString) {
    var err = check(this, searchString, "endsWith");
    if (err !== null) {
      throw new TypeError(err);
    }
    var a = "" + this, b = "" + searchString, p = arguments[1], c = +p, u;
    a = String(this), b = String(searchString);
    c = (p === u ? a.length : c > 0 ? Math.min(c | 0, a.length) : 0) - b.length;
    return c >= 0 && a.indexOf(b, c) === c;
  };
  function check(a, b, func) {
    if (a == null) {
      return "String.prototype." + func + " called on null or undefined";
    }
    if (!b) {
      return null;
    }
    var i, f, u;
    i = typeof Symbol === "function" && Symbol.match && (f = b[Symbol.match]) !== u ? f : b instanceof RegExp;
    return i ? "First argument to String.prototype." + func + " must not be a regular expression" : null;
  }
})();

var _ = {};
_.now = Date.now;
_.throttle = function(func, wait, options) {
  if (wait <= 0) { return func; }
  var context, args, result;
  var timeout = null;
  var previous = 0;
  if (!options)
    options = {};
  var later = function() {
    previous = options.leading === false ? 0 : _.now();
    timeout = null;
    result = func.apply(context, args);
    if (!timeout)
      context = args = null;
  };
  return function() {
    var now = _.now();
    if (!previous && options.leading === false)
      previous = now;
    var remaining = wait - (now - previous);
    context = this;
    args = arguments;
    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      previous = now;
      result = func.apply(context, args);
      if (!timeout)
        context = args = null;
      return result;
    } else if (!timeout && options.trailing !== false) {
      timeout = setTimeout(later, remaining);
    }
    return result;
  };
};
