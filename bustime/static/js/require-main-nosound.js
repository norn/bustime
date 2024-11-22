var require_blibs =  ['jquery', 'jquery-ui', 'jquery.modal.min', 'city-'+us_city+'-'+us_city_rev, 'addtohomescreen-ru.min', 'leaflet', 'justgage', 'jscolor.min', 'socket.io-2.0.4', 'hotkeys.min', "js.cookie", 'semantic-main.min'];

require.config({
    baseUrl: '/static/js/',
    shim: {
      "bustime-main": require_blibs,
      "semantic-main.min": ['jquery']
    }
});

require(["socket.io-2.0.4"], function(aaa) {
  io = aaa;
});
require(["js.cookie"], function(a) {
  Cookies = a;
});

require(['jquery', 'jquery-ui', 'jquery.modal.min', 'city-'+us_city+'-'+us_city_rev, 'addtohomescreen-ru.min', 'leaflet', 'justgage', 'jscolor.min', 'socket.io-2.0.4', 'hotkeys.min', 'semantic-main.min', "js.cookie", "common", 'bustime-main'], function() {
      document_ready();
});
