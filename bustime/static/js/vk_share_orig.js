(function() {
  if (!window.VK) window.VK = {};
  if (VK.Share) return;

  var head = document.getElementsByTagName('head')[0],
    tpl = function(a, b) {return a.replace(/\{(\w+?)\}/g, function(c, d) {return b[d] !== void 0 ? b[d] : ''})};

  VK.Share = {
    _popups: [],
    _gens: [],
    _base_domain: '',
    _ge: function(id) {
      return document.getElementById(id);
    },
    button: function(gen, but, index) {
      if (!gen) gen = {};
      if (gen === gen.toString()) gen = {url: gen.toString()};
      if (!gen.url) gen.url = VK.Share._loc;
      gen.url = (gen.url || '').replace(/"/g, '');

      if (!but) but = {type: 'round'};
      if (but === but.toString()) but = {type: 'round', text: but};
      if (!but.text) but.text = '\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c';

      var old = true, count_style = 'display: none';
      if (index === undefined) {
        gen.count = 0;
        gen.shared = (but.type == 'button' || but.type == 'round') ? false : true;
        this._gens.push(gen);
        this._popups.push(false);
        index = this._popups.length - 1;
        old = false;
      } else {
        if ((gen.count = this._gens[index].count) && (but.type == 'button' || but.type == 'round')) {
          count_style = '';
        }
        gen.shared = this._gens[index].shared;
        this._gens[index] = gen;
      }

      if (!this._base_domain) {
        for (var elem = head.firstChild; elem; elem = elem.nextSibling) {
          var m;
          if (elem.tagName && elem.tagName.toLowerCase() == 'script' && (m = elem.src.match(/(https?:\/\/(?:[a-z0-9_\-\.]*\.){0,2}(?:vk\.com|vkontakte\.ru)\/)js\/api\/share\.js(?:\?|$)/))) {
            this._base_domain = m[1];
          }
        }
      }
      this._base_domain = this._base_domain.replace('vkontakte.ru', 'vk.com');
      if (!this._base_domain) {
        this._base_domain = '//vk.com/';
      }
      if (!old && (but.type == 'button' || but.type == 'round')) {
        var elem = document.createElement('script');
        elem.src = this._base_domain + 'share.php?act=count&index=' + index + '&url=' + encodeURIComponent(gen.url);
        head.appendChild(elem);
      }

      var radius = '-webkit-border-radius: {v};-moz-border-radius: {v};border-radius: {v};',
        strs = {
          domain: this._base_domain,
          table: '<table cellspacing="0" cellpadding="0" style="position: relative; cursor: pointer; width: auto; line-height: normal; border: 0; direction: ltr;" ',
          is2x: window.devicePixelRatio >= 2 ? '_2x' : '',
          i: index,
          a2: '</a>',
          td2: '</td>',
          font: 'font: 400 12px Arial, Helvetica, sans-serif;letter-spacing: 0.1px;text-shadow: none;',
          radiusl: tpl(radius, {v: '2px 0px 0px 2px'}),
          radiusr: tpl(radius, {v: '0px 2px 2px 0px'}),
          radius: tpl(radius, {v: '2px'}),
          text: but.text,
          acolor: 'color: #33567f;',
          bg: 'background: #6287AE;-webkit-transition: background 200ms linear;transition: background 200ms linear;',
        };
      strs.td1 = tpl('<td style="vertical-align: middle;{font}">', strs);
      strs.a = tpl('<a href="{domain}share.php?url=' + encodeURIComponent(gen.url) + '" onmouseup="this._btn=event.button;this.blur();" onclick="return VK.Share.click({i}, this);"', strs);
      strs.a1 = tpl('{a} style="{acolor}text-decoration: none;{font}line-height: 16px;">', strs);
      strs.a3 = tpl('{a} style="display: inline-block;text-decoration: none;">', strs);
      strs.sprite = tpl("background-size: 19px 59px;background-image: url('{domain}images/icons/like_widget{is2x}.png');", strs);
      strs.logo = tpl('<div style="{sprite}height: 8px;width: 14px;margin: 4px 0 3px;"></div>', strs);

      if (but.type == 'round' || but.type == 'round_nocount' || but.type == 'button' || but.type == 'button_nocount') {
         return tpl('{table}id="vkshare{i}" onmouseover="VK.Share.change(1, {i});" onmouseout="VK.Share.change(0, {i});" onmousedown="VK.Share.change(2, {i});" onmouseup="VK.Share.change(1, {i});"><tr style="line-height: normal;">{td1}{a} style="border: 0;display: block;box-sizing: content-box;{bg}{radiusl}padding: 2px 6px 4px;">{logo}{a2}{td2}{td1}{a} style="color: #FFF;text-decoration: none;border: 0;{bg}{radiusr}{font}line-height: 16px;display:block;padding: 2px 6px 4px 0;height: 15px;">{text}{a2}{td2}'+ ((but.type == 'round' || but.type == 'button') ? '{td1}{a} style="text-decoration: none;{font}line-height: 15px;-webkit-font-smoothing: subpixel-antialiased;' + count_style + '"><div style="{sprite};background-position: 0 -49px;margin: 5px 0 0 4px;width: 5px; height: 10px;position: absolute; z-index:100;"></div><div id="vkshare_cnt{i}" style="border: 1px solid #adbdcc;background: #FFF;font-size:11px;padding: 2px 5px;margin-left: 8px;color: #55677d;z-index: 99;box-sizing: content-box;{radius}">' + gen.count + '</div>{a2}{td2}' : '') + '</tr></table>', strs);
      } else if (but.type == 'link') {
        return tpl('{table}onmouseover="this.rows[0].cells[1].firstChild.style.textDecoration=\'underline\'" onmouseout="this.rows[0].cells[1].firstChild.style.textDecoration=\'none\'"><tr style="line-height: normal;">{td1}{a1}<img src="{domain}images/icons/share_link{is2x}.png" width="16" height="16" style="vertical-align: top;margin-right: 8px;"/>{a2}{td2}{td1}{a1}{text}{a2}{td2}</tr></table>', strs);
      } else if (but.type == 'link_noicon') {
        return tpl('{a3}<span style="{acolor}position: relative;{font}line-height: normal;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{text}</span>{a2}', strs);
      } else {
        return tpl('{a3}<span style="position: relative;padding: 0;">{text}</span>{a2}', strs);
      }
    },
    change: function(state, index) {
      var el = this._ge('vkshare' + index),
        color = ['#6287AE','#678EB4','#5D7FA4'][state],
        els = [el.rows[0].cells[0].firstChild, el.rows[0].cells[1].firstChild];
      for (var i in els) {
        els[i].style.backgroundColor = color;
        els[i].style.color = '#FFF';
        if (state == 2) {
          els[i].style.paddingTop = '3px';
          els[i].style.paddingBottom = '3px';
        } else {
          els[i].style.paddingTop = '2px';
          els[i].style.paddingBottom = '4px';
        }
      }
    },
    click: function(index, el) {
      var e = window.event;
      if (e) {
        if (!e.which && el._btn) e.which = (el._btn & 1 ? 1 : (el._btn & 2 ? 3 : (el._btn & 4 ? 2 : 0)));
        if (e.which == 2) {
          return true;
        }
      }
      var details = this._gens[index];
      if (!details.shared) {
        VK.Share.count(index, details.count + 1);
        details.shared = true;
      }
      var undefined;
      if (details.noparse === undefined) {
        details.noparse = details.title && details.description && details.image;
      }
      details.noparse = details.noparse ? 1 : 0;

      var params = {},
        fields = ['title', 'description', 'image', 'noparse'];

      for (var i = 0; i < fields.length; ++i) {
        if (details[fields[i]]) {
          params[fields[i]] = details[fields[i]];
        }
      }

      var popupName = '_blank',
        width = 650,
        height = 610,
        left = Math.max(0, (screen.width - width) / 2),
        top = Math.max(0, (screen.height - height) / 2),
        url = this._base_domain + 'share.php?url=' + encodeURIComponent(details.url),
        popupParams = 'width='+width+',height='+height+',left='+left+',top='+top+',menubar=0,toolbar=0,location=0,status=0',
        popup = false;

      try {
        var doc_dom = '', loc_hos = '';
        try {
          doc_dom = document.domain;
          loc_hos = location.host;
        } catch (e) {
        }
        if (doc_dom != loc_hos) {
          var ua = navigator.userAgent.toLowerCase();
          if (!/opera/i.test(ua) && /msie/i.test(ua)) {
            throw 'wont work';
          }
        }
        popup = this._popups[index] = window.open('', popupName, popupParams);
        var text = '<form accept-charset="UTF-8" action="' + url + '" method="POST" id="share_form">';
        for (var i in params) {
          text += '<input type="hidden" name="' + i + '" value="' + params[i].toString().replace(/"/g, '&myquot;').replace(/&quot/ig, '&myquot') + '" />';
        }
        text += '</form>';
        text += '<script type="text/javascript">document.getElementById("share_form").submit()</script>';

        text = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">' +
               '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">' +
               '<head><meta http-equiv="content-type" content="text/html; charset=windows-1251" /></head>' +
               '<body>' + text + '</body></html>';
        popup.document.write(text);
        popup.focus();
      } catch (e) { // ie with changed domain.
        try {
          if (popup) {
            popup.close();
          }
          url += '?';
          for (var i in params) {
            url += encodeURIComponent(i) + '=' + encodeURIComponent(params[i]) + '&';
          }
          popup = this._popups[index] = window.open(url, popupName, popupParams);
          popup.focus();
        } catch (e) {
        }
      }
      return false;
    },
    count: function(index, count) {
      this._gens[index].count = count;
      var elem = this._ge('vkshare'+index);
      if (elem) {
        var counter = this._ge('vkshare_cnt'+index);
        if (counter) {
          if (count) counter.innerHTML = count;
          elem.rows[0].cells[2].firstChild.style.display = count ? 'block' : 'none';
        }
      }
    }
  }

  try {
    VK.Share._loc = location.toString();
  } catch(e) {
    VK.Share._loc = 'http://vk.com/';
  }

})();

try{if (window.stManager) stManager.done('api/share.js');}catch(e){}
