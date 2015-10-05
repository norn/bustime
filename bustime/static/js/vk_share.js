if (!window.VK) window.VK = {};
if (!VK.Share) {
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

      var head = document.getElementsByTagName('head')[0];
      if (!this._base_domain) {
        for (var elem = head.firstChild; elem; elem = elem.nextSibling) {
          var m;
          if (elem.tagName && elem.tagName.toLowerCase() == 'script' && (m = elem.src.match(/(https?:\/\/(?:[a-z0-9_\-\.]*\.)?(?:vk\.com|vkontakte\.ru)\/)js\/api\/share\.js(?:\?|$)/))) {
            this._base_domain = m[1];
          }
        }
      }
      this._base_domain = this._base_domain.replace('vkontakte.ru', 'vk.com');
      if (!this._base_domain) {
        this._base_domain = 'http://vk.com/';
      }
      if (!old && (but.type == 'button' || but.type == 'round')) {
        var elem = document.createElement('script');
        elem.src = this._base_domain + 'share.php?act=count&index=' + index + '&url=' + encodeURIComponent(gen.url);
        head.appendChild(elem);
      }
      var is2x = window.devicePixelRatio >= 2 ? '_2x' : '';
      var iseng = but.eng ? '_eng' : '';
      var a = '<a href="'+this._base_domain+'share.php?url='+encodeURIComponent(gen.url)+'" onmouseup="this._btn=event.button;this.blur();" onclick="return VK.Share.click(' + index + ', this);"', a1 = a+' style="text-decoration:none;">', a2='</a>', a3 = a+' style="display:inline-block;text-decoration:none;">', td1 = '<td style="vertical-align: middle;">', td2 = '</td>';
      if (but.type == 'round' || but.type == 'round_nocount' || but.type == 'button' || but.type == 'button_nocount') {
        var logo = but.eng ? '' : '0px 0px';
         return '<table cellspacing="0" cellpadding="0" id="vkshare'+index+'" onmouseover="VK.Share.change(1, '+index+');" onmouseout="VK.Share.change(0, '+index+');" onmousedown="VK.Share.change(2, '+index+');" onmouseup="VK.Share.change(1, '+index+');" style="position: relative; width: auto; cursor: pointer; border: 0px;"><tr style="line-height: normal;">'+
            td1+a+' style="border: none;box-sizing: content-box;background: #5F83AA;-webkit-border-radius: 2px 0px 0px 2px;-moz-border-radius: 2px 0px 0px 2px;border-radius: 2px 0px 0px 2px;display:block;text-decoration: none;padding: 3px 3px 3px 6px;color: #FFFFFF;font-family: tahoma, arial;height: 15px;line-height:15px;font-size: 10px;text-shadow: none;">'+but.text+'<div class="float:right"></div>'+a2+td2+
            td1+a+' style="border: none;background: #5F83AA;-webkit-border-radius: 0px 2px 2px 0px;-moz-border-radius: 0px 2px 2px 0px;border-radius: 0px 2px 2px 0px;display:block; padding: 3px;'+(but.eng ? 'padding-left: 1px;' : '')+'"><div style="background: url(\'//vk.com/images/icons/share_logo'+is2x+'.png\') 0px '+(but.eng ? '-15px' : '0px')+' no-repeat; background-size: 16px 31px; '+(but.eng ? 'width: 17px;height:9px;margin: 3px 0px;' : 'width: 15px;height: 15px;')+'"></div>'+a2+td2+
            ((but.type == 'round' || but.type == 'button') ? td1+a+' style="text-decoration: none;font-weight:bold;font-family: tahoma, arial;'+count_style+'"><div style="background: url(\'//vk.com/images/icons/share_logo'+is2x+'.png\') 0px -24px no-repeat; background-size: 16px 31px; width: 4px; height: 7px;position: absolute; margin: 7px 0px 0px 4px;z-index:100;"></div><div id="vkshare_cnt'+index+'" style="border: 1px solid #bbbfc4;background: #FFFFFF;height: 15px;line-height: 15px;5px; padding: 2px 4px;min-width: 12px;margin-left: 7px;border-radius: 2px;-webkit-border-radius: 2px;-moz-border-radius:2px;text-align: center; color: #666c73;font-size: 10px;z-index:99;box-sizing: content-box;">'+gen.count+'</div>'+a2+td2 : '')+
            '</tr></table>';
      } else if (but.type == 'link') {
        return '<table style="position: relative; cursor:pointer; width: auto; line-height: normal;" onmouseover="this.rows[0].cells[1].firstChild.firstChild.style.textDecoration=\'underline\'" onmouseout="this.rows[0].cells[1].firstChild.firstChild.style.textDecoration=\'none\'" cellspacing="0" cellpadding="0"><tr style="line-height: normal;">' +
               td1+a1+'<img src="//vk.com/images/icons/share_link'+iseng+is2x+'.png" width="16" height="16" style="vertical-align: middle;border:0;"/>'+a2+td2 +
               td1+a1+'<span style="padding: 0 0 0 5px; color: #2B587A; font-family: tahoma, arial; font-size: 11px;">' + but.text + '</span>'+a2+td2 +
               '</tr></table>';
      } else if (but.type == 'link_noicon') {
        return a3+'<span style="position: relative; font-family: tahoma, arial; font-size: 11px; color: #2B587A; line-height: normal;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">' + but.text + '</span>'+a2;
      } else {
        return a3+'<span style="position: relative; padding:0;">' + but.text + '</span>'+a2;
      }
    },
    change: function(state, index) {
      var el = this._ge('vkshare' + index), color;
      if (state == 0) {
        color = '#5F83AA';
      } else if (state == 1) {
        color = '#6890bb';
      } else if (state == 2) {
        color = '#557599';
      }
      var els = [el.rows[0].cells[0].firstChild, el.rows[0].cells[1].firstChild];
      for (var i in els) {
        els[i].style.backgroundColor = color;
        els[i].style.color = '#FFFFFF';
        if (state == 2) {
          els[i].style.paddingTop = '4px';
          els[i].style.paddingBottom = '2px';
        } else {
          els[i].style.paddingTop = '3px';
          els[i].style.paddingBottom = '3px';
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

      var params = {};
      var fields = ['title', 'description', 'image', 'noparse'];
      for (var i = 0; i < fields.length; ++i) {
        if (details[fields[i]]) {
          params[fields[i]] = details[fields[i]];
        }
      }

      var popupName = '_blank';
      var width = 554;
      var height = 349;
      var left = (screen.width - width) / 2;
      var top = (screen.height - height) / 2;
      var url = this._base_domain + 'share.php?url=' + details.url;
      var popupParams = 'scrollbars=0, resizable=1, menubar=0, left=' + left + ', top=' + top + ', width=' + width + ', height=' + height + ', toolbar=0, status=0';
      var popup = false;
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
        var row = elem.rows[0];
        if (count) {
          var c = this._ge('vkshare_cnt'+index);
          c.innerHTML = count;
          row.cells[2].firstChild.style.display = 'block';
        } else {
          row.cells[2].firstChild.style.display = 'none';
        }
      }
    }
  }
  try {
    VK.Share._loc = location.toString();
  } catch(e) {
    VK.Share._loc = 'http://vk.com/';
  }
}
try{if (window.stManager) stManager.done('api/share.js');}catch(e){}
