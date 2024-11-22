// "use strict";
/* существует переменная test_mode, равная true, при добавлении ?t (&t) в url или при наличии куки debug со значением > 0 */
var test_latlng = null; // для тестирования
var autoupdate = "";
var autoupdate_force = 0;
var BUS_ID = "";
var STOP_IDS = [];
var STOP_IDS_SUBS = [];
var STOP_DESTINATION_IDS = [];
var NEAREST_STOPS = [];
var BUS_SIDE_IMG = "/static/img/side_bus_original.png";
var CAT_IMG = '/static/img/cat-male.png';
var CAT_SYM = 'fa-user';
if (holiday_flag == "cosmonautics") {
    CAT_SYM = "fa-rocket";
} else if (holiday_flag == "joke") {
    CAT_SYM = "fa-hand-spock-o";
} else if (holiday_flag == "bitcoin") {
    CAT_SYM = "fa-btc";
}
var CAT_IMG_OLD;
var CAT_SYM_OLD;
var BUS_VOICE_ANOUNCE=0
var VOICE_QUEUE=[];
var VOICE_NOW=0;
var TTYPE = 0;
var refresh = 30000;
var ticktackt = 0;
var ticktacktick = 500;
var cats = {};
var mycat;
var audioinited = 0;
var socket;
var supportsVibrate = "vibrate" in navigator;
var isiPad = isIpad();
var isWP = isWinPhon();
var isAndroid = isAndroid();
var is_chrome = isChrome();
var lastCheck = 0;
var last_bdata_mode10;
var globus = {};
var current_vehicle_info;
var current_rating_data;
var map_is_centered = 0;
var usePositionWatch_last = 0;
var speed_show_last = new Date();
var bus_mode10_subs;
var bus_mode11_subs;
var swidget;
var radio_status = 0;
var radio_curtime = 0;
var current_nbusstop;
var current_nbusstop_notified;
var game;
var radar_circle = null;
var schedule = { 0: [], 1: [] };
var ol_map;
var ol_map_view;
var CITY_MONITOR_ONSCREEN = {};
var NO_MORE_USE_POSITION = 0;
var timer_minutes;
var PIXI;
var autobahn;
var running_light_cnt = 1;
var express_dial = "";
var express_dial_type = 0;
// var BNAME_BID = {};
var DB;
var OSM_STYLE = 'https://demotiles.maplibre.org/style.json'
var OSMURL = '//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var message_queue = [];
var current_item = null;
var interval_id = null;

// TODO [skincat]: Map for cities Spb, Voronezh, Belgorod was disabled
// https://wiki.openstreetmap.org/wiki/Raster_tile_providers
/*
if (us_city == 5 || us_city == 18 || us_city == 126 || us_city == 46 || us_city == 17) {
    OSMURL = "//a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png";
    OSMURL = "//tile.openstreetmap.de/{z}/{x}/{y}.png"; // красивше
}
*/
// var OSMURL = '//osmtile.bustime.ru/{z}/{x}/{y}.png';
// var osm = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
var recognition;
var recognition_result = '';
var recognition_inited = 0;
var gosnum_recognition;
var gosnum_recognition_result = '';
var gosnum_recognition_inited = 0;

var is_retina = (window.devicePixelRatio > 1);
var sound_main, sound_speed, sound_radio_in, sound_radio_out;
//var mode_selected = 0; // moved to _js_init
var dance_move = 1;
var rate;
var speed_gauge;
var routes_data;
var routes_data_current;
var scroll; // vehicle info position
var scroller_dir = 0; // scroller for show mode 7
var counter_online = 0;
var counter_today = 0;
var animate_ads_shuttle_original = 0;
var animate_ads_shuttle_step = 0;
var THEME = "modern";
var recorder;
var audio_context;
var ptt_stream;
var watch_gps_send = 0;
var gps_send_last = null;
var watch_usepos = 0;
var taxi_sound = null;
var taxi_maps = {};
var busstop_click_cnt = 0;
var current_inf_for_counters = {};

function audiocontext_enable(){
    //console.log('audiocontext_enable');
    let AudioContext = window.AudioContext || window.webkitAudioContext;
    if(AudioContext){
        new AudioContext().resume();
    }
}   // audiocontext_enable

// var btype_color = {0: "#FFE216", 1: "#d3e7ff", 2: "#FFB76B", 3: "#a1ffa1"}

navigator.getUserMedia  = navigator.getUserMedia ||
                          navigator.webkitGetUserMedia ||
                          navigator.mozGetUserMedia ||
                          navigator.msGetUserMedia;
var media_connection;

// startswith for ie
if (!String.prototype.startsWith) {
    String.prototype.startsWith = function(str) {
        return this.lastIndexOf(str, 0) === 0;
    };
}

var standalone = window.navigator.standalone,
    userAgent = getUserAgent(),
    safari = isSafari(),
    is_ios = isIos();

function is_touch_device() {
  return 'ontouchstart' in window        // works on most browsers
      || navigator.maxTouchPoints;       // works on IE10/11 and Surface
};

function sound_init() {
    if (us_sound) {
        if (language == "ru") {
            sound_main = new Howl({
                src: ['/static/js/snd/bus-lq.ogg', '/static/js/snd/bus-lq.mp3'],
                sprite: {
                    arriving: [0, 2700],
                    one_plus: [2700, 2300],
                    one_minus: [5100, 2700]
                },
                volume: 0.7
            });
        } else if (language == "fi") {
            sound_main = new Howl({
                src: ['/static/js/snd/bus-fi.ogg', '/static/js/snd/bus-fi.mp3'],
                sprite: {
                    arriving: [0, 2100],
                },
                volume: 0.7
            });
        } else {
            sound_main = new Howl({
                src: ['/static/js/snd/bus-en.ogg', '/static/js/snd/bus-en.mp3'],
                sprite: {
                    arriving: [0, 2000],
                },
                volume: 0.7
            });
        }
        if (us_speed_show) {
            sound_speed = new Howl({
                src: ['/static/js/snd/speed_limit.ogg', '/static/js/snd/speed_limit.mp3'],
                volume: 0.7
            });
        }
        else {
            sound_speed = null;
        }
        if (us_radio) {
            sound_radio_in = new Howl({
                src: ['/static/js/snd/radio_in.ogg', '/static/js/snd/radio_in.mp3'],
                volume: 0.2
            });
            sound_radio_out = new Howl({
                src: ['/static/js/snd/radio_out.ogg', '/static/js/snd/radio_out.mp3'],
                volume: 0.2
            });
        }
    }
    audioinited = 1;
}

function start_location_service(force=0) {
    console.log("main: Start location service");
    /*
    Настройки пользователя, устанавливаемые на странице settings:
    us_gps_off - Выключить поиск остановок (по умолчанию включена)
    us_gps_send - Отправлять координаты (по умолчанию выключена)

    watchPosition работает во всех десктопных браузерах только при изменении координат,
    в Firefox работает с заданной периодичностью и без изменения координат
    */
    var options;
    if (navigator.geolocation) {
        // https://developer.mozilla.org/en-US/docs/Web/API/PositionOptions
        options = {
            enableHighAccuracy: false,
            maximumAge: 0
        };
        if(force || (taxiuser && taxiuser.gps_on)) {
            navigator.geolocation.getCurrentPosition(usePosition, noPosition, options);
        }

        if (us_gps_send === 1 || (taxiuser && taxiuser.gps_on)) {
            options = {
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 10000
            };
            watch_gps_send = navigator.geolocation.watchPosition(gps_send, noPosition, options);
        }
        else if (watch_gps_send){
            navigator.geolocation.clearWatch(watch_gps_send);
            watch_gps_send = 0;
        }

        if( !watch_usepos && !(taxiuser && taxiuser.gps_on) && !us_gps_send){
            options = { enableHighAccuracy: true, maximumAge: 0 };
            watch_usepos = navigator.geolocation.watchPosition(usePositionWatch, noPosition, options); // call usePosition() every 30 sec.
        }
    }   // if (navigator.geolocation)
}   // start_location_service


// отправка координат на сервер водителем автобуса
function gps_send(position) {
    //console.log('gps_send');
    let now = Date.now();
    if (gps_send_last && (now - gps_send_last < 6000)) {
       return; // don't send often
    }
    gps_send_last = now; // last time we sent
    prepare_to_send(position);
    if( !to_send || !to_send.timestamp ){
        return;
    }
    if (us_speed_show) {
        speed_show(position);
        $(".speed_show").html("");
    }
    to_send.taxi = (taxiuser && taxiuser.driver && taxiuser.gps_on);
    to_send.taxi_order = ((taxiuser && taxiuser.order_id) || null);

    // data=>zbusd/rpc_server.py:rpc_gps_send(data)=>bustime/inject_events.py:inject_custom(data)
    socket.emit("rpc_gps_send", to_send, function (data) {
        if(test_mode){
            console.log('gps_send', to_send, data);
        }

        var cnt = data['cnt'];
        var odometer = data['odometer'];

        $(".gps_send_cnt").parent().addClass("green");
        $(".gps_send_cnt").html(cnt).addClass('bhlight');
        setTimeout(function() {
            $('.gps_send_cnt').removeClass('bhlight');
        }, 400);
        var odometer_prev = $(".speed_show_odometer").html();
        if (odometer_prev) {
            odometer_prev = odometer_prev.substr(0, odometer_prev.length-3)
            odometer_prev = parseInt(odometer_prev, 10);
        }

        $(".speed_show_odometer").html(odometer+" " + trans_text_km);

        if (odometer_prev && odometer != odometer_prev) {
            $(".speed_show_odometer").addClass('bhlight');
            setTimeout(function() {
                $('.speed_show_odometer').removeClass('bhlight');
            }, 400);
        }
    });
}   // gps_send


// отправка координат на сервер пассажиром
function usePosition(position) {
    //console.log('usePosition');

    // ajax_metric("stop_name_gps", 1);

    prepare_to_send(position);

    if (NO_MORE_USE_POSITION > 0) {
        console.log("no more use position");
        return;
    }

    if(test_mode){
        console.log('usePosition', to_send);
    }

    var request = $.ajax({
        url: "/ajax/stops_by_gps/", // bustime.views.ajax_stops_by_gps(), сохраняется в модель PassengerStat
        type: "post",
        data: {
            lat: to_send.lat,
            lon: to_send.lon,
            accuracy: to_send.accuracy,
            timestamp: to_send.timestamp,
            bus_id: BUS_ID,
            bus_name: get_bname(BUS_ID),
            taxi_order: ((taxiuser && taxiuser.order_id) || null),
        },
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        //console.log("main: usePosition.done", msg);
        var s = "";
        var sname;
        if (msg.length > 0) {
            stop_ids(msg[0].ids);
            //set_current_nbusstop(msg[0].ids);
            set_current_nbusstop(msg[0].current_nbusstop);
            $("#id_stops").val(msg[0].name);    // from-to*.html
            NEAREST_STOPS = [];

            for (var i = 0; i < msg.length; i++) {
                NEAREST_STOPS[i] = msg[i];
                sname = msg[i].name;
                if (sname.length > 20) {
                    sname = sname.substring(0, 20) + "...";
                }
                s = s + "<button class='ui tiny compact button' onclick='nearest_click(" + i + ")'>" + sname + ' ' + msg[i].d + "м</button> ";
            }
        }
        $('.stop_sug').html(s); // in index-test.html, demo_show.html
        $('.stop_sug').show();
    });
}   // usePosition


function noPosition(error) {
    //console.log("GPS error: " + error.code);
    $(".speed_show").css("background-color", '#f99');

    switch (error.code) {
        case error.PERMISSION_DENIED:
            $(".speed_show").html("GPS denied");
            //ajax_metric("stop_name_gps_denied", 1);
            //"User denied the request for Geolocation."
            break;
        case error.POSITION_UNAVAILABLE:
            $(".speed_show").html("no GPS");
            //"Location information is unavailable."
            break;
        case error.TIMEOUT:
            $(".speed_show").html("GPS timed out");
            //"The request to get user location timed out."
            break;
        case error.UNKNOWN_ERROR:
            $(".speed_show").html("GPS error " + error.code);
            break;
    }
}   // noPosition


function prepare_to_send(position){
    let temp = null;
    let deltaseconds = Math.round( (position.timestamp - (to_send.timestamp || 0)) / 1000);
    //console.log(`prepare_to_send: position.timestamp=${position.timestamp}, to_send.timestamp=${to_send.timestamp}, deltaseconds=${deltaseconds}`);

    // speed & heading не предоставляются браузером, рассчитаем, если есть предыдущие координаты
    if( to_send.timestamp && (!position.coords.heading || !position.coords.speed) ){
        temp = distance(to_send.lat, to_send.lon, position.coords.latitude, position.coords.longitude, deltaseconds);
    }

    to_send.timestamp = position.timestamp;
    to_send.lat = position.coords.latitude;
    to_send.lon = position.coords.longitude;
    to_send.accuracy = position.coords.accuracy

    // Это для отладки такси
    if( test_mode && Cookies.get('debug') ){
        /* отладка такси, и см. комментарии в start_location_service() */
        to_send.lat = taxiuser.driver ? 56.039409 : test_latlng ? test_latlng.lat : 56.045954;    // Красноярск
        to_send.lon = taxiuser.driver ? 92.864565 : test_latlng ? test_latlng.lng : 92.888460;
        to_send.accuracy = 300;  // bustime.inject_events.inject_custom() требует accuracy <= 300, desktop borowsers устанавливает ~15000
    }

    to_send.us_id = us_id;
    to_send.speed = position.coords.speed ? position.coords.speed : (temp ? temp.speed : 0);
    to_send.heading = position.coords.heading ? position.coords.heading : (temp ? temp.heading : 0);
    to_send.taxi = (taxiuser && taxiuser.driver && taxiuser.gps_on);
    to_send.taxi_order = (taxiuser && taxiuser.order_id || null);

    window.gps_send_last = to_send;
    return deltaseconds;
}   // prepare_to_send


function nearest_click(i) {
    NO_MORE_USE_POSITION = 0;
    stop_ids(NEAREST_STOPS[i].ids);
    $("#id_stops").val(NEAREST_STOPS[i].name);
}

function set_current_nbusstop(ids) {
    //console.log("ids:"+ids);
    if (!ids) {return}
    //current_nbusstop = ids[0];
    current_nbusstop = ids;
    $(".bhlight_border").removeClass('bhlight_border');
    $("[bst_id=" + current_nbusstop + "]").next().addClass('bhlight_border');
    /*ids.forEach(function(id_) {
        $("[bst_id=" + id_ + "]").next().addClass('bhlight_border');
    });*/
}

// расстояние между двумя координатами, метры
function distance(latA, longA, latB, longB, deltatime) {
    const EARTH_RADIUS = 6378137.0;  /* радиус земли в метрах. */
    const D2R = 0.0174532925;        /* коэфф. перевода градусов в радианы */
    const R2D = 57.2957795131;       /* коэфф. перевода радиан в градусы */
    /* функции javascript работают с радианами */
    let lat1 = latA * D2R;
    let lat2 = latB * D2R;
    let long1 = longA * D2R;
    let long2 = longB * D2R;
    let deltalon = long2 - long1;
    let deltalat = lat2 - lat1;

   let retval = {
       'distance': 0,    /* метры */
       'heading': 0,
       'speed': 0
   }

    if( (latA != latB) || (longA != longB) ){
       /* угловое расстояние в радианах */
       let a = Math.acos(Math.sin(lat1) * Math.sin(lat2) + Math.cos(lat1) * Math.cos(lat2) * Math.cos(deltalon));
       retval['distance'] = Math.round(EARTH_RADIUS * a);    /* метры */

        if( deltatime && deltatime > 0 ){
            /* расчет направления */
            if( deltalat > 0 && deltalon >= 0 ) {       // 1 четверть (СВ) r = a
                retval['heading'] = Math.round(Math.atan(deltalon/deltalat) * R2D);
            }
            else if( deltalat < 0 && deltalon >= 0 ) {  // 2 четверть (ЮВ) a = 180° – r
                retval['heading'] = 180 - Math.round(Math.abs(Math.atan(deltalon/deltalat)) * R2D);
            }
            else if( deltalat < 0 && deltalon < 0 ) {   // 3 четверть (ЮЗ) a = r + 180°
                retval['heading'] = 180 + Math.round(Math.abs(Math.atan(deltalon/deltalat)) * R2D);
            }
            else if( deltalat > 0 && deltalon < 0 ) {   // 4 четверть (СЗ) a = 360° – r
                retval['heading'] = 360 - Math.round(Math.abs(Math.atan(deltalon/deltalat)) * R2D);
            }
            else if( deltalat === 0 ) {
                if( deltalon > 0 ) {      // 1 четверть (СВ)
                    retval['heading'] = 90;
                }
                else if( deltalon < 0 ) { // 3 четверть (ЮЗ)
                    retval['heading'] = 270;
                }
            }

            /* расчет скорости */
            let speed = retval['distance'] / deltatime * 3.6;   /* км/ч */
            retval['speed'] = parseFloat(speed.toFixed( speed > 10 ? 0 : 2 ));
        }
    }

   return retval;
}   // distance


function speed_show(position) {
    var speed = position.coords.speed;
    if (!speed) {speed=to_send.speed}
    if (!speed) {
        return;
    }
    // convert m/s to km/h == x * 60*60/1000.0
    speed = parseInt(speed * 3.6, 10);
    if (speed > 55) {
        aplay("sound_speed");
        $(".speed_show_warn").html("<img style='width:220px;height:234px' src='/static/img/speed_limit_mascot.png'>");
    } else {
        $(".speed_show_warn").html("");
    }
    speed_gauge.refresh(speed);
}


function usePositionWatch(position) {
    var now = new Date();
    if (us_gps_off === 0 && (usePositionWatch_last === 0 || now.getTime() - usePositionWatch_last.getTime() > 30 * 1000)) {
        usePositionWatch_last = now;
        usePosition(position);
    }
    if (us_speed_show) {
        speed_show(position);
    }
}

function peer_set(peer_id) {
    var to_send_peer = {
        us_id: us_id,
        peer_id: peer_id
    }
    socket.emit("rpc_peer_set", to_send);
}

String.prototype.endsWith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1;
};


function speed_show_init() {
    speed_gauge = new JustGage({
        id: "speed_show_gauge",
        value: 0,
        min: 0,
        max: 100,
        label: "км/ч",
        levelColorsGradient: false,
        pointer: true,
        pointerOptions: {
            toplength: -18,
            bottomlength: 7,
            bottomwidth: 12,
            color: '#8e8e93',
            stroke: '#ffffff',
            stroke_width: 2,
            stroke_linecap: 'round'
        },
        customSectors: [{
            color: "#b9d409",
            lo: 0,
            hi: 60
        }, {
            color: "#faa001",
            lo: 60,
            hi: 67
        }, {
            color: "#fc0000",
            lo: 67,
            hi: 100
        }]
    });
}

function websconnect() {
    //     io.on('connection', function(socket){
    //   socket.join('some join');
    //   console.log("JOIN");
    // });
    if (io_port) {
        socket = io(`http://127.0.0.1:${io_port}`);
    } else {
        socket = io(); // wss://host:port/socket.io/
    }
    
    // http://stackoverflow.com/questions/10405070/socket-io-client-respond-to-all-events-with-one-handler
    var onevent = socket.onevent;
    socket.onevent = function (packet) {
        var args = packet.data || [];
        onevent.call (this, packet);    // original call
        packet.data = ["*"].concat(args);
        onevent.call(this, packet);      // additional call to catch-all
    };


    socket.on('connect', function() {
        var d = new Date();
        //console.log(d + ": Socket connected");
        $('#status_city_circular').removeClass('red').addClass('green');  // меняем цвет индикатора на зеленый
        $('#status_city_text').text('Online');                           // меняем текст индикатора с Offline на Online
        socket.emit('authentication', {username: us_id, password: "", os:"web"});
        // socket.emit('authentication', '{"username": '+us_id+', "password": "", "os":"mac"}');
        // $(".downloado").removeClass('download').addClass("globe").attr("title", 'оптимальное соединение Websocket');
        // $('.busnumber').removeClass('bw');
        if (BUS_ID) {
            sub_bus_id();
        } else {
            hashcheck();    // переключение типа ТС: Автобус/Троллейбус...
        }
        update_notify(0);

        socket.emit('join', "ru.bustime.counters");
        socket.emit('join', "ru.bustime.bus_amounts__" + us_city);
        //socket.emit('join', "ru.bustime.counters__" + us_city);
        socket.emit('join', "ru.bustime.us__" + us_id);
        socket.emit('join', "ru.bustime.city__" + us_city);
        socket.emit('join', "ru.bustime.taxi__" + us_city);
        if (us_live_indicator) {
            socket.emit('join', "ru.bustime.updater__"+ us_city);  // data for live_indicator
        }

        if (us_speed_show) {
            speed_show_init();
        }
        if (lastCheck === 0) {
            lastCheck = 1;
        } else {
            console.log("time travel detected");
            socket.emit("rpc_bootstrap_amounts", us_city, function (data) {
              router(data);
            });
        }
    });

    socket.on("*",function(event,data) {
        // var d = new Date();
        // if (event == "ru.bustime.counters") {return}
        // console.log(d+": "+event);
        // console.log(data);
        router(data);
    });

    // socket.on("ru.bustime.counters", function(data) {
    //     router(data);
    // });

    socket.on('disconnect', function() {
        $('#status_city_circular').removeClass('green').addClass('red');  // меняем цвет индикатора на зеленый
        $('#status_city_text').text('Offline');                           // меняем текст индикатора с Offline на Online
        //console.log("Disconnect");
    });
}

// периодический запрос данных AJAX, если не работает websocket
function ticktack() {
    if (!socket && autoupdate) {
        // $('#update-icon').css('transform', 'rotate(-' + ticktackt / 1000 * 12 + 'deg)');
        if (ticktackt % 2000 === 0) {
            $('.downloado').html(ticktackt / 2000);
        }
        if (ticktackt === 0 || ticktackt == 15000 || autoupdate_force) {
            ajax_subs();
            autoupdate_force = 0;
            if (STOP_IDS.length > 0) {
                ajax_stop_ids();
            }
        }
    }

    if (ticktackt === 0 || ticktackt < 0) {
        ticktackt = refresh;
    } else {
        ticktackt = ticktackt - ticktacktick;
    }

    setTimeout(function() {
        ticktack();
    }, ticktacktick);
}   // ticktack

function osdclock() {
    var currentTime = new Date();
    var currentHours = currentTime.getHours();
    var currentMinutes = currentTime.getMinutes();
    if (currentMinutes < 10) {currentMinutes = "0"+currentMinutes;}
    $(".osdclock").html('<div class="value"><b>' + currentHours + ":" + currentMinutes) + '</b></div>';

    setTimeout(function() {
        osdclock();
    }, 60000);
}

/*
function update_routes(data, napr, ttype) {
    TTYPE = ttype;
    var i, r, t, sname, middle_num, middle_num0 = 0,
        middle_num1 = 0;

    for (i = 0; i < data.length; i++) {
        if (data[i]['d'] === 0) { middle_num0++ }
        if (data[i]['d'] === 1) { middle_num1++ }
    }
    middle_num0 = middle_num0 / 2;
    middle_num1 = middle_num1 / 2;

    if (middle_num0 <= middle_num1) {
        middle_num = middle_num0;
    } else {
        middle_num = middle_num1;
    }
    if (us_premium) {
        middle_num = 999;
    }
    middle_num0 = middle_num;
    middle_num1 = middle_num;

    var ha1 = "";
    var ha2 = "";
    var hb1 = "";
    var hb2 = "";
    var edit_mode = "";
    for (var i = 0; i < data.length; i++) {
        r = data[i];
        t = "";
        sname = r['name'];
        if (sname.length > 32) {
            sname = sname.substring(0, 32) + "...";
        }
        if (us_edit_mode) {
            edit_mode = ' <a target="_blank" href="/'+us_city_slug+'/stop/id/'+ r['bst'] +'/edit/"><i class="fa fa-pencil fa-fw"></i></a>';
        }
        t = t + '<div class="indicator ';
        if (us_premium) {
          t = t + "premium";
        }
        t = t + '" id="' + r['id'] +
            '" bst_id="' + r['bst'] + '"></div><div class="inf"><div class="busstop_name">'+ edit_mode + sname +'<div class="b1"></div></div></div><br/>';
            // <a href="/'+us_city_slug+'/stop/?id='+r['bst']+'"><i class="fa fa-info fa-fw"></i></a>'

        if (r['d'] === 0) {
            if (middle_num0 <= 0) {
                ha2 = ha2 + t;
            } else {
                ha1 = ha1 + t;
            }
            middle_num0--;
        } else {
            if (middle_num1 <= 0) {
                hb2 = hb2 + t;
            } else {
                hb1 = hb1 + t;
            }
            middle_num1--;
        }
    }
    $('.htmlr.a1').html(ha1);
    $('.htmlr.a2').html(ha2);
    $('.htmlr.b1').html(hb1);
    $('.htmlr.b2').html(hb2);

    $('.busstop_name').click(busstop_click);
    $('.busstop_name').mouseup(busstop_click_up_down).mousedown(busstop_click_up_down);

    // headers
    // $('#napr_a').html(napr[0]);
    // $('#napr_b').html(napr[1]);
    set_current_nbusstop(current_nbusstop);
    // console.log(current_nbusstop);
    routes_data = data;
    if (map) { map_draw_stops(); }
}   // update_routes
*/

