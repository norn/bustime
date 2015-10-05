var require_blibs =  ['jquery', 'jquery-ui', 'fastclick', 'autobahn-0.9.6x.min', 'soundcloud_api', "vk_openapi", 'nbusstops-'+us_city+'b', 'addtohomescreen-ru.min', 'vk_share', 'leaflet', 'semantic-main.min'];

require.config({
    baseUrl: '/static/js/',
    shim: {
      "bustime-main": require_blibs,
      "semantic-main.min": ['jquery']
    }
});

require(["autobahn-0.9.6x.min"], function(aaa) {
  autobahn = aaa;
});

require(['jquery', 'jquery-ui', 'fastclick', 'autobahn-0.9.6x.min', 'soundcloud_api', "vk_openapi", 'nbusstops-'+us_city+'b', 'addtohomescreen-ru.min', 'vk_share', 'leaflet', 'semantic-main.min', 'bustime-main'], function() {
      document_ready();
});
