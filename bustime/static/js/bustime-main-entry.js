var system_deps;
if (test_mode) {
    system_deps = ['jquery', 'howler', 'leaflet', 'justgage', 'jscolor', "socket_io", "maplibre-gl",
        "recorder", "hotkeys", "js_cookie", 'vue', 'tablesort', "semantic",
        "common"];
    if (is_main_page) {
        system_deps.push("bustime-maplibre");
    }
        
    System.register(system_deps, function (exports, context) {
        "use strict";
        var jquery, howler, leaflet, justgage, jscolor, io, Recorder,
            hotkeys, Cookies, vue, tablesort, semantic, city_vars, common;
        var __moduleName = context && context.id;
        return {
            execute: function () {
                System.import("jquery-ui").then(function () {
                    System.import("jquery.modal").then(function () {
                        System.import("leaflet-maplibre-gl").then(function() {
                            System.import("bustime-main").then(function () {
                                if (is_main_page) {
                                    document_ready();
                                } else {
                                    page_ready();
                                }
                            });
                        });
                    });
                });
            }
        };
    });
} else {
    system_deps = ["bundle_built"];
    if (typeof us_sound !== 'undefined' && us_sound) {
        system_deps.push("howler");
    }

    if (is_main_page) {
    //   system_deps.push("maplibre-gl");
      system_deps.push("bustime-maplibre");
    }

    System.register(system_deps, function (exports, context) {
        "use strict";
        var main_deps;
        var __moduleName = context && context.id;
        return {
            execute: function () {
                if (is_main_page) {
                    document_ready();
                } else {
                    page_ready();
                }
                // System.import("bundle_built").then(function () {
                //     document_ready();
                // });
            }
        };
    });
}


// const _baseUrl = "/static/js"
// let deps = ['jquery', 'jquery-ui', 'jquery.modal.min', 'howler.min', 'city-' + us_city + '-' + us_city_rev, 'addtohomescreen-ru.min', 'leaflet', 'justgage', 'jscolor.min', 'socket.io-2.0.4', 'recorder.min', 'hotkeys.min', "js.cookie", 'semantic-main.min']
// let imports = deps.map(entry => {
//     return {entry: _baseUrl + "/" + entry};
// })

// System.addImportMap({
//     "imports": {
//         "main_deps": "/static/js/main-deps.js",
//         "main_built": `/static/js/main-built-30.js`,
//         "howler": "/static/js/howler.min.js",
//         "city_vars": `/static/js/city-${us_city}-${us_city_rev}.js`
//     }
// });