function blink_clear() {
    $(".disappear").removeClass('vehicle_here blink-fast-half disappear').html("").css('background', '').removeAttr("vehicle_id");
    $('[time_prediction]').each(function() {
        if ( !$(this).hasClass("vehicle_here") ) {
           var time_prediction = $(this).attr("time_prediction");

           if (time_prediction) {
               $(this).addClass("time_prediction").html(time_prediction);
           }
        }
    });
}

function gosnum_format(g) {
    // http://oarf.ru/gibdd/docs/kody-regionov-na-gos-nomerah.html
    if (us_city == 9) {
        g = g.replace(/(.+?) (59|81|159)$/, '$1');
    } else if (us_city == 5) {
        g = g.replace(/(.+?)(78|98|178|123)$/, '$1');
    } else if (us_city == 16) {
        g = g.replace(/(.+?) (63|163)$/, '$1');
    } else if (us_city == 22) {
        g = g.replace(/(.+?) (55|56|174)$/, '$1');
    }
    return g;
}

function update_bdata_mode10(data) {
    //console.log("update_bdata_mode10 data=", data);
    // if (timeTravel) {
    //     console.log("update_bdata_mode10: time travel fixed");
    //     return;
    // }
    var z, t, i, side_img, sleep, vehicle, vehicle_old;
    var cat_change = 0;
    $(".sleep_bus").remove();
    blink_clear();
    // $(".indicator").removeClass("vehicle_here").css('background','');
    $(".indicator.vehicle_here").addClass("disappear");

    // var globus_old = globus;
    var globus_old = $.extend({}, globus);
    var antiblink, html;
    var anounced={0:0, 1:0};
    var zombie;
    // var copiedObject = jQuery.extend(true, {}, originalObject)

    for (i = 0; i < data['l'].length; i++) {
        vehicle = data['l'][i];

        /*
        antiblink = 0;
        if ( globus[vehicle['u']] && vehicle['b'] != globus[vehicle['u']]['b']) {
            // console.log('antiblink');
            antiblink=1;
        }
        */

        zombie = vehicle['z'];

        globus[vehicle['u']] = vehicle;
        globus[vehicle['u']]['id'] = BUS_ID;
        z = vehicle['b'];
        sleep = vehicle['sleep'];
        if (zombie) {

        } else if (sleep) {
            html = "<div class='sleep_bus' onclick='vehicle_info(" + '"' + vehicle['u'] + '"' + ",0)'><i class='fa fa-coffee'></i> <span>" + gosnum_format(vehicle['g']) + "</span></div>";
            $("#" + vehicle['b']).next().find('.busstop_name').after(html); // список гос№
            //console.log("update_bdata_mode10 html=", html);
        } else {
            // side_img = side_compo(TTYPE, vehicle['r'], vehicle['g'], vehicle['s'], vehicle['custom']);
            // vehicle_old = globus_old[ vehicle['u'] ];
            var hcol = sidebo(vehicle);
            $("#" + z).removeClass("disappear time_prediction").addClass("vehicle_here").attr("vehicle_id", vehicle['u']).html(hcol);

            // if (antiblink)
            //     $("#" + z).addClass("blink-fast-half-anti")

            if (us_voice && !BUS_VOICE_ANOUNCE) {
                // console.log(vehicle);
                if (vehicle['d'] == 0 && anounced[0] == 0) {
                    voice_queue_add("on_busstops/"+BUS_ID+"_0") ;
                    anounced[0] = 1;
                }
                if (vehicle['d'] == 1 && anounced[1] == 0) {
                    voice_queue_add("on_busstops/"+BUS_ID+"_1") ;
                    anounced[1] = 1;
                }
                voice_queue_add("busstop/"+$('#' + z).attr('bst_id')) ;
            }
        }

        // force reload vehicle info if opened
        if (current_vehicle_info && vehicle['u'] == current_vehicle_info) {
            vehicle_info(vehicle['u'], 1);
        }
        if (!sleep && z && z == mycat) {
            mycat = null;
            // console.log("arriving");
            aplay("arriving");
            vibrate();
            $('body').toast({class: 'error', message: trans_text_arriving, showProgress: 'bottom', classProgress: 'red'});
        }
        if (current_nbusstop && current_nbusstop == $('#' + z).attr('bst_id') && current_nbusstop_notified != vehicle['u']) {
            // console.log("arriving");
            aplay("arriving");
            vibrate();
            current_nbusstop_notified = vehicle['u'];
        }
    }
    BUS_VOICE_ANOUNCE = 1;
    $('vehicle_here,img').click(indicator_click);
    $(".disappear").addClass('blink-fast-half');
    setTimeout(blink_clear, 1500);

    // $('.last_upd').html(data['updated']).addClass('bhlight');
    // $('.last_upd').html(data['updated']);
    // setTimeout(function() {
    //     $('.last_upd').removeClass('bhlight');
    // }, 400);

    recalc_schedule();
    if (map && data['l']) {
        update_bdata_mode2(data['l']);
    }
}   // update_bdata_mode10


function update_bdata_mode2(data) {
    var ev, d, g, sleep, marker, MapIconDiv, latlngs, sc, extra_c, i, j;
    var bname = get_bname(BUS_ID);

    if (routes_data_current != BUS_ID) {
        map_draw_stops();
    }

    myCollection.clearLayers();
    var label_txt="";

    for (var i = 0; i < data.length; i++) {
        ev = data[i];
        // название остановки достаем из DB
        // if (DB.route[ev['b']] && DB["route"][ev['b']][1]) {
        if (dbget('route', ev['b'], 'busstop_id')) {
            var id_stops = dbget('route', ev['b'], 'busstop_id')
            ev['bn'] = dbget('nbusstop', id_stops, 'name');
        }

        if (!("x" in ev)) {
            return;
        }
        if (ev['d'] === 0) {
            extra_c = "color-1-2-bg";
            sc = "#74c0ec";
        } else if (ev['d'] === 1) {
            extra_c = "color-2-2-bg";
            sc = "#5ec57c";
        } else {
            extra_c = "color-3-2-bg";
            sc = "#c5c5c5";
        }


        if (ev['g'] && us_show_gosnum) {
            g = '<b>' + gosnum_format(ev['g']) + '</b>, ';
            if (ev['l']){label_txt = "[" + gosnum_format(ev['g'])  + ", "  +  gosnum_format(ev['l']) + "]";}
            else {label_txt = "[" + gosnum_format(ev['g']) + "]";}
            if (ev['bn']) {label_txt = label_txt + "<br/>" + ev['bn'].substr(0, 15);}
        } else if (ev['l'] && us_show_gosnum) {
            g = '<b>' + gosnum_format(ev['l']) + '</b>, ';
            label_txt = "[" + gosnum_format(ev['l']) + "]";
            if (ev['bn']) {
                label_txt = label_txt + "<br/>" + ev['bn'].substr(0, 15);
            }
        } else {
            g = '<b>' + ev['u'] + '</b>, ';
            if (ev['bn']) {
                label_txt = ev['bn'].substr(0, 15 - bname.length);
            } else {
                label_txt = "";
            }
        }

        if (ev['sleep']) {
            sleep = '<br/><i class="fa-coffee icon"></i> ' + trans_text_sleep;
        } else if (ev['z']) {
            sleep = '<i class="fa-hourglass-half icon"></i> ';
        } else if (ev['away']) {
            sleep = '<i class="fa-external-link icon"></i> ';
        } else {
            sleep = "";
        }
        // console.log(ev);
        var big_icon = bus_icon_chooser(dbget('bus', BUS_ID, 'ttype'));
        big_icon = '<div class="sprite sprite-' + big_icon +' active" map_vehicle_id="' + ev['u'] + '" onclick=vehicle_info("' + ev['u'] + '",0)></div>';
        var html_ready = big_icon+"<b>" + bname + "</b> "+label_txt;

        MapIconDiv = L.divIcon({
            iconSize: [157, 43],
            iconAnchor: [0, 0],
            className: 'MapIconDiv ' + extra_c,
            html: html_ready
        });

        marker = L.marker([ev['y'], ev['x']], { icon: MapIconDiv, zIndexOffset: 100 }).addTo(myCollection);
        if (!ev['bn']) {
            ev['bn'] = '';
        }
        marker.bindTooltip(g + ev['s'] + trans_text_kmh + " <br/>" + ev['bn'] + sleep);
        if (ev['px']) {
            var dy = ev['y']-ev['py'];
            var dx = ev['x']-ev['px'];

            for (j=0;j<3;j++) {
                latlngs = [
                    [ev['py']+dy/3*j, ev['px']+dx/3*j],
                    [ev['py']+dy/3*(j+1), ev['px']+dx/3*(j+1)]
                ];
                L.polyline(latlngs, { color: sc, opacity: 0.6+0.2*j, weight:5+j }).addTo(myCollection);
            }
        }
    }
}   // update_bdata_mode2


function update_bdata_mode11(data) {
    var html, extra_class, mm, extra_side;
    $(".multi_bus").remove();
    for (var key in data) {
        html = "";

        for (var i = 0; i < data[key].length; i++) {
            mm = data[key][i];
            //console.log(mm);
            if (mm['id'] == BUS_ID) {
                // no info for current route
                continue;
            }

            // use only favor
            if ($.inArray(mm['id'], busfavor) > -1 || us_multi_all) {
                extra_class = "multi_bus";
                if (mm['r']) {
                    extra_class = extra_class + " micro_ramp";
                    if (!us_premium) { extra_class = extra_class + " blue"; }
                }
                if (mm['sleep']) {
                    extra_class = extra_class + " micro_sleep";
                    if (!us_premium) { extra_class = extra_class + " grey"; }
                }
                // if (mm['custom'] && us_premium) {
                //     extra_class = extra_class + " blink";
                // }
                if (us_multi_all && $.inArray(mm['id'], busfavor) > -1) {
                    extra_class = extra_class + " micro_favor";
                }
                // if (mm[1] in bus_design_map) {
                //     extra_class = extra_class + " image";
                // }
                // html = html + "<span class='multi_bus " + extra_class + "' onclick='vehicle_info(" + mm[4] + ",0)'>" + BID_BNAME[mm[0]];
                html = html + "<div class='" + extra_class + "' onclick='vehicle_info(" + '"' + mm['u'] +'"'+ ",0)'>";
                if (us_bigsticker && mm['g'] in bus_design_map) {
                    extra_side = bus_design_map[mm["g"]];
                    html = html + "<img src='" + extra_side + "'>";
                }
                if (mm['custom'] && us_premium) {
                    html = html + "<i class='fa fa-upload'></i> ";
                }
                html = html + get_bname([mm['id']]);
                // I am so smart!
                if (mm['g'] && (us_city != 3 || (us_premium && transaction_key == "premium") || gps_send_enough || us_show_gosnum)) {
                    html = html + "<span>" + gosnum_format(mm['g']) + "</span>";
                }
                html = html + "</div>";
                if (mm['u'] in globus) {
                    globus[mm['u']]['g'] = mm['g'];
                    globus[mm['u']]['s'] = mm['s'];
                    globus[mm['u']]['id'] = mm['id'];
                } else {
                    globus[mm['u']] = { 'g': mm['g'], 's': mm['s'], 'id': mm['id'] };
                }
                if (mm['sleep']) {
                    globus[mm['u']]['sleep'] = 1;
                }
            }
        }
        $("[bst_id=" + key + "]").next().find('.busstop_name').after(html);
        var z1 = $("[bst_id=" + key + "]").next().find(".multi_bus");
    }
    if ( $(".express_dial").hasClass('express_dial_fixed') ) {
        $(".multi_bus").css("display", 'none');
    }
}   // update_bdata_mode1

function iconizer(url, iconSize) {
    return new L.icon({
        iconUrl: url,
        iconSize: iconSize,
        iconAnchor: [iconSize[0] / 2, iconSize[1]],
        popupAnchor: [0, -iconSize[1]],
        shadowUrl: ''
    });
}

function lonlat2latlng(lonlat) {
    var latlng = [];
    for (var i in lonlat) {
      latlng.push([lonlat[i][1], lonlat[i][0]]);
    }
    return latlng;
}


function request_jam(city_id) {
     // download all the jamlines, lazy
    if (typeof JAM_LINES == 'undefined') {
        var script = document.createElement('script');
        script.src = '/static/js/jamline-'+city_id+'-'+us_city_rev+".js";
        script.type = 'text/javascript';
        script.onload = function () {
            request_jam(city_id);
        };
        document.getElementsByTagName('head')[0].appendChild(script);
        return;
    }
    var data = {
        'city_id': city_id,
        'bus_ids': JSON.stringify([BUS_ID])
    }

    $.ajax({
        type: "GET",
        url: "/ajax/jam/",
        data: data,
        dataType: 'json',
        success: function(result) {
            update_data_jam(result);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log(`bustime-main::request_jam(): ${textStatus} ${errorThrown}`);
        }
    });
}   // request_jam



function update_data_jam(data) {
    if (typeof map === 'undefined') {
        return;
    }

    if (typeof JAM_LINES == 'undefined' || $.isEmptyObject(JAM_LINES)) {
        return;
    }

    if (!jamcollection) {
        jamcollection = L.featureGroup().addTo(map);
    }
    else {
        jamcollection.clearLayers();
    }

    var ratio, icon_stop, latlng, x1, x2, y1, y2, color;
    var line_point = [];

    icon_stop = iconizer('/static/img/bs_26_0.png', [26, 34]);

    for (var i = 0; i < data.length; i++) {
        busstop_from = data[i].busstop_from;
        busstop_to = data[i].busstop_to;
        ratio = data[i].ratio;

        if (ratio === 0) {
            color = "#10e835";
        } else if (ratio === 1) {
            color = "#45e72e";
        } else if (ratio === 2) {
            color = "#83e526";
        } else if (ratio === 3) {
            color = "#c1e41e";
        } else if (ratio === 4) {
            color = "#ffe216";
        } else if (ratio === 5) {
            color = "#f2b41a";
        } else if (ratio === 6) {
            color = "#e4821e";
        } else if (ratio === 7) {
            color = "#d55123";
        } else if (ratio === 8) {
            color = "#c82327";
        } else if (ratio === 9) {
            color = "#a4090d";
        } else {color = "#a4090d";}

        line_point = JAM_LINES[busstop_from + "_" + busstop_to] || [];
        for (var k = 0; k < line_point.length; k++) {
             var yx = line_point[k][0];
             line_point[k][0] = line_point[k][1];
             line_point[k][1] = yx;
         }

        if(line_point.length > 0) {
            L.polyline(line_point, {color: color}).addTo(jamcollection);
        }
    }   // for (var i = 0; i < data.length; i++)
}   // update_data_jam



function map_draw_stops() {
    if (!routes_data) {return}
    var i, r, icon_stop, icon_stop0, icon_stop1, marker;
    busstop_collection.clearLayers();
    icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
    icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);
    for (i = 0; i < routes_data.length; i++) {
        r = routes_data[i]; // конкретный route для конкретного автобуса с bus_id
        var id_r = Object.keys(r); // id этого route

        /* route в DB имеет такой вид:
        "route": {
            "2499507": [1394, 1119, 0, 3],
            "2499508": [1394, 1124, 0, 4]
        }

        (расшифрока полей: "id": ["bus_id", "busstop_id", "direction", "order"])

        поэтому:
            id_r[0] = 2499507                  - это id route
            r[id_r[0]] = [1394, 1119, 0, 3]    - это сам route
            r[id_r[0]][2] = 0                  - это направление
        */
        if (r[id_r[0]][2] == 0) { // определяем направление
            icon_stop = icon_stop0;
        } else {
            icon_stop = icon_stop1;
        }

        var point_x = dbget('nbusstop', r[id_r[0]][1], 'point_x');
        var point_y = dbget('nbusstop', r[id_r[0]][1], 'point_y');
        var name_stop = dbget('nbusstop', r[id_r[0]][1], 'name');
        var slug_stop = dbget("nbusstop", [r[id_r[0]][1]], 'slug');

        marker = L.marker([point_y, point_x], { icon: icon_stop }).addTo(busstop_collection);
        if (us_edit_mode) {
            marker.bindPopup(' <a target="_blank" href="/'+us_city_slug+'/stop/id/'+ r[id_r[0]][1] +'/edit/"><i class="fa fa-pencil fa-fw"></i></a> <a target="_blank" href="/'+us_city_slug+'/stop/'+slug_stop+'"><i class="fa fa-external-link"></i></a>  ' + name_stop);
            marker.bindTooltip(name_stop);
        } else {
            if(test_mode){
                marker.bindPopup( '<a target="_blank" href="/'+us_city_slug+'/stop/'+ slug_stop +'"><i class="fa fa-external-link"></i></a> '+ name_stop + '<br>Lat: ' + point_y.toFixed(6) + ' Lon: ' + point_x.toFixed(6));
            }
            else {
                marker.bindPopup( '<a target="_blank" href="/'+us_city_slug+'/stop/'+ slug_stop +'"><i class="fa fa-external-link"></i></a> '+ name_stop);
            }
            marker.bindTooltip(name_stop);
        }
    }
    routes_data_current = BUS_ID;
    if (!map_is_centered) {
      map.fitBounds(busstop_collection.getBounds());
      map_is_centered = 1;
    }
    var request = $.ajax({
            url: "/ajax/route-line/",
            type: "get",
            data: {
                bus_id: BUS_ID
            },
            dataType: "json"
        });
    request.done(function(msg) {
        var d,color;
        for (d = 0; d < 2; d++) {
           if (msg[d]) {
              if (d === 0) {
                  color = "#74c0ec";
              } else {
                  color = "#5ec57c";
              }
              L.polyline(lonlat2latlng(msg[d]), {color: color}).addTo(busstop_collection);
           }
        }
    });
}

function update_passenger(data) {
    cats = data;
    for (var j in cats) {
        $("#" + j).next().find('.cats').remove();
        for (var i = 0; i < cats[j]; i++) {
            if (holiday_flag == "new year") {
              // gifs slow down some browsers
              $("#"+j).next().find('.busstop_name').after('<img class="cats" src="/static/img/elochka_2016.png"/>');
            } else if (holiday_flag == "valentine") {
              $("#"+j).next().find('.busstop_name').after('<img class="cats" src="/static/img/cat-female.png"/>');
            } else {
              $("#" + j).next().find('.b1').after('<i class="cats fa ' + CAT_SYM + '"></i>');
            }
        }
    }
}


function update_time_bst(data) {
    var type_num, busstp;
    //$(".time_prediction").removeClass('time_prediction').html('').removeAttr("time_prediction");
    for (var j in data) {
        //if (data[j]) {
            var time = ""
            // изменяем bdata_mode10 time_bst в формат для отображения на сайте
            if (data[j] == 0) {
                time = "";
            } else {
                var date_time = new Date(data[j] * 1000);
                //var hours = date_time.getHours();
                var hours = date_time.toLocaleString('en-US', { timeZone: 'Asia/Krasnoyarsk', hour: 'numeric', hour12: false });
                var minutes = date_time.getMinutes();
                time = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
            }
            $("#" + j).attr("time_prediction", time);
            if ( !$("#" + j).hasClass('vehicle_here') ) {
                $("#" + j).addClass('time_prediction').html(time);
                type_num = $(".bustable_head__bus").text();
                busstp = $("#" + j).next().find('.busstop_name').text();
                $("#" + j).next().find('.busstop_name').attr("aria-label", type_num + " приедет в " + time + " на остановку " + busstp);
                $("#" + j).attr("aria-label", type_num + " приедет в " + time + " на остановку " + busstp);

            }
            else {
                type_num = $(".bustable_head__bus").text();
                busstp = $("#" + j).next().find('.busstop_name').text();

                $("#" + j).find('.bcubic').find('img').attr("aria-label", type_num + " на остановке " + busstp);
            }
        //}
    }
}

function ajax_subs() {
    var request = $.ajax({
        url: "/ajax/bus/",
        type: "GET",
        data: {
            "bus_id": autoupdate
        },
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        router(msg);
    });
}

function get_bname(bus_id) {
    return dbget('bus', bus_id, 'name');
}

function get_bslug(bus_id) {
    return dbget('bus', bus_id, 'slug');
}

function get_provider_html(bus_id) {
    var html = "";
    var co_url = "<a href='/wiki/bustime/bus/" + bus_id + "/change/'>";
    if (dbget('bus', bus_id, 'price')) {
        html = '<i class="fa fa-ticket" aria-label="' + trans_text_price + '"></i> '+ dbget('bus', bus_id, 'price');
    }
    if (dbget('bus', bus_id, 'provider_id')) {
        var pid = dbget('bus', bus_id, 'provider_id')
        var name = dbget("busprovider", pid, 'name');
        if (html) {
            html = co_url+html+'</a>, ';
        }
        html = html + "<a href='/"+us_city_slug+"/company/" + pid + "/'>" + name + "</a>";
    } else {
        if (us_user) {
            html = html+co_url + trans_text_provider_edit + '</a>';
        } else {
            var link = "/wiki/bustime/bus/" + bus_id + "/change/";
            html = html+'<a href="/register/?next=' + link + '">' + trans_text_provider_edit + '</a>';
        }
    }
    return html;
}

function bus_icon_chooser(ttype) {
    var ttype_icon;
    if (ttype == "0") {
        ttype_icon = 'bus';
    } else if (ttype == "1") {
        ttype_icon = 'trolleybus';
    } else if (ttype == "2") {
        ttype_icon = 'tramway';
    } else if (ttype == "3") {
        ttype_icon = 'bus-taxi';
    } else if (ttype == "4") {
        ttype_icon = 'ferry';
    } else if (ttype == "5") {
        ttype_icon = '2bus';
    } else if (ttype == "6") {
        ttype_icon = 'train';
    } else if (ttype == "7") {
        ttype_icon = 'metro';
    }
    return ttype_icon;
}

