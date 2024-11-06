var require_blibs =  ['jquery', 'jquery-ui', 'jquery.modal.min', 'howler.min', 'semantic-page.min', 'leaflet', 'vue.min', 'jscolor.min', 'socket.io-2.0.4', 'tablesort', "js.cookie"];

require.config({
    baseUrl: '/static/js/',
    shim: {
      "bustime-page": require_blibs,
      'tablesort': ['jquery'],
      "semantic-page.min": ['jquery'],
      "jquery.modal.min": ['jquery']
    }
});

require(["vue.min"], function(aaa) {
  Vue = aaa;
});
require(["socket.io-2.0.4"], function(aaa) {
  io = aaa;
});
require(["js.cookie"], function(a) {
  Cookies = a;
});

require(['jquery', 'jquery-ui', 'jquery.modal.min', 'howler.min', 'semantic-page.min', 'leaflet', 'vue.min', 'jscolor.min', 'socket.io-2.0.4', 'tablesort', "js.cookie", "common", "bustime-page"], function() {
      document_ready();
});