// https://w.soundcloud.com/player/api

// 'material-1.0.4.min'
var require_blibs =  ['jquery', 'jquery-ui', 'fastclick', 'autobahn-0.9.6x.min', 'howler-2.0.beta.min', 'soundcloud_api', "vk_openapi", 'nbusstops-'+us_city+'b', 'addtohomescreen-ru.min', 'vk_share', 'leaflet', 'semantic-main.min'];
//if (us_sound) {
// require_blibs.push('howler-1.1.25.min');
// require(["howler-1.1.25.min"], function(aaa) {
//  });
//}
var require_blibss = require_blibs.slice();
require_blibss.push("bustime-main");

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

require(['jquery', 'jquery-ui', 'fastclick', 'autobahn-0.9.6x.min', 'howler-2.0.beta.min', 'soundcloud_api', "vk_openapi", 'nbusstops-'+us_city+'b', 'addtohomescreen-ru.min', 'vk_share', 'leaflet', 'semantic-main.min', 'bustime-main'], function() {
      document_ready();
});