function show_me_the_bus(bus_id) {
    if (us_sound && is_ios && audioinited === 0) {
        sound_init();
    }
    // osd_splash("bustime-splash.png");
    $('.busnumber').removeClass('bus_selected');
    $('.bid_' + bus_id).addClass('bus_selected');

    if (!dbget('bus', bus_id)) {
        alert('Please wait...');
        // show dynamic progress bar of DB load here
        return;
    }
    var ttype = dbget('bus', bus_id, 'ttype');
    var ttype_name, ttype_icon;
    ttype_name = trans_ttype_name[ttype];
    ttype_icon = "sprite-"+bus_icon_chooser(ttype);
    /*if (us_voice){
        BUS_VOICE_ANOUNCE=0;
        voice_queue_add(BUSES[bus_id]['slug'])
    }*/

    $(".bustable_head").css("display", "block");
    $(".bustable_head_multi_all").css("display", "block");
    $("#main_bases_map").show();
    $(".chat_bus_button").attr("href", "/" + us_city_slug + "/chat/" + dbget('bus', bus_id, 'slug') + "/");

    $('.bustable_head__icon')
        .removeClass()
        .addClass("bustable_head__icon sprite active")
        .addClass(ttype_icon)
        .attr("href",  "/help/" + trans_ttype_slug[dbget('bus', bus_id, 'ttype')] + "/");

    $('.bustable_head__bus').html( ttype_name+" "+get_bname(bus_id) );
    $('.bustable_head__provider').html( get_provider_html(bus_id) );

    var amnts = $('.bid_' + bus_id + ":first > .busamount").html();
    var b_amnts = amnts.split(" / ");
    var b_amnt0 = parseInt(b_amnts[0], 10);
    var b_amnt1 = parseInt(b_amnts[1], 10);
    $('.bustable_head__busamount').removeClass().addClass('bustable_head__busamount busamount busamount_' + bus_id).html(amnts).attr('aria-label', 'Машин на маршруте '+ (b_amnt0 + b_amnt1));

    $(".ui.grid.bustable").css('display', 'inline');
    $(".welcome-text").css('display', 'none');
    var busfavor_url = "/ajax/busfavor/?bus_id=" + bus_id;
    if (socket) {
        if (BUS_ID) {
            socket.emit('leave', "ru.bustime.bus_mode10__" + BUS_ID);
            socket.emit('leave', "ru.bustime.bus_mode11__" + BUS_ID);
        }
    } else {
        autoupdate = bus_id;
        autoupdate_force = 1;
    }

    BUS_ID = bus_id;
    sub_bus_id();

    if( BUS_ID && gtfs_alerts_buses.indexOf(parseInt(BUS_ID)) >= 0 )
        $('#gtfs_alerts_bus_button').css("display", "inline-block");
    else
        $('#gtfs_alerts_bus_button').css("display", "none");

    $.ajax({
        url: busfavor_url,
        type: "GET"
    });
    map_is_centered = 0;
    $(".reschedule_0_1, .reschedule_1_1").html("");
    $(".schedule_bar_cur > a").attr("href", "/" + us_city_slug + "/" + dbget('bus', bus_id, 'slug') + "/");
    $('html, body').scrollTop($('#separ').offset().top);
    $(".edit_panel_route").removeClass("hidden");
    if ($('.map').css("display") !== "none") {
        request_jam(us_city);
    }

    // достаем все route для этого автобуса из DB
    // в bdata_mode10 не приходит событие routes, поэтому достаем нужные данные из дампа
    var route_for_bus_id = Object.entries(DB.route)
        .filter(([key, value]) => value && value[0] === parseInt(BUS_ID))
        .map(([key, value]) => ({ [key]: value }));
    route_for_bus_id.sort((a, b) => Object.values(a)[0][3] - Object.values(b)[0][3]);

    var i, r, t, sname, middle_num, middle_num0 = 0,
        middle_num1 = 0;

    for (i = 0; i < route_for_bus_id.length; i++) {
        var route = route_for_bus_id[i];
        var id_route = Object.keys(route);

        if (route[id_route[0]][2] === 0) { middle_num0++ }
        if (route[id_route[0]][2] === 1) { middle_num1++ }
    }

    middle_num0 = middle_num0 / 2;
    middle_num1 = middle_num1 / 2;

    if (middle_num0 <= middle_num1) {
        middle_num = middle_num0;
    } else {
        middle_num = middle_num1;
    }
    if (us_premium) {
        middle_num = 999;
    }
    middle_num0 = middle_num;
    middle_num1 = middle_num;

    var ha1 = "";
    var ha2 = "";
    var hb1 = "";
    var hb2 = "";
    var edit_mode = "";

    for (i = 0; i < route_for_bus_id.length; i++) {
        r = route_for_bus_id[i]; // конкретный route для конкретного автобуса с bus_id
        var id_r = Object.keys(r); // id этого route
        /* route имеет такой вид:
        "route": {
            "739936": [11151, 115212, 1, 0],
            "739937": [11151, 115213, 1, 1]
        }

        (расшифрока полей: "id": ["bus_id", "busstop_id", "direction", "order"])

        поэтому достаем id таким образом: Object.keys(r);
        получается:
            r = "739936": [11151, 115212, 1, 0] - сам route
            id_r = 739936                       - его id
        */

        t = "";
        sname = dbget('nbusstop', r[id_r[0]][1], 'name');

        if (sname.length > 32) {
            sname = sname.substring(0, 32) + "...";
        }
        if (us_edit_mode) {
            edit_mode = ' <a target="_blank" href="/'+us_city_slug+'/stop/id/'+ r[id_r[0]][1] +'/edit/"><i class="fa fa-pencil fa-fw"></i></a>';
        }
        t = t + '<div class="indicator ';
        if (us_bigsticker) {
          t = t + "premium";
        }
        t = t + '" id="' + id_r[0] +
            '" bst_id="' + r[id_r[0]][1] + '"></div><div class="inf"><div class="busstop_name">'+ edit_mode + sname +'<div class="b1"></div></div></div><br/>';
            // <a href="/'+us_city_slug+'/stop/?id='+r['bst']+'"><i class="fa fa-info fa-fw"></i></a>'

        if (r[id_r[0]][2] === 0) {
            if (middle_num0 <= 0) {
                ha2 = ha2 + t;
            } else {
                ha1 = ha1 + t;
            }
            middle_num0--;
        } else {
            if (middle_num1 <= 0) {
                hb2 = hb2 + t;
            } else {
                hb1 = hb1 + t;
            }
            middle_num1--;
        }
    }
    $('.htmlr.a1').html(ha1);
    $('.htmlr.a2').html(ha2);
    $('.htmlr.b1').html(hb1);
    $('.htmlr.b2').html(hb2);

    $('.busstop_name').click(busstop_click);
    $('.busstop_name').mouseup(busstop_click_up_down).mousedown(busstop_click_up_down);


    set_current_nbusstop(current_nbusstop);

    routes_data = route_for_bus_id;
    if (map) { map_draw_stops(); }
} // show_me_the_bus


function tcard_check() {
    tcard = $('#id_tcard').val();
    if (tcard.length < 10) {
        alert('Неправильный формат. Введите не менее 10 символов.');
    }
    $('.tcard_balance').html("");
    var request = $.ajax({
        url: "/ajax/card/" + tcard + "/",
        type: "GET",
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        if (msg['social']) {
            $('.tcard_balance').html(msg['balance'] + " шт. " + msg['social'] + " доп.");
        } else {
            $('.tcard_balance').html(msg['balance'] + ' <i class="fa fa-rub"></i>');
        }
    });
}

function sub_bus_id() {
    if (socket) {
        socket.emit('join', "ru.bustime.bus_mode10__" + BUS_ID);
        socket.emit('join', "ru.bustime.bus_mode11__" + BUS_ID);
        socket.emit('rpc_bdata', {"bus_id":BUS_ID, "mode":10, "mobile":0}, function (data) {
          router(data);
          socket.emit('rpc_bdata', {"bus_id":BUS_ID, "mode":11, "mobile":0}, function (data) {
              router(data);
          });
        });
    }
}

function ajax_metric(metric, value) {
    $.ajax({
        url: "/ajax/metric/",
        data: {
            "metric": metric,
            "value": value
        },
        type: "GET",
        dataType: "json",
        cache: false
    });
}


function upload_photo(file) {
    var form = new FormData(),
        xhr = new XMLHttpRequest();
    form.append('image', file);
    xhr.open('post', '/ajax/photo/', true);
    xhr.send(form);
}

$(".take_photo").change(function() {
    var file = $(".take_photo").prop('files')[0];
    upload_photo(file);
    // http://www.shauninman.com/archive/2007/09/10/styling_file_inputs_with_css_and_the_dom
});

function ajax_gvote(positive) {
    if (positive) {
        $("i.fa-thumbs-down").removeClass("fa-thumbs-down").addClass("fa-thumbs-o-down");
        $("i.fa-thumbs-o-up").removeClass("fa-thumbs-o-up").addClass("fa-thumbs-up");
        $(".gvote_comment").css('display', 'none');
    } else {
        $("i.fa-thumbs-o-down").removeClass("fa-thumbs-o-down").addClass("fa-thumbs-down");
        $("i.fa-thumbs-up").removeClass("fa-thumbs-up").addClass("fa-thumbs-o-up");
        $(".gvote_comment").css('display', 'block');
    }
    request = $.ajax({
        url: "/ajax/gvote/",
        data: {
            "positive": positive
        },
        type: "GET",
        dataType: "json",
        cache: false
    });
    request.done(function(msg) {
        $(".gvote_down_cnt").html(msg[0]);
        $(".gvote_up_cnt").html(msg[1]);
    });
}

function update_gvotes(event) {
    var down = parseInt($(".gvote_down_cnt").html(), 10);
    var up = parseInt($(".gvote_up_cnt").html(), 10);

    if (down != event['down']) {
        $(".gvote_down_cnt").html(event['down']);
        $(".ui.label.gvote_down_cnt").css('background-color', "#ffba16");
    }
    if (up != event['up']) {
        $(".gvote_up_cnt").html(event['up']);
        $(".ui.label.gvote_up_cnt").css('background-color', "#ffba16");
    }

    setTimeout(function() {
        $(".ui.label.gvote_down_cnt").css("background-color", "")
        $(".ui.label.gvote_up_cnt").css("background-color", "")
    }, 400);
}

function check_wise(txt) {
    var check = true;

    txt = txt.replace(/ /g, '');
    if (txt.length < 5) {
        check = false;
    }

    return check;
}

function ajax_gvote_comment() {
    var comment = $("textarea").val();
    var check_result = check_wise(comment);
    if (!check_result) {
        alert("Напишите сообщение чтобы мы могли улучшить сайт");
        return;
    }

    request = $.ajax({
        url: "/ajax/gvote/comment/",
        data: {
            "comment": comment
        },
        type: "POST",
        cache: false
    });
    request.done(function() {
        $(".gvote_comment").css('display', 'none');
        $(".gvote_comment").after("<br/><center>Спасибо!</center>");
    });
}   // ajax_gvote_comment


function settings_set_silent(setting, value) {
    var request = $.ajax({
        url: "/ajax/settings/",
        data: {
            "setting": setting,
            "value": value
        },
        type: "GET",
        cache: false
    });
}

function update_city_rhythm(msg) {
    $(".osd_city_rhythm").html(msg);
}

function stop_ids(ids) {
    // ajax_metric("stop_ids", 1);
    var i, stop_ids_str, idx;
    if (socket) {
        while (STOP_IDS_SUBS.length) {
            idx = STOP_IDS_SUBS.pop()
            socket.emit('leave', idx);
        }
        STOP_IDS = ids;
        for (i = 0; i < STOP_IDS.length; i++) {
            stop_ids_str = "ru.bustime.stop_id__" + STOP_IDS[i];
            socket.emit('join', stop_ids_str);
            STOP_IDS_SUBS.push(stop_ids_str)
        }
        ajax_stop_ids();
    } else {
        STOP_IDS = ids;
        ajax_stop_ids();
    }
}


function flash_dance() {
    var els = $(".sr_busnum").toArray(),
        i;
    for (i = 0; i < els.length; i++) {
        if (dance_move % 2 == i % 2) {
            $(els[i]).addClass("lightup");
        } else {
            $(els[i]).removeClass("lightup");
        }
    }
    dance_move++;
    if (dance_move < 0) {
        dance_move = 1;
        $(".sr_busnum").removeClass("lightup");
        return;
    }
    setTimeout(function() {
        flash_dance();
    }, 1000);
}

// XXX
// function highlight_dance() {
//     $(".busnumber").removeClass('lightup_fallback');
//     var els = $(".busnumber").toArray();
//     var target = els.length;
//     target = Math.floor(Math.random() * els.length);
//     console.log(target);
//     $(els[target]).addClass('lightup_fallback');

//     setTimeout(function() {
//         highlight_dance();
//     }, 500);
// }


function ajax_stop_ids() {
    // console.log(STOP_IDS);
    socket.emit('rpc_stop_ids', {"ids":STOP_IDS, "mobile":0}, function (data) {
      router(data);
    });
}


function matrix_inverto() {
    if(test_mode){
        console.log('matrix_inverto');
    }
    var cur = $(".matrix").css('display');
    if (cur == "none") {
        $(".matrix").css('display', 'block');
        $("#show_matrix_button").html('Скрыть');
        settings_set_silent("matrix_show", true);
        change_mode(mode_selected);
        // $("[class^='item modec_']").removeClass('disabled');
    } else if (cur == "block") {
        $(".matrix").css('display', 'none');
        $("#show_matrix_button").html('Показать');
        settings_set_silent("matrix_show", false);
        $(".modec_" + mode_selected).removeClass('active');
        $(".pointing > .item .sprite").removeClass('active');
        // $("[class^='item modec_']").addClass('disabled');
    }
}


function indicator_click() {
    vehicle_info( $(this).parent().parent().attr('vehicle_id'), 0 );
}


function obj_get_bid(obj) {
    var classes = $(obj).attr("class").split(/\s+/);
    for (var i = 0; i < classes.length; i++) {
        if (classes[i].startsWith("bid_")) {
            return classes[i].substring(4);
        }
    }
}


var page_ready = function() {
    var d = new Date();
    window.console && console.log(d + `: Page ready, test_mode=${test_mode}`);
    //websconnect(); // todo, may be it is used on city status, check later
    if (typeof(js_page_extra) === 'function') {
      js_page_extra();
    }

    var cp = Cookies.get('cookie_policy');
    if (cp === undefined) {
        $(".cookie_policy").removeClass("hidden");
    }
    $('[name="select_language"]').change(function() {
        var name  = $(this).prop("name");
        var value = $(this).prop("value");
        var path = window.location.pathname
        var currentUrl = window.location.href;
        var languageRegex = /\/\/(\w+)\./;
        var newUrl = currentUrl.replace(languageRegex, '//' + value + '.');
        window.location.href = newUrl;
    });

}   // page_ready


var document_ready = function() {
    // console.log("Сначала они тебя не замечают, потом смеются над тобой, затем борются с тобой. А потом ты побеждаешь.");
    $('.ui.dropdown').dropdown();
    $('.popup_element').popup();

    if (!is_main_page) {
        return page_ready();
    }

    if (window.screen.width > us_city_transport_count * 100) {
        for(var i=0;i<10; i++) {
            // возвращает размер шрифта в норму если экран широкий
            let t = $(".modec_"+i);
            if(t){
                t.removeClass("xsfont");
            }
        }
    }

    var startTime = Date.now(); // время начала ожидания дампа
    var check_BUSES = setInterval(function() {
        if (Object.keys(dbgetsafe('bus')).length !== 0) { // если DB['bus'] заполнен или время ожидания вышло
        //if (Object.keys(DB['bus']).length !== 0 || (Date.now() - startTime) > 5000) { // если BUSES заполнен или время ожидания вышло
            clearInterval(check_BUSES); // цикл останавливается, если BUSES заполнен или истекло время ожидания
            if (Object.keys(dbgetsafe('bus')).length !== 0) {
                // for (var key in BUSES) {
                //     BNAME_BID[BUSES[key]['name']] = key;
                // }

                // заменяет ссылки на интерактивные хэш, #bus-1
                var busnumbers  = $(".busnumber");
                var bus_id_, classList, classArr;

                for (var q = 0; q < busnumbers.length; q++) {
                    classList = $(busnumbers[q]).attr("class");
                    classArr = classList.split(/\s+/);
                    $.each(classArr, function(index, value) {
                      if (value.startsWith("bid_")) {
                        bus_id_ = value.split(/_/)[1];
                        if (bus_id_ in dbget('bus')) {
                             $(busnumbers[q]).attr('href', "#"+dbget('bus', bus_id_, 'slug')).removeClass("bw");;
                        } else {
                            console.log("No bus key "+bus_id_+" in DB!");
                        }
                      }
                    });
                }   // for
            }// if (DB['bus'])
        } // if (DB['bus'] || (Date.now() - startTime) > 1000)
    }, 100);

    if (us_sound) {
        sound_init();
    }

    $(".busnumber").click(function() {
        var bid = obj_get_bid($(this));
        show_me_the_bus(bid);
    });

    var d = new Date();
    window.console && console.log(d + `: Document ready, test_mode=${test_mode}`);

    websconnect();

    if (typeof(js_page_extra) === 'function') {
      js_page_extra();
    }

    if (us_device != "opera_mini") {
        // инициализация контролов выбора остановок (from-to.html)
        setTimeout(function() {
            if (typeof(fromToInit) == 'function') {
                fromToInit();
            }    
        }, 1000);

        if (us_speed_show || us_gps_send) {
            start_location_service();
        } else if (navigator && navigator.permissions && us_gps_off === 0) {
            navigator.permissions.query({name:'geolocation'})
                .then(function(permissionStatus) {
                var hasPermission = permissionStatus.state;
                if (hasPermission == "granted") {
                    start_location_service();
                }
                permissionStatus.onchange = function() {
                    console.log('geolocation permission state has changed to ', this.state);
                };
            });
        }

        $('input.deletable').wrap('<span class="deleteicon" />').after($('<span/>').click(function() {
            $(this).prev('input').val('').focus();
        }));
    }

    if (typeof(load_extra) == 'function') {
        load_extra();   // in _js_init.html
    }
    ticktack(); // периодический запрос данных AJAX, если не работает websocket

    if (us_gps_send) {
        var currentTime = new Date();
        var currentSeconds = currentTime.getSeconds();
        setTimeout(function() {
            osdclock();
        }, 60000-currentSeconds*1000);
    }

    $('.fa-heart').hover(function() {
        $(this).css('color', '#fff');
    }, function() {
        $(this).css('color', '');
    });

    $('.fa-heart').click(function(e) {
        e.stopPropagation();
        // isn'it can be easier?
        // var bus_id = $(this).parent().parent().parent().parent().parent().attr("bus_id");
        // yes, it can
        var busnumber = $(this).parentsUntil(".busnumber").parent();
        var bus_id = obj_get_bid(busnumber);
        busnumber.remove();
        $.ajax({
            url: "/ajax/busdefavor/",
            type: "GET",
            data: {
                "bus_id": bus_id
            }
        });
    });

    if (!isiPad && !isAndroid) {
        $(document).tooltip();
    }

    $(".show_map_button").click(function() {
        show_map(0);    // параметр влияет только на запрос настроек при показе карты (вызов settings_set_silent())
        if ($('.map').css("display") !== "none") {
            request_jam(us_city);
        }
    });
    if (us_map_show) {
        show_map(1);
    }

    $(".show_matrix_button").click(function() {
        matrix_inverto();
    });

    // android 2.3 check
    if (radar_mode) {
        radar_init();
        if (navigator.geolocation) {
            options = {
                enableHighAccuracy: false,
                maximumAge: 0
            };
            navigator.geolocation.getCurrentPosition(radar_position, noPosition, options);
            navigator.geolocation.watchPosition(radar_watch, noPosition);
        }
    }
    express_dial_init();
    rating_init();

    // $(".htmlr").on("click", ".indicator", indicator_click);
    // $(".htmlr").on("click", ".busstop_name", busstop_click);

    // for some reasone this speed things up
    setTimeout(function() {
        low_bootstrap();
    }, 500);

    if (us_premium) {
        $("[name=gosnum]").keypress(function(e) {
            if (e.keyCode === 13) {
                vehicle_info_gosnum();
            }
        });
    }

    // taxi
    if (us_sound) {
      audiocontext_enable();
    }

    $('[name="multi_all"]').change(function() {
      var name  = $(this).prop("name");
      var checked = $(this).prop("checked");
      $.ajax({
        url: "/ajax/ajax_settings1/",
        type: "GET",
        data: {
          name: name, checked: checked, csrfmiddlewaretoken: '{{csrf_token}}'
        }
        }).done(function(data) {
          window.location.reload(true);
      });
    });

    $('[name="select_language"]').change(function() {
        var name  = $(this).prop("name");
        var value = $(this).prop("value");
        var path = window.location.pathname
        var currentUrl = window.location.href;
        var languageRegex = /\/\/(\w+)\./;
        var newUrl = currentUrl.replace(languageRegex, '//' + value + '.');
        window.location.href = newUrl;
    });

    $(document).click(function(e){
        var $target = $(e.target);
        if ( !$target.is('.fa-question-circle-o') && !$target.parents('.fa-question-circle-o').length) {
            $('.popup_descr_index').removeClass("show_descr_index");
        }
    });

};  // document_ready = function()

function descripton_settings_index(id_elem) {
    $('.' + id_elem).toggleClass("show_descr_index");
}

function rpcBdata(bus_id, mode) {
    // see rpc_bdata in rpc_server.py
    socket.emit('rpc_bdata', {"bus_id":bus_id, "mode":mode, "mobile":0}, function (data) {
      router(data);
    });
}

function getRotationDegrees(obj) {
    var matrix = obj.css("-webkit-transform") ||
    obj.css("-moz-transform")    ||
    obj.css("-ms-transform")     ||
    obj.css("-o-transform")      ||
    obj.css("transform");
    if(matrix !== 'none') {
        var values = matrix.split('(')[1].split(')')[0].split(',');
        var a = values[0];
        var b = values[1];
        var angle = Math.round(Math.atan2(b, a) * (180/Math.PI));
    } else { var angle = 0; }
    return (angle < 0) ? angle + 360 : angle;
}
var radio_deg =0;
function radio_gplay() {
    if (radio_status === 0) {
        // $('.ui.sidebar').sidebar('toggle');
        document.getElementById('groove').play();
        $(".bustime-logo-pro").removeClass('bustime-logo-pro').addClass('bustime-logo');
        $(".bustime-logo").css('transform', '').addClass('logorot');
        $(".fa-music").removeClass('fa-music').addClass('fa-pause');
        radio_status = 1;
        ajax_metric("radio_play", 1);

        CAT_SYM_OLD = CAT_SYM;
        CAT_SYM = 'fa-volume-up';
        $(".cats").removeClass(CAT_SYM_OLD).addClass(CAT_SYM);
    } else {
        document.getElementById('groove').pause();
        radio_deg = getRotationDegrees( $(".bustime-logo") );
        $(".bustime-logo").removeClass("logorot").css('transform', 'rotate('+radio_deg+'deg)');
        $(".fa-pause").removeClass('fa-pause').addClass('fa-music');
        radio_status = 0;
        $(".cats").removeClass(CAT_SYM).addClass(CAT_SYM_OLD);
        CAT_SYM = CAT_SYM_OLD;
    }
}

