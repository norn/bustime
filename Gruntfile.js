const glob = require("glob");
module.exports = function (grunt) {
    let buildNum = parseInt(grunt.option('build')) || 1;
    console.log("BUILD_NUM:", buildNum);
    grunt.initConfig({
        uglify: {
            'bundle': {
                options: {
                    // beautify: true,
                    // mangle: false,
                    beautify: false,
                    mangle: true,
                    // sourceMap: true,
                    // sourceMapName: 'sourceMap.map'
                },
                src: [
                    'bustime/static/js/socket.io-2.0.4.js',
                    'bustime/static/js/jquery.js',
                    'bustime/static/js/jquery-ui.js',
                    'bustime/static/js/justgage.js',
                    'bustime/static/js/recorder.min.js',
                    'bustime/static/js/hotkeys.min.js',
                    'bustime/static/js/js.cookie.js',
                    'bustime/static/js/leaflet.js',
                    'bustime/static/maplibre/maplibre-gl.js',
                    'bustime/static/maplibre/leaflet-maplibre-gl.js',
                    'bustime/static/js/semantic.min.js',
                    'bustime/static/js/vue.global.prod.js',
                    'bustime/static/js/tablesort.js',
                    'bustime/static/js/jscolor.min.js',
                    'bustime/static/js/jquery.modal.min.js',
                    'bustime/static/js/common.js',
                    'bustime/static/js/bustime-main.js',
                    'bustime/static/js/bustime-main-entry.js',
                ],
                dest: `bustime/static/js/bundle-built-${buildNum}.js`,
            },
        },
        jshint: {
            options: {
                curly: true,
                eqeqeq: true,
                eqnull: true,
                browser: true,
                globals: {
                    jQuery: true
                },
		esversion: 6		
            },
            all: [
                'bustime/static/js/bustime_main.js',
                'bustime/static/js/common.js',
                'bustime/static/js/bustime-page.js',
                'bustime/static/js/bustime-main-entry.js',
            ]
        },
        cssmin: {
            options: {
                mergeIntoShorthands: false,
                roundingPrecision: -1
            },
            target: {
                files: [{
                    src: [
                        "bustime/static/css/leaflet.css",
                        "bustime/static/css/semantic.min.css",
                        "bustime/static/css/font-awesome.min.css",
                        "bustime/static/css/jquery-ui.min.css",
                        "bustime/static/css/jquery.modal.min.css",
                        "bustime/static/maplibre/maplibre-gl.css",
                        "bustime/static/css/bustime-maplibre.css",
                        "bustime/static/css/bustime-main.css",
                        "bustime/static/css/bustime-page.css",
                    ],
                    dest: `bustime/static/css/base-union-${buildNum}.css`
                }]
            }
        },
    });

    function getBuildNum(regex) {
        const glob = require("glob");
        const paths = glob.sync(regex)
        const buildNum = (paths.length > 0) ?
            Math.max(...paths.map(o => {
                let r = o.match(new RegExp('-(\\d+\).'));
                return r ? r[1] : 0;
            })) + 1 : 1;
        console.log('Output:', regex.replace("*", buildNum));
        return buildNum
    }
    // grunt.loadNpmTasks('grunt-contrib-concat');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-contrib-cssmin');

    grunt.registerTask('default', ['jshint', 'uglify']);
};
