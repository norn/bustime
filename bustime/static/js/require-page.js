var require_blibs =  ['jquery', 'fastclick', 'semantic-page.min', 'vk_openapi', 'leaflet', "bustime-page"];

require.config({
    baseUrl: '/static/js/',
    shim: {
      "semantic-page.min": ['jquery']
    }
});

require(['jquery', 'fastclick', 'semantic-page.min', 'vk_openapi', 'leaflet', "bustime-page"], function() {
      document_ready();
});