/*
function sseek() {
    var radio_curtime = $("#scwidget").attr("skip_seconds");
    radio_curtime = parseInt(radio_curtime, 10);
    if (radio_curtime === 0) {
        return;
    }

    if (isAndroid) {
        radio_curtime = 45 * 1000;
    } else {
        radio_curtime = radio_curtime * 1000;
    }
    swidget.seekTo(radio_curtime);
}
function radio_onpogress(e) {
    if (e.loadedProgress && e.loadedProgress > 50000 / 3600000) {
        sseek();
        swidget.unbind(SC.Widget.Events.PLAY_PROGRESS);
    }
}
function radio_ready() {
    if (us_device == "ios" || us_device == "android") {
        alert("Запустите музыку в открывшемся проигрывателе");
    }
    // flash_dance();
}

function radio_onplay() {
    $(".bustime-logo-pro").removeClass('bustime-logo-pro').addClass('bustime-logo');
    $(".bustime-logo").addClass("logorot");
    $(".fa-music").removeClass('fa-music').addClass('fa-pause');
    // $(".music_ctrl").html("Музыка ВКЛ");
    radio_status = 2;
}

function radio_onpause() {
    $(".bustime-logo").removeClass("logorot");
    $(".fa-pause").removeClass('fa-pause').addClass('fa-music');
    // $(".music_ctrl").html("Музыка ВЫКЛ");
    radio_status = 1;
    dance_move = -10;
}


function radio_play() {
    // $(".radio_play").hide();
    $('.ui.sidebar').sidebar('toggle');

    if (radio_status === 0) {
        CAT_IMG_OLD = CAT_IMG;
        CAT_IMG = '/static/img/cat-male-dancing.gif';
        $(".cats").attr("src", CAT_IMG);
        // highlight_dance();
        $('#scwidget').css('display', 'block').css('width', '100%').css('height', '100%');
        $('#scwidget').attr('src', $('#scwidget').attr('srcc'));
        ajax_metric("radio_play", 1);
        swidget = SC.Widget(document.getElementById('scwidget'));

        swidget.bind(SC.Widget.Events.READY, radio_ready);
        swidget.bind(SC.Widget.Events.PLAY_PROGRESS, radio_onpogress);
        swidget.bind(SC.Widget.Events.PAUSE, radio_onpause);
        swidget.bind(SC.Widget.Events.PLAY, radio_onplay);
        radio_status = 1;
    } else if (radio_status == 1) {
        swidget.play();
        radio_status = 2;
    } else if (radio_status == 2 || radio_status == 3) { // 2=play_and _seek
        swidget.pause();
        radio_status = 1;
        CAT_IMG = CAT_IMG_OLD;
        $(".cats").attr("src", CAT_IMG);
    }
} */
function vehicle_info(vehicle_id, force) {
    scroll = document.documentElement.scrollTop || document.body.scrollTop;
    var side_img, r, s, h, dir, gosnum_union, driver_ava, driver_name;
    if (current_vehicle_info) {
        $(".vehicle_selected").removeClass('vehicle_selected');
    }
    if (current_vehicle_info == vehicle_id && force === 0) {
        vehicle_info_close();
        return;
    }
    $(".vehicle_journal").attr("href", "/"+us_city_slug+"/transport/"+today_date+"/"+vehicle_id+"/");

    $(".vehicle_here[vehicle_id=" + vehicle_id + "]").addClass('vehicle_selected');
    current_vehicle_info = vehicle_id;
    var vehicle = globus[vehicle_id];
    if (!vehicle) {return} //wtf?
    var vehicle_bus = dbget('bus', vehicle['id'], null, true);
    var vehicle_ttype = vehicle_bus['ttype'];
    // console.log(vehicle_bus);
    // console.log(vehicle_ttype);
    // change images depend on type
    if (vehicle_ttype == 1) {
        $(".driver_ava").attr('src', "/static/img/stop_n_trolleybus.png");
    } else if (vehicle_ttype == 2) {
        $(".driver_ava").attr('src', "/static/img/stop_n_tramway.png");
    } else {
        $(".driver_ava").attr('src', "/static/img/stop_n_bus.png");
    }
    $(".vehicle_info_gosnum").css('display', 'inline');
    // $(".vehicle_info_gosnum").find(".label").html( get_bname(vehicle['id']) );
    $(".vehicle_feedback_ts").attr("href", "/"+us_city_slug+"/feedback/"+vehicle_id+"/");
    $(".express_fixed").css('display', 'none');

    if (vehicle["g"]) {
        if ( $("[name=gosnum]:focus").length === 0 ) {
            // make sure nobody edit this right now
            $("[name=gosnum]").val(vehicle['g']);
        }
    } else {
        if ( $("[name=gosnum]:focus").length === 0 ) {
          $("[name=gosnum]").val("");
        }
    }

    if (vehicle['custom'] && us_premium) {
        var request = $.ajax({
            url: "/ajax/peer_get/",
            type: "post",
            data: {
                us_id: vehicle['custom_src']
            },
            dataType: "json",
            cache: false
        });

        request.done(function(msg) {
            if ( msg['peer_id'] ) {
              $(".call_button").removeClass("hiddeni");
            }
        });
    } else {
        $(".call_button").addClass("hiddeni");
    }

    // side_img = side_compo(vehicle_ttype, vehicle['r'], vehicle['g'], vehicle['s'], vehicle['custom']);
    // vehicle_old = globus_old[ vehicle['u'] ];
    // var gosnum_visi = "";
    // if ( vehicle['g'] ) {
    //     gosnum_visi = "<div>" + gosnum_format(vehicle['g']) + "</div>";
    // }
    // $(".vehicle_info_img").addClass("vehicle_here").css('background', side_img).html(gosnum_visi);
    var hcol = sidebo(vehicle);
    $(".vehicle_info_img").html(hcol);


    $(".vehicle_info_name").html(trans_ttype_name[vehicle_ttype]+" "+get_bname(vehicle['id']));
    $(".vehicle_info_speed").html(vehicle['s']);
    h = vehicle['h'];
    if (h >= 337.5 || h < 22.5) {
        dir = "N";
    } else if (h >= 22.5 && h < 67.5) {
        dir = "NE";
    } else if (h >= 67.5 && h < 112.5) {
        dir = "E";
    } else if (h >= 112.5 && h < 157.5) {
        dir = "SE";
    } else if (h >= 157.5 && h < 202.5) {
        dir = "S";
    } else if (h >= 202.5 && h < 247.5) {
        dir = "SW";
    } else if (h >= 247.5 && h < 292.5) {
        dir = "W";
    } else if (h >= 292.5 && h < 337.5) {
        dir = "NW";
    }
    $(".vehicle_info_heading_w").html(dir);
    // console.log(h);
    h = h - 45; // it is 45 by default, so correct it
    $(".vehicle_info_heading").css('transform', 'rotate(' + h + 'deg)');

    $('.vehicle_info_speed').css('color', 'red');
    $('.vehicle_info_heading').css('color', 'red');
    $('.vehicle_info_heading_w').css('color', 'red');
    setTimeout(function() {
        $('.vehicle_info_speed').css('color', '');
        $('.vehicle_info_heading').css('color', '');
        $('.vehicle_info_heading_w').css('color', '');
    }, 400);
    if (force != 1) {
        if (!vehicle['g']) {
            $(".vote_comment").val("Оценка невозможна пока нет номера");
        } else {
            socket.emit("rpc_rating_get", {"bus_id":vehicle['id'], "g":vehicle['g']}, function (data) {
                rating_fill(data["rpc_rating_get"], 1);
            });
        }
    }
    if (us_premium) {
        $("input[name=gosnum]").focus();
    }

    // } else {
    //     $(".vote_comment").focus();
    // }
}

function sidebo(vehicle) {
    var hcol="";
    var sticker="";
    if (vehicle['g'] in bus_design_map) {
        sticker = bus_design_map[vehicle['g']];
    }

    // big sticker if settings say so
    if (us_bigsticker) {
        hcol = hcol+'<div class="bcubic">';

        if (sticker) {
          hcol = hcol+'<img class="sticker" aria-label="Стикер ТС" src="' + sticker + '">';
        }

        hcol = hcol+'</div>';
    }

    // central icon
    var tface = bus_icon_chooser(dbget('bus', BUS_ID, 'ttype'));

    if (vehicle['tface']) {
        tface = vehicle['tface'];
    }

    if (vehicle['tcolor']) {
      hcol = hcol+'<div class="bcubic"><img src="/static/img/theme/' + THEME +'/'+tface+'_'+vehicle['tcolor']+'.png"></div>';
    } else {
      hcol = hcol+'<div class="bcubic"><img src="/static/img/theme/' + THEME +'/'+tface+'.svg"></div>';
    }

    // 1
    hcol = hcol+"<div class='bcubic'>";
    if (sticker && !us_bigsticker) {
        hcol = hcol+"<div class='cubic active' aria-label='Стикер ТС'><img src='"+sticker+"'></div>";
    } else {
        hcol = hcol+"<div class='cubic '></div>";
    }
    // 2
    if (vehicle['custom']) {
        hcol = hcol+"<div class='cubic active' aria-label='ТС отправляет координаты'><i class='fa-upload fa'></i></div>";
    } else {
        hcol = hcol+"<div class='cubic '></div>";
    }
    hcol = hcol+"<br/>";

    // 3
    if (vehicle['r']) {
        hcol = hcol+"<div class='cubic active' aria-label='ТС оборудовано аппарелью'><i class='fa-wheelchair-alt fa'></i></div>";
    } else if (vehicle['rr']) {
        hcol = hcol+"<div class='cubic active' aria-label='Низкопольное ТС'><i class='fa-shopping-cart fa'></i></div>";
    } else {
        hcol = hcol+"<div class='cubic'></div>";
    }
    // 4
    hcol = hcol+"<div class='cubic'></div>";
    hcol = hcol+"</div>";


    if (vehicle['g'] && us_show_gosnum) {
        hcol = hcol + "<div class='gosnum'>" + gosnum_format(vehicle['g']);
        if(vehicle['l']) {
            hcol = hcol + ", " + gosnum_format(vehicle['l']);
        }
        hcol = hcol + "</div>";
    } else if (vehicle['l'] && us_show_gosnum) {
        hcol = hcol + "<div class='gosnum'>" + gosnum_format(vehicle['l']);
    }

    return hcol;
}

function vehicle_info_close() {
    $(".vehicle_info").css('display', 'none');
    $(".vehicle_info_gosnum").css('display', 'none');
    $(".express_fixed").css('display', '');
    rate = 0;
    $("[name=msg]").val("");
    $("[name=gosnum]").val("");
    $(".vehicle_selected").removeClass('vehicle_selected');
    // $(".gps_my").addClass('hiddeni');
    current_vehicle_info = "";

    // works on android
    // if (isAndroid) {
    //   document.documentElement.scrollTop = document.body.scrollTop = scroll;
    // } else

    // http://stackoverflow.com/questions/29001977/safari-in-ios8-is-scrolling-screen-when-fixed-elements-get-focus
    if (is_ios) {
        $('html, body').delay(400).animate({
            scrollTop: $('#separ').offset().top
        }, 400, 'linear');
    }


}


function busstop_click(event) {
    var r_id = $(this).parent().prev().attr('id');
    r_id = parseInt(r_id, 10);

    mycat = r_id;
    socket.emit("rpc_passenger", {"what":1, "bus_id":BUS_ID, "r_id":mycat}, function (data) {
      // nothing to do
    });

    if( $("#id_stops2") ){
        busstop_click_cnt++;
        if (busstop_click_cnt%2==1) {
          $('body').toast({title: event.target.innerText, message: trans_text_dst_change});
          $("#id_stops2").val(event.target.innerText);
        } else {
          $('body').toast({title: event.target.innerText, message: trans_text_src_change});
          $("#id_stops").val(event.target.innerText);
        }
        if ($("#id_stops").val() && $("#id_stops2").val()) {
            request_bus_trip(us_city);  // in from-to3.html
        }
    }

    ajax_metric("catplace", 1);
}   // busstop_click

function busstop_click_up_down(ev) {
    var dir, r_id = $(this).parent().prev().attr('id');
    r_id = parseInt(r_id, 10);
    if (ev.type=="mousedown") {
        dir=1
    } else {
        dir=0;
    }

//    if (mycat && mycat == r_id) {
//        socket.emit("rpc_passenger_horn", {"what":dir, "bus_id":BUS_ID, "r_id":mycat});
//    }
}

function push_to_talk_click_up_down(ev) {
    var dir;
    if (ev.type=="mousedown" || ev.type=="touchstart") {
        sound_radio_out.play();
        dir=1;
        recorder = new Recorder({encoderPath:'/static/js/encoderWorker.min.js', encoderBitRate:16000}); //, encoderSampleRate:24000
        recorder.ondataavailable = function( typedArray ){
            var dataBlob = new Blob( [typedArray], { type: 'audio/ogg' } );
            // console.log(dataBlob);
            $.ajax({
                type: 'POST',
                url: '/radio/say/',
                data: dataBlob,
                processData: false,
                contentType: false
            }).done(function(data) {
                console.log(data);
            });
        }
        recorder.start();
        // navigator.getUserMedia({audio: true},  function(stream) {
        //     var input = audio_context.createMediaStreamSource(stream);
        //     recorder = new Recorder(input);
        //     recorder.record();
        //     ptt_stream = stream;
        // }, function(e) {
        //   console.log('No live audio input: ' + e);
        // });
    } else {
        dir=0;
        recorder.stop();
        sound_radio_out.play();
        // var track = ptt_stream.getTracks()[0];  // if only one media track
        // track.stop();
        // recorder.exportWAV(function(blob) {
        //     console.log(blob);
        // });
        // recorder.clear();
    }
    console.log("push to talk: "+dir);
}


function update_notify(st) {
    if (st === 0) {
        // $(".button.settings").css("position", "absolute").removeClass('orange').addClass('blue');
        // $(".fa-cog.settings").removeClass('fa-spin');
        $(".downloado").removeClass('downloado_down');
    } else {
        // $(".button.settings").css("position", "fixed").removeClass('blue').addClass('orange');
        // $(".fa-cog.settings").addClass('fa-spin');
        $(".downloado").addClass('downloado_down');
    }
}

function router(event) {
    var p = 0;

    if (event['taxi']) {    // такси обрабатывать всегда
        taxi_event(event['taxi']);
        p++;
    }

    // if (timeTravel) {   // остальное, если вкладка с документом активна (timeTravel = 0, см. sleepCheck())
    //     console.log("router: time travel fixed");
    //     return;
    // }

    update_notify(1);

    if (event['routes']) {
        update_routes(event["routes"], event["napr"], event["ttype"]);
        p++;
    }
    if (event['bdata_mode10']) {
        update_bdata_mode10(event['bdata_mode10']);
        last_bdata_mode10 = event;
        p++;
    }
    if (event['bdata_mode11']) {
        update_bdata_mode11(event['bdata_mode11']);
        p++;
    }
    if (event['busamounts']) {
        update_bus_amount(event['busamounts']);
        update_counters_by_type(event['busamounts'])
        p++;
    }
    if (event['passenger']) {
        //console.log('passenger', event['passenger']);
        update_passenger(event['passenger']);
        p++;
    }
    if (event['time_bst']) {
        update_time_bst(event['time_bst']);
        p++;
    }
    if (event['stops']) {
        //23.05.2021 старый функционал поиска маршрута, удалить,если все работает нормально
        //update_stops(event['stops']);
        p++;
    }
    if (event['city_rhythm']) {
        update_city_rhythm(event['city_rhythm']);
        p++;
    }
    if (event['first_last']) {
        update_schedule(event['first_last']);
        p++;
    }
    if (event['passenger_monitor']) {
        update_passenger_monitor(event['passenger_monitor']);
        p++;
    }
    if (event['us_cmd']) {
        update_cmd(event);
        p++;
    }
    if (event['reschedule']) {
        update_reschedule(event['reschedule']);
        p++;
    }
    if (event['counter_online_city_web'] != undefined) {
        update_counter_online_city_web(event['counter_online_city_web']);
        p++;
    }
    if (event['counter_online_city_app'] != undefined) {
        update_counter_online_city_app(event['counter_online_city_app']);
        p++;
    }
    if (event['counter_today']) {
        update_counter_today(event['counter_today'])
        p++;
    }
    //if (event['counters_by_type']) {
    //    update_counters_by_type(event['counters_by_type'])
    //    p++;
    //}
    if (event['server_date']) {
        server_date(event['server_date']);
        p++;
    }
    if (event['status_counter']) {
        update_status_counter(event['status_counter']);
        p++;
    }
    if (event['updater']) {
        update_status_log(event['updater']);
        p++;
    }
    if (event['status_server']) {
        update_status_counter(event['status_server']);
        p++;
    }
    if (event['gps_send_signal']) {
        gps_send_signal(event['gps_send_signal']);
        p++;
    }
    if (event['btc_rub']) {
        btc_update(event['btc_rub']);
        p++;
    }
    if (event['radio']) {
        radio(event['radio']);
        p++;
    }
    if (event['rating_set']) {
        console.log("rating_set");
        event = event['rating_set'];
        for (var bus in globus) {
         if (globus[bus]['g'] == event['gosnum']) {
            //console.log(globus[bus]);
            //console.log(event);
            // rating_set:true
            // rating_wilson:1.625
            break;
         }
        }
        p++;
    }
    if (event['updater'] && event['updater']['state'] == 'idle') {                           // событие "Загрузка данных через Х сек"
        // сколько секунд до обновления
        var timeout = event['updater']['timeout'];

        // устанавливаем прогресс в прогрессбаре
        $('.ui.progress').progress('set progress', (100 - (timeout * 10)));


        if (timeout < 3) { // добавляем в inf_about_data только если timeout от 1 до 3

            // иконка  для отображения события
            var icon_idle = '<i class="fa fa-spinner" aria-hidden="true"></i> ';

            // надпись для отображения события
            var idle_message = trans_idle_message_load +" "+ timeout;

            // добавляем это событие в очередь
            message_queue.push(icon_idle + idle_message);

            if (current_item === null) {// если нет текущего отображаемого события, то смотрим очередь
                process_queue();
            }

        }
        p++;
    } else if (event['updater'] && event['updater']['state'] == 'update') {                  // событие "Данные обновлены"

        // иконка  для отображения события
        var icon_update = '<i class="fa fa-check" aria-hidden="true"></i> ';

        // добавляем это событие в очередь
        message_queue.push(icon_update + trans_update_message);

        // если нет текущего отображаемого события, то смотрим очередь
        if (current_item === null) {
            process_queue();
        }

        // устанавливаем прогресс 100% в прогрессбаре
        $('.ui.progress').progress('set progress', 100);
        p++;

    } else if (event['updater'] && event['updater']['state'] == 'post_turbine_update') {     // событие " Обработано Х событий"

        // иконка  для отображения события
        var icon_post_update = '<i class="fa fa-refresh" aria-hidden="true"></i> ';

        // надпись для отображения события
        var post_update_message = trans_post_update_message_processing + " " + event['updater']['events_count'];

        // добавляем это событие в очередь
        message_queue.push(icon_post_update + post_update_message);

        // если нет текущего отображаемого события, то смотрим очередь
        if (current_item === null) {
            process_queue();
        }
        p++;
    } else if (event['updater'] && event['updater']['state'] == 'post_update') {             // событие "Принято от поставщика Х  событий за W сек"

        // иконка  для отображения события
        var icon_post_turbine_update = '<i class="fa fa-clock-o" aria-hidden="true" style="font-size:14px;"></i> ';

        // надпись для отображения события
        var post_turbine_update_message = trans_post_turbine_update_message_provid +" "+ event['updater']['provider_events_count'] +" "+trans_post_turbine_update_message_for + " " + event['updater']['provider_delay'];

        // добавляем это событие в очередь
        message_queue.push(icon_post_turbine_update + post_turbine_update_message);

        // если нет текущего отображаемого события, то смотрим очередь
        if (current_item === null) {
            process_queue();
        }
        p++;
    }

    if (p===0) {
        /*
        var d = new Date();
        console.log(d+": Unknown event:", event);
        */
    }
    setTimeout(function() {
        update_notify(0);
    }, 300);
}   // router

function onPubBus(args) {
    router(args[0]);
}

function update_cmd(msg) {
    var cmd = msg["us_cmd"];
    var params = msg["params"];

    if (cmd == "reload") {
        if (location.pathname == "/") {
            location.reload();
        } else {
            window.location.href = '/';
        }
    } else if (cmd == "msg") {
        flash_message(params['text'], 3000);
    } else if (cmd == "gvotes") {
        update_gvotes(params);
    } else if (cmd == "error_update") {
        error_update(params);
    } else if (cmd == "weather") {
        weather_update(params);
    } else {
        console.log("unknown cmd: " + cmd + ". Params: ");
        console.log(params);
    }
}

function error_update(params) {
    console.log("Error update! " + params['tm']);
    var status = params['status'],
        tm = params['tm'];
    if (status === 0) {
        $("i.fa-unlink").parent().parent().addClass("hiddeni").attr("title", "");
        $(".error_update").addClass("hidden");
        aplay("sound_speed");
    } else if (status == 1) {
        $("i.fa-unlink").parent().parent().removeClass("hiddeni").attr("title", tm + ": " + trans_text_update_error);
        $(".error_update").removeClass("hidden");
        aplay("sound_speed");
    }
    console.log(status);
}

function server_date(msg) {
  var d = new Date(msg);
  var utc = d.getTime() + (d.getTimezoneOffset() * 60000);
  var offset = 7 + us_city_timediffk;
  var nd = new Date(utc + (3600000*offset));
  var htime = nd.toLocaleString('ru-RU');
  //console.log("time: "+htime);
}

function weather_update(params) {
    var t = params['temp'];
    var weather = params['weather'];
    if (t > 0) {
        t = "+" + t
    }
    console.log('weather update: t=', t, ' weather=', weather);
    $("#weather_t").addClass('bhlight');
    $("#weather_t").html(t + "˚");
    var iconElement = $('#weather_t').prev().closest('a.item').find('i');
    var i="";
    switch(weather){
    case 'rain':
        i = 'fa-tint';
        break;
    case 'snow':
        i = 'fa-snowflake-o';
        break;
    case 'ice':
        i = 'fa-snowflake-o';
        break;
    case 'smoke':
        i = 'fa-recycle';
        break;
    case 'clear':
        i = 'fa-sun-o';
        break;
    case 'clouds':
        i = 'fa-mixcloud';
        break;
    case 'dark_clouds':
        i = 'fa-cloud';
        break;
    case 'fog':
        i = 'fa-tree';
        break;
    default:
        i = 'fa-thermometer-half';
    }   // switch(weather)
    iconElement.attr('class', 'icon ' + i);
    setTimeout(function() {
        $("#weather_t").removeClass('bhlight');
    }, 1500);
}   // function weather_update

function btc_update(params) {
    // console.log('btc_rub: ' + params);
    $(".btc_rub").addClass('bhlight');
    $(".btc_rub").html('<i style="margin-right:-0.1rem" class="fa-btc icon"></i>'+params);
    setTimeout(function() {
        $(".btc_rub").removeClass('bhlight');
    }, 1000);
}

function bus_amount_update(key, amount) {
    if (city_monitor_mode) {return}

    var bus_id = key.substr(0, key.length - 3);
    var target = $(".bid_" + bus_id + " > .busamount, .busamount_" + bus_id);

    if(target && target.length) {
        var d = target.html().split("/");
        if (key.substr(key.length - 2, 2) == "d0") {
            d[0] = amount;
            d[1] = parseInt(d[1], 10) || 0;
        } else {
            d[0] = parseInt(d[0], 10) || 0;
            d[1] = amount;
        }

        target.addClass('bhlight').html(d[0] + " / " + d[1]);

        var kp = target.parent();
        kp.removeClass('coloramount0').removeClass('coloramount1').removeClass('coloramount2');
        var total = d[0] + d[1];
        if (total < 1) {
            kp.addClass('coloramount0');
        } else if (total < 3) {
            kp.addClass('coloramount1');
        } else {
            kp.addClass('coloramount2');
        }
    }
}

function turnoff_hl(bid) {
        $(".bid_" + bid + ">.busamount").removeClass('bhlight');
        $(".busamount_"+bid).removeClass('bhlight');
}

function update_bus_amount(data) {
    // if (timeTravel) {
    //     console.log("update_bus_amount: time travel fixed");
    //     return;
    // }
    var t, bid, amount, old_amount, old_amounts, mdir, ttype;
    for (var key in data) {
        amount = parseInt(data[key], 10);
        mdir = key.substring(key.length-2, key.length);
        if (mdir == "d0") {
            mdir = 0;
        } else {
            mdir = 1;
        }
        bid = key.replace("_d0", '').replace("_d1", '');
        bid = parseInt(bid, 10);
        if (bid == BUS_ID) {
        let  tposition = "top left";
        let  tdirection = trans_text_in_dir_forward;
        let  tamount = trans_text_one_plus;
        if (mdir) {
            tdirection = trans_text_in_dir_reverse;
            tposition = "top right";
        }
            old_amounts = $(".bid_" + bid).find(".busamount").html();
            old_amounts = old_amounts.split(" / ");
            old_amount = parseInt(old_amounts[mdir], 10);
            ttype = dbget('bus', bid, 'ttype');

            if (amount > old_amount) {
                // console.log("plus_one");
                //osd_show('one_plus_'+ttype+'.png');
                if (us_plusone) {
                    $('body').toast({ title: tamount, message: tdirection, position: tposition});
                }
                // some delay to prevent overvoice
                if (us_sound_plusone){
                if (mdir) {
                    setTimeout(function() {
                        aplay('one_plus');
                    }, 1700);
                } else {
                    aplay('one_plus');
                }}
            } else if (amount < old_amount) {
                //osd_show('one_minus_'+ttype+'.png');
                tamount = trans_text_one_minus;
                if (us_plusone) {
                    $('body').toast({ title: tamount, message: tdirection, position: tposition});
                }
                if (us_sound_plusone){
                if (mdir) {
                    setTimeout(function() {
                        aplay('one_minus');
                    }, 1700);
                } else {
                    aplay('one_minus');
                }}
            }
        }
        bus_amount_update(key, amount);
        /*setTimeout(function() {
            $('.busamount').removeClass('bhlight');
        }, 750, bid);*/
        // for async mode
        setTimeout(turnoff_hl, 750, bid);
    }
}

function hashcheck() {
    var hashname = window.location.hash;
    if (hashname) {
        var bname = hashname.replace("#", "");
        if (bname == "bus") {
            change_mode(0);
        } else if (bname == "trolleybus") {
            change_mode(1);
        } else if (bname == "tramway") {
            change_mode(2);
        } else if (bname == "bus-taxi") {
            change_mode(3);
        } else if (bname == "bus-intercity") {
            change_mode(5);
        } else if (bname == "taxi") {
            change_mode(8);
        } else {
            for (var key in dbget('bus')) {
                let curr_bname = dbget('bus', key, 'slug');
                if (bname == curr_bname || "bus-"+bname == curr_bname) {
                    change_mode(dbget('bus', key, "ttype"));
                    show_me_the_bus(key);  // здесь открывается маршрут при загрузке страницы
                }
            }
        }

    }
}

function metric_checkt() {
    ajax_metric("checkt", 1);
}

function aplay(name) {
    if (!us_sound) {
        return;
    }

    if (name == "sound_speed" && sound_speed) {
        sound_speed.play();
    } else {
        sound_main.play(name);
    }
}

