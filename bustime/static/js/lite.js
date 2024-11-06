window.__debugMode = true; // Don't turn it off

var parseJSON = (window.JSON && JSON.parse) ? function (obj) {
  try { return JSON.parse(obj); } catch (e) {
    topError('<b>parseJSON:</b> ' + e.message, {dt: -1, type: 5, answer: obj});
    return eval('('+obj+')');
  }
} : function(obj) {
  return eval('('+obj+')');
}

var cur = {destroy: [], nav: []}; // Current page variables and navigation map.
var _ua = navigator.userAgent.toLowerCase();
var browser = {
  version: (_ua.match( /.+(?:me|ox|on|rv|it|ra|ie)[\/: ]([\d.]+)/ ) || [0,'0'])[1],
  opera: /opera/i.test(_ua),
  msie: (/msie/i.test(_ua) && !/opera/i.test(_ua)),
  msie6: (/msie 6/i.test(_ua) && !/opera/i.test(_ua)),
  msie7: (/msie 7/i.test(_ua) && !/opera/i.test(_ua)),
  msie8: (/msie 8/i.test(_ua) && !/opera/i.test(_ua)),
  msie9: (/msie 9/i.test(_ua) && !/opera/i.test(_ua)),
  mozilla: /firefox/i.test(_ua),
  chrome: /chrome/i.test(_ua),
  safari: (!(/chrome/i.test(_ua)) && /webkit|safari|khtml/i.test(_ua)),
  iphone: /iphone/i.test(_ua),
  ipod: /ipod/i.test(_ua),
  iphone4: /iphone.*OS 4/i.test(_ua),
  ipod4: /ipod.*OS 4/i.test(_ua),
  ipad: /ipad/i.test(_ua),
  safari_mobile: /iphone|ipod|ipad/i.test(_ua),
  android: /android/i.test(_ua),
  opera_mobile: /opera mini|opera mobi/i.test(_ua),
  mobile: /iphone|ipod|ipad|opera mini|opera mobi/i.test(_ua),
  mac: /mac/i.test(_ua)
};

if (!window.vk) window.vk = {loginscheme: 'http', ip_h: ''};

(function() {
  var flash = [0, 0, 0], axon = 'ShockwaveFlash.ShockwaveFlash';
  var wrapType = 'embed', wrapParam = 'type="application/x-shockwave-flash" ';
  var escapeAttr = function(v) {
    return v.toString().replace('&', '&amp;').replace('"', '&quot;');
  }
  if (navigator.plugins && navigator.mimeTypes.length) {
    var x = navigator.plugins['Shockwave Flash'];
    if (x && x.description) {
      var ver = x.description.replace(/([a-zA-Z]|\s)+/, '').replace(/(\s+r|\s+b[0-9]+)/, '.').split('.');
      for (var i = 0; i < 3; ++i) flash[i] = ver[i] || 0;
    }
  } else {
    if (_ua.indexOf('Windows CE') >= 0) {
      var axo = true, ver = 6;
      while (axo) {
        try {
          ++ver;
          axo = new ActiveXObject(axon + '.' + ver);
          flash[0] = ver;
        } catch(e) {}
      }
    } else {
      try {
        var axo = new ActiveXObject(axon + '.7');
        flash = axo.GetVariable('$version').split(' ')[1].split(',');
      } catch (e) {}
    }
    wrapType = 'object';
    wrapParam = 'classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" ';
  }
  browser.flashwrap = (wrapType == 'embed') ? function(opts, params) {
    params = extend({
      id: opts.id,
      name: opts.id,
      width: opts.width,
      height: opts.height,
      style: opts.style,
      preventhide: opts.preventhide
    }, params);
    if (browser.flash >= opts.version) {
      params.src = opts.url;
    } else {
      params.src = opts.express;
    }
    var paramsStr = [];
    for (var i in params) {
      var p = params[i];
      if (p !== undefined && p !== null) {
        paramsStr.push(i + '="' + escapeAttr(p) + '" ');
      }
    }
    return '<embed ' + wrapParam + paramsStr.join('') + '/>';
  } : function(opts, params) {
    if (browser.flash >= opts.version) {
      params.movie = opts.url;
    } else {
      params.movie = opts.express;
    }
    var attr = {
      id: opts.id,
      width: opts.width,
      height: opts.height,
      style: opts.style,
      preventhide: opts.preventhide
    }
    var attrStr = [];
    for (var i in attr) {
      var p = attr[i];
      if (p !== undefined && p !== null) {
        attrStr.push(i + '="' + escapeAttr(p) + '" ');
      }
    }
    var paramsStr = [];
    for (var i in params) {
      var p = params[i];
      if (p !== undefined && p !== null) {
        paramsStr.push('<param name="' + i + '" value="' + escapeAttr(p) + '" />');
      }
    }
    return '<object ' + wrapParam + attrStr.join('') +'>' + paramsStr.join('') + '</object>';
  }
  if (flash[0] < 7) flash = [0, 0, 0];
  browser.flash = intval(flash[0]);
  browser.flashfull = {
    major: browser.flash,
    minor: intval(flash[1]),
    rev: intval(flash[2])
  }
})();

if (!browser.msie6) {
  delete StaticFiles['ie6.css'];
}
if (!browser.msie7) {
  delete StaticFiles['ie7.css'];
}
for (var i in StaticFiles) {
  var f = StaticFiles[i];
  f.t = (i.indexOf('.css') != -1) ? 'css' : 'js';
  f.n = i.replace(/[\\/\\.]/g, '_');
  f.l = 0;
  f.c = 0;
}

