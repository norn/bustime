"use strict";

const fs = require("fs");
const glob = require('glob');
const path = require("path");
const webpack = require('webpack');
// const SystemJSPublicPathWebpackPlugin = require("systemjs-webpack-interop/SystemJSPublicPathWebpackPlugin");
const UglifyJsPlugin = require('uglifyjs-webpack-plugin');
const WebpackObfuscator = require('webpack-obfuscator');
const {CleanWebpackPlugin} = require("clean-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
// const exclusions = /node_modules/;

const paths = glob.sync('./bustime/static/js/main-built-*.js')
// const code = fs.readFileSync("./bustime/static/js/bustime-main.js")

const buildNum = (paths.length > 0) ?
    Math.max(...paths.map(o => {
        let r = o.match(new RegExp('-(\\d+\).js'));
        return r ? r[1] : 0;
    })) : 1;

console.log(buildNum)

module.exports = {
    context: __dirname + "/bustime/static/js",
    // __system_context.import(`city-${us_city}-${us_city_rev}.js`),
    entry: ["./bustime-main.js"],
    resolve: {
        modules: ['./', 'node_modules'],
        alias: {
            common$: './common.js',
        }
    },

    externals: {
        'lodash': 'lodash'
    },
    amd: {
        "jQuery": true,
        "leaflet": true,
        "js-cookie": true,
    },

    module: {
        rules: [
            { parser: { system: true }},
            {
                test: require.resolve("./bustime/static/js/common.js"),
                loader: "exports-loader",
                options: {
                    exports: [
                        "isIpad",
                        "isAndroid",
                        "isWinPhon",
                        "isIos",
                        "isChrome",
                        "isSafari",
                        "getUserAgent"
                    ]
                }
            },
            {
                test: require.resolve("./bustime/static/js/bustime-main.js"),
                loader: "exports-loader",
                options: {
                    exports: [
                        "isIpad",
                        "isAndroid",
                        "isWinPhon",
                        "isIos",
                        "isChrome",
                        "isSafari",
                        "getUserAgent",
                        "Howl",
                        "change_mode",
                    ]
                }
            },
            {
                test: require.resolve('./bustime/static/js/jquery-3.5.1.min.js'),
                use: [{
                    loader: 'expose-loader',
                    options: {
                        exposes: [
                            "$",
                            "jquery",
                            "jQuery",
                        ]
                    }
                }]
            },
            {
                test: require.resolve("./bustime/static/js/bustime-main.js"),
                use: [{
                    loader: "imports-loader",
                    options: {
                        imports: [
                            // "default jquery $",
                            "named ./common.js isIpad",
                            "named ./common.js isAndroid",
                            "named ./common.js isWinPhon",
                            "named ./common.js isIos",
                            "named ./common.js isChrome",
                            "named ./common.js isSafari",
                            "named ./common.js getUserAgent",
                            "named howler Howl",
                            "default socket.io-client io",
                            "default hotkeys.min.js hotkeys",
                            "default jquery-ui core",
                            "default jquery-ui widgets",
                            "default ./semantic-main.min.js semantic"
                            // "default js-cookie Cookies",
                        ],
                        // wrapper: "window",
                        additionalCode: "" +
                            "define([`city-${us_city}-${us_city_rev}`], function() {\n" +
                            "    document_ready();\n" +
                            "});"
                    }
                },
                ]
            },
            // {
            //     test: require.resolve("./bustime/static/js/bustime-main.js"),
            //     use: [{
            //         loader: "imports-loader",
            //         options: {
            //             type: 'commonjs',
            //             imports: [
            //                 "single js-cookie Cookies"
            //             ],
            //         }
            //     },
            //     ]
            // },
        ],

    },

    output: {
        path: path.resolve(__dirname, "bustime/static/js"),
        // publicPath: "/static/",
        // filename: "[name].js",
        filename: `main-built-29.js`,

        library: {
            type: 'window',
            // type: 'system',
        },
        // filename: '[name].[id].bundle.js',
        // chunkFilename: "[id]-[chunkhash].js",
        // library: {
        //     name: `main-built-${buildNum}`,
        //     type: "umd",
        // }
        // umdNamedDefine: true,
        // library: {
        //     name: `main-built-${buildNum}`,
        //     type: 'global',
        // }
    },

    // optimization: {
    // minimizer: [new UglifyJsPlugin({
    //     uglifyOptions: {
    //         mangle: true,
    //         output: {
    //             comments: false
    //         }
    //     }
    // })],
    // },
    plugins: [
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "window.jQuery": "jquery",
            "window.$": "jquery",
            Cookies: ["js-cookie", "default"],
            "window.Cookies": ["js-cookie", "default"],
            L: "leaflet",
            "window.L": "leaflet",
        }),
        // new SystemJSPublicPathWebpackPlugin({
        //
        // }),
        // new webpack.ProvidePlugin({
        //     identifier: path.resolve(__dirname, "bustime/static/js/common.js"),
        // }),
        // new webpack.ProvidePlugin({
        // }),
        // new UglifyJsPlugin({minimize: true})
        // new webpack.optimize.UglifyJsPlugin({minimize: true})
        // new webpack.ProvidePlugin({
        //     L: 'leaflet',
        // identifier: path.resolve(path.join(__dirname, './bustime/static/js/jquery')),
        // identifier: path.resolve(path.join(__dirname, './bustime/static/js/leaflet')),
        // identifier: 'leaflet',
        // }),
        // new WebpackObfuscator (),
        // new webpack.DefinePlugin({
        //   BUILT_AT: webpack.DefinePlugin.runtimeValue(Date.now, {
        //     fileDependencies: [fileDep],
        //   }),
        // })
    ],
    devServer: {
        injectClient: false,
        // writeToDisk: true,
    },

    mode: "development"
}


// module.exports.module.rules.concat(CITIES.map((name) => {
//         return {
//             test: require.resolve(`./bustime/static/js/${name}`),
//             loader: "exports-loader",
//             options: {
//                 exports: [
//                     "stops",
//                     "BUS_PROVIDERS",
//                     "BUSES",
//                 ]
//             }
//         }
//     }),
// )