function osd_show(im) {
    var tag = "<img src='/static/img/" + im + "' />";
    $('.osd_message').html(tag);
    $('.osd_message').slideDown('fast');
    setTimeout(function() {
        $('.osd_message').fadeOut('fast');
    }, 1200);
}

function osd_splash() {
    $('.osd_message').css('display', 'inline');
    setTimeout(function() {
        // $('.osd_message').fadeOut(100);
        $('.osd_message').css('display', 'none');
    }, 500);
}

function flash_message(msg, delay) {
    $('.flash_message').html(msg);
    $('.flash_message').slideDown('fast');
    if (delay > 0) {
        setTimeout(function() {
            $('.flash_message').fadeOut('fast');
        }, delay);
    }
}

function vibrate() {
    if (supportsVibrate) {
        navigator.vibrate([700, 300, 700]);
    }
}

function cookie_policy_agree() {
    Cookies.set('cookie_policy', "1", { expires: 3650, domain: '.bustime.loc' });
    $(".cookie_policy").addClass("hidden");
}

function map_data_go() {
    if (last_bdata_mode10) {
        router(last_bdata_mode10);
    }
}


function show_map(ret) {
    if (us_dark_theme === "on" || (us_dark_theme === "auto" && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        OSM_STYLE = 'https://demotiles.maplibre.org/style.json'
    }
    //console.log(`show_map(${ret})`);
    var html_ = '<i class="fa-globe icon"></i> ';
    if ($('.map').css("display") == "none") {
        $('.map').css("display", "block");
    //    $('.show_jam_button').css("display", "inline-block");
        $('.show_map_button').html(html_ + trans_text_hide_map);
        if (!map) {
            // ajax_metric("show_map", 1);
            if (ret == 0) {
                settings_set_silent("map_show", true);
            }
            myCollection = L.featureGroup();
            busstop_collection = L.featureGroup();
            passenger_collection = L.featureGroup();
            jamcollection = L.featureGroup();
            setInterval(passenger_removal, 10 * 1000);
            // var osm = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
            var osm = L.maplibreGL({
                style: OSM_STYLE,
                minZoom: 1,maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            });

            map = L.map('lmap', { scrollWheelZoom: true, fullscreenControl: true, layers: [osm, busstop_collection, myCollection, passenger_collection, jamcollection] });
            map.on('load', function() {
                if (typeof onMapLoaded === 'function') { onMapLoaded(map) }
            });
            var baseLayers = {};
            baseLayers[trans_text_map] = osm;
            var overlays = {};
            overlays[trans_text_transport] = myCollection;
            overlays[trans_text_stops] = busstop_collection;
            overlays[trans_text_passenger] = passenger_collection;
            overlays[trans_text_jam] = jamcollection;
            L.control.layers(baseLayers, overlays, {hideSingleBase:true}).addTo(map);
            if(test_mode){
                let mouseMoveControl = L.Control.extend({
                    options: {
                        position: 'bottomleft'
                    },

                    onAdd: function (map) {
                        var container = L.DomUtil.create('div', 'my-custom-control');
            			map.on('mousemove', function(MouseEvent){
                            container.innerHTML = 'Lat: ' + MouseEvent.latlng.lat.toFixed(6) +
                                                    ' Lon: ' + MouseEvent.latlng.lng.toFixed(6);
            			});
                        return container;
                    }
                });

                map.addControl(new mouseMoveControl());

                map.on('click', function(e) {
                    test_latlng = e.latlng;
                    let m = L.circleMarker(e.latlng);
                    m.addTo(map);
                    setTimeout(() => {
                        map.removeLayer(m);
                    }, 3000);
                });
            }
            else {
                test_latlng = null;
            }
            map.on("viewreset", function() {
                map.invalidateSize(false);
                map_data_go();
            });
            map_draw_stops();
            map_data_go();
        }
        // map.invalidateSize(false);

    } else {
        $('.map').css("display", "none");
        $('.show_map_button').html(html_ + trans_text_show_map);
        settings_set_silent("map_show", false);
    }
}   // show_map


function map_mousemove(MouseEvent){
    console.log('map_mousemove', MouseEvent, div);
    // MouseEvent.latlng: Object { lat: 55.97419523800931, lng: 92.91927337646486 }
}


function radar_init(ymaps) {
    map = L.map('lmap', { scrollWheelZoom: true, fullscreenControl: true });
    map.on('load', function() {
        if (typeof onMapLoaded === 'function') { onMapLoaded(map) }
    });
    myCollection = L.featureGroup().addTo(map);
    var osm = L.maplibreGL({
        style: OSM_STYLE,
        minZoom: 1,maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    // var osm = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
    osm.addTo(map);
    map.setView([US_CITY_POINT_Y, US_CITY_POINT_X], 15);
    L.Icon.Default.imagePath = '/static/img/';
    console.log('radar inited');

    // ol_map_view =  new ol.View({
    //   center: ol.proj.transform([US_CITY_POINT_X, US_CITY_POINT_Y], 'EPSG:4326', 'EPSG:3857'),
    //   rotation: 7,
    //   zoom: 18
    // });
    // ol_map = new ol.Map({
    // target: 'ol_map',
    // layers: [
    //   new ol.layer.Tile({
    //     source: new ol.source.OSM()
    //   })
    // ],
    // view: ol_map_view
    // });

    // ol_map_view.centerOn(ol.proj.transform([93, 56], 'EPSG:4326', 'EPSG:3857'));
    // var position = new ol.LonLat(93,56.02); //.transform('EPSG:4326', 'EPSG:3857');
    // ol_map_view.centerOn([93,56]);
    // http://openlayers.org/en/v3.3.0/apidoc/
    // ol_map_view.centerOn(position, 18);
    // ol_map_view.setRotation(90);
}

function city_monitor() {
    map = L.map('lmap', { scrollWheelZoom: true, fullscreenControl: true });
    map.on('load', function() {
        if (typeof onMapLoaded === 'function') { onMapLoaded(map) }
    });
    myCollection = L.featureGroup().addTo(map);
    passenger_collection = L.featureGroup().addTo(map);;
    setInterval(passenger_removal, 10 * 1000);
    var osm = L.maplibreGL({
        style: OSM_STYLE,
        minZoom: 1,maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    // var osm = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
    osm.addTo(map);
    map.setView([US_CITY_POINT_Y, US_CITY_POINT_X], 12);
    L.Icon.Default.imagePath = '/static/img/';

    socket.emit('join', "ru.bustime.city_monitor__" + us_city);
    socket.emit('join', "ru.bustime.status__" + us_city);
    socket.emit('join', "ru.bustime.updater__" + us_city);
    socket.emit('join', "ru.bustime.status_server");
    console.log('City status monitor');
}

function recalc_schedule() {
    var now = new Date();
    var i, job_done = 0;

    for (i = 0; i < schedule[0].length; i++) {
        if (schedule[0][i] > now) {
            $(".schedule_0_1").html(schedule[0][i].toTimeString().substr(0, 5));
            $(".schedule_0_1").addClass('bhlight_black');
            setTimeout(function() {
                $(".schedule_0_1").removeClass('bhlight_black');
            }, 400);
            job_done = 1;
            break;
        }
    }
    if (job_done === 0) {
        $(".schedule_0_1").html("");
    }
    job_done = 0;
    for (i = 0; i < schedule[1].length; i++) {
        if (schedule[1][i] > now) {
            $(".schedule_1_1").html(schedule[1][i].toTimeString().substr(0, 5));
            $(".schedule_1_1").addClass('bhlight_black');
            setTimeout(function() {
                $(".schedule_1_1").removeClass('bhlight_black');
            }, 400);
            job_done = 1;
            break;
        }
    }
    if (job_done === 0) {
        $(".schedule_1_1").html("");
    }
}

function update_schedule(msg) {
    $(".schedule").css('display', 'block');
    var now = new Date();
    var s1 = "";
    var i, d;
    schedule[0] = [];
    schedule[1] = [];

    if (msg["s0"] && msg["s0"].length > 0) {
        $(".schedule_0").css('display', 'table');
        for (i = 0; i < msg["s0"].length; i++) {
            d = new Date(now.getFullYear(), now.getMonth(), now.getDate(), msg["s0"][i][0], msg["s0"][i][1]);
            if (i === 0) {
                $(".schedule_0_0").html(d.toTimeString().substr(0, 5));

            }

            if (d > now) {
                schedule[0].push(d);
            }

            if (i === msg["s0"].length - 1) {
                $(".schedule_0_2").html(d.toTimeString().substr(0, 5));
            }
        }
    } else {
        $(".schedule_0").css('display', 'none');
    }


    if (msg["s1"] && msg["s1"].length > 0) {
        $(".schedule_1").css('display', 'table');
        for (i = 0; i < msg["s1"].length; i++) {
            d = new Date(now.getFullYear(), now.getMonth(), now.getDate(), msg["s1"][i][0], msg["s1"][i][1]);
            if (i === 0) {
                $(".schedule_1_0").html(d.toTimeString().substr(0, 5));
            }
            if (d > now) {
                schedule[1].push(d);
            }
            if (i === msg["s1"].length - 1) {
                $(".schedule_1_2").html(d.toTimeString().substr(0, 5));
            }
        }
    } else {
        $(".schedule_1").css('display', 'none');
    }
    recalc_schedule();
}

function passenger_removal() {
    var now = new Date();
    // clean up dots older then 1 minute
    for (var key in CITY_MONITOR_ONSCREEN) {
        if (now - CITY_MONITOR_ONSCREEN[key][0] > 35 * 1000) {
            passenger_collection.removeLayer(CITY_MONITOR_ONSCREEN[key][1]);
            delete CITY_MONITOR_ONSCREEN[key];
            $(".passengers_amount").html(passenger_collection.getLayers().length);
            // aplayfile("barcode_out");
        }
    }
}

function update_passenger_monitor(msg) {
    if (!map) {return}
    var now = new Date();
    var marker;
    var date = msg['time'];
    var sess_id = msg['sess'];
    var lon = msg['lon'];
    var lat = msg['lat'];
    var accuracy = msg['accuracy'];
    var bus_name = msg['bus_name'];
    var nb_id = msg['nb_id'];
    var nb_name = msg['nb_name'];
    var os = msg['os'];
    var pass_icon = L.divIcon({
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            className: '',
            html: "<img src='/static/img/person_status.svg' onmouseover='this.src=\"/static/img/person_status_red.svg\"' onmouseout='this.src=\"/static/img/person_status.svg\"'>"
    });
    // console.log(msg);


    if (Math.abs(US_CITY_POINT_X - lon) > 1 || Math.abs(US_CITY_POINT_Y - lat) > 1) {
        return;
    }

    // if already in array - update coords and time
    if (sess_id in CITY_MONITOR_ONSCREEN) {
        marker = CITY_MONITOR_ONSCREEN[sess_id][1];
        marker.setLatLng([lat, lon]);
        CITY_MONITOR_ONSCREEN[sess_id][0] = now;
        return;
    }
    marker = L.marker([lat, lon], {icon: pass_icon}).addTo(map);

    var popup_data = "";

    if (nb_name) {
        popup_data = popup_data + nb_name + "<br/>";
    }

    if (os == "web") {
        popup_data = popup_data + "<i class='fa-globe icon'></i>";
        // aplayfile("barcode_out");
    } else if (os == "android") {
        popup_data = popup_data + "<i class='fa-android icon'></i>";
        // aplayfile("barcode");
    } else if (os == "ios") {
        popup_data = popup_data + "<i class='fa-apple icon'></i>";
        // aplayfile("barcode");
    }

    if (bus_name) {
        popup_data = popup_data + "жду " + bus_name;
    }
    if (popup_data) {
        marker.bindTooltip(popup_data);
    }
    passenger_collection.addLayer(marker);
    CITY_MONITOR_ONSCREEN[sess_id] = [now, marker];

    // map.fitBounds(myCollection.getBounds());
    // console.log(marker);
    $(".passengers_amount").html(passenger_collection.getLayers().length);
}

function aplayfile(snd) {
    if (us_sound) {
        var sound_mini = new Howl({
            src: ["/static/js/snd/" + snd + '.mp3', "/static/js/snd/" + snd + '.ogg'],
            volume: 0.7
        }).play();
        return true;
    } else {
        return false;
    }
}

function scroller() {
    var d;
    if (scroller_dir == 0) {
        d = 0;
    } else {
        d = $( document ).height();
        d = d / 5 * scroller_dir;
    }


    scroller_dir++;
    if (scroller_dir == 2 || scroller_dir == 4) {
        osd_splash("bustime-splash.png");
    }
    if (scroller_dir == 5) {
        scroller_dir = 0;
    }

    $('html, body').animate({ scrollTop: d }, 1000);
}


// function mobile_test_rpc_status_server() {
//     socket.emit("rpc_status_server");
//         socket.emit("rpc_status_server", function (data) {
//             console.log("rpc_status_server");
//             console.log(data);
//         });
// }
// function mobile_test_rpc_status_counter() {
//         socket.emit("rpc_status_counter", us_city, function (data) {
//             console.log("rpc_status_counter");
//             console.log(data);
//         });
// }
// function mobile_test_rpc_city_error() {
//         socket.emit("rpc_city_error", us_city, function (data) {
//             console.log("rpc_city_error");
//             console.log(data);
//         });
// }

// function mobile_test_rpc_bootstrap_amounts() {
//     socket.emit("rpc_bootstrap_amounts", us_city);
// }


// function mobile_test_rpc_tcard() {
//     socket.emit("rpc_tcard", "0100000006877964", function (data) {
//         console.log("rpc_tcard");
//         console.log(data);
//     });
// }

// function mobile_test_rpc_stop_ids() {
//     socket.emit("rpc_stop_ids", {"ids":[7642, 7701, 7972, 8060], "mobile":true}, function (data) {
//         console.log("rpc_stop_ids");
//         console.log(data);
//     });
// }

// function mobile_test_rpc_mobile_bootstrap() {
//     socket.emit("rpc_mobile_bootstrap", function (data) {
//         console.log("rpc_mobile_bootstrap");
//         console.log(data);
//     });
// }

// function mobile_test_rpc_buses_by_radius() {
//     var data = {"city_id":3, "x":92.9411, "y":56.00518, "buses":[532,534,536], "radius":1500};
//     socket.emit("rpc_buses_by_radius", data, function (data) {
//         console.log("rpc_buses_by_radius");
//         console.log(data);
//     });
// }

// function mobile_test_rpc_city_monitor() {
//     var data = {"city_id":3,
//                 "sess":123,
//                 "x":92.9411,
//                 "y":56.00518,
//                 "bus_name":"2",
//                 "nb_id":7701,
//                 "nb_name":"родина",
//                 "mob_os":"android"
//             };
//     socket.emit("rpc_city_monitor", data, function (data) {
//         console.log("rpc_city_monitor");
//         console.log(data);
//     });
// }

// function mobile_test_chat_get() {
//     socket.emit('join', "ru.bustime.chat__534");
//     socket.emit("rpc_chat_get", {bus_id:534}, function (data) {
//         console.log("rpc_chat_get");
//         console.log(data);
//     });
// }
// function mobile_test_chat() {
//     // socket.emit('join', "ru.bustime.chat__534");
//     socket.emit("rpc_chat", {bus_id:534, message:"Привет"}, function (data) {
//         console.log("rpc_chat");
//         console.log(data);
//     });
// }

function mobile_test_cases() {
    console.log("Mobile_test_cases started.");
    // mobile_test_rpc_status_server();
    // mobile_test_rpc_status_counter();
    // mobile_test_rpc_city_error();
    // mobile_test_rpc_bootstrap_amounts();
    // mobile_test_rpc_tcard();
    // mobile_test_rpc_stop_ids();
    // mobile_test_rpc_mobile_bootstrap();
    // mobile_test_rpc_buses_by_radius();
    // mobile_test_rpc_city_monitor();
    // mobile_test_chat_get();
    // mobile_test_chat();
}

function startUserMedia(stream) {
    var input = audio_context.createMediaStreamSource(stream);
    recorder = new Recorder(input, {'type':'audio/ogg'});
    console.log('Recorder initialised.');
}

function low_bootstrap() {
    // mobile_test_cases();
    // miner.start();
    $.fn.dropdown.settings.message['noResults'] = trans_text_city_not_found;
    $('.ui.dropdown').dropdown();
    // if (!us_premium || us_pro_demo) {
    //     // 1m delay before first minute
    //     if (us_mode != 7 && us_city != 3 && us_city != 11 && us_city != 12 && !gps_send_enough) {
    //         setTimeout(function() {
    //             session_timer();
    //         }, 60 * 1000);
    //     }
    // }
    // $(".lucky_message").remove();
    // pixijs_load();
    if (city_monitor_mode) {
        city_monitor();
    } else {
        // var now = new Date();
        if (holiday_flag) {
            console.log(holiday_flag);
        }
        if (holiday_flag == "new year") {
            BUS_SIDE_IMG = "/static/img/santa_2016.png";
          // if (typeof Phaser != 'undefined' && !us_premium && !isAndroid) { // doublec check if I not forget tom compile it in
          //   game = new Phaser.Game("100", "100", Phaser.AUTO, 'ph_container', { preload: ny_preload, create: ny_create }, true);
          // }
        }
    }
    if (ads_show) {
        blockAdblockUser();
        // animate_ads_shuttle();
    }
    if (us_mode == 7) {
        setInterval(scroller, 7000);
    }
    if (us_radio && (us_premium || gps_send_enough)) {
        socket.emit('join', "ru.bustime.radio__" + us_city);
    }

    var cp = Cookies.get('cookie_policy');
    if (cp == undefined) {
        $(".cookie_policy").removeClass("hidden");
    }
    $(".edit_title_b").click(edit_title);
    $('input.search').attr("type", "search"); // prevents 'key' keyb button on android

    hotkeys('n', function(event, handler){
      // https://github.com/jaywcjlove/hotkeys
      var as = $(".search .menu > a.item");
      var next_one = false;
      for(var i=0;i<as.length;i++) {
        if ($(as[i]).hasClass('active')) {
            // console.log(as[i].href, );
            next_one = i+1;
            if (i == as.length-1) {
                next_one = 0;
            }
            break;
        }
      }
      window.location.href = as[next_one].href;
    });
}

// jQuery.loadScript = function (url, callback) {
//     jQuery.ajax({
//         url: url,
//         dataType: 'script',
//         success: callback,
//         async: true
//     });
// }

function edit_title() {
    if ($(".edit_title").hasClass("hiddeni")) {
        $(".logo_header").addClass("hiddeni");
        $(".edit_title").removeClass("hiddeni");
        $(".edit_title_b").addClass("hiddeni");
    } else {
        var name = $(".edit_title>input").val();
        var request = $.ajax({
            url: "/ajax/settings/",
            type: "GET",
            data: {
                "setting": "name",
                "value": name
            }
        });

        request.done(function(msg) {
            $(".logo_header").html(msg);
        });
        $(".logo_header").removeClass("hiddeni");
        $(".edit_title").addClass("hiddeni");
        $(".edit_title_b").removeClass("hiddeni");
    }
}

function citynews_watched(cn_id) {
    console.log(cn_id)
    var request = $.ajax({
        url: "/ajax/citynews_watched/",
        type: "GET",
        data: {
            "cn_id": cn_id
        }
    });
}

function voice_queue_add(fname) {
    // console.log("bda news")
    VOICE_QUEUE.push(fname);
    // console.log("voice_queue push: "+fname);
    voice_queue();
}

function voice_queue() {
    if (VOICE_QUEUE.length == 0) {
        return
    }
    if (VOICE_NOW) {
        return
    }
    VOICE_NOW = 1;
    var snd = VOICE_QUEUE.splice(0,1);
    var prfx = "ol/";
    // prfx = "ama/";
    var sound_mini = new Howl({
        src: ["/static/sounds/" + prfx + snd + '.ogg', "/static/sounds/" + prfx + snd + '.mp3'],
        volume: 0.7,
        onend: function() {
            VOICE_NOW = 0;
            voice_queue();
        },
        onloaderror: function() {
            console.log('onloaderror: ' + snd)
            VOICE_NOW = 0;
            voice_queue();
        }
    }).play();
}

function animate_ads_shuttle() {
    if (!animate_ads_shuttle_original) {
        animate_ads_shuttle_original = $(".ads_shuttle").offset().left;
    }
    // xnew = animate_ads_shuttle_original + animate_ads_shuttle_step*animate_ads_shuttle_step*50;
    xnew = animate_ads_shuttle_original + Math.pow(2,animate_ads_shuttle_step);
    // if (animate_ads_shuttle_original + Math.pow(2,animate_ads_shuttle_step+1) + 50 > screen.width) {
    //   $(".ads_shuttle").css('color','red');
    // } else {
    //   $(".ads_shuttle").css('color','');
    // }

    animate_ads_shuttle_step ++;
    if (xnew + 50> screen.width) {
        animate_ads_shuttle_step = 0;
        xnew = animate_ads_shuttle_original;
    }
    $(".ads_shuttle").offset({left:xnew});


    // -animate_ads_shuttle_step*10
    setTimeout(function() {
        animate_ads_shuttle();
    }, 500);
}

function session_timer() {
    request = $.ajax({
        url: "/ajax/timer/",
        type: "GET",
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        if (us_premium === 0 && msg['minutes'] >= 110) {
            location.reload();
        }
        if (us_pro_demo === 1 && msg['pro_minutes'] >= 10) {
            location.reload();
        }

        if (us_pro_demo) {
            timer_minutes = msg['pro_minutes'];
            $(".ut_minutes").html(10-timer_minutes);
        } else {
          timer_minutes = msg['minutes'];
          $(".ut_minutes").html(110-timer_minutes);
        }
        $(".ut_minutes").addClass('bhlight');
        setTimeout(function() {
            $(".ut_minutes").removeClass('bhlight');
        }, 1000);
    });

    setTimeout(function() {
        session_timer();
    }, 60 * 1 * 1000);
}

function radar_center(position) {
    if (!map) {
        return;
    }

    map.panTo([position.coords.latitude, position.coords.longitude]);
    if (radar_circle === null) {
        radar_circle = L.circle([position.coords.latitude, position.coords.longitude], 30).addTo(map);
    } else {
        radar_circle.setLatLng([position.coords.latitude, position.coords.longitude]);
    }
}

function radar_watch(position) {
    var now = new Date();
    if (now.getTime() - usePositionWatch_last.getTime() > 10 * 1000) {
        usePositionWatch_last = now;
        radar_position(position);
    } else {
        radar_center(position);
    }
}

function radar_position(position) {
    radar_center(position);
    var request = $.ajax({
        url: "/ajax/radar/",
        type: "post",
        data: {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy: position.coords.accuracy
        },
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        update_radar_mode(msg);
    });
}


function update_radar_mode(data) {
    if (!map) {
        return;
    }
    var event, d, g, sleep, st, sc, bname, MapIconDiv, latlngs;
    var polyline, marker;
    if (myCollection) {
        myCollection.clearLayers();
    }



    for (var i = 0; i < data.length; i++) {
        if (!("point_x" in data[i])) {
            return;
        }
        event = data[i];
        bname = event['bus_name'];
        d = event['direction'];
        if (d === 0) {
            extra_c = "color-1-2-bg";
            sc = "#74c0ec";
        } else {
            extra_c = "color-2-2-bg";
            sc = "#5ec57c";
        }
        if (event['gosnum'] && us_premium) {
            g = event['gosnum'] + '<br/>';
        } else {
            g = "";
        }

        MapIconDiv = L.divIcon({
            iconSize: [112, 18],
            iconAnchor: [0, 0],
            className: 'MapIconDiv ' + extra_c,
            html: "<b>" + bname + ":</b> " + event["bn"]
        });
        marker = L.marker([event['point_y'], event['point_x']], { icon: MapIconDiv, zIndexOffset: 100});
        marker.bindPopup("<b>" + bname + "</b> " + g);

        latlngs = [
            [event['point_y'], event['point_x']],
            [event['point_prev_y'], event['point_prev_x']]
        ];
        polyline = L.polyline(latlngs, { color: sc, opacity: 0.8 });

        myCollection.addLayer(marker);
        myCollection.addLayer(polyline);
    }
}

function express_dial_show() {
    $(".express_dial").addClass('express_dial_fixed');
    $(".express_fixed").css('display', 'none');
    // $(".multi_bus").css("display", 'none');
    $('.push_to_talk').removeClass('hidden');

    if (!audio_context)  {
      try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            audio_context = new AudioContext();
            if (is_touch_device()) {
                $('.push_to_talk').on({ 'touchstart' : push_to_talk_click_up_down });
                $('.push_to_talk').on({ 'touchend' : push_to_talk_click_up_down });
            } else {
                $('.push_to_talk').mouseup(push_to_talk_click_up_down).mousedown(push_to_talk_click_up_down);
            }
          } catch (e) {
            alert('No web audio support in this browser!');
          }
    }
}

function express_dial_hide() {
    $(".express_dial").removeClass('express_dial_fixed');
    $(".express_fixed").css('display', '');
    $('.push_to_talk').addClass('hidden');
    // $(".multi_bus").css("display", '');
}

// mode_new: 0|1|2...
function change_mode(mode_new) {
    if(test_mode){
        console.log(`change_mode(${mode_new}), mode_selected=${mode_selected}`);
    }

    // это Панель кнопок маршрутов
    //$(".mode_" + mode_selected).addClass("fhidden");  // это относится к закомментированному блоку в turbo_index.html
    $(".mode_" + mode_selected).css("display", "none");

    $(".modec_" + mode_selected).removeClass('active'); // это меню из кнопок Автобус/Троллейбус...
    mode_selected = mode_new;

    //$(".mode_" + mode_selected).removeClass("fhidden");
    $(".mode_" + mode_selected).css("display", "flex");

    $(".modec_" + mode_selected).addClass('active');

    if(mode_new != 8 && matrix_show){  // taxi
        $(".bus_hide").show();
        if( $(".bustable_head").css("display") != "block" ){
            $("#main_bases_map").hide();
        }
    }

    $(".pointing > .item > .sprite_svg").removeClass("active");
    if (mode_new == 0) {
        // window.location.href = "#bus";
        $(".item .svg-bus").addClass("active");
    } else if (mode_new == 1) {
        // window.location.href = "#trolleybus";
        $(".item .svg-trolleybus").addClass("active");
    } else if (mode_new == 2) {
        // window.location.href = "#tramway";
        $(".item .svg-tramway").addClass("active");

    } else if (mode_new == 3) {
        $(".item .svg-bus-taxi").addClass("active");
        // window.location.href = "#bus-taxi";
    } else if (mode_new == 4) {
        // window.location.href = "#water";
        $(".item .svg-ferry").addClass("active");
    } else if (mode_new == 5) {
        // window.location.href = "#bus-intercity";
        $(".item .svg-2bus").addClass("active");
    } else if (mode_new == 6) {
        // window.location.href = "#train";
        $(".item .svg-train").addClass("active");
    } else if (mode_new == 7) {
        // window.location.href = "#metro";
        $(".item .svg-metro").addClass("active");
    } else if (mode_new == 8) {
        // window.location.href = "#carpool";
        $(".item .sprite-search").addClass("active");
        $(".bus_hide").hide();
        loadTaxiSounds();
    }

}

function gosnum_by_voice() {
    if ('webkitSpeechRecognition' in window) {
        // heh
    } else {
        alert(trans_text_recognition);
        return;
    }
    if (!gosnum_recognition_inited) {
        gosnum_recognition_init();
    }
    gosnum_recognition.start();
}


function express_dial_init() {
    // mousedown touchstart click
    var eventus = "click";
    if (is_ios) {
        // eventus = "touchstart";
        // event.stopPropagation()
        // проблема alex2, пробивает насквозь
        // stopPropagation stops the event from bubbling up the event chain.
        // preventDefault prevents the default action the browser makes on that event.
        eventus = "touchend";
    } else if (is_chrome) {
        eventus = "mousedown";
    }
    if ('webkitSpeechRecognition' in window) {
        $(".calc-mic").removeClass("hidden");
    }

    $(".calc").on(eventus, function(event) {
        var classes = $(this).attr('class').split(/\s+/);
        var cl = classes.pop().slice(5);

        if (cl == "go") {
            express_dial_go();
        } else {
            if (cl == "backspace") {
                if (express_dial.length) {
                    express_dial = express_dial.substring(0, express_dial.length - 1);
                }
            } else if (cl == "mic") {
                // https://www.google.com/intl/en/chrome/demos/speech.html
                // http://shapeshed.com/html5-speech-recognition-api/
                // http://updates.html5rocks.com/2013/01/Voice-Driven-Web-Apps-Introduction-to-the-Web-Speech-API
                // flash_message("Голосовые команды работают только в Chrome", 2500);
                if (!recognition_inited) {
                    recognition_init();
                }
                recognition.start();
                ajax_metric("recognition", 1);
                express_dial_hide();
            } else if (express_dial.length < 1 && cl == "0") {
                // nothing
            } else if (express_dial.length < 3) {
                express_dial += cl;
            }
            $(".busnumber").removeClass("calc-influence");
            if (express_dial) {
                var bus_ids = [];
                for (var key in dbgetsafe('bus')) {
                    let bbus = dbget('bus', key, null, true);
                    if (bbus['name'].startsWith(express_dial) && bbus['ttype'] == express_dial_type) {
                        bus_ids.push(key);
                    }
                }
                if (bus_ids.length == 1) {
                    express_dial_go();
                } else {
                    var s = "";
                    for (var i = 0; i < bus_ids.length; i++) {
                        s += ".bid_" + bus_ids[i] + ", ";
                    }
                    s = s.substring(0, s.length - 2);
                    $(s).addClass("calc-influence");
                }
            }
        }

        $(".calc-go").html(express_dial + ' <i class="fa fa-arrow-right"></i>');
        $(".calc-mic").html(express_dial + ' <i class="microphone fa fa-microphone"></i>');
    });

    $(".calc-mode").on(eventus, function(event) {
        var classes = $(this).attr('class').split(/\s+/);
        // console.log(classes);
        var cl = classes.pop();
        // console.log(cl);

        if (cl == "calc-up") {
            $('html, body').scrollTop(0);
            express_dial_hide();
            return;
        }
        // if (cl=="calc-favor") {
        //     $('html, body').scrollTop( $('.stg').offset().top );
        //     return;
        // }

        $(".calc-mode_selected").removeClass('calc-mode_selected');
        $(this).addClass('calc-mode_selected');
        $(".calc-mode .sprite").removeClass("active");
        if (cl == "calc-a") {
            express_dial_type = 0;
            // $(".calc").css("background", btype_color[express_dial_type]);
            $(".calc-mode .sprite-bus").addClass('active');
        } else if (cl == "calc-t") {
            express_dial_type = 1;
            // $(".calc").css("background", btype_color[express_dial_type]);
            $(".calc-mode .sprite-trolleybus").addClass('active');
        } else if (cl == "calc-tv") {
            express_dial_type = 2;
            // $(".calc").css("background", btype_color[express_dial_type]);
            $(".calc-mode .sprite-tramway").addClass('active');
        } else if (cl == "calc-bt") {
            express_dial_type = 3;
            // $(".calc").css("background", btype_color[express_dial_type]);
            $(".calc-mode .sprite-bus-taxi").addClass('active');
        } else if (cl == "calc-mg") {
            express_dial_type = 5;
            // $(".calc").css("background", btype_color[express_dial_type]);
            $(".calc-mode .sprite-2bus").addClass('active');
        }

    });
}

function express_dial_go() {
    var express_dial_fixed = $(".express_dial").hasClass('express_dial_fixed');
    setTimeout(function() {
        express_dial_hide();
    }, 200);
    if (!express_dial) {
        return;
    }
    var bus_id;

    for (var key in dbgetsafe('bus')) {
        let bbus = dbget('bus', key, null, true);
        if (bbus['name'] == express_dial && bbus['ttype'] == express_dial_type) {
            bus_id = key;
        }
    }
    if (!bus_id) {
        express_dial = "";
        $(".calc-go").html('<i class="fa fa-arrow-right"></i>');
        $(".calc-mic").html(' <i class="microphone fa fa-microphone"></i>');
        return;
    }

    window.location.href = "#" + dbget('bus', bus_id, 'slug');
    express_dial = "";
    $(".busnumber").removeClass("calc-influence");
    show_me_the_bus(bus_id);

    if (express_dial_fixed) {
        ajax_metric("express_dial", 1);
    } else {
        ajax_metric("express_dial_mini", 1);
    }
}

function rating_fill(data, force) {
    current_rating_data = data;
    var i;

    if (data['error']) {
        $(".rating_scores").html(0);
        $(".rating_votes").html(0);
        console.log(data['error']);
        return 0;
    }

    $('.rating').rating({
        initialRating: data['rating_wilson'],
        maxRating: 5
    });
    $(".rating_wilson").html(data['rating_wilson'].toFixed(1));
    $(".votes_wilson").html(data['votes_wilson']);

    $(".rate_positive").html('<i class="fa-thumbs-o-up icon"></i>');
    $(".rate_negative").html('<i class="fa-thumbs-o-down icon"></i>');

    if (data['myvote_ctime']) {
        if (data['myvote_positive']) {
            $(".rate_positive").addClass("active");
            $(".rate_positive").html('<i class="fa-thumbs-up icon"></i>');
        } else {
            $(".rate_negative").addClass("active").html('<i class="fa-thumbs-down icon"></i>');
        }
        $(".vote_comment").val(data["myvote_comment"]);
    } else {
        $(".vote_comment").val("");
    }

    // if (data["driver_ava"]) {
    //    $(".driver_ava").attr('src', '/static/img/ava/'+data['driver_ava']+".jpg");
    // }
    if (data["name"]) {
       var old=$(".vehicle_info_name").html();
       $(".vehicle_info_name").html(old+" ("+data['name']+")");
    }
    // lazy integrate counter
    var reviews_txt = $(".vehicle_feedback_ts").html();
    reviews_txt = reviews_txt.split(" ")[0];
    if (data["comments_count"]) {
        $(".vehicle_feedback_ts").html(reviews_txt+" ("+data["comments_count"]+")");
    } else {
        $(".vehicle_feedback_ts").html(reviews_txt);
    }
    return 1;
}

function rating_click(ev) {
    if (reg_today) {
        alert(trans_text_no_vote);
        return;
    }

    if ($(this).hasClass('rate_positive')) {
        rate = 1;
        $(".rate_positive").html('<i class="fa-thumbs-up icon"></i>');
        $(".rate_negative").html('<i class="fa-thumbs-o-down icon"></i>');
    } else if ($(this).hasClass('rate_negative')) {
        rate = -1;
        $(".rate_negative").html('<i class="fa-thumbs-down icon"></i>');
        $(".rate_positive").html('<i class="fa-thumbs-o-up icon"></i>');
    }
}


function vehicle_info_itsme(ev) {
    vehicle = globus[current_vehicle_info];

    var request = $.ajax({
        url: "/ajax/settings/",
        type: "get",
        data: {
            "setting": "gps_send_of",
            "value": current_vehicle_info,
        },
        dataType: "json",
        cache: false
    }); // => bustime.views.ajax_settings()
    request.done(function(msg) {});
    vehicle_info_close();
    flash_message(trans_text_gps_overwrite, 3000);
}   // vehicle_info_itsme


function vehicle_info_gosnum(ev) {
    var gosnum = $("[name=gosnum]").val();

    var request = $.ajax({
        url: "/ajax/gosnum/",
        type: "get",
        data: {
            "uniqueid": current_vehicle_info,
            "gosnum": gosnum,
            "city_id": us_city
        },
        dataType: "json",
        cache: false
    });
    request.done(function(msg) {
        if (msg['error']) {
            alert(msg['error']);
        } else {
            var cnt = msg['result']['counter'];
            var gift = msg['result']['gift'];
            vehicle_info_close();
            if (gift) {
                flash_message("Подарок: +1 премиум день!");
                location.reload();
            } else {
                flash_message("Принято" +" " + cnt + ": " + gosnum, 2500);
            }
        }
    });
}



function rating_submit(ev) {
    var msg = $("[name=msg]").val();
    if (msg === "" && rate !== 0) {
        alert(trans_text_m1);
        return;
    }
    if (msg !== "" && rate === 0) {
        alert(trans_text_m2);
        return;
    }

    var check_result = check_wise(msg);
    if (!check_result) {
        alert(trans_text_m3);
        return;
    }

    vehicle = globus[current_vehicle_info];
    socket.emit("rpc_rating_set", {
        "bus_id":vehicle['id'],
        "g":vehicle['g'],
        "comment": msg,
        "rate": rate
        },
        function (data) {
            // console.log(data);
            data = data["rpc_rating_set"];
            if (data['error'] == "no gosnum") {
                alert(trans_text_m4);
            } else if (data['error']) {
                alert(data['error']);
            }
            rating_fill(data, 1);
            if (!data['error']) {
                flash_message(trans_text_m5, 750);
            }
    });

    vehicle_info_close();
    rate = 0;
}

function rating_statuser(rate, good) {
    var status;
    if (good) {
        if (rate >= 4.9) {
            status = "высший класс";
        } else if (rate >= 4.5) {
            status = "замечательный человек";
        } else if (rate >= 3.5) {
            status = "хороший работник";
        } else if (rate >= 2.5) {
            status = "работает посредственно";
        } else if (rate >= 1.5) {
            status = "профессионально непригоден";
        } else if (rate >= 1) {
            status = "мешает жить окружающим";
        } else {
            status = "нет оценки";
        }
    } else {
        if (rate >= 5) {
            status = "замечательный человек";
        } else if (rate >= 4) {
            status = "хороший работник";
        } else if (rate >= 3) {
            status = "работает посредственно";
        } else if (rate >= 2) {
            status = "профессионально непригоден";
        } else if (rate >= 1) {
            status = "мешает жить окружающим";
        } else {
            status = "нет оценки";
        }
    }

    return status;
}



function rating_init() {
    $(".rate_negative").click(rating_click);
    $(".rate_positive").click(rating_click);
}

// function ava_change_click(ev) {
//     var what, dir, i, idx, vars, vehicle;
//     what = $(this).parent().parent().attr('class').split(/\s+/);
//     what = what.pop();
//     vehicle = globus[current_vehicle_info];

//     if (what=="driver") {
//         vars=["001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011", "012", "013", "014", "015", "016", "017"];
//     } else if (what == "conductor") {
//         vars=["500", "501", "502", "503", "504", "505", "506", "507", "508", "002"];
//     }

//     dir = $(this).attr('class').split(/\s+/)[1];

//     idx =  $(".ava_"+what).attr('src').substr(20,3);
//     idx = vars.indexOf(idx);
//     if (dir == "fa-chevron-circle-right") {
//        if (idx < vars.length -1) {
//          idx += 1;
//        } else {
//         idx = 0;
//        }
//     } else {
//        if (idx > 1) {
//          idx -= 1;
//        } else {
//         idx = vars.length-1;
//        }
//     }
//     $(".ava_"+what).attr('src', '/static/img/ava/ava-'+vars[idx]+'.jpg');

//     var request = $.ajax({
//         url: "http://bustime.loc/ajax/ava_change/",
//         type: "post",
//         data: {
//             "what": what,
//             "g": vehicle['g'],
//             "u": current_vehicle_info,
//             "ava": vars[idx]
//         },
//         dataType: "json",
//         cache: false
//     });
// }
function word_to_number(word) {
    var d = trans_text_word_to_number;
    var number = "";
    if (word == d[0]) {
        number = 0;
    } else if (word == d[1]) {
        number = 1;
    } else if (word == d[2]) {
        number = 2;
    } else if (word == d[3]) {
        number = 3;
    } else if (word == d[4]) {
        number = 4;
    } else if (word == d[5]) {
        number = 5;
    } else if (word == d[6]) {
        number = 6;
    } else if (word == d[7]) {
        number = 7;
    } else if (word == d[8]) {
        number = 8;
    } else if (word == d[9]) {
        number = 9;
    }

    return number;
}

function recognition_init() {
    recognition_inited = 1;
    recognition = new webkitSpeechRecognition();
    // recognition.lang = "ru-RU";
    recognition.lang = language;
    // recognition.continuous = true;
    // recognition.interimResults = true;
    recognition.onstart = function(event) {
        flash_message(trans_text_recog, 0);
    };

    recognition.onresult = function(event) {
        // $('.flash_message').fadeOut('fast');
        for (var i = event.resultIndex; i < event.results.length; ++i) {
            var interim_transcript = '',
                parsed_num;
            if (event.results[i].isFinal) {
                recognition_result += event.results[i][0].transcript;
            } else {
                interim_transcript += event.results[i][0].transcript;
            }

            recognition_result = recognition_result.toLowerCase();
            var parsed = recognition_result.split(" ");
            var parse_fail = 0;
            var parsed_type = 0;
            // console.log(parsed[0]);

            if (parsed[0] == trans_ttype_name[0].toLowerCase()) {
                parsed_type = 0;
            } else if (parsed[0] == trans_ttype_name[1].toLowerCase()) {
                parsed_type = 1;
            } else if (parsed[0] == trans_ttype_name[2].toLowerCase()) {
                parsed_type = 2;
            } else if (parsed[0] == trans_ttype_name[3].toLowerCase()) {
                parsed_type = 3;
            } else if (parsed[0] == trans_ttype_name[5].toLowerCase()) {
                parsed_type = 5;
            } else {
                parse_fail = 1;
            }
            var nummy = parsed[parsed.length-1];
            parsed_num = parseInt(nummy, 10);
            if (!parsed_num) {
                parsed_num = word_to_number(nummy);
            }
            if (!parsed_num) {
                parse_fail = 1;
            }

            if (parse_fail) {
                flash_message(trans_text_recog_fail + ': ' + recognition_result, 1500);
            } else {
                var bus_id;
                for (var key in dbgetsafe('bus')) {
                    let bbus = dbget('bus', key, null, true);
                    if (bbus['name'] == parsed_num && bbus['ttype'] == parsed_type) {
                        bus_id = key;
                    }
                }
                if (!bus_id) {
                    flash_message(parsed[0] + " " + parsed_num + " " +  trans_text_not_found, 2500);
                    recognition_result = "";
                    return;
                }
                flash_message(parsed[0] + " " + parsed_num, 1000);
                show_me_the_bus(bus_id);
                ajax_metric("mic_dial", 1);
            }
            recognition_result = "";
        }
    };
}

function gosnum_recognition_init() {
    gosnum_recognition_inited = 1;
    gosnum_recognition = new webkitSpeechRecognition();
    gosnum_recognition.lang = "ru-RU";
    // recognition.continuous = true;
    // recognition.interimResults = true;
    gosnum_recognition.onstart = function(event) {
        flash_message(trans_text_recog_start, 1600);
        $("[name=gosnum]").focus();
    };

    gosnum_recognition.onresult = function(event) {
        var voice_msg;
        for (var i = event.resultIndex; i < event.results.length; ++i) {
            var interim_transcript = '',
                parsed_num;
            if (event.results[i].isFinal) {
                voice_msg = event.results[i][0].transcript;
            } else {
                interim_transcript += event.results[i][0].transcript;
            }

            // voice_msg = voice_msg.toLowerCase();
            // flash_message("Распознано: <b>" + voice_msg+"</b>", 800);
            console.log(voice_msg);
            ajax_metric("gosnum_by_voice", 1);
            $("[name=gosnum]").attr("type", "text").val(voice_msg);
        }
    };
}

function check_float64() {
    if (typeof Float64Array != 'function' && typeof Float64Array != 'object') {
        return 0;
    }
    return 1;
}

function update_counter_online_city_web(data) {
    var cur = $(".counter_online_сity").html();
    cur = parseInt(cur, 10);
    if (data > cur) {
      $(".counter_online_сity").addClass('bhlight_red');
    } else {
      $(".counter_online_сity").addClass('bhlight_grey');
    }
    $(".counter_online_сity").html(data);

    setTimeout(function() {
        $(".counter_online_сity").removeClass('bhlight_red').removeClass('bhlight_grey');
    }, 200);
}

function update_counter_online_city_app(data) {
    var cur = $(".counter_online").html();
    cur = parseInt(cur, 10);
    if (data > cur) {
      $(".counter_online").addClass('bhlight_red');
    } else {
      $(".counter_online").addClass('bhlight_grey');
    }
    $(".counter_online").html(data);

    setTimeout(function() {
        $(".counter_online").removeClass('bhlight_red').removeClass('bhlight_grey');
    }, 200);
}

function update_counter_today(data) {
    if (data > counter_today) {
      $(".counter_today").addClass('bhlight_red');
    } else {
      $(".counter_today").addClass('bhlight_grey');
    }
    $(".counter_today").html(data);
    counter_today = data;
    setTimeout(function() {
        $(".counter_today").removeClass('bhlight_red').removeClass('bhlight_grey');
    }, 800);
}

function update_counters_by_type(data) {
    var d0, d1, ttype, all_d, amount, mdir, bid, current_amount = 0;
    var current_counters_by_type = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0};

    if (Object.keys(current_inf_for_counters).length === 0) { // если информации о счетчиках нет
        for (var key in dbgetsafe('bus')) { // идем по каждому ТС города
            var busamounts = $(".bid_" + key).find(".busamount").html(); // достаем кол-во ТС на обоих направлениях
            if( busamounts ) {
                busamounts = busamounts.split(" / ");
                d0 = parseInt(busamounts[0], 10); // достаем кол-во ТС на 0 направлении
                d1 = parseInt(busamounts[1], 10); // достаем кол-во ТС на 1 направлении
                ttype = dbget('bus', key, 'ttype'); // записываем тип ТС
                all_d = d0 + d1; // считаем кол-во ТС на обоих направлениях

                current_inf_for_counters[key] = {'ttype': ttype, 'd0': d0, 'd1': d1, 'all_d': all_d}; // записываем всю информацию по ТС
                current_counters_by_type[ttype] += all_d; // суммируем ТС по типу
            }
        }

    } else { // если информация о счетчиках есть
        var ttype_for_update = [];
        for (var key in data) { // идем по пришедшим обновленным данным
            amount = parseInt(data[key], 10); // новое кол-во тс
            mdir = key.substring(key.length-2, key.length); // направление
            bid = key.replace("_d0", '').replace("_d1", '');
            bid = parseInt(bid, 10); // id автобуса с измененным кол-вом

            if (!ttype_for_update.includes(current_inf_for_counters[bid]["ttype"])) {
                ttype_for_update.push(current_inf_for_counters[bid]["ttype"]);
            }
            current_amount = current_inf_for_counters[bid][mdir]; //старое кол-во ТС в определенном направлении

            if (amount != current_amount) { // если новое не равно старому
                current_inf_for_counters[bid][mdir] = amount // записываем новое кол-во ТС
                current_inf_for_counters[bid]["all_d"] = current_inf_for_counters[bid]["d0"] + current_inf_for_counters[bid]["d1"]; // заново считаем общее кол-во тс на обоих направлениях
            }
        }
        for (var b_id in current_inf_for_counters) {
            current_counters_by_type[current_inf_for_counters[b_id]["ttype"]] += current_inf_for_counters[b_id]["all_d"]; // суммируем кол-во тс.
        }
        var bubu;
        for (var i = 0; i < ttype_for_update.length; i++) {
            bubu = '.counters_by_type__' + ttype_for_update[i];
            $(bubu).removeClass("orange").addClass('blue');
            $(bubu).html(current_counters_by_type[ttype_for_update[i]]);
        }
        setTimeout(function() {
            $("div[class *= 'counters_by_type__']").removeClass('blue').addClass("orange");
        }, 800);
    }
}

function update_status_counter(data) {
    // console.log(data);
    var key, cur, keys = [];
    for (key in data) {
        if (key === 'stat_replication') {
            data[key].forEach((stat_item, stat_index) => {
                stat_item.forEach((item, index) => {
                    let stat_key = "";
                    switch (index) {
                        case 0:
                            let ip = item;
                            stat_key = key+"_ip"+stat_index
                            cur = $("."+stat_key).html();
                            break;
                        case 1:
                            let status = item;
                            stat_key = key+"_status"+stat_index
                            cur = $("."+stat_key).html();
                            break;
                        case 2:
                            let write_lag = item;
                            stat_key = key+"_write_lag"+stat_index
                            cur = $("."+stat_key).html();
                            cur = parseFloat(cur);
                            break;
                        case 3:
                            let flush_lag = item;
                            stat_key = key+"_flush_lag"+stat_index
                            cur = $("."+stat_key).html();
                            cur = parseFloat(cur);
                            break;
                        case 4:
                            let replay_lag = item;
                            stat_key = key+"_replay_lag"+stat_index
                            cur = $("."+stat_key).html();
                            cur = parseFloat(cur);
                            break;
                        default:
                            return;
                    }
                    if (item != cur) {
                        $("."+stat_key).html(item).parent().removeClass('grey').addClass("red");
                    }
                });
            });
        } else if (key === 'redis') {
            Object.keys(data[key]).forEach(function(rkey) {
               $(".redis_"+rkey).html(data[key][rkey]).parent().removeClass('grey').addClass("red");
            });
        } else {
            cur = $("."+key).html();
            cur = parseInt(cur, 10);
            if (data[key] != cur) {
                $("."+key).html(data[key]).parent().removeClass('grey').addClass("red");
            }
        }
    }
    setTimeout(function() {
        $(".statistic").removeClass('red').addClass('grey');
    }, 600);
}

function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    let seconds = now.getSeconds();

    if (minutes < 10) {
        minutes = '0' + minutes;
    }

    if (hours < 10) {
        hours = '0' + hours;
    }

    if (seconds < 10) {
        seconds = '0' + seconds;
    }
    return `${hours}:${minutes}:${seconds}`;
}
function dictToString(data) {
    return Object.entries(data)
        .map(([key, value]) => `${key}=${value}`)
        .join(', ');
}
function update_status_log(data) {
    // console.log(data);
    if (!city_monitor_mode) {return}
    var target, i, key, cur, keys, log_pm, flag = [];
    let str = getCurrentTime() + ": " + dictToString(data);
    log_pm = $(".log").val().split("\n");
    log_pm.push(str);
    if (log_pm.length > 100) {
            log_pm.slice(10);
        }
    $(".log").val( log_pm.join("\n") );

    var psconsole = $('.log');
    if(psconsole.length)
       psconsole.scrollTop(psconsole[0].scrollHeight - psconsole.height());
}


function gps_send_signal(uid) {
    // console.log("gps_send_signal:"+uid);
    // var target = $("[vehicle_id="+uid+"] > .vcustom");
    let target = $("[vehicle_id="+uid+"]").find("i.fa-upload").parent();
    target.addClass('active_now');
    // var target2 = $("[vehicle_id="+uid+"]").find("img");
    let target2 = $("[vehicle_id="+uid+"]").find("img");
    let target3 = $("[map_vehicle_id="+uid+"]");
    target2.addClass('happy_scale');
    target3.addClass('happy_scale');
    setTimeout(function() {
        target.removeClass('active_now');
    }, 500);
    setTimeout(function() {
        target2.removeClass('happy_scale');
        target3.removeClass('happy_scale');
    }, 1000);
}


function update_reschedule(data) {
    if (!us_premium && !gps_send_enough) {
        return;
    }
    $(".schedule").css('display', 'block');
    $(".schedule_0").css('display', 'table');
    $(".schedule_1").css('display', 'table');
    var a = data[0];
    var b = data[1];
    if (a.length > 0) {
        $(".reschedule_0_1").html(a[0] + ", " + a[1])
        $(".reschedule_0_1").addClass('bhlight');
        setTimeout(function() {
            $(".reschedule_0_1").removeClass('bhlight');
        }, 400);
    } else {
        $(".reschedule_0_1").html("");
    }

    if (b.length > 0) {
        $(".reschedule_1_1").html(b[0] + ", " + b[1])
        $(".reschedule_1_1").addClass('bhlight');
        setTimeout(function() {
            $(".reschedule_1_1").removeClass('bhlight');
        }, 400);
    } else {
        $(".reschedule_1_1").html("");
    }
}


function route_lines_calc(bus_id){
    bus_id = BUS_ID || -1;
    $.ajax({
        type: "post",
        url: "/ajax/route_lines_calc/",
        data: {
            bus_id: bus_id,
            city_id: us_city
        },
        dataType: "json",
        cache: false,
        success: function(data) {
            if( data.result ){
                if(busstop_collection)
                    map_draw_stops();
            }
            else
                console.error(data.error || 'Неизвестная ошибка');
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error(errorThrown, textStatus);
        }
    });
}


function route_edit() {
    window.location.href = "/" + us_city_slug + "/" + BUS_ID + "/edit/";
}


function route_detector() {
    window.location.href = "/" + us_city_slug + "/" + get_bslug(BUS_ID) + "/detector/";
}


function route_monitor() {
    window.location.href = "/" + us_city_slug + "/" + get_bslug(BUS_ID) + "/monitor/";
}


function route_journal() {
    window.location.href = "/" + us_city_slug + "/transport/" + today_date + "/?bus_id="+BUS_ID;
}


function route_info() {
    window.location.href = "/wiki/bustime/bus/" + BUS_ID + "/change/";
}


function radio(data) {
    console.log('radio event');
    sound_radio_in.play();
    var path_base = "/static/sounds/radio/" + data['filename'];
    new Howl({
        src: [path_base + ".ogg", path_base + ".mp4"],
        volume: 0.8,
        onend: function() {
            sound_radio_out.play();
        },
        onloaderror: function() {
            console.log('onloaderror: ' + data['filename'])
        }
    }).play();
}


function blockAdblockUser() {
    /*
    if ($('.busnumber_container').length && $('.adsbygoogle').filter(':visible').length == 0) {
        ajax_metric("adblock", 1);
        //if (us_days_on > 14) {
            // alert(trans_text_adblock);
            // window.location.href = "/noadblock/";
            //ajax_metric("adblock_redirect", 1);
        //}
        console.log("У вас отключена реклама? Всем добра! :)");
    } else if ($('.adsbygoogle').filter(':hidden').length > 0) {
        console.log("У вас отключена реклама (hidden)? Всем добра! :)");
    }
    */
}

// function pixijs_load() {
//     PIXI = require('pixi');
//     var stage = new PIXI.Stage();
//     if ($("#pixi-canvas").width()> 500) {
//         $("#pixi-canvas").width(500);
//     }
//     var pixi_canvas_width = $("#pixi-canvas").width();
//     var pixi_canvas_height = $("#pixi-canvas").height();
//     var renderer = PIXI.autoDetectRenderer(pixi_canvas_width, pixi_canvas_height,
//         {transparent:true, view:document.getElementById("pixi-canvas"),  antialias : true}
//     );

//     // stage.interactive = true;

//     var bg = PIXI.Sprite.fromImage("/static/img/pixi/BGrotate.jpg");
//     bg.anchor.x = 0.5;
//     bg.anchor.y = 0.5;
//     bg.position.x = 620 / 2;
//     bg.position.y = 380 / 2;
//     stage.addChild(bg);
//     // bg.alpha=0.5;

//     var container = new PIXI.DisplayObjectContainer();
//     container.position.x = pixi_canvas_width/2;
//     container.position.y = pixi_canvas_height/2-25;

//     var light2 = PIXI.Sprite.fromImage("/static/img/pixi/LightRotate2.png");
//     light2.anchor.x = 0.5;
//     light2.anchor.y = 0.5;
//     container.addChild(light2);

//     var light1 = PIXI.Sprite.fromImage("/static/img/pixi/LightRotate1.png");
//     light1.anchor.x = 0.5;
//     light1.anchor.y = 0.5;
//     container.addChild(light1);

//     var panda =  PIXI.Sprite.fromImage("/static/img/bustime-2.0.png");
//     panda.anchor.x = 0.5;
//     panda.anchor.y = 0.5;
//     container.addChild(panda);

//     var ten =  PIXI.Sprite.fromImage("/static/img/pixi/10000.png");
//     ten.anchor.x = 0.5;
//     ten.anchor.y = 0.5;
//     ten.y += 85;
//     container.addChild(ten);

//     stage.addChild(container);

//     var count = 0;
//     requestAnimFrame(animate);

//     function animate() {
//         bg.rotation += 0.005;

//         light1.rotation += 0.02;
//         light2.rotation -= 0.01;

//         panda.scale.x = 1 + Math.sin(count) * 0.04;
//         panda.scale.y = 1 + Math.cos(count) * 0.04;

//         ten.scale.x = 1 + Math.sin(count*2) * 0.03;
//         ten.scale.y = 1 + Math.cos(count*2) * 0.03;

//         count += 0.1;
//         renderer.render(stage);
//         requestAnimFrame(animate);
//     }

// }





// function running_light() {
//     $(".lightdown").removeClass('lightdown').removeClass('lightup');
//     $(".lightup").addClass('lightdown');
//     $(".forlightup"+running_light_cnt%4).addClass('lightup');
//     running_light_cnt++;

//     setTimeout(function() {
//         running_light();
//     }, 500);
// }









/* phaser stuff*/
/*************** phaser stuff ****************/
/* phaser stuff*/

function ny_preload() {
    game.load.spritesheet('snowflakes', '/static/img/snowflakes.png', 17, 17);
    game.load.spritesheet('snowflakes_large', '/static/img/snowflakes_large.png', 64, 64);
}

var ny_max = 0;
var front_emitter;
var mid_emitter;
var back_emitter;
var update_interval = 4 * 60;
var ny_i = 0;

function ny_create() {
    back_emitter = game.add.emitter(game.world.centerX, -32, 300);
    back_emitter.makeParticles('snowflakes', [0, 1, 2, 3, 4, 5]);
    back_emitter.maxParticleScale = 0.6;
    back_emitter.minParticleScale = 0.2;
    back_emitter.setYSpeed(20, 100);
    back_emitter.gravity = 0;
    back_emitter.width = game.world.width * 1.5;
    back_emitter.minRotation = 0;
    back_emitter.maxRotation = 40;

    mid_emitter = game.add.emitter(game.world.centerX, -32, 120);
    mid_emitter.makeParticles('snowflakes', [0, 1, 2, 3, 4, 5]);
    mid_emitter.maxParticleScale = 1.2;
    mid_emitter.minParticleScale = 0.8;
    mid_emitter.setYSpeed(50, 150);
    mid_emitter.gravity = 0;
    mid_emitter.width = game.world.width * 1.5;
    mid_emitter.minRotation = 0;
    mid_emitter.maxRotation = 40;

    front_emitter = game.add.emitter(game.world.centerX, -32, 25);
    front_emitter.makeParticles('snowflakes_large', [0, 1, 2, 3, 4, 5]);
    front_emitter.maxParticleScale = 0.75;
    front_emitter.minParticleScale = 0.25;
    front_emitter.setYSpeed(100, 200);
    front_emitter.gravity = 0;
    front_emitter.width = game.world.width * 1.5;
    front_emitter.minRotation = 0;
    front_emitter.maxRotation = 40;

    changeWindDirection();

    back_emitter.start(false, 14000, 20);
    mid_emitter.start(false, 12000, 40);
    front_emitter.start(false, 6000, 1000);

}

function update() {

    ny_i++;

    if (ny_i === update_interval)
    {
        changeWindDirection();
        update_interval = Math.floor(Math.random() * 20) * 60; // 0 - 20sec @ 60fps
        ny_i = 0;
    }

}

function changeWindDirection() {

    var multi = Math.floor((ny_max + 200) / 4),
        frag = (Math.floor(Math.random() * 100) - multi);
    ny_max = ny_max + frag;

    if (ny_max > 200) ny_max = 150;
    if (ny_max < -200) ny_max = -150;

    setXSpeed(back_emitter, ny_max);
    setXSpeed(mid_emitter, ny_max);
    setXSpeed(front_emitter, ny_max);

}

function setXSpeed(emitter, ny_max) {
    emitter.setXSpeed(ny_max - 20, ny_max);
    emitter.forEachAlive(setParticleXSpeed, this, ny_max);
}

function setParticleXSpeed(particle, ny_max) {
    particle.body.velocity.x = ny_max - Math.floor(Math.random() * 30);
}

// leaflet full screen
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        // AMD
        define(['leaflet'], factory);
    } else if (typeof module !== 'undefined') {
        // Node/CommonJS
        module.exports = factory(require('leaflet'));
    } else {
        // Browser globals
        if (typeof window.L === 'undefined') {
            throw new Error('Leaflet must be loaded first');
        }
        factory(window.L);
    }
}(function (L) {
    L.Control.Fullscreen = L.Control.extend({
        options: {
            position: 'topleft',
            title: {
                'false': 'View Fullscreen',
                'true': 'Exit Fullscreen'
            }
        },

        onAdd: function (map) {
            var container = L.DomUtil.create('div', 'leaflet-control-fullscreen leaflet-bar leaflet-control');

            this.link = L.DomUtil.create('a', 'leaflet-control-fullscreen-button leaflet-bar-part', container);
            this.link.href = '#';

            this._map = map;
            this._map.on('fullscreenchange', this._toggleTitle, this);
            this._toggleTitle();

            L.DomEvent.on(this.link, 'click', this._click, this);

            return container;
        },

        _click: function (e) {
            L.DomEvent.stopPropagation(e);
            L.DomEvent.preventDefault(e);
            this._map.toggleFullscreen(this.options);
        },

        _toggleTitle: function() {
            this.link.title = this.options.title[this._map.isFullscreen()];
        }
    });

    // MapLibre GL JS does not handle RTL text by default, so we recommend adding this dependency to fully support RTL rendering.
    //maplibregl.setRTLTextPlugin('https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-rtl-text/v0.2.1/mapbox-gl-rtl-text.js');

    L.Map.include({
        isFullscreen: function () {
            return this._isFullscreen || false;
        },

        toggleFullscreen: function (options) {
            var container = this.getContainer();
            if (this.isFullscreen()) {
                if (options && options.pseudoFullscreen) {
                    this._disablePseudoFullscreen(container);
                } else if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    document.webkitCancelFullScreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                } else {
                    this._disablePseudoFullscreen(container);
                }
            } else {
                if (options && options.pseudoFullscreen) {
                    this._enablePseudoFullscreen(container);
                } else if (container.requestFullscreen) {
                    container.requestFullscreen();
                } else if (container.mozRequestFullScreen) {
                    container.mozRequestFullScreen();
                } else if (container.webkitRequestFullscreen) {
                    container.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                } else if (container.msRequestFullscreen) {
                    container.msRequestFullscreen();
                } else {
                    this._enablePseudoFullscreen(container);
                }
            }

        },

        _enablePseudoFullscreen: function (container) {
            L.DomUtil.addClass(container, 'leaflet-pseudo-fullscreen');
            this._setFullscreen(true);
            this.fire('fullscreenchange');
        },

        _disablePseudoFullscreen: function (container) {
            L.DomUtil.removeClass(container, 'leaflet-pseudo-fullscreen');
            this._setFullscreen(false);
            this.fire('fullscreenchange');
        },

        _setFullscreen: function(fullscreen) {
            this._isFullscreen = fullscreen;
            var container = this.getContainer();
            if (fullscreen) {
                L.DomUtil.addClass(container, 'leaflet-fullscreen-on');
            } else {
                L.DomUtil.removeClass(container, 'leaflet-fullscreen-on');
            }
            this.invalidateSize();
        },

        _onFullscreenChange: function (e) {
            var fullscreenElement =
                document.fullscreenElement ||
                document.mozFullScreenElement ||
                document.webkitFullscreenElement ||
                document.msFullscreenElement;

            if (fullscreenElement === this.getContainer() && !this._isFullscreen) {
                this._setFullscreen(true);
                this.fire('fullscreenchange');
            } else if (fullscreenElement !== this.getContainer() && this._isFullscreen) {
                this._setFullscreen(false);
                this.fire('fullscreenchange');
            }
        }
    });

    L.Map.mergeOptions({
        fullscreenControl: false
    });

    L.Map.addInitHook(function () {
        if (this.options.fullscreenControl) {
            this.fullscreenControl = new L.Control.Fullscreen(this.options.fullscreenControl);
            this.addControl(this.fullscreenControl);
        }

        var fullscreenchange;

        if ('onfullscreenchange' in document) {
            fullscreenchange = 'fullscreenchange';
        } else if ('onmozfullscreenchange' in document) {
            fullscreenchange = 'mozfullscreenchange';
        } else if ('onwebkitfullscreenchange' in document) {
            fullscreenchange = 'webkitfullscreenchange';
        } else if ('onmsfullscreenchange' in document) {
            fullscreenchange = 'MSFullscreenChange';
        }

        if (fullscreenchange) {
            var onFullscreenChange = L.bind(this._onFullscreenChange, this);

            this.whenReady(function () {
                L.DomEvent.on(document, fullscreenchange, onFullscreenChange);
            });

            this.on('unload', function () {
                L.DomEvent.off(document, fullscreenchange, onFullscreenChange);
            });
        }
    });

    L.control.fullscreen = function (options) {
        return new L.Control.Fullscreen(options);
    };
}));