window.locHost = location.host;
window.locProtocol = location.protocol;
window.__dev = /[a-z0-9_\-]+\.[a-z0-9_\-]+\.[a-z0-9_\-]+\.[a-z0-9_\-]+/i.test(locHost);
if (!__dev) __debugMode = false;
window.locHash = location.hash.replace('#/', '').replace('#!', '');
window.locDomain = locHost.toString().match(/[a-zA-Z]+\.[a-zA-Z]+\.?$/)[0];
window.locBase = location.toString().replace(/#.+$/, '');
if (!vk.nodomain) {
  if (!browser.msie6 || document.domain != locDomain) document.domain = locDomain;
}

function topMsg(text, seconds, color) {
  if (!color) color = '#D6E5F7';
  if (!text) {
    hide('system_msg');
  } else {
    clearTimeout(window.topMsgTimer);
    var el = ge('system_msg');
    el.style.backgroundColor = color;
    el.innerHTML = text;
    show(el);
    if (seconds) {
      window.topMsgTimer = setTimeout(topMsg.pbind(false), seconds * 1000);
    }
  }
}

function topError(text, seconds) {
  if (text.message) {
    var e = text;
    text = '<b>JavaScript error:</b> ' + e.message;
    if (e.stack && __debugMode) text += '<br/>' + e.stack.replace(/\n/g, '<br/>');
  }
  topMsg(text, seconds, '#FFB4A3');
}

function langNumeric(count, vars, formatNum) {
  if (!vars || !window.langConfig) { return count; }
  var res;
  if (!isArray(vars)) {
    result = vars;
  } else {
    res = vars[1];
    if(count != Math.floor(count)) {
      res = vars[langConfig.numRules['float']];
    } else {
      each(langConfig.numRules['int'], function(i,v){
        if (v[0] == '*') { res = vars[v[2]]; return false; }
        var c = v[0] ? count % v[0] : count;
        if(indexOf(v[1], c) != -1) { res = vars[v[2]]; return false; }
      });
    }
  }
  if (formatNum) {
    var n = count.toString().split('.'), c = [];
    for(var i = n[0].length - 3; i > -3; i -= 3) {
      c.unshift(n[0].slice(i > 0 ? i : 0, i + 3));
    }
    n[0] = c.join(langConfig.numDel);
    count = n.join(langConfig.numDec);
  }
  res = (res || '%s').replace('%s', count);
  return res;
}

function langSex(sex, vars) {
  if (!isArray(vars)) return vars;
  var res = vars[1];
  if (!window.langConfig) return res;
  each(langConfig.sexRules, function(i,v){
    if (v[0] == '*') { res = vars[v[1]]; return false; }
    if (sex == v[0] && vars[v[1]]) { res = vars[v[1]]; return false; }
  });
  return res;
}

function getLang() {
  try {
    var args = Array.prototype.slice.call(arguments);
    var key = args.shift();
    if (!key) return '...';
    var val = (window.cur.lang && window.cur.lang[key]) || (window.lang && window.lang[key]) || (window.langpack && window.langpack[key]) || window[key];
    if (!val) {
      var res = key.split('_');
      res.shift();
      return res.join(' ');
    }
    if (isFunction(val)) {
      return val.apply(null, args);
    } else if (isArray(val)) {
      return langNumeric(args[0], val, args[1]);
    } else {
      return val;
    }
  } catch(e) {
    debugLog('lang error:' + e.message + '(' + Array.prototype.slice.call(arguments).join(', ') + ')');
  }
}

// Debug Log

var _logTimer = (new Date()).getTime();
function debugLog(msg){
  try {
    var t = '[' + (((new Date()).getTime() - _logTimer) / 1000) + '] ';
    if (ge('debuglog')) {
      if (msg === null) {
        msg = '[NULL]';
      } else if (msg === undefined) {
        msg = '[UNDEFINED]';
      }
      ge('debuglog').innerHTML += t + msg.toString().replace('<', '&lt;').replace('>', '&gt;')+'<br/>';
    }
    if (window.console && console.log) {
      Array.prototype.unshift.call(arguments, t);
      console.log.apply(console, arguments);
    }
  } catch (e) {
  }
}

// DOM

function ge(el) {
  return (typeof el == 'string' || typeof el == 'number') ? document.getElementById(el) : el;
}
function geByTag(searchTag, node) {
  return (node || document).getElementsByTagName(searchTag);
}
function geByTag1(searchTag, node) {
  node = node || document;
  return node.querySelector && node.querySelector(searchTag) || geByTag(searchTag, node)[0];
}
function geByClass(searchClass, node, tag) {
  node = node || document;
  tag = tag || '*';
  var classElements = [];

  if (node.querySelectorAll && tag != '*') {
    return node.querySelectorAll(tag + '.' + searchClass);
  }
  if (node.getElementsByClassName) {
    var nodes = node.getElementsByClassName(searchClass);
    if (tag != '*') {
      tag = tag.toUpperCase();
      for (var i = 0, l = nodes.length; i < l; ++i) {
        if (nodes[i].tagName.toUpperCase() == tag) {
          classElements.push(nodes[i]);
        }
      }
    } else {
      classElements = Array.prototype.slice.call(nodes);
    }
    return classElements;
  }

  var els = geByTag(tag, node);
  var pattern = new RegExp('(^|\\s)' + searchClass + '(\\s|$)');
  for (var i = 0, l = els.length; i < l; ++i) {
    if (pattern.test(els[i].className)) {
      classElements.push(els[i]);
    }
  }
  return classElements;
}
function geByClass1(searchClass, node, tag) {
  node = node || document;
  tag = tag || '*';
  return node.querySelector && node.querySelector(tag + '.' + searchClass) || geByClass(searchClass, node, tag)[0];
}

function ce(tagName, attr, style) {
  var el = document.createElement(tagName);
  if (attr) extend(el, attr);
  if (style) setStyle(el, style);
  return el;
}

window.cf = (function(doc) {
  var frag = doc.createDocumentFragment(),
      elem = doc.createElement('div'),
      range = doc.createRange && doc.createRange();
  frag.appendChild(elem);
  range && range.selectNodeContents(elem);

  return range && range.createContextualFragment ?
    function (html) {
      if (!html) return doc.createDocumentFragment();
      return range.createContextualFragment(html);
    } :
    function (html) {
      if (!html) return doc.createDocumentFragment();
      elem.innerHTML = html;
      var frag = doc.createDocumentFragment();
      while (elem.firstChild) {
        frag.appendChild(elem.firstChild);
      }
      return frag;
    };
})(document);

function re(el) {
  el = ge(el);
  if (el && el.parentNode) el.parentNode.removeChild(el);
  return el;
}

function se(html) {return ce('div', {innerHTML: html}).firstChild;}
function rs(html, repl) {
  each (repl, function (k, v) {
    html = html.replace(new RegExp('%' + k + '%', 'g'), v);
  });
  return html;
}
function psr(html) {
  if (locProtocol != 'https:') return html;
  html = html.replace(/http:\/\/cs(\d+)\.(userapi\.com|vk\.com|vk\.me|vkontakte\.ru)\/([a-z0-9\/_:]+\.jpg)/gi, 'https://pp.vk.me/c$1/$3');
  html = html.replace(/http:\/\/cs(\d+)\.(userapi\.com|vk\.com|vk\.me|vkontakte\.ru)\//gi, 'https://ps.vk.me/c$1/');
  html = html.replace(/http:\/\/video(\d+)\.vkadre\.ru\//gi, 'https://ps.vk.me/v$1/');
  return html;
}

function domEL(el, p) {
  p = p ? 'previousSibling' : 'nextSibling';
  while (el && !el.tagName) el = el[p];
  return el;
}
function domNS(el) {
  return domEL((el || {}).nextSibling);
}
function domPS(el) {
  return domEL((el || {}).previousSibling, 1);
}
function domFC(el) {
  return domEL((el || {}).firstChild);
}
function domLC(el) {
  return domEL((el || {}).lastChild, 1);
}
function domPN(el) {
  return (el || {}).parentNode;
}

function show(elem) {
  if (arguments.length > 1) {
    for (var i = 0; i < arguments.length; ++i) {
      show(arguments[i]);
    }
    return;
  }
  elem = ge(elem);
  if (!elem || !elem.style) return;
  var old = elem.olddisplay, newStyle = 'block', tag = elem.tagName.toLowerCase();
  elem.style.display = old || '';


  if (getStyle(elem, 'display') == 'none') {
    if (hasClass(elem, 'inline')) {
      newStyle = 'inline';
    } else if (tag == 'tr' && !browser.msie) {
      newStyle = 'table-row';
    } else if (tag == 'table' && !browser.msie) {
      newStyle = 'table';
    } else {
      newStyle = 'block';
    }
    elem.style.display = elem.olddisplay = newStyle;
  }
}

function hide(elem) {
  if (arguments.length > 1) {
    for (var i = 0; i < arguments.length; i++) {
      hide(arguments[i]);
    }
    return;
  }
  elem = ge(elem);
  if (!elem || !elem.style) return;
  var d = getStyle(elem, 'display');
  elem.olddisplay = (d != 'none') ? d : '';
  elem.style.display = 'none';
}

function isVisible(elem) {
  elem = ge(elem);
  if (!elem || !elem.style) return false;
  return getStyle(elem, 'display') != 'none';
}

function toggle(elem, val) {
  if (val === undefined) {
    val = !isVisible(elem);
  }
  if (val) {
    show(elem);
  } else {
    hide(elem);
  }
}

var hfTimeout = 0;
function toggleFlash(show, timeout) {
  //if (/mac/i.test(navigator.userAgent)) return;
  clearTimeout(hfTimeout);
  if (timeout > 0) {
    hfTimeout = setTimeout(function() {toggleFlash(show, 0)}, timeout);
    return;
  }

  var vis = show ? 'visible' : 'hidden';

  triggerEvent(document, show ? 'unblock' : 'block');

  var f = function() {
    if (this.getAttribute('preventhide')) {
      return;
    } else if (this.id == 'app_container' && browser.msie) {
      show ? setStyle(this, {position: 'static', top: 0}) : setStyle(this, {position: 'absolute', top: '-5000px'});
    } else {
      this.style.visibility = vis;
    }
  };
  each(geByTag('embed'), f);
  each(geByTag('object'), f);
}

function getXY(obj, forFixed) {
  if (!obj || obj == undefined) return;
  var left = 0, top = 0, pos, lastLeft;
  if (obj.offsetParent) {
    do {
      left += (lastLeft = obj.offsetLeft);
      top += obj.offsetTop;
      pos = getStyle(obj, 'position');
      if (pos == 'fixed' || pos == 'absolute' || pos == 'relative') {
        left -= obj.scrollLeft;
        top -= obj.scrollTop;
        if (pos == 'fixed' && !forFixed) {
          left += ((obj.offsetParent || {}).scrollLeft || bodyNode.scrollLeft || htmlNode.scrollLeft);
          top += ((obj.offsetParent || {}).scrollTop || bodyNode.scrollTop || htmlNode.scrollTop);
        }
      }
    } while (obj = obj.offsetParent);
  }
  if (forFixed && browser.msie && intval(browser.version) < 9) {
    if (lastLeft) {
      left += ge('page_layout').offsetLeft;
    }
  }
  return [left,top];
}

function getSize(elem, withoutBounds) {
  elem = ge(elem);
  var s = [0, 0], de = document.documentElement;
  if (elem == document) {
    s =  [Math.max(
        de.clientWidth,
        bodyNode.scrollWidth, de.scrollWidth,
        bodyNode.offsetWidth, de.offsetWidth
      ), Math.max(
        de.clientHeight,
        bodyNode.scrollHeight, de.scrollHeight,
        bodyNode.offsetHeight, de.offsetHeight
      )];
  } else if (elem){
    function getWH() {
      s = [elem.offsetWidth, elem.offsetHeight];
      if (!withoutBounds) return;
      var padding = 0, border = 0;
      each(s, function(i, v) {
        var which = i ? ['Top', 'Bottom'] : ['Left', 'Right'];
        each(which, function(){
          s[i] -= parseFloat(getStyle(elem, 'padding' + this)) || 0;
          s[i] -= parseFloat(getStyle(elem, 'border' + this + 'Width')) || 0;
        });
      });
      s = [Math.round(s[0]), Math.round(s[1])];
    }
    if (!isVisible(elem)) {
      var props = {position: 'absolute', visibility: 'hidden', display: 'block'};
      var old = {};
      each(props, function(i, v) {
        old[i] = elem.style[i];
        elem.style[i] = v;
      });
      getWH();
      each(props, function(i, v) {
        elem.style[i] = old[i];
      });
    } else getWH();

  }
  return s;
}

/**
 *  Useful utils
 */

Function.prototype.pbind = function() {
  var args = Array.prototype.slice.call(arguments);
  args.unshift(window);
  return this.bind.apply(this, args);
};
Function.prototype.bind = function() {
  var func = this, args = Array.prototype.slice.call(arguments);
  var obj = args.shift();
  return function() {
    var curArgs = Array.prototype.slice.call(arguments);
    return func.apply(obj, args.concat(curArgs));
  }
}
function rand(mi, ma) { return Math.random() * (ma - mi + 1) + mi; }
function irand(mi, ma) { return Math.floor(rand(mi, ma)); }
function isFunction(obj) {return Object.prototype.toString.call(obj) === '[object Function]'; }
function isArray(obj) { return Object.prototype.toString.call(obj) === '[object Array]'; }
function isObject(obj) { return Object.prototype.toString.call(obj) === '[object Object]'; }
function isEmpty(o) { if(Object.prototype.toString.call(o) !== '[object Object]') {return false;} for(var i in o){ if(o.hasOwnProperty(i)){return false;} } return true; }
function vkNow() { return +new Date; }
function vkImage() { return window.Image ? (new Image()) : ce('img'); } // IE8 workaround
function trim(text) { return (text || '').replace(/^\s+|\s+$/g, ''); }
function stripHTML(text) { return text ? text.replace(/<(?:.|\s)*?>/g, '') : ''; }
function escapeRE(s) { return s ? s.replace(/[.*+?^${}()|[\]\/\\]/g, '\\$0') : ''; }
function intval(value) {
  if (value === true) return 1;
  return parseInt(value) || 0;
}
function floatval(value) {
  if (value === true) return 1;
  return parseFloat(value) || 0;
}
function positive(value) {
  value = intval(value);
  return value < 0 ? 0 : value;
}

function winToUtf(text) {
  var m, i, j, code;
  m = text.match(/&#[0-9]{2}[0-9]*;/gi);
  for (j in m) {
    var val = '' + m[j]; // buggy IE6
    code = intval(val.substr(2, val.length - 3));
    if (code >= 32 && ('&#' + code + ';' == val)) { // buggy IE6
      text = text.replace(val, String.fromCharCode(code));
    }
  }
  text = text.replace(/&quot;/gi, '"').replace(/&amp;/gi, '&').replace(/&lt;/gi, '<').replace(/&gt;/gi, '>');
  return text;
}

function replaceEntities(str) {
  str = str.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  return ce('div', {innerHTML: '<textarea>' + str + '</textarea>'}).firstChild.value;
}

/**
 *  Arrays, objects
 **/

function each(object, callback) {
  var name, i = 0, length = object.length;

  if (length === undefined) {
    for (name in object)
      if (callback.call(object[name], name, object[name]) === false)
        break;
  } else {
    for (var value = object[0];
      i < length && callback.call(value, i, value) !== false;
        value = object[++i]) {}
  }

  return object;
}

function indexOf(arr, value, from) {
  for (var i = from || 0; i < arr.length; i++) {
    if (arr[i] == value) return i;
  }
  return -1;
}
function inArray(value, arr) {
  return indexOf(arr, value) != -1;
}
function clone(obj) {
  var newObj = isArray(obj) ? [] : {};
  for (var i in obj) {
    newObj[i] = obj[i];
  }
  return newObj;
}

// Extending object by another
function extend() {
  var a = arguments, target = a[0] || {}, i = 1, length = a.length, deep = false, options;

  if (typeof target === 'boolean') {
    deep = target;
    target = a[1] || {};
    i = 2;
  }

  if (typeof target !== 'object' && !isFunction(target)) target = {};

  if (length == i) return target;

  for (; i < length; i++) {
    if ((options = a[i]) != null) {
      for (var name in options) {
        var src = target[name], copy = options[name];

        if (target === copy) continue;

        if (deep && copy && typeof copy === 'object' && !copy.nodeType) {
          target[name] = extend(deep, src || (copy.length != null ? [] : {}), copy);
        } else if (copy !== undefined) {
          target[name] = copy;
        }
      }
    }
  }

  return target;
}


/**
 * CSS classes
 **/

function hasClass(obj, name) {
  obj = ge(obj);
  return obj && (new RegExp('(\\s|^)' + name + '(\\s|$)')).test(obj.className);
}
function addClass(obj, name) {
  if ((obj = ge(obj)) && !hasClass(obj, name)) {
    obj.className = (obj.className ? obj.className + ' ' : '') + name;
  }
}
function removeClass(obj, name) {
  if (obj = ge(obj)) {
    obj.className = trim((obj.className || '').replace((new RegExp('(\\s|^)' + name + '(\\s|$)')), ' '));
  }
}
function toggleClass(obj, name, val) {
  if (val === undefined) {
    val = !hasClass(obj, name);
  }
  (val ? addClass : removeClass)(obj, name);
}
function replaceClass(obj, oldName, newName) {
  removeClass(obj, oldName);
  addClass(obj, newName);
}

// Get computed style
function getStyle(elem, name, force) {
  elem = ge(elem);
  if (isArray(name)) { var res = {}; each(name, function(i,v){res[v] = getStyle(elem, v);}); return res; }
  if (force === undefined) {
    force = true;
  }
  if (!force && name == 'opacity' && browser.msie) {
    var filter = elem.style['filter'];
    return filter ? (filter.indexOf('opacity=') >= 0 ?
      (parseFloat(filter.match(/opacity=([^)]*)/)[1] ) / 100) + '' : '1') : '';
  }
  if (!force && elem.style && (elem.style[name] || name == 'height')) {
    return elem.style[name];
  }

  var ret, defaultView = document.defaultView || window;
  if (defaultView.getComputedStyle) {
    name = name.replace(/([A-Z])/g, '-$1').toLowerCase();
    var computedStyle = defaultView.getComputedStyle(elem, null);
    if (computedStyle) {
      ret = computedStyle.getPropertyValue(name);
    }
  } else if (elem.currentStyle) {
    if (name == 'opacity' && browser.msie) {
      var filter = elem.currentStyle['filter'];
      return filter && filter.indexOf('opacity=') >= 0 ?
        (parseFloat(filter.match(/opacity=([^)]*)/)[1]) / 100) + '' : '1';
    }
    var camelCase = name.replace(/\-(\w)/g, function(all, letter){
      return letter.toUpperCase();
    });
    ret = elem.currentStyle[name] || elem.currentStyle[camelCase];
    //dummy fix for ie
    if (ret == 'auto') {
      ret = 0;
    }

    if (!/^\d+(px)?$/i.test(ret) && /^\d/.test(ret)) {
      var style = elem.style, left = style.left, rsLeft = elem.runtimeStyle.left;

      elem.runtimeStyle.left = elem.currentStyle.left;
      style.left = ret || 0;
      ret = style.pixelLeft + 'px';

      style.left = left;
      elem.runtimeStyle.left = rsLeft;
    }
  }

  if (force && (name == 'width' || name == 'height')) {
    var ret2 = getSize(elem, true)[({'width': 0, 'height': 1})[name]];
    ret = (intval(ret) ? Math.max(floatval(ret), ret2) : ret2) + 'px';
  }

  return ret;
}

function setStyle(elem, name, value){
  elem = ge(elem);
  if (!elem) return;
  if (typeof name == 'object') return each(name, function(k, v) { setStyle(elem,k,v); });
  if (name == 'opacity') {
    if (browser.msie) {
      if ((value + '').length) {
        elem.style.filter = 'alpha(opacity=' + value * 100 + ')';
      } else {
        elem.style.filter = '';
      }
      elem.style.zoom = 1;
    };
    elem.style.opacity = value;
  } else {
    try{
    var isN = typeof(value) == 'number';
    if (isN && (/height|width/i).test(name)) value = Math.abs(value);
    elem.style[name] = isN && !(/z-?index|font-?weight|opacity|zoom|line-?height/i).test(name) ? value + 'px' : value;
    } catch(e){debugLog([name, value]);}
  }
}

/**
 * Store data connected to element
 **/

var vkExpand = 'VK' + vkNow(), vkUUID = 0, vkCache = {};

function data(elem, name, data) {
  var id = elem[vkExpand], undefined;
  if (!id) {
    id = elem[vkExpand] = ++vkUUID;
  }

  if (name && !vkCache[id]) {
    vkCache[id] = {};
    if (__debugMode) vkCache[id].__elem = elem;
  }

  if (data !== undefined) {
    vkCache[id][name] = data;
  }

  return name ? vkCache[id][name] : id;
}
function removeAttr(el) {
  for (var i = 0; i < arguments.length; ++i) {
    var n = arguments[i];
    if (el[n] === undefined) continue;
    try {
      delete el[n];
    } catch(e) {
      try {
        el.removeAttribute(n);
      } catch(e) {}
    }
  }
}
function removeData(elem, name) {
  var id = elem ? elem[vkExpand] : false;
  if (!id) return;

  if (name) {
    if (vkCache[id]) {
      delete vkCache[id][name];
      name = '';
      for (name in vkCache[id]) {
        break;
      }

      if (!name) {
        removeData(elem);
      }
    }
  } else {
    removeEvent(elem);
    removeAttr(elem, vkExpand);
    delete vkCache[id];
  }
}
function cleanElems() {
  var a = arguments;
  for (var i = 0; i < a.length; ++i) {
    var el = ge(a[i]);
    if (el) {
      removeData(el);
      removeAttr(el, 'btnevents');
    }
  }
}

// Simple FX
function animate(el, params, speed, callback) {
  el = ge(el);
  if (!el) return;
  var _cb = isFunction(callback) ? callback : function() {};
  var options = extend({}, typeof speed == 'object' ? speed : {duration: speed, onComplete: _cb});
  var fromArr = {}, toArr = {}, visible = isVisible(el), self = this, p;
  options.orig = {};
  params = clone(params);
  if (browser.iphone)
    options.duration = 0;
  var tween = data(el, 'tween'), i, name, toggleAct = visible ? 'hide' : 'show';
  if (tween && tween.isTweening) {
    options.orig = extend(options.orig, tween.options.orig);
    tween.stop(false);
    if (tween.options.show) toggleAct = 'hide';
    else if (tween.options.hide) toggleAct = 'show';
  }
  for (p in params)  {
    if (!tween && (params[p] == 'show' && visible || params[p] == 'hide' && !visible)) {
      return options.onComplete.call(this, el);
    }
    if ((p == 'height' || p == 'width') && el.style) {
      if (options.orig.overflow == undefined) {
        options.orig.overflow = getStyle(el, 'overflow');
      }
      el.style.overflow = 'hidden';
      if (!hasClass(el, 'inl_bl')) {
        el.style.display = 'block';
      }
    }
    if (/show|hide|toggle/.test(params[p])) {
      if (params[p] == 'toggle') {
        params[p] = toggleAct;
      }
      if (params[p] == 'show') {
        var from = 0;
        options.show = true;
        if (options.orig[p] == undefined) {
          options.orig[p] = getStyle(el, p, false) || '';
          setStyle(el, p, 0);
        }

        var o;
        if (p == 'height' && browser.msie6) {
          o = '0px';
          el.style.overflow = '';
        } else {
          o = options.orig[p];
        }

        var old = el.style[p];
        el.style[p] = o;
        params[p] = parseFloat(getStyle(el, p, true));
        el.style[p] = old;

        if (p == 'height' && browser.msie) {
          el.style.overflow = 'hidden';
        }
      } else {
        if (options.orig[p] == undefined) {
          options.orig[p] = getStyle(el, p, false) || '';
        }
        options.hide = true;
        params[p] = 0;
      }
    }
  }
  if (options.show && !visible) {
    show(el);
  }
  tween = new Fx.Base(el, options);
  each(params, function(name, to) {
    if (/backgroundColor|borderBottomColor|borderLeftColor|borderRightColor|borderTopColor|color|borderColor|outlineColor/.test(name)) {
      var p = (name == 'borderColor') ? 'borderTopColor' : name;
      from = getColor(el, p);
      to = getRGB(to);
    } else {
      var parts = to.toString().match(/^([+-]=)?([\d+-.]+)(.*)$/),
        start = tween.cur(name, true) || 0;
      if (parts) {
        to = parseFloat(parts[2]);
        if (parts[1]) {
          to = ((parts[1] == '-=' ? -1 : 1) * to) + to;
        }
      }

      if (options.hide && name == 'height' && browser.msie6) {
        el.style.height = '0px';
        el.style.overflow = '';
      }
      from = tween.cur(name, true);
      if (options.hide && name == 'height' && browser.msie6) {
        el.style.height = '';
        el.style.overflow = 'hidden';
      }
      if (from == 0 && (name == 'width' || name == 'height'))
        from = 1;

      if (name == 'opacity' && to > 0 && !visible) {
        setStyle(el, 'opacity', 0);
        from = 0;
        show(el);
      }
    }
    if (from != to || (isArray(from) && from.join(',') == to.join(','))) {
      fromArr[name] = from;
      toArr[name] = to;
    }
  });
  tween.start(fromArr, toArr);
  data(el, 'tween', tween);

  return tween;
}

function fadeTo(el, speed, to, callback) {
  return animate(el, {opacity: to}, speed, callback);
}

var Fx = fx = {
  Transitions: {
    linear: function(t, b, c, d) { return c*t/d + b; },
    sineInOut: function(t, b, c, d) { return -c/2 * (Math.cos(Math.PI*t/d) - 1) + b; },
    halfSine: function(t, b, c, d) { return c * (Math.sin(Math.PI * (t/d) / 2)) + b; },
    easeOutBack: function(t, b, c, d) { var s = 1.70158; return c*((t=t/d-1)*t*((s+1)*t + s) + 1) + b; },
    easeInCirc: function(t, b, c, d) { return -c * (Math.sqrt(1 - (t/=d)*t) - 1) + b; },
    easeOutCirc: function(t, b, c, d) { return c * Math.sqrt(1 - (t=t/d-1)*t) + b; },
    easeInQuint: function(t, b, c, d) { return c*(t/=d)*t*t*t*t + b; },
    easeOutQuint: function(t, b, c, d) { return c*((t=t/d-1)*t*t*t*t + 1) + b; }
  },
  Attrs: [
    [ 'height', 'marginTop', 'marginBottom', 'paddingTop', 'paddingBottom' ],
    [ 'width', 'marginLeft', 'marginRight', 'paddingLeft', 'paddingRight' ],
    [ 'opacity', 'left', 'top' ]
  ],
  Timers: [],
  TimerId: null
}

Fx.Base = function(el, options, name) {
  this.el = ge(el);
  this.name = name;
  this.options = extend({
    onComplete: function() {},
    transition: Fx.Transitions.sineInOut,
    duration: 500
  }, options || {});
}

function genFx(type, num) {
  var obj = {};
  each(Fx.Attrs.concat.apply([], Fx.Attrs.slice(0, num)), function() {
    obj[this] = type;
  });
  return obj;
};

// Shortcuts for custom animations
each({slideDown: genFx('show', 1),
  slideUp: genFx('hide', 1),
  slideToggle: genFx('toggle', 1),
  fadeIn: {opacity: 'show'},
  fadeOut: {opacity: 'hide'},
  fadeToggle: {opacity: 'toggle'}}, function(f, val) {
  window[f] = function(el, speed, callback) { return animate(el, val, speed, callback); }
});

Fx.Base.prototype = {
  start: function(from, to){
    this.from = from;
    this.to = to;
    this.time = vkNow();
    this.isTweening = true;

    var self = this;
    function t(gotoEnd) {
      return self.step(gotoEnd);
    }
    t.el = this.el;
    if (t() && Fx.Timers.push(t) && !Fx.TimerId) {
      Fx.TimerId = setInterval(function() {
        var timers = Fx.Timers;
        for (var i = 0; i < timers.length; i++) {
          if (!timers[i]()) {
            timers.splice(i--, 1);
          }
        }
        if (!timers.length) {
          clearInterval(Fx.TimerId);
          Fx.TimerId = null;
        }
      }, 13);
    }
    return this;
  },

  stop: function(gotoEnd) {
    var timers = Fx.Timers;

    for (var i = timers.length - 1; i >= 0; i--) {
      if (timers[i].el == this.el ) {
        if (gotoEnd) {
          timers[i](true);
        }
        timers.splice(i, 1);
      }
    }
    this.isTweening = false;
  },

  step: function(gotoEnd) {
    var time = vkNow();
    if (!gotoEnd && time < this.time + this.options.duration) {
      this.cTime = time - this.time;
      this.now = {};
      for (p in this.to) {
        // color fx
        if (isArray(this.to[p])) {
          var color = [], j;
          for (j = 0; j < 3; j++) {
            if (this.from[p] === undefined || this.to[p] === undefined) {
              return false;
            }
            color.push(Math.min(parseInt(this.compute(this.from[p][j], this.to[p][j])), 255));
          }
          this.now[p] = color;
        } else {
          this.now[p] = this.compute(this.from[p], this.to[p]);
        }
      }
      this.update();
      return true;
    } else {
      setTimeout(this.options.onComplete.bind(this, this.el), 10);
      this.now = extend(this.to, this.options.orig);
      this.update();
      if (this.options.hide) hide(this.el);
      this.isTweening = false;
      return false;
    }
  },

  compute: function(from, to){
    var change = to - from;
    return this.options.transition(this.cTime, from, change, this.options.duration);
  },

  update: function(){
    for (var p in this.now) {
      if (isArray(this.now[p])) setStyle(this.el, p, 'rgb(' + this.now[p].join(',') + ')');
      else this.el[p] != undefined ? (this.el[p] = this.now[p]) : setStyle(this.el, p, this.now[p]);
    }
  },

  cur: function(name, force){
    if (this.el[name] != null && (!this.el.style || this.el.style[name] == null))
      return this.el[name];
    return parseFloat(getStyle(this.el, name, force)) || 0;
  }
};

// Parse strings looking for color tuples [255,255,255]
function getRGB(color) {
  var result;
  if (color && isArray(color) && color.length == 3)
    return color;
  if (result = /rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)/.exec(color))
    return [parseInt(result[1]), parseInt(result[2]), parseInt(result[3])];
  if (result = /rgb\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*\)/.exec(color))
    return [parseFloat(result[1])*2.55, parseFloat(result[2])*2.55, parseFloat(result[3])*2.55];
  if (result = /#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(color))
    return [parseInt(result[1],16), parseInt(result[2],16), parseInt(result[3],16)];
  if (result = /#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(color))
    return [parseInt(result[1]+result[1],16), parseInt(result[2]+result[2],16), parseInt(result[3]+result[3],16)];
}

function getColor(elem, attr) {
  var color;
  do {
    color = getStyle(elem, attr);
    if (!color.indexOf('rgba')) color = '';
    if (color != '' && color != 'transparent' || elem.nodeName.toLowerCase() == 'body') {
      break;
    }
    attr = 'backgroundColor';
  } while (elem = elem.parentNode);
  return getRGB(color);
}

function scrollToTop(speed) {
  if (speed == undefined) speed = 400;
  if (speed) {
    if (browser.msie6) {
      animate(pageNode, {scrollTop: 0}, speed);
    } else {
      animate(htmlNode, {scrollTop: 0}, speed);
      animate(bodyNode, {scrollTop: 0}, speed);
    }
  } else {
    window.scroll(0, 0);
    if (browser.msie6) {
      pageNode.scrollTop = 0;
    }
  }
}

function scrollGetY() {
  return window.pageYOffset || scrollNode.scrollTop || document.documentElement.scrollTop;
}

function notaBene(el, color, nofocus) {
  el = ge(el);
  if (!el) return;

  if (!nofocus) elfocus(el);
  var oldBack = data(el, 'back') || data(el, 'back', getStyle(el, 'backgroundColor'));
  var colors = {notice: '#FFFFE0', warning: '#FAEAEA'};
  setStyle(el, 'backgroundColor', colors[color] || color || colors.warning);
  setTimeout(animate.pbind(el, {backgroundColor: oldBack}, 300), 400);
}

function setTitle(el) {
  el = ge(el);
  if (!el || el.titleSet) return;
  if (el.scrollWidth > el.clientWidth) {
    el.setAttribute('title', el.innerText || el.textContent);
  } else {
    var b = geByTag1('b', el);
    if (b && b.scrollWidth > b.clientWidth) {
      el.setAttribute('title', el.innerText || el.textContent);
    } else {
      el.removeAttribute('title');
    }
  }
  el.titleSet = 1;
}

window.__adsLoaded = vkNow();
function __adsGetAjaxParams(ajaxParams, ajaxOptions) {
  __adsGetAjaxParams = function() {
    return window.AdsLight && AdsLight.getAjaxParams.apply(AdsLight.getAjaxParams, arguments) || {al_ad: null};
  };
  var result = stManager.add(['aes_light.js'], __adsGetAjaxParams.pbind(ajaxParams, ajaxOptions));
  return result || {al_ad: null};
}
function __adsUpdate(force) {
  __adsUpdate = function() {
    window.AdsLight && AdsLight.updateBlock.apply(AdsLight.updateBlock, arguments);
  };
  stManager.add(['aes_light.js'], __adsUpdate.pbind(force));
}
function __adsSet(adsHtml, adsSection, adsCanShow, adsShowed, adsParams) {
  __adsSet = function() {
    window.AdsLight && AdsLight.setNewBlock.apply(AdsLight.setNewBlock, arguments);
  };
  stManager.add(['aes_light.js'], __adsSet.pbind(adsHtml, adsSection, adsCanShow, adsShowed, adsParams));
}

function currentAudioId() {
  return window.audioPlayer && audioPlayer.id;
}

function padAudioPlaylist() {
  return window.audioPlaylist || ls.get('pad_playlist');
}

function clean(str) {
  return str ? (str+'').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;') : '';
}
function isObject(obj) { return Object.prototype.toString.call(obj) === '[object Object]'; }
function isArray(obj) { return Object.prototype.toString.call(obj) === '[object Array]'; }
function cleanObj(data) {
  if (isObject(data)) {
    var dataCleaned = {};
    for(var i in data) {
      dataCleaned[i.replace(/[^a-zA-Z0-9_\-]/g, '')] = cleanObj(data[i]);
    }
  } else if (isArray(data)) {
    var dataCleaned = [];
    for(var i in data) {
      dataCleaned.push(cleanObj(data[i]));
    }
  } else {
    var type = typeof(data);
    if (type == 'number' || type == 'boolean') {
      var dataCleaned = data;
    } else {
      var dataCleaned = clean(data);
    }
  }
  return dataCleaned;
}
function updGlobalPlayer() {
  return false;
}

var _postsSeen = {}, _postsSaved = {}, _postsSaveTimer, _postsSendTimer, _postsCleanTimer;
var ls = {
  checkVersion: function() {
    return false;
  },
  set: function(k, v) {
    return false;
  },
  get: function(k) {
    return false;
  },
  remove: function(k) {
    return false;
  }
}

/**
 * Events
 **/
var KEY = window.KEY = {
  LEFT: 37,
  UP: 38,
  RIGHT: 39,
  DOWN: 40,
  DEL: 8,
  TAB: 9,
  RETURN: 13,
  ENTER: 13,
  ESC: 27,
  PAGEUP: 33,
  PAGEDOWN: 34,
  SPACE: 32
};

function addEvent(elem, types, handler, custom, context) {
  elem = ge(elem);
  if (!elem || elem.nodeType == 3 || elem.nodeType == 8)
    return;

  var realHandler = context ? function (e) {
    var prevData = e.data;
    e.data = context;
    var ret = handler.apply(this, [e]);
    e.data = prevData;
    return ret;
  } : handler;

  // For IE
  if (elem.setInterval && elem != window) elem = window;

  var events = data(elem, 'events') || data(elem, 'events', []),
      handle = data(elem, 'handle') || data(elem, 'handle', function() {
        _eventHandle.apply(arguments.callee.elem, arguments);
      });
  // to prevent a memory leak
  handle.elem = elem;

  each(types.split(/\s+/), function(index, type) {
    if (!events[type]) {
      events[type] = [];
      if (!custom && elem.addEventListener) {
        elem.addEventListener(type, handle, false);
      } else if (!custom && elem.attachEvent) {
        elem.attachEvent('on' + type, handle);
      }
    }
    events[type].push(realHandler);
  });

  elem = null;
}
function removeEvent(elem, types, handler) {
  elem = ge(elem);
  if (!elem) return;
  var events = data(elem, 'events');
  if (!events) return;
  if (typeof(types) != 'string') {
    for (var i in events) {
      removeEvent(elem, i);
    }
    return;
  }
  each(types.split(/\s+/), function(index, type) {
    if (!isArray(events[type])) return;
    if (isFunction(handler)) {
      for (var i = 0; i < events[type].length; i++) {
        if (events[type][i] == handler) {
          for (var j = i + 1; j < events[type].length; j++) {
            events[type][j - 1] = events[type][j];
          }
          events[type].pop();
          break;
        }
      }
    } else {
      for (var i = 0; i < events[type].length; i++) {
        delete events[type][i];
      }
    }
    if (!events[type].length) {
      if (elem.removeEventListener) {
        elem.removeEventListener(type, data(elem, 'handle'), false);
      } else if (elem.detachEvent) {
        elem.detachEvent('on' + type, data(elem, 'handle'));
      }
      delete events[type];
    }
  });
}
function triggerEvent(elem, type, ev) {
  var handle = data(elem, 'handle');
  if (handle) {
    setTimeout(function() {
      handle.call(elem, extend((ev || {}), {type: type, target: elem}))
    }, 0);
  }
}
function cancelEvent(event) {
  event = (event || window.event);
  if (!event) return false;
  event = (event.originalEvent || event);
  if (event.preventDefault) event.preventDefault();
  if (event.stopPropagation) event.stopPropagation();
  event.cancelBubble = true;
  event.returnValue = false;
  return false;
}
function _eventHandle(event) {
  event = event || window.event;

  var originalEvent = event;
  event = clone(originalEvent);
  event.originalEvent = originalEvent;

  if (!event.target) {
    event.target = event.srcElement || document;
  }

  // check if target is a textnode (safari)
  if (event.target.nodeType == 3) {
    event.target = event.target.parentNode;
  }

  if (!event.relatedTarget && event.fromElement) {
    event.relatedTarget = event.fromElement == event.target;
  }

  if (event.pageX == null && event.clientX != null) {
    var doc = document.documentElement, body = bodyNode || document.body;
    event.pageX = event.clientX + (doc && doc.scrollLeft || body && body.scrollLeft || 0) - (doc.clientLeft || 0);
    event.pageY = event.clientY + (doc && doc.scrollTop || body && body.scrollTop || 0) - (doc.clientTop || 0);
  }

  if (!event.which && ((event.charCode || event.charCode === 0) ? event.charCode : event.keyCode)) {
    event.which = event.charCode || event.keyCode;
  }

  if (!event.metaKey && event.ctrlKey) {
    event.metaKey = event.ctrlKey;
  }

  // click: 1 == left; 2 == middle; 3 == right
  if (!event.which && event.button) {
    event.which = (event.button & 1 ? 1 : ( event.button & 2 ? 3 : ( event.button & 4 ? 2 : 0 ) ));
  }

  var handlers = data(this, 'events');
  if (!handlers || typeof(event.type) != 'string' || !handlers[event.type] || !handlers[event.type].length) {
    return;
  }

  for (var i in (handlers[event.type] || [])) {
    if (event.type == 'mouseover' || event.type == 'mouseout') {
      var parent = event.relatedElement;
      while (parent && parent != this) {
        try { parent = parent.parentNode; }
        catch(e) { parent = this; }
      }
      if (parent == this) {
        continue
      }
    }
    var ret = handlers[event.type][i].apply(this, arguments);
    if (ret === false) {
      cancelEvent(event);
    }
  }
}

function normEvent(event) {
  event = event || window.event;

  var originalEvent = event;
  event = clone(originalEvent);
  event.originalEvent = originalEvent;

  if (!event.target) {
    event.target = event.srcElement || document;
  }

  // check if target is a textnode (safari)
  if (event.target.nodeType == 3) {
    event.target = event.target.parentNode;
  }

  if (!event.relatedTarget && event.fromElement) {
    event.relatedTarget = event.fromElement == event.target;
  }

  if (event.pageX == null && event.clientX != null) {
    var doc = document.documentElement, body = bodyNode;
    event.pageX = event.clientX + (doc && doc.scrollLeft || body && body.scrollLeft || 0) - (doc.clientLeft || 0);
    event.pageY = event.clientY + (doc && doc.scrollTop || body && body.scrollTop || 0) - (doc.clientTop || 0);
  }

  if (!event.which && ((event.charCode || event.charCode === 0) ? event.charCode : event.keyCode)) {
    event.which = event.charCode || event.keyCode;
  }

  if (!event.metaKey && event.ctrlKey) {
    event.metaKey = event.ctrlKey;
  } else if (!event.ctrlKey && event.metaKey && browser.mac) {
    event.ctrlKey = event.metaKey;
  }

  // click: 1 == left; 2 == middle; 3 == right
  if (!event.which && event.button) {
    event.which = (event.button & 1 ? 1 : ( event.button & 2 ? 3 : ( event.button & 4 ? 2 : 0 ) ));
  }

  return event;
}

// Prevent memory leaks in IE
addEvent(window, 'unload', function() {
  for (var id in vkCache) {
    if (vkCache[id].handle && vkCache[id].handle.elem != window) {
      removeEvent(vkCache[id].handle.elem);
    }
  }
});

function onCtrlEnter(ev, handler) {
  ev = ev || window.event;
  if (ev.keyCode == 10 || ev.ctrlKey && ev.keyCode == 13) {
    handler();
  }
}

var layoutWidth = 791;
function domStarted() {
  window.headNode = geByTag1('head');
  var bl = ge('box_layer_bg'), blw = bl.nextSibling;
  extend(window, {
    icoNode:  geByTag1('link', headNode),
    bodyNode: geByTag1('body'),
    htmlNode: geByTag1('html'),
    utilsNode: ge('utils'),
    boxLayerBG: bl,
    boxLayerWrap: blw,
    boxLayer: blw.firstChild,
    boxLoader: blw.firstChild.firstChild,
    __afterFocus: false,
    __needBlur: false
  });
  if (!utilsNode) return;

  for (var i in StaticFiles) {
    var f = StaticFiles[i];
    f.l = 1;
    if (f.t == 'css') {
      utilsNode.appendChild(ce('div', {id: f.n}));
    }
  }

  hab.init();
}
function domReady() {
  if (!utilsNode) return;


  extend(window, {
    pageNode: document.body
  });

  window.scrollNode = browser.msie6 ? pageNode : ((browser.chrome || browser.safari) ? bodyNode : htmlNode);

  onBodyResize();

  var scrolledNode = browser.msie6 ? pageNode : window;
}
function onDomReady(f) {
  f();
}

// Ajax
function serializeForm(form) {
  if (typeof(form) != 'object') {
    return false;
  }
  var result = {};
  var g = function(n) {
    return geByTag(n, form);
  };
  var nv = function(i, e){
    if (!e.name) return;
    if (e.type == 'text' || !e.type) {
      result[e.name] = val(e);
    } else {
      result[e.name] = (browser.msie && !e.value && form[e.name]) ? form[e.name].value : e.value;
    }
  };
  each(g('input'), function(i, e) {
    if ((e.type != 'radio' && e.type != 'checkbox') || e.checked) return nv(i, e);
  });
  each(g('select'), nv);
  each(g('textarea'), nv);

  return result;
}

function ajx2q(qa) {
  var query = [], enc = function (str) {
    try {
      return encodeURIComponent(str);
    } catch (e) { return str;}
  };

  for (var key in qa) {
    if (qa[key] == null || isFunction(qa[key])) continue;
    if (isArray(qa[key])) {
      for (var i = 0, c = 0; i < qa[key].length; ++i) {
        if (qa[key][i] == null || isFunction(qa[key][i])) {
          continue;
        }
        query.push(enc(key) + '[' + c + ']=' + enc(qa[key][i]));
        ++c;
      }
    } else {
      query.push(enc(key) + '=' + enc(qa[key]));
    }
  }
  query.sort();
  return query.join('&');
}
function q2ajx(qa) {
  if (!qa) return {};
  var query = {}, dec = function (str) {
    try {
      return decodeURIComponent(str);
    } catch (e) { return str;}
  };
  qa = qa.split('&');
  each(qa, function(i, a) {
    var t = a.split('=');
    if (t[0]) {
      var v = dec(t[1] + '');
      if (t[0].substr(t.length - 2) == '[]') {
        var k = dec(t[0].substr(0, t.length - 2));
        if (!query[k]) {
          query[k] = [];
        }
        query[k].push(v);
      } else {
        query[dec(t[0])] = v;
      }
    }
  });
  return query;
}

var stManager = {
  _add: function(f, old) {
    var name = f.replace(/[\/\.]/g, '_');
    if (old && old.l && old.t == 'css') {
      var elem = ce('style', {
        type: 'text/css',
        media: 'screen'
      });
      headNode.appendChild(elem);
      var text = '#' + name + ' { display: block; }';
      if (elem.sheet) {
        elem.sheet.insertRule(text, 0);
      } else if (elem.styleSheet) {
        elem.styleSheet.cssText = text;
      }
    }
    StaticFiles[f] = {v: stVersions[f], n: name, l: 0, c: 0};
    var f_full = f + '?' + stVersions[f];
    if (f.indexOf('.js') != -1) {
      var p = 'js/';
      if (stTypes.fromLib[f]) {
        p += 'lib/';
      } else if (!/^lang\d/i.test(f) && !stTypes.fromRoot[f] && f.indexOf('api')) {
        p += 'al/';
      }
      headNode.appendChild(ce('script', {
        type: 'text/javascript',
        src: p + f_full
      }));

      StaticFiles[f].t = 'js';
    } else if (f.indexOf('.css') != -1) {
      var p = 'css/' + (stTypes.fromRoot[f] ? '' : 'al/');
      headNode.appendChild(ce('link', {
        type: 'text/css',
        rel: 'stylesheet',
        href: p + f_full
      }));

      StaticFiles[f].t = 'css';

      if (!ge(name)) {
        utilsNode.appendChild(ce('div', {id: name}));
      }
    }
  },

  add: function(files, callback) {
    var wait = [], de = document.documentElement;
    if (!isArray(files)) files = [files];
    for (var i in files) {
      var f = files[i];
      if (f.indexOf('?') != -1) {
        f = f.split('?')[0];
      }
      if (/^lang\d/i.test(f)) {
        stVersions[f] = stVersions['lang'];
      } else if (!stVersions[f]) {
        stVersions[f] = 1;
      }
      var old = StaticFiles[f];
      if (!old || old.v != stVersions[f]) {
        stManager._add(f, old);
      }
      if (callback && !StaticFiles[f].l) {
        wait.push(f);
      }
    }
    if (!callback) return;
    if (!wait.length) {
      return callback();
    }
    var waiter = function() {
      var nwait = [];
      for (var i in wait) {
        var f = wait[i];
        if (!StaticFiles[f].l && StaticFiles[f].t == 'css' && getStyle(StaticFiles[f].n, 'display') == 'none') {
          if (stVersions[f] < 0) {
            topMsg('<b>Warning:</b> Something is bad, please <b><a href="/techsupp.php?fid=1&act=t&tid=497998">clear your cache</a></b> and restart your browser.', 10);
          }
          StaticFiles[f].l = 1;
        }
        if (!StaticFiles[f].l) {
          if (++StaticFiles[f].c > 150) { // Can't load for 15 seconds.
            if (stVersions[f] < 0) {
              topError('<b>Error:</b> Could not load <b>' + f + '</b>.', 3);
              StaticFiles[f].l = 1;
            } else {
              topMsg('Some problems with loading <b>' + f + '</b>...', 3);
              stVersions[f] = irand(-10000, -1);
              stManager._add(f, StaticFiles[f]);
            }
          }
        }
        if (!StaticFiles[f].l) {
          nwait.push(f);
        }
      }
      wait = nwait;
      if (wait.length) {
        return setTimeout(arguments.callee, 100);
      }
      callback();
    }
    setTimeout(waiter, 1);
  },
  done: function(f) {
    StaticFiles[f].l = 1;
  }
}

function requestBox(box, onDone, onFail) {
  box.setOptions({onHide: onFail});
  box.onDone = function() {
    box.setOptions({onHide: false});
    onDone();
  }
  return box;
}
function activateMobileBox(opts) {
  return requestBox(showBox('activation.php', {
    act: 'activate_mobile_box',
    hash: opts.hash
  }), function() {
    vk.nophone = 0;
    opts.onDone();
  }, opts.onFail);
}

var ajaxCache = {};
var globalAjaxCache = {};
var ajax = {
  _init: function() {
    var r = false;
    try {
      if (r = new XMLHttpRequest()) {
        ajax._req = function() { return new XMLHttpRequest(); }
        return;
      }
    } catch(e) {}
    each(['Msxml2.XMLHTTP', 'Microsoft.XMLHTTP'], function() {
      try {
        var t = '' + this;
        if (r = new ActiveXObject(t)) {
          (function(n) {
            ajax._req = function() { return new ActiveXObject(n); }
          })(t);
          return false;
        }
      } catch(e) {}
    });
    if (!ajax._req) {
      location.replace('/badbrowser.php');
    }
  },
  _getreq: function() {
    if (!ajax._req) ajax._init();
    return ajax._req();
  },
  _frameover: function() {
    var node = iframeTransport.parentNode;
    node.innerHTML = '';
    utilsNode.removeChild(node);
    iframeTransport = false;
    ajax.framegot(false);
    if (cur.onFrameBlocksDone) {
      cur.onFrameBlocksDone();
    }
  },
  _receive: function(cont, html, js) {
    cont = cont && ge(cont);
    if (cont && html) {
      html = ce('div', {innerHTML: html});
      while (html.firstChild) {
        cont.appendChild(html.firstChild);
      }
    }
    if (js) {
      eval('(function(){' + js + ';})()');
    }
    ajax._framenext();
  },
  framedata: false,
  _framenext: function() {
    if (!(ajax.framedata || {}).length) return;
    var d = ajax.framedata.shift();
    if (d === true) {
      ajax._framenext();
    } else if (d === false) {
      ajax.framedata = false;
    } else {
      setTimeout(ajax._receive.pbind(d[0], d[1], d[2]), 0);
    }
  },
  framegot: function(c, h, j) {
    if (!ajax.framedata) return;
    ajax.framedata.push((h === undefined && j === undefined) ? c : [c, h, j]);
    if (ajax.framedata.length === 1) {
      ajax._framenext();
    }
  },
  framepost: function(url, query, done) {
    if (window.iframeTransport) {
      ajax._frameover();
    }
    window.iframeTransport = utilsNode.appendChild(ce('div', {innerHTML: '<iframe></iframe>'})).firstChild;
    ajax.framedata = [true];
    ajax._framedone = done;
    iframeTransport.src = url + '?' + ((typeof(query) != 'string') ? ajx2q(query) : query);
  },
  plainpost: function(url, query, done, fail) {
    var r = ajax._getreq();
    var q = (typeof(query) != 'string') ? ajx2q(query) : query;
    r.onreadystatechange = function() {
      if (r.readyState == 4) {
        if (r.status >= 200 && r.status < 300) {
          if (done) done(r.responseText, r);
        } else if (r.status) {
          if (fail) fail(r.responseText, r);
        }
      }
    }
    try {
      r.open('POST', url, true);
    } catch(e) {
      topMsg('<b>Ajax Error:</b> ' + e.message);
    }
    r.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    r.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    r.send(q);
    return r;
  },
  post: function(url, query, options) {
    if (url.substr(0, 1) != '/') url = '/' + url;
    var o = extend({_captcha: false, _box: false}, options || {}), q = extend({al: o.frame ? -1 : 1}, query);
    if (o.progress) {
      if (!o.showProgress) {
        o.showProgress = show.pbind(o.progress);
      }
      if (!o.hideProgress) {
        o.hideProgress = hide.pbind(o.progress);
      }
    }
    return ajax._post(url, q, o);
  },
  preload: function(url, query, data) {
    if (url.substr(0, 1) != '/') url = '/' + url;
    ajaxCache[url + '#' + ajx2q(query)] = data;
  },
  _debugLog: function(text) {
     window._updateDebug = function() {
       var dlw = ge('debuglogwrap');
       if (dlw) {
         dlw.innerHTML = text;
         window._updateDebug = false;
       }
     }
  },
  _parseRes: function(answer) {
    window._updateDebug = false;
    for (var i = 0; i < answer.length; ++i) {
      var ans = answer[i];
      if (ans.substr(0, 2) == '<!') {
        var from = ans.indexOf('>');
        var type = ans.substr(2, from - 2);
        ans = ans.substr(from + 1);
        switch (type) {
        case 'json' : answer[i] = eval('(' + ans + ')'); break;
        case 'int'  : answer[i] = intval(ans); break;
        case 'float': answer[i] = floatval(ans); break;
        case 'bool' : answer[i] = intval(ans) ? true : false; break;
        case 'null' : answer[i] = null; break;
        case 'debug':
          ajax._debugLog(ans);
          answer.pop(); // <!debug> must be last one
        break;
        }
      }
    }
  },
  _post: function(url, q, o) {
    if (!q.captcha_sid && o.showProgress) o.showProgress();
    var cacheKey = false;
    extend(q, __adsGetAjaxParams(q, o));
    if (o.cache) {
      var boldq = clone(q);
      delete boldq.al;
      delete boldq.al_ad;
      delete boldq.ads_section;
      delete boldq.captcha_sid;
      delete boldq.captcha_key;
      cacheKey = url + '#' + ajx2q(boldq);
    }
    var hideBoxes = function() {
      for (var i = 0; i < arguments.length; ++i) {
        var box = arguments[i];
        if (box && box.isVisible()) {
          box.setOptions({onHide: false});
          box.hide();
        }
      }
      return false;
    }
    var fail = function(text) {
      if (o.hideProgress) o.hideProgress();
      if (o._suggest) cleanElems(o._suggest);
      o._suggest = o._captcha = o._box = hideBoxes(o._box, o._captcha);
      if (isFunction(o.onFail)) {
        if (o.onFail(text)) {
          return;
        }
      }
      topError(text);
    }
    // Process response function
    var processResponse = function(code, answer) {
      if (o.cache && !o.forceGlobalCache) {
        if (!code) {
          ajaxCache[cacheKey] = answer;
        }
        if (o.cache === 2) {
          return;
        }
      }

      // Parse response

      if (o.hideProgress) o.hideProgress();
      o._box = hideBoxes(o._box);
      if (o._captcha && code != 2) {
        if (o._suggest) cleanElems(o._suggest);
        o._suggest = o._captcha = hideBoxes(o._captcha);
      }
      switch (code) {
      case 1: // email not confirmed
        if (ge('confirm_mail')) {
          showFastBox({
            width: 430,
            title: ge('confirm_mail_title').value,
            onHide: o.onFail
          }, '<div class="confirm_mail">' + ge('confirm_mail').innerHTML + '</div>');
        } else {
          topMsg('<b>Error!</b> Email is not confirmed!');
        }
        break;
      case 2: // captcha
        var resend = function(sid, key) {
          var nq = extend(q, {captcha_sid: sid, captcha_key: key});
          var no = o.cache ? extend(o, {cache: -1}) : o;
          ajax._post(url, nq, no);
        }
        var addText = '';
        if (vk.nophone == 1 && !vk.nomail) {
          addText = getLang('global_try_to_activate').replace('{link}', '<a class="phone_validation_link">').replace('{/link}', '</a>');
          addText = '<div class="phone_validation_suggest">' + addText + '</div>';
        }
        o._captcha = showCaptchaBox(answer[0], intval(answer[1]), o._captcha, {
          onSubmit: resend,
          addText: addText,
          onHide: function() {
            if (o.onFail) o.onFail();
          }
        });
        if (o._captcha && o._captcha.bodyNode && (o._suggest = geByClass1('phone_validation_link', o._captcha.bodyNode))) {
          addEvent(o._suggest, 'click', function() {
            o._box = activateMobileBox({onDone: o._captcha.submit});
          });
        }
        break;
      case 3: // auth failed
        var no = o.cache ? extend(o, {cache: -1}) : o;
        window.onReLoginDone = ajax._post.pbind(url, q, no);
        window.onReLoginFailed = function(toRoot) {
          if (toRoot === -1) {
            location.href = location.href.replace(/^http:/, 'https:');
          } else if (toRoot) {
            nav.go('/');
          } else {
            window.onReLoginDone();
          }
        }
        var iframe = ce('iframe', {src: vk.loginscheme + '://login.vk.com/?role=al_frame&_origin=' + (locProtocol + '//' + locHost) + '&ip_h=' + (answer[0] || vk.ip_h)}), t = 0;
        utilsNode.appendChild(iframe);
        break;
      case 4: // redirect
        if (answer[1]) { // ajax layout redirect
          nav.go(answer[0]);
        } else {
          hab.stop();
          location.href = answer[0];
        }
        break;
      case 5: // reload
        nav.reload({force: intval(answer[0])}); // force reload
        break;
      case 6: // mobile activation needed
        var no = o.cache ? extend(o, {cache: -1}) : o;
        o._box = activateMobileBox({onDone: ajax._post.pbind(url, q, no), onFail: o.onFail, hash: answer[0]});
        break;
      case 7: // message
        if (o.onFail) o.onFail();
        topMsg(answer[0], 10);
        break;
      case 8: // error
        if (o.onFail) {
          if (o.onFail(answer[0])) {
            return;
          }
        }
        topError(answer[0], answer[1] ? 0 : 10);
        break;
      case 9: // votes payment
        o._box = showFastBox(answer[0], answer[1]);
        var no = extend(clone(o), {showProgress: o._box.showProgress, hideProgress: o._box.hideProgress});
        if (o.cache) {
          no.cache = -1;
        }
        o._box = requestBox(o._box, function() {
          if (isVisible(o._box.progress)) return;
          ajax._post(url, extend(q, {_votes_ok: 1}), no);
        }, o.onFail);
        var f = eval('((function() { return function() { var box = this; ' + (answer[2] || '') + ' ;}; })())');
        f.apply(o._box);
        break;
      case 10: //zero zone
        o._box = showFastBox({
          title: answer[0] || getLang('global_charged_zone_title'),
          onHide: o.onFail
        }, answer[1], getLang('global_charged_zone_continue'), function() {
          var nq = extend(q, {charged_confirm: answer[3]});
          ajax._post(url, nq, o);
        }, getLang('global_cancel'));
        break;
      default:
        if (code == -1 || code == -2) {
          var adsShowed  = answer.pop();
          var adsCanShow = answer.pop();
          var adsHtml    = answer.pop();
          __adsSet(adsHtml, null, adsCanShow, adsShowed);
        }
        if (o.onDone) { // page, box or other
          o.onDone.apply(window, answer);
        }
        break;
      }
      if (window._updateDebug) _updateDebug();
    }
    var done = function(text, data) { // data - for iframe transport post
      if (!trim(text).length) {
        data = [8, getLang('global_unknown_error')];
        text = stVersions['nav'] + '<!><!>' + vk.lang + '<!>' + stVersions['lang'] + '<!>8<!>' + data[1];
      }

      var answer = text.split('<!>');

      var navVersion = intval(answer.shift());
      if (!navVersion) {
        return fail(text);
      }

      // First strict check for index.php reloading, in vk.al == 1 mode.
      if (vk.version && vk.version != navVersion) {
        if (navVersion && answer.length > 4) {
          nav.reload({force: true});
        } else {
          if (nav.strLoc) {
            location.replace(locBase);
          } else {
            topError('Server error.');
          }
        }
        return;
      }
      vk.version = false;

      // Common response fields
      var newStatic = answer.shift();
      var langId = intval(answer.shift());
      var langVer = intval(answer.shift());

      if (o.frame) answer = data;

      var code = intval(answer.shift());
      if (vk.lang != langId && o.canReload) { // Lang changed
        nav.reload({force: true});
        return;
      }

      // Wait for attached static files
      var waitResponseStatic = function() {
        //var st = ['lite.css'];
        var st = [];
        if (newStatic) {
          newStatic = newStatic.split(',');
          for (var i = 0; i < newStatic.length; ++i) {
            st.push(newStatic[i]);
          }
        }
        if (stVersions['lang'] < langVer) {
          stVersions['lang'] = langVer;
          for (var i in StaticFiles) {
            if (/^lang\d/i.test(i)) {
              st.push(i);
            }
          }
        }

        if (!o.frame) {
          try {
            ajax._parseRes(answer);
          } catch(e) {
            topError('<b>JSON Error:</b> ' + e.message);
          }
        }
        stManager.add(st, processResponse.pbind(code, answer));
      }

      // Static managing function
      if (navVersion <= stVersions['nav']) {
        return waitResponseStatic();
      }
      headNode.appendChild(ce('script', {
        type: 'text/javascript',
        src: '/js/loader_nav' + navVersion + '_' + vk.lang + '.js'
      }));
      setTimeout(function() {
        if (navVersion <= stVersions['nav']) {
          return waitResponseStatic();
        }
        setTimeout(arguments.callee, 100);
      }, 0);
    }
    if (o.cache > 0 || o.forceGlobalCache) {
      var answer = ajaxCache[cacheKey];
      if (answer && !o.forceGlobalCache) {
        processResponse(0, answer);
        return;
      } else if (answer = globalAjaxCache[cacheKey]) {
        if (answer == -1) {
          globalAjaxCache[cacheKey] = o.onDone;
        } else {
          o.onDone.apply(window, answer);
        }
        return;
      }
    }
    return o.frame ? ajax.framepost(url, q, done) : ajax.plainpost(url, q, done, fail);
  }
}

function HistoryAndBookmarks(params) {
  // strict check for cool hash display in ff.
  var fixEncode = function(loc) {
    var h = loc.split('#');
    var l = h[0].split('?');
    return l[0] + (l[1] ? ('?' + ajx2q(q2ajx(l[1]))) : '') + (h[1] ? ('#' + h[1]) : '');
  }

  var frame = null, withFrame = browser.msie6 || browser.msie7;
  var frameDoc = function() {
    return frame.contentDocument || (frame.contentWindow ? frame.contentWindow.document : frame.document);
  }

  var options = extend({onLocChange: function() {}}, params);

  var getLoc = function(skipFrame) {
    var loc = '';
    if (vk.al == 3) {
      loc = (location.pathname || '') + (location.search || '') + (location.hash || '');
    } else {
      if (withFrame && !skipFrame) {
        try {
          loc = frameDoc().getElementById('loc').innerHTML.replace(/&lt;/ig, '<').replace(/&gt;/ig, '>').replace(/&quot;/ig, '"').replace(/&amp;/ig, '&');
        } catch(e) {
          loc = curLoc;
        }
      } else {
        loc = browser.msie6 ? ((location.toString().match(/#(.*)/) || {})[1] || '') : location.hash.replace(/^#/, '');
        if (loc.substr(0, 1) != vk.navPrefix) {
          loc = (location.pathname || '') + (location.search || '') + (location.hash || '');
        }
      }
    }
    if (!loc && vk.al > 1) {
      loc = (location.pathname || '') + (location.search || '');
    }
    return fixEncode(loc.replace(/^(\/|!)/, ''));
  }

  var curLoc = getLoc(true);

  var setFrameContent = function(loc) {
    try {
      var d = frameDoc();
      d.open();

      d.write('<div id="loc">' +
          loc.replace('&', '&amp;').replace('"', '&quot;').replace('>', '&gt;').replace('<', '&lt;') +
        '</div>'
      );

      d.close();
    } catch(e) {}
  }

  var setLoc = function(loc) {
    //curLoc = fixEncode(loc.replace(/#(\/|!)?/, ''));
    curLoc = fixEncode(loc);
    var l = (location.toString().match(/#(.*)/) || {})[1] || '';
    if (!l && vk.al > 1) {
      l = (location.pathname || '') + (location.search || '');
    }
    l = fixEncode(l);
    if (l.replace(/^(\/|!)/, '') != curLoc) {
      if (vk.al == 3) {
        try {
          history.pushState({}, '', '/' + curLoc);
          return;
        } catch(e) {}
      }
      window.chHashFlag = true;
      location.hash = '#' + vk.navPrefix + curLoc;
      if (withFrame && getLoc() != curLoc) {
        setFrameContent(curLoc);
      }
    }
  }

  var locChecker = function() {
    var loc = getLoc(true);
    if (loc != curLoc) {
      setFrameContent(loc);
    }
  }

  var checker = function(force) {
    var l = getLoc();
    if (l == curLoc && force !== true) {
      return;
    }

    options.onLocChange(l);

    curLoc = l;
    if (withFrame && location.hash.replace('#' + vk.navPrefix, '') != l) {
      location.hash = '#' + vk.navPrefix + l;
    }
  }
  var checkTimer;
  var frameChecker = function() {
    try {
      if (frame.contentWindow.document.readyState != 'complete') {
        return;
      }
    } catch(e) {
      return;
    }
    checker();
  }
  var init = function() {
    if (vk.al == 1) {
      checker(true);
    }
    if (vk.al < 3) {
      if (withFrame) {
        frame = document.createElement('iframe');
        frame.id = 'hab_frame';
        frame.attachEvent('onreadystatechange', frameChecker);
        frame.src = 'al_loader.php?act=hab_frame&loc=' + encodeURIComponent(curLoc) + '&domain=' + encodeURIComponent(locDomain);

        utilsNode.appendChild(frame);

        checkTimer = setInterval(locChecker, 200);
      } else {
        if ('onhashchange' in window) {
          addEvent(window, 'hashchange', function() {
            if (window.chHashFlag) {
              window.chHashFlag = false;
            } else {
              checker();
            }
          });
        } else {
          checkTimer = setInterval(checker, 200);
        }
      }
    } else if (vk.al == 3) {
      addEvent(window, 'popstate', checker);
    }
  }

  return {
    setLoc: setLoc,
    getLoc: getLoc,
    init: init,
    setOptions: function(params) {
      options = extend(options, params);
    },
    checker: checker,
    stop: function() {
      if (vk.al < 3) {
        clearInterval(checkTimer);
        if (withFrame) {
          frame.detachEvent('onreadystatechange', frameChecker);
        }
      } else if (vk.al == 3) {
        removeEvent(window, 'popstate', checker);
      }
    }
  }
}

window.hab = new HistoryAndBookmarks({onLocChange: function(loc) {
  nav.go('/' + loc, undefined, {back: true});
}});

function checkEvent(e) {
  return (e && (e.which > 1 || e.button > 1 || e.ctrlKey));
}


function processDestroy(c) {
  if (c._back && c._back.hide && c == cur) {
    for (var i in c._back.hide) {
      try {c._back.hide[i]();}catch(e){}
    }
  }
  if (!c.destroy || !c.destroy.length) return;
  for (var i in c.destroy) {
    try {c.destroy[i](c);}catch(e){}
  }
}

var nav = {
  getData: function(loc) {
    if (loc.length) {
      for (var i in navMap) {
        if (i[0] == '<') continue;
        var m = loc.match(new RegExp('^' + i, 'i'));
        if (m) {
          return {url: navMap[i][0], files: navMap[i][1]};
        }
      }
      var m = loc.match(/^[a-z0-9\-_]+\.php$/i);
      if (m) {
        return {url: loc};
      }
      return {url: navMap['<other>'][0], files: navMap['<other>'][1]};
    }
    return {url: navMap['<void>'][0], files: navMap['<void>'][1]};
  },
  reload: function(opts) {
    opts = opts || {};
    if (opts.force) {
      hab.stop();
      location.href = '/' + nav.strLoc;
    } else {
      nav.go('/' + nav.strLoc, undefined, extend({nocur: true}, opts));
    }
  },
  go: function(loc, ev, opts) {
    return;
    if (checkEvent(ev)) return;
    if (cur.noNavGo && !opts.force) return;
    if (loc.tagName && loc.tagName.toLowerCase() == 'a' && loc.href) {
      loc = loc.href;
    }
    var strLoc = '', objLoc = {};
    if (typeof(loc) == 'string') {
      loc = loc.replace(new RegExp('^(http://' + locHost + ')?/?', 'i'), '');
      strLoc = loc;
      objLoc = nav.fromStr(loc);
    } else {
      if (!loc[0]) loc[0] = '';
      strLoc = nav.toStr(loc);
      objLoc = loc;
    }

    opts = opts || {};
    if (!opts.nocur) {
      var changed = clone(objLoc);
      for (var i in nav.objLoc) {
        if (nav.objLoc[i] == changed[i]) {
          delete(changed[i]);
        } else if (changed[i] === undefined) {
          changed[i] = false;
        }
      }
      if (zNav(clone(changed)) === false) {
        return false;
      }
      for (var i in (cur.nav || {})) {
        if (cur.nav[i](clone(changed), nav.objLoc, objLoc, opts) === false) {
          return false;
        }
      }
    }
    if (vk.al == 4) {
      location.href = '/' + strLoc;
      return false;
    }
    if (opts.back) {
      for (var i = 0, l = globalHistory.length; i < l; ++i) {
        if (globalHistory[i].loc == strLoc) {
          var h = globalHistory.splice(i, 1)[0];
          var wNode = ge('wrap3'), tNode = ge('title');

          if (window.tooltips) tooltips.destroyAll();
          processDestroy(cur);
          radioBtns = h.radioBtns;
          ajaxCache = h.ajaxCache;
          boxQueue.hideAll();

          cur = h.cur;
          setTimeout(function() {
            wNode.innerHTML = '';
            wNode.parentNode.replaceChild(h.content, wNode);
            document.title = h.htitle;
            tNode.innerHTML = h.title;
            setStyle(tNode.parentNode, 'display', h.hideHeader ? 'none' : 'block');
            for (var i = 0, l = cur._back.show.length; i < l; ++i) cur._back.show[i]();
            nav.setLoc(strLoc);
            var b = h.back || {};
          }, 20);
          return false;
        }
      }
    }

    var dest = objLoc[0];
    delete(objLoc[0]);

    var where = nav.getData(dest);
    if (where.files) {
      stManager.add(where.files);
    }
    where.params = extend({__query: dest, al_id: vk.id}, objLoc);
    var done = function(title, html, js, params) {
      if (stVersions['lite.js'] > StaticFiles['lite.js'].v) {
        nav.setLoc(params.loc || '');
        location.reload(true);
        return;
      }
      var newPage = (where.params.al_id === undefined) || (where.params.al_id != params.id);
      var _back = (strLoc != (cur._back || {}).loc) && cur._back, wNode = ge('wrap3'), tNode = ge('title'), hist = false;

      if (window.tooltips) tooltips.destroyAll();
      processDestroy(cur);
      if (window.globalHistory && globalHistory.length) {
        var h = globalHistory.shift();
        processDestroy(h.cur);
        h.content.innerHTML = '';
      }
      radioBtns = {};
      ajaxCache = {};
      boxQueue.hideAll();

      cur = {destroy: [], nav: []};
      if (newPage) {
        cleanElems('quick_login_button', 'quick_expire', 'search_form', 'top_links', 'bottom_nav')
        while(globalHistory.length) processDestroy(globalHistory.shift().cur);
        pageNode.innerHTML = html;
      } else {
        if (_back) {
          var newW = ce('div', {id: 'wrap3'});
          extend(hist, {
            content: wNode.parentNode.replaceChild(newW, wNode),
            title: tNode.innerHTML
          });
          globalHistory.push(hist);
          wNode = newW;
        }
        if (window.wNode && window.tNode) {
          wNode.innerHTML = html;
          tNode.innerHTML = title;
          (title ? show : hide)(tNode.parentNode);
        }
      }

      if (!opts.noscroll && !params.noscroll) scrollToTop(0);
      eval('(function(){' + js + ';})()');

      ajax._framenext();

      setTimeout(nav.setLoc.pbind(params.loc || ''), browser.chrome ? 100 : 50);
    }
    ajax.post(where.url, where.params, {onDone: function() {
      var a = arguments;
      if (__debugMode) {
        done.apply(null, a);
      } else try {
        done.apply(null, a);
      } catch (e) {
        topError(e, 15);
      }
    }, onFail: opts.onFail || function(text) {
      if (!text) return;

      setTimeout(showFastBox(getLang('global_error'), text).hide, 2000);
      return true;
    }, frame: opts.noframe ? 0 : 1, canReload: true});
    return false;
  },
  setLoc: function(loc) {
    if (typeof(loc) == 'string') {
      nav.strLoc = loc;
      nav.objLoc = nav.fromStr(loc);
    } else {
      nav.strLoc = nav.toStr(loc);
      nav.objLoc = loc;
    }
    hab.setLoc(nav.strLoc);
  },
  change: function(loc, ev, opts) {
    var params = clone(nav.objLoc);
    each(loc, function(i,v) {
      if (v === false) {
        delete params[i];
      } else {
        params[i] = v;
      }
    });
    return nav.go(params, ev, opts);
  },
  fromStr: function(str) {
    str = str.split('#');
    var res = str[0].split('?');
    var param = {'0': res[0] || ''}
    if (str[1]) {
      param['#'] = str[1];
    }
    return extend(q2ajx(res[1] || ''), param);
  },
  toStr: function(obj) {
    obj = clone(obj);
    var hash = obj['#'] || '';
    var res = obj[0] || '';
    delete(obj[0]);
    delete(obj['#']);
    var str = ajx2q(obj);
    return (str ? (res + '?' + str) : res) + (hash ? ('#' + hash) : '');
  },
  init: function() {
    nav.strLoc = hab.getLoc();
    nav.objLoc = nav.fromStr(nav.strLoc);
  }
}

nav.init();

/**
 * Cookies
 **/

var _cookies;
function _initCookies() {
  _cookies = {};
  var ca = document.cookie.split(';');
  var re = /^[\s]*([^\s]+?)$/i;
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i].split('=');
    if (c.length == 2) {
     _cookies[c[0].match(re)[1]] = unescape(c[1].match(re) ? c[1].match(re)[1] : '');
    }
  }
}
function getCookie(name) {
  _initCookies();
  return _cookies[name];
}
function setCookie(name, value, days) {
  var expires = '';
  if (days) {
    var date = new Date();
    date.setTime(date.getTime()+(days*24*60*60*1000));
    expires = '; expires='+date.toGMTString();
  }
  var domain = locDomain;
  document.cookie = name + '='+escape(value) + expires + '; path=/' + (domain ? '; domain=.' + domain : '');
}

/**
 * Other stuff
 **/

function parseLatin(text){
  var outtext = text;
  var lat1 = ['yo','zh','kh','ts','ch','sch','shch','sh','eh','yu','ya','YO','ZH','KH','TS','CH','SCH','SHCH','SH','EH','YU','YA',"'"];
  var rus1 = ['�', '�', '�', '�', '�', '�',  '�',   '�', '�', '�', '�', '�', '�', '�', '�', '�', '�',  '�',   '�', '�', '�', '�', '�'];
  for (var i = 0; i < lat1.length; i++) {
    outtext = outtext.split(lat1[i]).join(rus1[i]);
  }
  var lat2 = 'abvgdezijklmnoprstufhcyABVGDEZIJKLMNOPRSTUFHCY¸¨';
  var rus2 = '������������������������������������������������';
  for (var i = 0; i < lat2.length; i++) {
    outtext = outtext.split(lat2.charAt(i)).join(rus2.charAt(i));
  }
  return (outtext == text) ? null : outtext;
}

function __phCheck(el, back, focus, blur) {
  var val = el.value, shown = el.phshown, ph = el.phcont;

  if (shown && (back && val || !back && (focus || val))) {
    hide(ph);
    el.phshown = false;
  } else if (!shown && !val && (back || blur)) {
    show(ph);
    el.phshown = true;
  }
  if (back && !val) {
    if (focus) {
      clearTimeout(el.phanim);
      el.phanim = setTimeout(function() {
        animate(ph.firstChild.firstChild, {color: '#C0C8D0'}, 200);
      }, 100);
    }
    if (blur) {
      clearTimeout(el.phanim);
      el.phanim = setTimeout(function() {
        animate(ph.firstChild.firstChild, {color: '#777777'}, 200);
      }, 100);
    }
  }
}
function placeholderSetup(id, opts) {
  var el = ge(id), ph, o = opts ? clone(opts) : {};
  if (!el || (el.phevents && !o.reload) || !(ph = (el.getAttribute('placeholder') || el.placeholder))) {
    return;
  }

  el.setAttribute('placeholder', '');

  var pad = {}, dirs = ['Top', 'Bottom', 'Left', 'Right'];
  if (o.pad) {
    pad = o.pad;
  } else {
    if (o.fast) {
      for (var i = 0; i < 4; ++i) {
        pad['padding' + dirs[i]] = 3;
        pad['margin' + dirs[i]] = 0;
      }
      extend(pad, o.styles || {});
    } else {
      var prop = [];
      for (var i = 0; i < 4; ++i) {
        prop.push('margin' + dirs[i]);
        prop.push('padding' + dirs[i]);
      }
      pad = getStyle(el, prop);
    }
    for (var i = 0; i < 4; ++i) { // add border 1px
      var key = 'margin' + dirs[i];
      pad[key] = (intval(pad[key]) + 1) + 'px';
    }
  }

  if (o.reload) {
    var prel = el.previousSibling;
    if (prel && hasClass(prel, 'input_back_wrap')) re(prel);
  }
  var b1 = el.phcont = el.parentNode.insertBefore(ce('div', {className: 'input_back_wrap no_select', innerHTML: '\
<div class="input_back"><div class="input_back_content">' + ph + '</div></div>\
  '}), el), b = b1.firstChild, c = b.firstChild;
  setStyle(b, pad);

  var cv = __phCheck.pbind(el, o.back), checkValue = browser.mobile ? cv : function(f, b) {
    setTimeout(cv.pbind(f, b), 0);
  }

  if (browser.msie && !browser.msie8) {
    setStyle(b, {marginTop: 1});
  }
  el.phonfocus = function(hid) {
    el.focused = true;
    cur.__focused = el;
    if (hid === true) {
      setStyle(el, {backgroundColor: '#FFF'});
      hide(b);
    }
    checkValue(true, false);
  }
  el.phonblur = function() {
    cur.__focused = el.focused = false;
    show(b);
    checkValue(false, true);
  }
  el.phshown = true, el.phanim = null;
  if (el.value) {
    el.phshown = false;
    hide(b1);
  }

  if (!browser.opera_mobile) {
    addEvent(b1, 'focus click', function() { el.blur(); el.focus(); });
    addEvent(el, 'focus', el.phonfocus);
    addEvent(el, 'keydown paste cut input', checkValue);
  }
  addEvent(el, 'blr', el.phonblur);

  el.getValue = function() {
    return el.value;
  }
  el.setValue = function(v) {
    el.value = v;
    __phCheck(el, o.back);
  }
  el.phevents = true;
  el.phonsize = function() {};

  if (o.global) return;

  if (!o.reload) {
    if (!cur.__phinputs) {
      cur.__phinputs = [];
      cur.destroy.push(function() {
        for (var i = 0, l = cur.__phinputs.length; i < l; ++i) {
          removeData(cur.__phinputs[i]);
        }
      });
    }
    cur.__phinputs.push(el);
  }
}

function val(input, value, nofire) {
  input = ge(input);
  if (!input) return;

  if (value !== undefined) {
    if (input.setValue) {
      input.setValue(value);
      !nofire && input.phonblur && input.phonblur();
    } else if (input.tagName == 'INPUT' || input.tagName == 'TEXTAREA') {
      input.value = value
    } else {
      input.innerHTML = value
    }
  }
  return input.getValue ? input.getValue() :
         (((input.tagName == 'INPUT' || input.tagName == 'TEXTAREA') ? input.value : input.innerHTML) || '');
}

function elfocus(el, from, to) {
  el = ge(el);
  try {
    el.focus();
    if (from === undefined || from === false) from = el.value.length;
    if (to === undefined || to === false) to = from;
    if (el.createTextRange) {
      var range = el.createTextRange();
      range.collapse(true);
      range.moveEnd('character', from);
      range.moveStart('character', to);
      range.select();
    } else if (el.setSelectionRange) {
      el.setSelectionRange(from, to);
    }
  } catch(e) {}
}

// Message box
var _message_box_guid = 0, _message_boxes = [], _show_flash_timeout = 0;

var __bq = boxQueue = {
  hideAll: function() {
    if (__bq.count()) {
      var box = _message_boxes[__bq._boxes.pop()];
      box._in_queue = false;
      box._hide();
    }
    while (__bq.count()) {
      var box = _message_boxes[__bq._boxes.pop()];
      box._in_queue = false;
    }
  },
  hideLast: function(check, e) {
    if (__bq.count()) {
      var box = _message_boxes[__bq._boxes[__bq.count() - 1]];
      if (check === true && (box.changed || __bq.skip)) {
        __bq.skip = false;
        return;
      }
      box.hide();
    }
    if (e && e.type == 'click') return cancelEvent(e);
  },
  hideBGClick: function(e) {
    if (e && e.target && /^box_layer/.test(e.target.id)) {
      __bq.hideLast();
    }
  },
  count: function() {
    return __bq._boxes.length;
  },
  _show: function(guid) {
    var box = _message_boxes[guid];
    if (!box || box._in_queue) return;
    if (__bq.count()) {
      _message_boxes[__bq._boxes[__bq.count() - 1]]._hide(true, true);
    } else if (window.tooltips) {
      tooltips.hideAll();
    }
    box._in_queue = true;
    var notFirst = __bq.count() ? true : false;
    __bq.curBox = guid;
    box._show(notFirst || __bq.currHiding, notFirst);
    __bq._boxes.push(guid);
    //show(boxLayerWrap);
    //show(boxLayerBG);
  },
  _hide: function(guid) {
    var box = _message_boxes[guid];
    if (!box || !box._in_queue || __bq._boxes[__bq.count() - 1] != guid || !box.isVisible()) return;
    box._in_queue = false;
    __bq._boxes.pop();
    box._hide(__bq.count() ? true : false);
    if (__bq.count()) {
      var prev_guid = __bq._boxes[__bq.count() - 1];
      __bq.curBox = prev_guid;
      _message_boxes[prev_guid]._show(true, true, true);
    }
    //hide(boxLayerWrap);
    //hide(boxLayerBG);
  },
  _boxes: [],
  curBox: 0
}

__bq.hideLastCheck = __bq.hideLast.pbind(true);
function curBox() { var b = _message_boxes[__bq.curBox]; return (b && b.isVisible()) ? b : null; }

if (!browser.mobile) {
  addEvent(document, 'keydown', function(e) {
    if (e.keyCode == KEY.ESC && __bq.count()) {
      __bq.hideLast();
      return false;
    }
  });
}

function MessageBox(options, dark) {
  var defaults = {
    width: 410,
    animSpeed: 0,
    height: 'auto',
    bodyStyle: '',
    dark: false,
    selfDestruct: true,
    progress: false
  };

  options = extend(defaults, options);
  if (dark) {
    options.dark = 1;
  }

  var buttonsCount = 0,
      boxContainer, boxBG, boxContainer, boxLayout;
  var boxTitleWrap, boxTitle, boxCloseButton, boxBody;
  var boxControlsWrap, boxControls, boxButtons, boxProgress, boxControlsText;
  var guid = _message_box_guid++, visible = false;

  if (!options.progress) options.progress = 'box_progress' + guid;

  var controlsStyle = options.hideButtons ? ' style="display: none"' : '';
  boxContainer = ce('div', {
    className: 'popup_box_container'+(options.dark ? ' box_dark' : ''),
    innerHTML: '\
<div class="box_layout" onclick="__bq.skip=true;">\
<div class="box_title_wrap"><div class="box_x_button">'+(options.dark ? getLang('global_close') : '')+'</div><div class="box_title"></div></div>\
<div class="box_body" style="' + options.bodyStyle + '"></div>\
<div class="box_controls_wrap"' + controlsStyle + '><div class="box_controls">\
<table cellspacing="0" cellpadding="0" class="fl_r"><tr></tr></table>\
<div class="progress" id="' + options.progress + '"></div>\
<div class="box_controls_text"></div>\
</div></div>\
</div>'
  }, {
    display: 'none'
  });
  hide(boxContainer);

  boxLayout = domFC(boxContainer);

  boxTitleWrap = domFC(boxLayout);
  boxCloseButton = domFC(boxTitleWrap);
  boxTitle = domNS(boxCloseButton);

  if (options.noCloseButton) hide(boxCloseButton);

  boxBody = domNS(boxTitleWrap);

  boxControlsWrap = domNS(boxBody);
  boxControls = domFC(boxControlsWrap);
  boxButtons = domFC(boxControls);
  boxProgress = domNS(boxButtons);
  boxControlsText = domNS(boxProgress);

  boxLayer.appendChild(boxContainer);

  refreshBox();
  refreshCoords();

  // Refresh box position
  function refreshCoords() {
    var height = window.innerHeight ? window.innerHeight : (document.documentElement.clientHeight ? document.documentElement.clientHeight : boxLayerBG.offsetHeight);
    var top = browser.mobile ? intval(window.pageYOffset) : 0;
    containerSize = getSize(boxContainer);
    boxContainer.style.marginTop = Math.max(10, top + (height - containerSize[1]) / 3) + 'px';
  }

  // Refresh box properties
  function refreshBox() {
    // Set title
    if (options.title) {
      boxTitle.innerHTML = options.title;
      removeClass(boxBody, 'box_no_title');
      show(boxTitleWrap);
    } else {
      addClass(boxBody, 'box_no_title');
      hide(boxTitleWrap);
    }

    // Set box dimensions
    boxContainer.style.width = typeof(options.width) == 'string' ? options.width : options.width + 'px';
    boxContainer.style.height = typeof(options.height) == 'string' ? options.height : options.height + 'px';
  }

  // Add button
  function addButton(label, onclick, type) {
    if (options.dark && type == 'no') {
      return false;
    }
    ++buttonsCount;
    if (type == 'no') type = 'gray';
    if (type == 'yes') type = 'blue';
    var buttonWrap = ce('div', {
      className: 'button_' + (type ? type : 'blue'),
      innerHTML: '<button>' + label + '</button>'
    }), row = boxButtons.rows[0], cell = row.insertCell(0);
    cell.appendChild(buttonWrap);
    createButton(buttonWrap.firstChild, onclick);
    return buttonWrap;
  }

  // Add custom controls text
  function setControlsText(text) {
    boxControlsText.innerHTML = text;
  }

  // Remove buttons
  function removeButtons() {
    var row = boxButtons.rows[0];
    while (row.cells.length) {
      cleanElems(row.cells[0]);
      row.deleteCell(0);
    }
  }

  var destroyMe = function() {
    if (options.onClean) options.onClean();
    removeButtons();
    cleanElems(boxContainer, boxCloseButton, boxTitleWrap, boxControlsWrap);
    boxLayer.removeChild(boxContainer);
    delete _message_boxes[guid];
    if (options.onWidgetHide) {
      options.onWidgetHide();
    }
  }

  // Hide box
  var hideMe = function(showingOther, tempHiding) {
    if (!visible) return;
    visible = false;

    var speed = (showingOther === true) ? 0 : options.animSpeed;

    if (options.hideOnBGClick) {
      removeEvent(document, 'click', __bq.hideBGClick);
    }

    if (isFunction(options.onBeforeHide)) {
      options.onBeforeHide();
    }

    var onHide = function () {
      if (__bq.currHiding == _message_boxes[guid]) {
        __bq.currHiding = false;
      }
      if (!tempHiding && options.selfDestruct) {
        destroyMe();
      } else {
        hide(boxContainer);
      }

      if (options.onHide) {
        options.onHide();
      }
    }
    if (speed > 0) {
      __bq.currHiding = _message_boxes[guid];
      fadeOut(boxContainer, speed, onHide);
    } else {
      onHide();
    }
  }

  // Show box
  function showMe(noAnim, notFirst, isReturned) {
    if (visible || !_message_boxes[guid]) return;
    visible = true;

    var speed = (noAnim === true || notFirst) ? 0 : options.animSpeed;

    if (options.hideOnBGClick) {
      addEvent(document, 'click', __bq.hideBGClick);
    }

    if (__bq.currHiding) {
      __bq.currHiding.shOther = true;
      var cont = __bq.currHiding.bodyNode.parentNode.parentNode;
      data(cont, 'tween').stop(true);
    }

    // Show box
    if (speed > 0) {
      fadeIn(boxContainer, speed);
    } else {
      show(boxContainer);
    }

    refreshCoords();
    if (options.onShow) {
      options.onShow(isReturned);
    }

    _message_box_shown = true;

    if (options.dark) {
      addClass(boxLayerBG, 'bg_dark');
    }
  }

  var fadeToColor = function(color) {
    return function() {
      animate(this, {backgroundColor: color}, 200);
    }
  }
  if (!options.dark) {
    addEvent(boxCloseButton, 'mouseover', fadeToColor('#FFFFFF'));
    addEvent(boxCloseButton, 'mouseout', fadeToColor('#9CB8D4'));
  }
  addEvent(boxCloseButton, 'click', __bq.hideLast);

  var retBox = _message_boxes[guid] = {
    guid: guid,
    _show: showMe,
    _hide: hideMe,

    bodyNode: boxBody,
    dark: options.dark,

    // Show box
    show: function() {
      __bq._show(guid);
      return this;
    },
    progress: boxProgress,
    showProgress: function() {
      hide(boxControlsText);
      show(boxProgress);
    },
    hideProgress: function() {
      hide(boxProgress);
      show(boxControlsText);
    },

    // Hide box
    hide: function(attemptParam) {
      if (isFunction(options.onHideAttempt) && !options.onHideAttempt(attemptParam)) return false;
      if (options.dark) {
        removeClass(boxLayerBG, 'bg_dark');
      }
      __bq._hide(guid);
      return true;
    },

    isVisible: function() {
      return visible;
    },
    bodyHeight: function() {
      return getStyle(boxBody, 'height');
    },

    // Insert html content into the box
    content: function(html) {
      if (options.onClean) options.onClean();
      boxBody.innerHTML = html;
      refreshCoords();
      refreshBox();
      return this;
    },

    // Add button
    addButton: function(label, onclick, type, returnBtn) {
      var btn = addButton(label, onclick ? onclick: this.hide, type);
      return (returnBtn) ? btn : this;
    },

    setButtons: function(yes, onYes, no, onNo) {
      var b = this.removeButtons();
      if (!yes) return b.addButton(box_close);
      if (no) b.addButton(no, onNo, 'no');
      return b.addButton(yes, onYes);
    },

    // Set controls text
    setControlsText: setControlsText,

    // Remove buttons
    removeButtons: function() {
      removeButtons();
      return this;
    },

    destroy: destroyMe,

    // Update box options
    setOptions: function(newOptions) {
      if (options.hideOnBGClick) {
        removeEvent(document, 'click', __bq.hideBGClick);
      }
      options = extend(options, newOptions);
      if ('bodyStyle' in newOptions) {
        var items = options.bodyStyle.split(';');
        for (var i = 0; i < items.length; ++i) {
          var name_value = items[i].split(':');
          if (name_value.length > 1 && name_value[0].length) {
            boxBody.style[trim(name_value[0])] = trim(name_value[1]);
            if (boxBody.style.setProperty) {
              boxBody.style.setProperty(trim(name_value[0]), trim(name_value[1]), '');
            }
          }
        }
      }
      if (options.hideOnBGClick) {
        addEvent(document, 'click', __bq.hideBGClick);
      }
      if (options.hideButtons) {
        hide(boxControlsWrap);
      } else {
        show(boxControlsWrap);
      }
      refreshBox();
      refreshCoords();
      return this;
    },
    evalBox: function(js, url, params) {
      var fn = eval('((function() { return function() { var box = this; ' + (js || '') + ';}; })())'); // IE :(
      fn.apply(this, [url, params]);
    }
  }
  return retBox;
}

function showBox(url, params, options, e) {
  if (checkEvent(e)) return false;

  var opts = options || {},
      boxParams = opts.params || {},
      box = new MessageBox(boxParams, opts.dark), p = {
    onDone: function(title, html, js) {
      if (!box.isVisible()) return;
      try {
        show(boxLayerBG);
        box.setOptions({title: title, hideButtons: boxParams.hideButtons || false});
        if (opts.showProgress) {
          box.show();
        } else {
          show(box.bodyNode);
        }
        box.content(html);
        box.evalBox(js, url, params);
        if (opts.onDone) opts.onDone();
      } catch(e) {
        topError(e, {dt: 15, type: 103, url: url, query: ajx2q(params), answer: Array.prototype.slice.call(arguments).join('<!>')});
        if (box.isVisible()) box.hide();
      }
    },
    onFail: function(error) {
      box.failed = true;
      setTimeout(box.hide, 0);
      if (isFunction(opts.onFail)) return opts.onFail(error);
    },
    cache: opts.cache,
    stat: opts.stat,
    fromBox: true
  };

  if (opts.prgEl) {
    opts.showProgress = showGlobalPrg.pbind(opts.prgEl, {cls: opts.prgClass, w: opts.prgW, h: opts.prgH, hide: true});
    opts.hideProgress = hide.pbind('global_prg');
  }
  if (opts.showProgress) {
    extend(p, {
      showProgress: opts.showProgress,
      hideProgress: opts.hideProgress
    });
  } else {
    box.setOptions({title: false, hideButtons: true}).show();
    if (__bq.count() < 2) {
      hide(boxLayerBG);
    }
    hide(box.bodyNode);
    p.showProgress = function() {
      show(boxLoader);
      boxRefreshCoords(boxLoader);
    }
    p.hideProgress = hide.pbind(boxLoader);
  }
  box.removeButtons().addButton(getLang('global_close'));

  ajax.post(url, params, p);
  return box;
}

function showTabbedBox(url, params, options, e) {
  options = options || {};
  options.stat = options.stat || [];
  options.stat.push('box.js', 'boxes.css');
  return showBox(url, params, options, e)
}

function showFastBox(o, c, yes, onYes, no, onNo) {
  return (new MessageBox(typeof(o) == 'string' ? {title: o} : o)).content(c).setButtons(yes, onYes, no, onNo).show();
}

function showCaptchaBox(sid, dif, box, o) {
  var done = function(e) {
    if (e && e.keyCode !== undefined && e.keyCode != 10 && e.keyCode != 13) return;
    var key = geByTag1('input', box.bodyNode);
    if (!trim(key.value) && e !== true) {
      elfocus(key);
      return;
    }
    var imgs = geByTag1('img', box.bodyNode);
    var captcha = imgs[0], loader = imgs[1];
    removeEvent(key);
    removeEvent(captcha);
    show(geByClass1('progress', box.bodyNode));
    hide(key);
    o.onSubmit(sid, key.value);
  }
  var was_box = box ? true : false;
  var difficulty = intval(dif) ? '' : '&s=1';
  var imgSrc = o.imgSrc || '/captcha.php?sid=' + sid + difficulty;
  if (!was_box) {
    var content = '\
<div class="captcha">\
  <div><img src="' + imgSrc + '"/></div>\
  <div><input type="text" class="text" maxlength="7" /><div class="progress" /></div></div>\
</div>' + (o.addText || '');
    box = showFastBox({
      title: getLang('captcha_enter_code'),
      width: 300,
      onHide: o.onHide,
      dark: 1,
    }, content, getLang('captcha_send'), function() {
      box.submit();
    }, getLang('captcha_cancel'), function() {
      var key = geByTag1('input', box.bodyNode);
      var captcha = geByTag1('img', box.bodyNode);
      removeEvent(key);
      removeEvent(captcha);
      box.hide();
    });
  }
  box.submit = done.pbind(true);
  var key = geByTag1('input', box.bodyNode);
  var captcha = geByTag1('img', box.bodyNode);
  if (was_box) {
    key.value = '';
    captcha.src = '/captcha.php?sid=' + sid + difficulty;
    hide(geByClass1('progress', box.bodyNode));
  }
  show(key);
  addEvent(key, 'keypress', done);
  addEvent(captcha, 'click', function() {
    this.src = '/captcha.php?sid=' + sid + difficulty + '&v=' + irand(1000000, 2000000);
  });
  elfocus(key);
  return box;
}

// Three-state button

function createButton(el, onClick) {
  el = ge(el);
  if (!el || el.btnevents) return;
  var p = el.parentNode;

  if (hasClass(p, 'button_blue') || hasClass(p, 'button_gray')) {
    if (isFunction(onClick))
      el.onclick = onClick.pbind(el);
    return;
  }
  var hover = false;
  addEvent(el, 'click mousedown mouseover mouseout', function(e) {
    if (hasClass(p, 'locked')) return;
    switch (e.type) {
    case 'click':
      if (!hover) return;
      el.className = 'button_hover';
      onClick(el);
    break;
    case 'mousedown':
      el.className = 'button_down';
    break;
    case 'mouseover':
      hover = true;
      el.className = 'button_hover';
    break;
    case 'mouseout':
      el.className = 'button';
      hover = false;
    break;
    }
  });
  el.btnevents = true;
}

function lockButton(el) {
  el = ge(el);
  if (!el || el.tagName.toLowerCase() != 'button') return;
  var lock = ce('span', {className: 'button_lock'});
  el.parentNode.insertBefore(lock, el);
  el['old_width'] = el.style.width;
  el['old_height'] = el.style.height;
  var s = getSize(el.parentNode);
  setStyle(el, {width: s[0], height: s[1]});
  if (browser.msie6 || browser.msie7) {
    el['old_html'] = el.innerHTML; el.innerHTML = '';
  } else {
    el.style.textIndent = '-9999px';
  }
}
function unlockButton(el) {
  el = ge(el);
  var lock = geByClass('button_lock', el.parentNode, 'span')[0];
  if (!lock) return;
  el.parentNode.removeChild(lock);
  el.style.width = el['old_width'];
  el.style.height = el['old_height'];
  if (browser.msie6 || browser.msie7) el.innerHTML = el['old_html'];
  el.style.textIndent = '';
}
function buttonLocked(el) {
  if (!(el = ge(el))) return;
  return geByClass1('button_lock', el.parentNode, 'span') ? true : false;
}

function disableButton(el, disable) {
  if (!(el = ge(el)) || el.tagName.toLowerCase() !== 'button') return;
  toggleClass(el.parentNode, 'button_disabled', !!disable);
  if (disable) {
    el.parentNode.insertBefore(ce('button', {innerHTML: el.innerHTML, className: 'disabled'}), el);
    hide(el);
  } else {
    var disabledEl = geByClass1('disabled', el.parentNode);
    if (disabledEl) re(disabledEl);
    show(el);
  }
}

function sbWidth() {
  if (window._sbWidth === undefined) {
    var t = ce('div', {innerHTML: '<div style="height: 75px;">1<br>1</div>'}, {
      overflowY: 'scroll',
      position: 'absolute',
      width: '50px',
      height: '50px'
    });
    bodyNode.appendChild(t);
    window._sbWidth = t.offsetWidth - t.firstChild.offsetWidth - 1;
    bodyNode.removeChild(t);
  }
  return window._sbWidth;
}

function onBodyResize(force) {
  var w = window, de = document.documentElement;
  if (!w.pageNode) return;
  var dwidth = Math.max(intval(w.innerWidth), intval(de.clientWidth));
  var dheight = Math.max(intval(w.innerHeight), intval(de.clientHeight));
  var sbw = sbWidth();

  if (browser.mobile) {
    dwidth = Math.max(dwidth, intval(bodyNode.scrollWidth));
    dheight = Math.max(dheight, intval(bodyNode.scrollHeight));
  } else if (browser.msie7) {
    if (htmlNode.scrollHeight > htmlNode.offsetHeight) {
      dwidth += sbw + 1;
    }
  } else if (browser.msie8) {
    if (htmlNode.scrollHeight + 3 > htmlNode.offsetHeight) {
      dwidth += sbw + 1;
    }
  }
  if (w.lastWindowWidth != dwidth || force === true) {
    w.lastInnerWidth = w.lastWindowWidth = dwidth;

    if (bodyNode.offsetWidth < layoutWidth + sbw + 2) {
      dwidth = layoutWidth + sbw + 2;
    }
    if (dwidth) {
      for (var el = pageNode.firstChild; el; el = el.nextSibling) {
        if (!el.tagName) continue;
        for (var e = el.firstChild; e; e = e.nextSibling) {
          if (e.className == 'scroll_fix') {
            e.style.width = ((w.lastInnerWidth = (dwidth - sbw * (browser.msie7 ? 2 : 1) - 1)) - 1) + 'px';
          }
        }
      }
    }
  }
  if (w.lastWindowHeight != dheight || force === true) {
    w.lastWindowHeight = dheight;
    if (browser.msie6) {
      pageNode.style.height = dheight + 'px';
    }
  }
  if (cur.lSTL) {
    setStyle(cur.lSTL, {width: Math.max(getXY(cur.lSTL.el)[0], 0), height: dheight - 1});
  }
}


function checkTextLength(maxLen, inp, warn, nobr) {
  var val = (inp.getValue) ? inp.getValue() : inp.value;
  if (inp.lastLen === val.length) return;
  inp.lastLen = val.length;
  var countRealLen = function(text, nobr) {
    var spec = {'&': 5, '<': 4, '>': 4, '"': 6, "\n": (nobr ? 1 : 4), "\r": 0, '!': 5, "'": 5};
    var res = 0;
    for (var i = 0; i < text.length; i++) {
      var l = spec[text.charAt(i)], c = text.charCodeAt(i);
      if (l !== undefined) res += l;
      else if ((c > 0x80 && c < 0xC0) || c > 0x500) res += ('&#' + c + ';').length;
      else res += 1;
    }
    return res;
  }
  var realLen = countRealLen(val, nobr);
  warn = ge(warn);
  if (realLen > maxLen - 100) {
    show(warn);
    if (realLen > maxLen) {
      warn.innerHTML = getLang('text_exceeds_symbol_limit', realLen - maxLen);
    } else {
      warn.innerHTML = getLang('text_N_symbols_remain', maxLen - realLen);
    }
  } else {
    hide(warn);
  }
}

function autosizeSetup(el, options) {
  el = ge(el);
  if (!el) return;
  if (el.autosize) {
    el.autosize.update();
    return;
  }

  options.minHeight = intval(options.minHeight) || intval(getStyle(el, 'height'));
  options.maxHeight = intval(options.maxHeight);

  var elwidth = intval(getStyle(el, 'width'));
  if (elwidth < 1) {
    elwidth = intval(getStyle(el, 'width', false));
  }
  el.autosize = {
    options: options,
    helper: ce('textarea', {className: 'ashelper'}, {
      width: elwidth,
      height: 10,
      fontFamily: getStyle(el, 'fontFamily'),
      fontSize: intval(getStyle(el, 'fontSize')) + 'px',
      lineHeight: getStyle(el, 'lineHeight')
    }),
    handleEvent: function(val, e) {
      var ch = e.charCode ? String.fromCharCode(e.charCode) : e.charCode;
      if (ch === undefined) {
        ch = String.fromCharCode(e.keyCode);
        if (e.keyCode == 10 || e.keyCode == 13) {
          ch = '\n';
        } else if (!browser.msie && e.keyCode <= 40) {
          ch = '';
        }
      }
      if (!ch) {
        return val;
      }
      if (!browser.msie) {
        return val.substr(0, el.selectionStart) + ch + val.substr(el.selectionEnd);
      }
      var r = document.selection.createRange();
      if (r.text) {
        val = val.replace(r.text, '');
      }
      return val + ch;
    },
    update: function(e) {
      var value = el.value;
      if (e && e.type != 'blr' && e.type != 'keyup' && (!browser.msie || e.type == 'keypress')) {
        if (!e.ctrlKey && !e.altKey) {
          value = el.autosize.handleEvent(value, e);
        }
      }
      if (!value) {
        value = ' ';
      }
      if (el.autosize.helper.value != value) {
        el.autosize.helper.value = value;
      }
      var opts = el.autosize.options;

      var oldHeight = getSize(el, true)[1];
      var newHeight = el.autosize.helper.scrollHeight;
      if (newHeight < opts.minHeight) {
        newHeight = opts.minHeight;
      }
      var newStyle = {overflow: 'hidden'};
      if (opts.maxHeight && newHeight > opts.maxHeight) {
        newHeight = opts.maxHeight;
        newStyle = extend(newStyle, {overflow: 'auto', overflowX: 'hidden'});
      }
      if (oldHeight != newHeight) {
        newStyle.height = newHeight;
        setStyle(el, newStyle);
        if (el.phonsize) el.phonsize();
        if (isFunction(opts.onResize)) {
          opts.onResize(newHeight);
        }
      }
    }
  }
  utilsNode.appendChild(el.autosize.helper);
  if (browser.opera_mobile) {
    setStyle(el, {overflow: 'hidden'});
    el.autosize.update();
    addEvent(el, 'blr', el.autosize.update);
  } else {
    addEvent(el, 'keydown keyup keypress', el.autosize.update);
    setTimeout(function() {
      setStyle(el, {overflow: 'hidden'});
      el.autosize.update();
    }, 0);
  }
}

function goAway(lnk, prms, e) {
  return true;
}

function isChecked(el) {
  el = ge(el);
  return hasClass(el, 'on') ? 1 : '';
}
function checkbox(el, val) {
  el = ge(el);
  if (!el || hasClass(el, 'disabled')) return;

  if (val === undefined) {
    val = !isChecked(el);
  }
  if (val) {
    addClass(el, 'on');
  } else {
    removeClass(el, 'on');
  }
  return false;
}

function disable(el, val) {
  el = ge(el);

  if (val === undefined) {
    val = !hasClass(el, 'disabled');
  }
  if (val) {
    addClass(el, 'disabled');
  } else {
    removeClass(el, 'disabled');
  }
  return false;
}

var radioBtns = {};
function radioval(name) {
  return radioBtns[name] ? radioBtns[name].val : false;
}
function radiobtn(el, val, name) {
  if (!radioBtns[name]) return;
  each(radioBtns[name].els, function() {
    if (this == el) {
      addClass(this, 'on');
    } else {
      removeClass(this, 'on');
    }
  });
  radioBtns[name].val = val;
}

function renderFlash(cont, opts, params, vars) {
  if (!opts.url || !opts.id) {
    return false;
  }
  opts = extend({
    version: 9,
    width: 1,
    height: 1
  }, opts);
  var f = opts.url;
  if (!stVersions[f]) {
    stVersions[f] = '';
  }
  if (__debugMode && stVersions[f] < 1000000) stVersions[f] += irand(1000000, 2000000);

  opts.url += ((opts.url.indexOf('?') == -1) ? '?' : '&') + '_stV=' + stVersions[f];

  params = extend({
    quality: 'high',
    flashvars: ajx2q(vars)
  }, params);
  if (browser.flash < opts.version) {
//    if (opts.express) {
//      params.flashvars += '&MMplayerType=PlugIn&MMredirectURL=' + encodeURIComponent(locBase + location.hash);
//    } else {
      return false;
//    }
  }
  ge(cont).innerHTML = browser.flashwrap(opts, params);
  return true;
}

function playAudioNew() {
  cur.gpHidden = true;
  var args = arguments;
  if (args[args.length-1] !== false) args = Array.prototype.slice.apply(arguments).concat([true]);
  if (!browser.ipad) {
    stManager.add(['audioplayer.js', 'audioplayer.css'], function() {
      audioPlayer.operate.apply(null, args);
    });
  } else {
    audioPlayer.operate.apply(null, args);
  }
}

window.onLogout = window.onLoginDone = nav.reload;

function callHub(func, count) {
  this.count = count || 1;
  this.done = function(c) {
    this.count -= c || 1;
    if (this.count <= 0) {
      func();
    }
  };
}


// opts: {url: '...', params: {}} or {text: '...'} or {content: '...'}
var _cleanHide = function(el) {
  if (el.temphide) {
    removeEvent(el, 'mouseout', el.temphide);
    removeAttr(el, 'temphide');
  }
}
function showTooltip(el, opts) {
  _cleanHide(el);

  var showing = true;
  el.temphide = function() {
    showing = false;
  }
  addEvent(el, 'mouseout', el.temphide);

  if (opts.stat) stManager.add(opts.stat);
  stManager.add(['tooltips.js', 'tooltips.css'], function() {
    if (!showing) return;
    _cleanHide(el);

    if (!el.tt || !el.tt.el || opts.force) {
      tooltips.create(el, opts);
      if (opts.onCreate) opts.onCreate();
    }
    tooltips.show(el, opts);
  });
}

function setFavIcon() {}

function animateCount (el, newCount, opts) {
  el = ge(el);
  opts = opts || {};

  if (opts.str) {
    newCount = trim(newCount.toString()) || '';
  } else {
    newCount = positive(newCount);
  }
  if (!el) return;
  if (browser.msie6 || browser.mobile && !browser.safari_mobile && !browser.android) {
    val(el, newCount || '');
    return;
  }

  var curCount = data(el, 'curCount'),
      nextCount = data(el, 'nextCount');

  if (typeof nextCount == 'number' || opts.str && typeof nextCount == 'string') {
    if (newCount != nextCount) {
      data(el, 'nextCount', newCount);
    }
    return;
  }
  if (typeof curCount == 'number' || opts.str && typeof curCount == 'string') {
    if (newCount != curCount) {
      data(el, 'nextCount', newCount);
    }
    return;
  }
  if (opts.str) {
    curCount = trim(val(el).toString()) || '';
  } else {
    curCount = positive(val(el));
  }
  if (curCount == newCount) {
    return;
  }
  data(el, 'curCount', newCount);
  var incr = opts.str ? (curCount.length == newCount.length ? curCount < newCount : curCount.length < newCount.length) : curCount < newCount,
      big = (incr ? newCount : curCount).toString(),
      small = (incr ? curCount : newCount).toString(),
      constPart = [],
      constEndPart = [],
      bigPart = '',
      smallPart = '',
      i, l, j;

  if (!opts.str) {
    small = ((new Array(big.length - small.length + 1)).join('0')) + small;
  }
  for (i = 0, l = big.length; i < l; i++) {
    if ((j = big.charAt(i)) !== small.charAt(i)) {
      break;
    }
    constPart.push(j);
  }
  bigPart = big.substr(i);
  smallPart = small.substr(i);

  if (opts.str) {
    for (i = bigPart.length; i > 0; i--) {
      if ((j = bigPart.charAt(i)) !== smallPart.charAt(i)) {
        break;
      }
      constEndPart.unshift(j);
    }
    if (constEndPart.length) {
      bigPart = bigPart.substr(0, i + 1);
      smallPart = smallPart.substr(0, i + 1);
    }
  }

  constPart = constPart.join('').replace(/\s$/, '&nbsp;');
  constEndPart = constEndPart.join('').replace(/^\s/, '&nbsp;');

  if (!trim(val(el))) {
    val(el, '&nbsp;');
  }
  var h = el.clientHeight || el.offsetHeight;
  val(el, '<div class="counter_wrap inl_bl"></div>');
  var wrapEl = el.firstChild,
      constEl1, constEl2, animwrapEl, animEl,
      vert = true;

  if (constPart.length) {
    wrapEl.appendChild(constEl1 = ce('div', {className: 'counter_const inl_bl', innerHTML: constPart}));
  }
  if (!constPart.length) {
    smallPart = smallPart.replace(/^0+/, '');
  }
  if (!smallPart || smallPart == '0') {
    smallPart = '&nbsp;';
    vert = constPart.length ? true : false;
  }

  wrapEl.appendChild(animwrapEl = ce('div', {className: 'counter_anim_wrap inl_bl'}));
  animwrapEl.appendChild(animEl = ce('div', {
    className: 'counter_anim ' + (incr ? 'counter_anim_inc' : 'counter_anim_dec'),
    innerHTML: '<div class="counter_anim_big"><span class="counter_anim_big_c">' + bigPart + '</span></div>' +
               (vert ? '<div class="counter_anim_small"><span class="counter_anim_small_c">' + smallPart + '</span></div>' : '')
  }, vert ? {marginTop: incr ? -h : 0} : {right: 'auto', left: 0}));
  if (opts.str) {
    setStyle(animEl, {textAlign: 'left', right: 'auto', left: 0});
  }

  var bigW = geByClass1('counter_anim_big_c', animEl, 'span').offsetWidth,
      smallW = vert ? (smallPart == '&nbsp;' ? bigW : geByClass1('counter_anim_small_c', animEl, 'span').offsetWidth) : 0;

  if (constEndPart.length) {
    wrapEl.appendChild(constEl2 = ce('div', {className: 'counter_const inl_bl', innerHTML: constEndPart}));
  }

  setStyle(wrapEl, {width: (constEl1 && constEl1.offsetWidth || 0) + (constEl2 && constEl2.offsetWidth || 0) + bigW})

  if (browser.csstransitions === undefined) {
    var b = browser, bv = floatval(b.version);
    browser.csstransitions =
      (b.chrome && bv >= 9.0) ||
     (b.mozilla && bv >= 4.0) ||
     (b.opera && bv >= 10.5) ||
     (b.safari && bv >= 3.2) ||
     (b.safari_mobile) ||
     (b.android);
  }
  var css3 = browser.csstransitions;
  setStyle(animwrapEl, {width: incr ? smallW : bigW});
  // return debugLog(css3, incr, curCount, newCount, animwrapEl, animEl, geByClass1('counter_anim_big_c', animEl, 'span'), geByClass1('counter_anim_small_c', animEl, 'span'), h, bigW, smallW);
  var onDone = function () {
    val(el, newCount || ' ');
    var next = data(el, 'nextCount');
    data(el, 'curCount', false);
    data(el, 'nextCount', false);
    if (typeof next == 'number' || opts.str && typeof next == 'string') {
      setTimeout(animateCount.pbind(el, next, opts), 0);
    }
  }, margin = vert ? {marginTop: incr ? 0 : -h} : {marginRight: incr ? -smallW : 0};
  if (css3) {
    getStyle(animwrapEl, 'width');
    addClass(animwrapEl, 'counter_css_anim_wrap');
    if (bigW != smallW) {
      setStyle(animwrapEl, {width: incr ? bigW : smallW});
    }
    if (vert) setStyle(animEl, margin);
    setTimeout(onDone, 300);
  } else {
    if (bigW != smallW) {
      animate(animwrapEl, {width: incr ? bigW : smallW}, {duration: 100});
    }
    if (vert) {
      animate(animEl, margin, {duration: 300, transition: Fx.Transitions.easeOutCirc, onComplete: onDone});
    } else {
      setTimeout(onDone, 300);
    }
  }
}

function boxRefreshCoords(cont) {
  var height = window.innerHeight ? window.innerHeight : (document.documentElement.clientHeight ? document.documentElement.clientHeight : boxLayerBG.offsetHeight);
  var top = browser.mobile ? intval(window.pageYOffset) : 0;
  containerSize = getSize(cont);
  cont.style.marginTop = Math.max(10, top + (height - containerSize[1]) / 3) + 'px';
}

function showDoneBox(msg, opts) {
  opts = opts || {};
  var l = (opts.w || 380) + 20;
  var style = opts.w ? ' style="width: ' + opts.w + 'px;"' : '';
  var pageW = bodyNode.offsetWidth,
      resEl = ce('div', {
      className: 'top_result_baloon_wrap fixed',
      innerHTML: '<div class="top_result_baloon"' + style + '>' + msg + '</div>'
  }, {left: (pageW - l) / 2});
  bodyNode.insertBefore(resEl, bodyNode.firstChild);
  boxRefreshCoords(resEl);
  var out = opts.out || 2000;
  var _fadeOut = function() {
    setTimeout(function() {
      if (opts.permit && !opts.permit()) {
        _fadeOut();
        return;
      }
      fadeOut(resEl.firstChild, 500, function() {
        re(resEl);
        if (opts.callback) {
          opts.callback();
        }
      });
    }, out);
  }
  _fadeOut();
}

function showGlobalPrg(img, opts) {
  var xy = getXY(img), sz = getSize(img), o = opts || {}, w = o.w || 32, h = o.h || 13, el = ge('global_prg');
  el.className = o.cls || 'progress';
  setStyle(el, {
    left: xy[0] + Math.floor((sz[0] - w) / 2),
    top: xy[1] + Math.floor((sz[1] - h) / 2),
    width: w, height: h,
    display: 'block'
  });
  if (o.hide) {
    img.style.visibility = 'hidden';
  }
}

function cssAnim(obj, prep, opts, callb) {
  var v = intval(browser.version);
  if (obj && ((browser.chrome && v > 14) || (browser.mozilla && v > 13) || (browser.opera && v > 2))) {
    var callbWrap;
    var st = 'all '+opts.duration+'ms '+(opts.func || 'ease-out');
    obj.style.WebkitTransition = st;
    obj.style.MozTransition = st;
    obj.style.OTransition = st;
    obj.style.transition = st;
    var callbWrap = function() {
      if (browser.opera) {
        obj.removeEventListener('oTransitionEnd', callbWrap);
      } else {
        removeEvent(obj, 'webkitTransitionEnd transitionend msTransitionEnd oTransitionEnd', callbWrap);
      }
      obj.style.WebkitTransition = '';
      obj.style.MozTransition = '';
      obj.style.OTransition = '';
      obj.style.transition = '';
      if (callb) callb();
      return false;
    }
    if (callb) {
      if (browser.opera) {
        obj.addEventListener('oTransitionEnd', callbWrap)
      } else {
        addEvent(obj, 'webkitTransitionEnd transitionend msTransitionEnd oTransitionEnd', callbWrap);
      }
    }
    setTimeout(setStyle.pbind(obj, prep), 0);
  } else {
    animate(obj, prep, extend(opts, {onComplete: callb}));
  }
}

try{stManager.done('lite.js');}catch(e){}
