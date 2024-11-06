// https://w.soundcloud.com/player/api

// 'material-1.0.4.min'

var require_blibs =  ['jquery', 'jquery-ui', 'jquery.modal.min', 'howler.min', 'city-'+us_city+'-'+us_city_rev, 'addtohomescreen-ru.min', 'leaflet', 'justgage', 'jscolor.min', 'socket.io-2.0.4', 'recorder.min', 'hotkeys.min', "js.cookie", 'semantic-main.min'];
//if (us_sound) {
// require_blibs.push('howler-1.1.25.min');
// require(["howler-1.1.25.min"], function(aaa) {
//  });
//}

//var require_blibss = require_blibs.slice();
//require_blibss.push("bustime-main");

require.config({
    baseUrl: '/static/js/',
    shim: {
      "bustime-main": require_blibs,
      "semantic-main.min": ['jquery'],
      "jquery.modal.min": ['jquery']
    }
});

require(["socket.io-2.0.4"], function(a) {
  io = a;
});
require(["recorder.min"], function(a) {
  Recorder = a;
});
require(["js.cookie"], function(a) {
  Cookies = a;
});

/*define(['socket.io-1.4.8'], function (io) {
  var socket = io.connect ...
}*/

require(['jquery', 'jquery-ui', 'jquery.modal.min', 'howler.min', 'city-'+us_city+'-'+us_city_rev, 'addtohomescreen-ru.min', 'leaflet', 'justgage', 'semantic-main.min', 'jscolor.min', 'socket.io-2.0.4', 'recorder.min', 'hotkeys.min', "js.cookie", "common", 'bustime-main'], function() {
      document_ready();
});