// пассажир создаёт или отменяет заказ (нажимает Голосовать, order_inputs.html)
function set_order(){
    if( taxiuser.gps_on ){
        order_delete();
    }
    else {
        order_create();
    }
}   // set_order


// пассажир создаёт заказ (нажимает Голосовать, order_inputs.html)
function order_create(){
    if( test_mode ){
        console.log('order_create');
    }

    $("#taxiuser_passenger_start_stop").prop("disabled", true);
    // таксист после поиска маршрута имеет 2 кнопки: и Голосовать и Подвозить,
    // если начал подвозить, то кнопки Голосовать нет (так как переходит на /taxi/vote/),
    // а если начал голосовать, то отключить возможность подвозить:
    $("#taxiuser_driver_start_stop").hide();    // кнопка Начать подвозить на главной странице (bistime/templates/index.html)
    $(".driver.item").children(".ui.button").addClass("disabled");   // таб Подвезти на главной странице (bistime/templates/from-to4.html)
    $("#taxiuser_driver_start_stop2").prop("disabled", true); // кнопка Начать подвозить в табе Подвезти (карточка водителя)(taxi/templates/driver_card.html)

    let data = {
            'passengers': $('#passengers').val(),
            'price': $('#price').val(),
            'note': $('#note').val(),
            //'taxi_path': (taxi_path ? JSON.stringify(taxi_path) : Cookies.get('taxi_path')),
            'taxi_path': (window.taxi_path ? JSON.stringify(window.taxi_path) : JSON.stringify('{}')),
        };

    $.ajax({
        url: "/carpool/api/order/create/",
        method: "POST",
        headers: {'X-CSRFToken': Cookies.get('csrftoken')},
        data: data
    })
    .done(function(data) {
        if( test_mode ){
            console.log('order_create.done, data=', data);
        }
        if( !data.error ){
            taxiuser = Object.assign(data.result.passenger);
            Cookies.set('taxi_user', JSON.stringify(taxiuser), { path: '/', sameSite: 'lax', expires: Infinity });
            start_location_service();   // включит GPS по флагу taxiuser.gps_on = true

            $("#taxiuser_passenger_start_stop").html("Прекратить голосовать");  // order_inputs.html
            $("#taxiuser_passenger_start_stop").css('background-color', '#EF3905');
            $("#taxiuser_passenger_start_stop").css('color', 'white');
            $("#pass_message1").hide(); // Введите откуда и куда, чтобы поиск сработал, index.html
            $("#taxi_order_params .ui.input").addClass("disabled");    // Параметры заказа: число пассажиров, стоимость..., order_inputs.html
            $("#div_wait_iffers").show(); // Ожидаем предложений от водителей, order_inputs.html
            $("#header_offers").show();
        }   // if( !data.error )
        else {
            $("#modal_dialog p").html(data.error);
            $('#modal_dialog').modal();
        }   // else if( !data.error )

        $("#taxiuser_passenger_start_stop").prop("disabled", false);
    })  // done
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.log("order_create, error:", errorThrown);
        $("#taxiuser_passenger_start_stop").prop("disabled", false);
    });
}   // order_create


// пассажир удаляет заказ (нажимает Прекратить голосовать, order_inputs.html)
function order_delete(){
    if( test_mode ){
        console.log('order_delete', taxiuser.order_id);
    }

    $("#taxiuser_passenger_start_stop").prop("disabled", true);
    // см. комментарии в order_create():
    $("#taxiuser_driver_start_stop").show();
    $(".driver.item").children(".ui.button").removeClass("disabled");
    $("#taxiuser_driver_start_stop2").prop("disabled", false);

    let data = {
            'order_id': taxiuser.order_id ? taxiuser.order_id : -1, // если заказ не найден, удалим все незаконченные для юзера
        };

    $.ajax({
        url: "/carpool/api/order/delete/",
        method: "POST",
        headers: {'X-CSRFToken': Cookies.get('csrftoken')},
        data: data
    })
    .done(function(data) {
        //console.log('order_delete, done', JSON.stringify(data.result));
        if( !data.error ){
            taxiuser = taxiuser = Object.assign(data.result.passenger);
            Cookies.set('taxi_user', JSON.stringify(taxiuser), { path: '/', sameSite: 'lax', expires: Infinity });
            start_location_service();   // выключит GPS по флагу taxiuser.gps_on = false

            $("#taxiuser_passenger_start_stop").html("Голосовать"); // order_inputs.html
            $("#taxiuser_passenger_start_stop").css('background-color', '#FFDF32');
            $("#taxiuser_passenger_start_stop").css('color', 'black');
            if( !taxi_path )
                $("#pass_message1").show(); // Введите откуда и куда, чтобы поиск сработал, index.html
            $("#taxi_order_params .ui.input").removeClass("disabled");  // Параметры заказа: число пассажиров, стоимость..., order_inputs.html
            $("#div_wait_iffers").hide(); // Ожидаем предложений от водителей, order_inputs.html

            // очистить список Хотят подвезти (order_inputs.html)
            $("#header_offers").hide();
            $("#offers").empty();

            $("#taxiuser_passenger_start_stop").prop("disabled", false);
        }   // if( !data.error )
        else {
            $("#modal_dialog p").html(data.error);
            $('#modal_dialog').modal();
        }   // else if( !data.error )
    })  // done
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.log("order_delete, error:", errorThrown);
        $("#taxiuser_passenger_start_stop").prop("disabled", false);
    });
}   // order_delete


// обработка действий водителя
// обработка действий пассажира в order_create() и order_delete()
function set_taxi_user(who){
    //console.log(`set_taxi_user(${who})`);

    $("#taxiuser_driver_start_stop").prop("disabled", true);
    let csrftoken = Cookies.get('csrftoken');
    let data = {
            'who': who,
            'active': (taxiuser.gps_on ? 0 : 1), // переключить состояние на противоположное
        };

    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/setuser/",
        data: data,
    })
    .done(function(data) {
        //console.log(`set_taxi_user:done, data=`, data);
        if( !data.error ){
            taxiuser = Object.assign(data.result);
            Cookies.set('taxi_user', JSON.stringify(taxiuser), { path: '/', sameSite: 'lax', expires: Infinity });
            $("#taxiuser_driver_start_stop").prop("disabled", false);
            start_location_service();

            if(taxiuser.car_count){
                // может быть водителем (таксистом)
                $("#taxiuser_driver_start_stop").html(taxiuser.gps_on ? "Прекратить подвозить" : "Начать подвозить");
                window.location.hash = '';
                if(taxiuser.gps_on){
                    $("#taxiuser_driver_start_stop").css('background-color', '#EF3905');
                    $("#pass_message1").hide(); // Надпись Если вы хотите, чтобы вас подвезли
                    // активировать страницу/вкладку с заказами пассажиров
                    if( window.location.pathname != "/carpool/votes/" ){
                        window.location.href = "/carpool/votes/";
                    }
                }
                else {
                    if( window.location.pathname == "/carpool/votes/" ) {
                        window.location.href = "/#carpool";
                    }
                    else {
                        $("#pass_message1").show();
                    }
                }
            }   // if(taxiuser.car_count)
        }   // if( !data.error )
        else {
            $("#modal_dialog p").html(data.error);
            $('#modal_dialog').modal();
        }   // else if( !data.error )
    })  // done
    .fail(function(jqXHR, textStatus, errorThrown) {
        $("#taxiuser_driver_start_stop").prop("disabled", false);
        console.log("set_taxi_user error:", errorThrown);
    });
}   // set_taxi_user


// вызывается из router() когда веб-сокет получает сообщение с тегом taxi
function taxi_event(event){
    //console.log('taxi_event event', event);
    let data = JSON.parse(event.data);
    //console.log('taxi_event data', data);
    switch(event.event){
        case 'car_add': {
            //console.log('taxi_event car_add', data[0]);
            // появилось новое такси (водитель нажал Начать подвозить)
            // добавляем машину (taxi_item.html) в список машин такси (bustime/templates/index.html)
            if(event.html && $("#taxi_grid").find(`#taxi_${data[0].id}`).length == 0 ){
                $("#taxi_grid").append(event.html);
            }
            break;
        }
        case 'car_del': {
            //console.log('taxi_event car_del', data);
            // такси перестало работать (водитель нажал Закончить подвозить (или взял заказ?))
            // удаляем машину из списка машин такси (bustime/templates/index.html)
            if(data && data.length){
                data.forEach(function(item) {
                    if(item){
                        let child = $("#taxi_grid").children(`#taxi_${item.id}`);
                        if(child){
                            $(child).remove();
                        }
                    }
                });
            }   // if(data.length)
            break;
        }
        case 'passenger': {
            //console.log('taxi_event passenger', data);
            // координаты пассажира, формируется в bustime.views.py.ajax_stops_by_gps(), в которую попадает из местной usePosition()
            // периодичность 30 сек.
            // data = {user_id:108660, lon:20.46448, lat:54.72435, timestamp:1651308669703, taxi_order:272}, user_id - bustime user.id
            // обновляем карты
            if( taxiuser.driver ){
                // водитель, order_map_update() в orders.html
                if (data.taxi_order && typeof order_map_update !== "undefined") {
                    order_map_update(data.taxi_order, null, [data.lat, data.lon]);   // in orders.html
                }
            }   // if( taxiuser.driver )
            else if( taxiuser.user == data.user_id ){
                // обновляется позиция пассажира на карте, taxi_map_set_marker() ниже
                taxi_map_set_marker(taxi_maps[data.user_id], 'passenger_marker', data.lat, data.lon, 'icon_p_24.png');
                taxi_fresh_map(data.user_id, data.lat, data.lon);
            }   // else if( taxiuser.driver )
            break;
        }
        case 'cars': {
            //console.log('taxi_event cars, data=', data);
            // список работающих такси с координатами и всеми параметрами
            // эвент формируется в bustime.update_lib.analyze_events() на основе кэша "tevents_%s" % city.id
            // в кэш попадает в bustime.inject_events.inject_custom() if data.get('taxi')

            // обновляем индикаторы кол-ва такси
            $(".counters_by_type__8").html(data.length);    // это на кнопке Попутки, на главной странице (index.html)
            $("#counters_by_type__8").html(data.length);    // это на табе X мин. (from_to4.html)
            // обновляем карты
            if( taxiuser.driver ){
                // водитель, карта и управление в orders.html и order_item.html
                if (typeof order_map_update !== "undefined") {
                    for(let i = 0; i < data.length; i++){
                        if( taxiuser.user == data[i].taxi.user ){
                            // это машина текущего юзера, индекс в taxi_maps по ID заказа, отправляем null, пусть ищет все свои заказы
                            order_map_update(null, [data[i].y, data[i].x], null);   // in orders.html
                            break;
                        }
                    }
                }
            }   // if( taxiuser.driver )
            else {
                // пассажир, карта и управление в trip_item_pass.html
                if( taxi_maps[taxiuser.user] ){
                    for(let i = 0; i < data.length; i++){
                        if( taxi_maps[taxiuser.user].car_id == data[i].taxi.car.id ){
                            // это машина заказа текущего юзера, индекс в taxi_maps по ID пассажира
                            taxi_map_set_marker(taxi_maps[taxiuser.user], 'car_marker', data[i].y, data[i].x, 'icon_d_24.png', 'blinking');
                            taxi_fresh_map(taxiuser.user, data[i].y, data[i].x);
                            taxi_fresh_pass_car_distance(data[i].y, data[i].x);
                            break;
                        }
                    }
                }   // if( taxi_maps[taxiuser.user] )
                else {
                    // обновить расстояние от меня до каждой из машин в списке машин такси div id="taxi_grid" (index.html)
                    let taxi_grid = $("#taxi_grid");
                    if( to_send && to_send.lat && taxi_grid && taxi_grid.is(":visible") ) {
                        data.forEach(function(item) {
                            if(item && item.y){
                                let child = $(`#taxi_${item.taxi.id}_distance`);
                                if(child){
                                    let dist = distance(item.y, item.x, to_send.lat, to_send.lon);
                                    child.html(
                                        '~ ' + (dist.distance / 1000).toFixed(1) + ' км.'
                                    );
                                }
                            }   // if(item)
                        });
                    }   // if( taxi_grid && taxi_grid.is(":visible") )
                }   // else if( taxi_maps[taxiuser.user] )
            }   // else if( taxiuser.driver )
            break;
        }
        case 'order_add': {
            console.log('taxi_event order_add', data);
            // появился заказ (пассажир нажал Начать голосовать)
            // data - [order, ...]
            if( taxiuser.driver && taxiuser.gps_on ){
                // добавляем заказ (order_item.html) в список голосующих пассажиров (orders.html)
                if(event.html){
                    $("#order_grid").append(event.html);
                    taxiPlay("order_new");
                }
                // рассчитываем расстояние до пассажира, near_distance in taxi/orders.html
                if(to_send && to_send.lat && to_send.lon && typeof near_distance != 'undefined'){
                    data.forEach(function(order) {
                        if(order && order.wf_point){
                            let xy = Point2XY(order.wf_point);
                            if( xy ){
                                let dis = distance(to_send.lat, to_send.lon, xy.lat, xy.lon);
                                if( dis.distance <= near_distance ){
                                    // если расстояние до пассажира менее near_distance (см. taxi.views.votes()),
                                    // увеличиваем счетчик Пассажиров поблизости (см. taxi/orders.html)
                                    let cnt = parseInt($("#passengers_near").html() || '0');
                                    $("#passengers_near").html( 1 + cnt );
                                }
                            }
                        }   // if(order && order.wf_point)
                    }); // data.forEach(function(order)
                }
            }   // if( taxiuser.driver && taxiuser.gps_on )
            break;
        }
        case 'order_del': {
            console.log('taxi_event order_del', data);
            // исчез заказ (пассажир нажал Закончить голосовать)
            // data - [order, ...]
            if(data && data.length){
                data.forEach(function(order) {
                    if(order){
                        // удаляем заказ из списка голосующих пассажиров (orders.html)
                        order_remove_from_grid(order);
                        // рассчитываем расстояние до пассажира, near_distance in taxi/orders.html
                        if(to_send && to_send.lat && to_send.lon && typeof near_distance != 'undefined'){
                            if(order.wf_point){
                                let xy = Point2XY(order.wf_point);
                                if( xy ){
                                    let dis = distance(to_send.lat, to_send.lon, xy.lat, xy.lon);
                                    if( dis.distance <= near_distance ){
                                        // если расстояние до пассажира менее near_distance (см. taxi.views.votes()),
                                        // уменьшаем счетчик Пассажиров поблизости (см. taxi/orders.html)
                                        let cnt = parseInt($("#passengers_near").html() || '0');
                                        if( cnt > 0 ){
                                            $("#passengers_near").html( cnt - 1 );
                                        }
                                    }
                                }
                            }   // if(order.wf_point)
                        }
                    }   // if(order)
                }); // data.forEach(function(order)

                if( taxiuser.driver && taxiuser.gps_on ){
                    taxiPlay("order_del");
                }
            }   // if(data.length)
            break;
        }
        case 'order_start': {
            console.log('taxi_event order_start', data);
            // пассажир нажал Выбрать на предожении водителя
            // data - заказ (order)
            if( data.taxist ){
                // элементы управления таксиста находятся на странице order_item.html
                if( data.taxist.user == taxiuser.user ){
                    // я - выбранный таксист
                    taxiuser['order_id'] = data.id;
                    // остановить таймер таймаута оффера (см. orders.html, set_offer(){ startTimerWait() })
                    if (taxi_driver_timeouts != 'undefined' && data.id in taxi_driver_timeouts){
                        clearTimeout( taxi_driver_timeouts[data.id] );
                        delete taxi_driver_timeouts[data.id];
                    }
                    // сделать заказ первым в списке:
                    let column = $(`#order_${data.id}`);
                    $(column).remove();
                    $("#order_grid").prepend($(column));
                    // обновить элементы заказа:
                    //$(`#offer_enabled_${data.id}`).html('Пассажир принял ваше предложение и ожидает вас');    // вероятно, не нужно?
                    $(`#offer_enabled_${data.id}`).hide();
                    $(`#btn_passenger_sel_${data.id}`).show();  // кнопка Пассажир сел
                    // желтая рамка заказа
                    /* не работает ни в каком варианте
                    $(`#order_${data.id}_item`).css("border", "2px solid #FFDF32 !important");
                    $(`#order_${data.id}_item`).css({"border": "2px solid #FFDF32 !important"});
                    $(`#order_${data.id}_item`).css({"border-color": "#FFDF32 !important", "border-style": "solid !important", "border-width": "2px !important"});
                    так работает: */
                    $(`#order_${data.id}_item`).attr("style", "border: 2px solid #FFDF32 !important");

                    taxiPlay("offer_accept");
                    // инициализировать карту заказа
                    order_map_init(data);
                }   // if( data.taxist.user == taxiuser.user )
                else {
                    // я - НЕ выбранный таксист (пассажир выбрал другого)
                    // удаляем заказ из списка голосующих пассажиров (orders.html)
                    order_remove_from_grid(data);
                }
            }   // if( data.taxist )
            break;
        }
        case 'order_close': {
            console.log('taxi_event order_close', data);
            // пассажир нажал Оценить поездку
            // data - заказ (order)
            // обрабатывать только если order.taxist.user == taxiuser.user
            if( data.taxist && data.taxist.user == taxiuser.user ){
                if( data.trip_status > 0 && data.trip_status == 6 ){    // Отказ пассажира
                    // элементы управления таксиста находятся на странице order_item.html
                    if (typeof order_trip_cancel !== "undefined") {  // order_trip_cancel() in orders.html
                        order_trip_cancel('passenger', data.id);
                    }
                }
            }   // if( data.taxist...
            break;
        }
        case 'trip_start': {
            console.log('taxi_event trip_start', data);
            // пассажир нажал Поездка начата (trip_item_pass.html) или водитель нажал Пассажир сел (order_item.html)
            // data - заказ (order)
            if( data.taxist && data.taxist.user == taxiuser.user ){
                // я таксист, мне сообщение
                // TODO: что сделать?
            }
            else if( data.passenger && data.passenger.user == taxiuser.user ){
                // я пассажир, мне сообщение
                // TODO: убрать кнопку Вижу автомобиль? показать что либо?
            }
            break;
        }
        case 'chat': {
            console.log('taxi_event chat', data);
            // просто сообщение отк гого-то кому-то (чат)
            // отправляется taxi_send_message_to_user() ниже
            // data={ from: 108660, to: 12, msg: "Вижу автомобиль", order_id: 293 }
            if( taxiuser.user == data.to ){ // это мне сообщение?
                if (typeof taxi_receive_message !== "undefined") {  // taxi_receive_message() in orders.html
                    taxi_receive_message(data);
                }
            }   // if( taxiuser.user == data.to )
            break;
        }
        case 'offer_add': {
            console.log('taxi_event offer_add', data);
            // появилось новое предложение водителя на заказ (водитель нажал Предложить на заказе (order_item.html))
            $("#div_wait_iffers").hide();
            // data - [offers], offer={order:{...}, taxi:{...}, timestamp}
            // добавляем машину (taxi_item.html) в список машин Хотят подвезти (order_inputs.html)
            data.forEach((offer) => {
                if( offer.order.passenger.user == taxiuser.user ){
                    if(event.html){
                        $("#offers").append(event.html);
                        taxiPlay("offer_new");
                    }
                }
            });
            break;
        }
        case 'offer_del': {
            console.log('taxi_event offer_del', data);
            // водитель отозвал своё предложение на заказ (водитель нажал Отказать на заказе (order_item.html))
            // data - [offers], offer={order:{...}, taxi:{...}, timestamp}
            if(data.length){
                data.forEach((offer) => {
                    if(offer && offer.order.passenger.user == taxiuser.user && offer.taxi){
                        // удаляем машину из списка машин Хотят подвезти (order_inputs.html)
                        let child = $("#offers").children(`#taxi_${offer.taxi.user}`);
                        if(child){
                            $(child).remove();
                        }

                        // клиенту, который уже успел согласиться на предложение присылаем отказ
                        if( typeof order_trip_cancel === "function" ){
                            // у клиента в это время работает страница trip_item_pass.html
                            console.log('Отказ водителя от заказа');
                            order_trip_cancel('driver', offer.order.id);   // in trip_item_pass.html
                        }
                    }   // if(offer && offer.taxi)
                }); // data.forEach

                if( $("#offers").children().length == 0 ){
                    $("#div_wait_iffers").show();
                }
            }   // if(data.length)
            break;
        }
    }   // switch(event.event)
}   // taxi_event


// удаление заказа из списка заказов (голосующих пассажиров) таксиста (orders.html)
function order_remove_from_grid(order){
    let child = $("#order_grid").children(`#order_${order.id}`);
    if(child){
        $(child).remove();
        Cookies.remove(`order_tout_${order.id}`, { path: '/taxi'});
    }
}   // order_remove_from_grid

// пассажир нажал кнопку Выбрать на предложение водителя (offer_item.html)
// т.е. это начало поездки водителя к пассажиру на заказ
function take_offer(taxi_id){
    console.log('take_offer', taxi_id, taxiuser);

    if( !taxiuser.order_id ){
        $("#modal_dialog p").html('Нет заказа');
        $('#modal_dialog').modal();
        return false;
    }
    else if( !taxi_id ){
        $("#modal_dialog p").html('Нет предложения для поездки');
        $('#modal_dialog').modal();
        return false;
    }

    let csrftoken = Cookies.get('csrftoken');
    let data = {
        'taxi_id': taxi_id,
        'order_id': taxiuser.order_id,
    };

    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/order/start/",   // начало поезки водителя на заказ, см. api.py order_start(), order.trip_status = 1 (Такси выехало к пассажиру)
        data: data,
    })
    .done(function(data) {
        // data - order
        if( !data.error ){
            console.log('take_offer done', data.result.order);
            if( data.result.html ){
                $("#search_result").html(data.result.html); // <= trip_item_pass.html
                pass_map_init(data.result.order.id, data.result.order.car.id);
            }
        }   // if( !data.error )
        else {
            $("#modal_dialog p").html(data.error);
            $('#modal_dialog').modal();
        }   // else if( !data.error )
    })  // done
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.log("take_offer error:", errorThrown);
    });
}   // take_offer


// расчет и обновление в trip_item_pass.html расстояния и времени до машины
function taxi_fresh_pass_car_distance(car_lat, car_lon){
    ///console.log('taxi_fresh_pass_car_distance', car_lat, car_lon, to_send.lat, to_send.lon);
    if( taxiuser.order_id ){
        let dist = distance(parseFloat(to_send.lat), parseFloat(to_send.lon), parseFloat(car_lat), parseFloat(car_lon));
        dist = dist.distance / 1000;

        let dom_element = $(`#order_${taxiuser.order_id}_distance`);
        if( dom_element ){
            $(dom_element).html(dist.toFixed(1) + ' км.');
        }

        dom_element = $(`#order_${taxiuser.order_id}_time`);
        if( dom_element ){
            let t = Math.ceil(dist / 40 * 1.3 * 3600);  // сек
            let h = Math.floor(t / 3600);
            let m = Math.floor(t % 3600 / 60);
            let s = t - (h * 3600 + m * 60);
            h = (h < 10 ? '0' : '') + h;
            m = (m < 10 ? '0' : '') + m;
            s = (h < 10 ? '0' : '') + s;
            if( parseInt(h) > 0 ){
                $(dom_element).html(`${h}:${m}:${s}`);
            }
            else {
                $(dom_element).html(`${m}:${s}`);
            }
        }
    }   // if( taxiuser.order_id )
}   // taxi_fresh_pass_car_distance


// создание макера на карте
function taxi_map_set_marker(map_obj, marker_type, lat, lon, icon, class_name){
    if( map_obj && marker_type && lat && lon ){
        if( !map_obj[marker_type] ){
            map_obj[marker_type] = L.marker([parseFloat(lat), parseFloat(lon)]);
            if( icon ){
                map_obj[marker_type].setIcon(L.icon({
                            iconUrl: `/static/taxi/img/${icon}`,
                            iconSize:     [24, 24], // size of the icon
                            iconAnchor:   [12, 12], // point of the icon which will correspond to marker's location
                            className: class_name,  // https://stackoverflow.com/questions/41884070/how-to-make-markers-in-leaflet-blinking
                        }));
            }
            map_obj[marker_type].addTo(map_obj.vlayer);
        }
        else {
            map_obj[marker_type].setLatLng([parseFloat(lat), parseFloat(lon)]);
        }
    }
}   // order_map_set_marker


// масштабирование или перелёт карты
function taxi_fresh_map(taxi_maps_index, lat, lon){
    if( taxi_maps_index in taxi_maps ){
        if( taxi_maps[taxi_maps_index].car_marker && taxi_maps[taxi_maps_index].passenger_marker) {
            map_boundsto(taxi_maps[taxi_maps_index].map, taxi_maps[taxi_maps_index].vlayer);
        }
        else if(lat && lon) {
            taxi_maps[taxi_maps_index].map.panTo([parseFloat(lat), parseFloat(lon)]);
        }
    }
}   // taxi_fresh_map


// инициализация карты пассажира
function pass_map_init(order_id, car_id){
    if( $(`order_${order_id}_map`) ){
        // add map
        console.log('pass_map_init, add map', order_id, car_id);
        /*
        if( !taxi_path ){
            taxi_path = Cookies.get('taxi_path');
        }
        */
        let map = {
            passenger_id: taxiuser.user,
            passenger_marker: null,
            car_id: car_id,
            car_marker: null,
            vlayer: L.featureGroup(),
            olayer: L.maplibreGL({
                style: OSM_STYLE,
                minZoom: 1,maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            })
            // olayer: new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}),
        }
        map['map'] = L.map(`order_${order_id}_map`, {
                layers: [map.olayer, map.vlayer],
                center: [parseFloat(window.taxi_path.wf.point[1]), parseFloat(window.taxi_path.wf.point[0])],
                zoom: 13
            });
        taxi_maps[taxiuser.user] = map;

        // маркер пассажира
        taxi_map_set_marker(taxi_maps[taxiuser.user], 'passenger_marker', window.taxi_path.wf.point[1], window.taxi_path.wf.point[0], 'icon_p_24.png');
        taxi_fresh_map(taxiuser.user, window.taxi_path.wf.point[1], window.taxi_path.wf.point[0]);
    }   // if( $(`order_
    else {
        // delete map
        console.log('pass_map_init, delete map', order_id);
        // if( taxi_maps.hasOwnProperty(order_id) ){
        if (taxiuser.user in taxi_maps){
            delete taxi_maps[taxiuser.user];
        }
    }
}   // pass_map_init


// отправка сообщения юзеру
function taxi_send_message_to_user(user_id, msg, order_id){
    console.log('taxi_send_message_to_user', user_id, msg, order_id);

    let post = {
        'from': taxiuser.user,
        'to': user_id,
        'msg': msg,
        'order_id': (order_id || 0),
    };

    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': Cookies.get('csrftoken')},
        url: "/carpool/api/message/",
        data: post,
    })
    .done(function(data) {
        // data.result - True
        if( !data.error ){
            console.log('taxi_send_message_to_user done', data.result);
        }   // if( !data.error )
        else {
            $("#modal_dialog p").html(data.error);
            $('#modal_dialog').modal();
        }   // else if( !data.error )
    })  // done
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.log("taxi_send_message_to_user error:", errorThrown);
    });
}   // taxi_send_message_to_user


// клик по звёздочке рейтинга в такси
function taxi_star_click(rate, order_id){
    console.log('taxi_star_click', rate, order_id);
    /* этот код выставляет рейтинг = 0 при повторном щелчке по первой звезде
    if( rate == 0 && $(`#order_status_3_${order_id} .ui.rating i:first`).css('color') == 'rgb(255, 223, 50)' ){
        // убрать оценку (рейтинг = 0)
        $(`#order_status_3_${order_id} .ui.rating i`).each(function(index, element) {
            $(element).css('color', '#FFF');
        });
        $(`#order_${order_id} #order_rating_number`).html(rate);
    }
    else {
        // установить оценку
        $(`#order_status_3_${order_id} .ui.rating i`).each(function(index, element) {
            $(element).css('color', (index <= rate ? '#FFDF32' : '#FFF'));
        });
        $(`#order_status_3_${order_id} #order_rating_number`).html(rate + 1);
    }
    */
    /* этот код действует в соответствии с https://gitlab.com/nornk/bustime/-/issues/2821#note_1035519876
    отмену оценки делают нажатием на ту звезду, на которой уже установлено
    */
    let stars = $(`#order_status_3_${order_id} .ui.rating i`);
    for(let index = stars.length -1; index >= 0; index--){
        let element = stars[index];
        $(element).css('color', (index <= rate ? '#FFDF32' : '#FFF'));
    }

    $(`#order_status_3_${order_id} #order_rating_number`).html(rate + 1);
}   // taxi_star_click


function map_del_marker(marker){
    marker.closeTooltip();
    marker.unbindTooltip();
    marker.closePopup();
    marker.unbindPopup();
    marker.removeFrom(map_taxi);
    marker = null;  // delete object L.marker from memory
    return marker;
}   // map_del_marker


// latlon = marker.getLatLng()
function map_panto(latlon, zoom){
    if(map_taxi && latlon){
        map_taxi.panTo(latlon);
        if(zoom){
            map_taxi.setZoom(zoom);
        }
    }
}   // map_panto


// latlon = marker.getLatLng()
function map_flyto(latlon, zoom){
    if(map_taxi && latlon){
        map_taxi.flyTo(latlon);
        if(zoom){
            map_taxi.setZoom(zoom);
        }
    }
}   // map_flyto


// layer = layer_markers | layer_route
function map_boundsto(map, layer){
    if(map && layer){
        map.flyToBounds(layer.getBounds());
    }
}   // map_boundsto


// загрузка звуков для такси (попутчика)
function loadTaxiSounds(){
    if( !taxi_sound ){
        setTimeout(function(){
            if( Howl != 'undefined' ){
                taxi_sound = {
                    "order_new": new Howl({src: '/static/taxi/sound/bell-sound.mp3', preload: true}),         // https://zvukipro.com/1013-zvuki-kolokolchikov.html
                    "order_del": new Howl({src: '/static/taxi/sound/10n888picy3g354534.mp3', preload: true}), // https://zvukipro.com/2781-zvuki-jemodzi-reakcii.html
                    "offer_new": new Howl({src: '/static/taxi/sound/bell-sound.mp3', preload: true}),
                    "offer_del": new Howl({src: '/static/taxi/sound/10n888picy3g354534.mp3', preload: true}),
                    "offer_accept": new Howl({src: '/static/taxi/sound/multimedia-notify-37.mp3', preload: true}),
                    "hutzpa": new Howl({src: '/static/taxi/sound/50y888picjes.mp3', preload: true}),
                    "5min": new Howl({src: '/static/taxi/sound/carhornahooga_bw_62154.mp3', preload: true}),
                    "pora": new Howl({src: '/static/taxi/sound/ahooga-horn.mp3', preload: true}),
                };
            }
            else {
                taxi_sound = null;
            }
        }, 500);
    }   // if( !taxi_sound )
}   // loadTaxiSounds

// проигрывание звука для такси (попутчика)
function taxiPlay(soundName){
    if( us_sound && Howl != 'undefined' && taxi_sound && taxi_sound[soundName] ){
        taxi_sound[soundName].play();
    }
}   // taxiPlay


/*
Получение координат из строки типа POINT
pointStr = "SRID=4326;POINT (20.5505211 54.671261)"
pointStr.match(/[0-9.]+/gi) = [ "4326", "20.5505211", "54.671261" ]
*/
function Point2XY(pointStr){
    let arr, retval = null;

    try {
        arr = pointStr.match(/[0-9.]+/gi);
        if( arr.length == 3 ){
            retval = {'lon': parseFloat(arr[1]), 'lat': parseFloat(arr[2])};
        }
    }
    catch (err) {
        debug('Point2XY:', err);
    }

    return retval;
}   // Point2YX


function debug(...args){
    if(test_mode){
        console.log('DEBUG', args);
    }
}   // debug

/* NEW UI 2024 */
function process_queue() {                       // ф-я для обработки очереди

        if (message_queue.length > 0) {              // если в очереди что-то есть
            let prev_item = current_item;
            while (prev_item == current_item) {
                current_item = message_queue.shift(); // первое событие из очереди, remove dupes
            }

            $('.inf_about_data').html(current_item); // добавляем это событие на страницу
            let timeout = 1000;
            setTimeout(function() {                  // задержка в 1 секунду для отображения события
                current_item = null;                 // сбрасываем текущее событие
                if (message_queue.length > 0) {      // если сообытия в очереди есть
                    process_queue();                 // запускаем следующую итерацию очереди
                }
            }, timeout );
        }
}