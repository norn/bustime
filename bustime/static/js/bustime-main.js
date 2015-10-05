var autoupdate = "";
var autoupdate_force = 0;
var BUS_ID = "";
var STOP_IDS = [];
var STOP_IDS_SUBS = [];
var STOP_DESTINATION_IDS = [];
var NEAREST_STOPS = [];
var BUS_SIDE_IMG = "/static/img/side_bus_original.png";
var CAT_IMG = '/static/img/cat-male.png';
var CAT_IMG_OLD;
var TTYPE = 0;
var refresh = 30000;
var ticktackt = 0;
var ticktacktick = 500;
var cats = {};
var mycat;
// var wsuri = "ws://www.bustime.ru:9002/";
var wsuri = "ws://www.bustime.ru:80/socket/";
if (window.location.protocol == "https:") {
    wsuri = "wss://www.bustime.ru:443/wss/";
}
var sess;
var audioinited = 0;
var WSSUPPORT = 1;
// WSSUPPORT = 0;
var supportsVibrate = "vibrate" in navigator;
var isiPad = navigator.userAgent.match(/(iPhone|iPod|iPad)/i) !== null;
var isWP = navigator.userAgent.match(/Windows Phone/i) !== null;
var isAndroid = navigator.userAgent.toLowerCase().indexOf("android") > -1;
var isOperaMini = navigator.userAgent.match(/Opera Mini/) !== null;
if (isOperaMini) {
    alert("На браузере Opera Mini автобусы не видны! Воспользуйтесь Chrome или вы будете перенаправлены.");
    window.location.href = "/classic/" + us_city + "/";
}
var is_chrome = navigator.userAgent.match(/Chrome/) !== null;
var lastCheck = 0;
var timeTravel = false;
var last_bdata_mode0;
var globus = {};
var current_vehicle_info;
var current_rating_data;
var map_is_centered = 0;
var usePositionWatch_last = new Date();
var speed_show_last = new Date();
var bus_mode0_subs;
var bus_mode1_subs;
var HASHCHECK_DONE = 0;
var wconnection;
var swidget;
var radio_status = 0;
var radio_curtime = 0;
var vk_like_pro_countdown = 5;
var current_nbusstop;
var current_nbusstop_notified;
var game;
var radar_circle = null;
var schedule = {0:[], 1:[]};
var ol_map;
var ol_map_view;
var CITY_MONITOR_ONSCREEN={};
var NO_MORE_USE_POSITION=0;
var timer_minutes;
var PIXI;
var autobahn;
var running_light_cnt=1;
var express_dial="";
var express_dial_type=0;
var BID_BNAME = {};
var BNAME_BID = {};
var BID_BTYPE = {};
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
// var BTYPE_NAME_BID = {0:{}, 1:{}, 2:{}, 3:{}, 4:{}};
var recognition;
var recognition_result = '';
var recognition_inited = 0;
var is_retina = 0;
if (window.devicePixelRatio > 1) {
    is_retina = 1;
}
var sound_main, sound_speed;
var mode_selected=0;
var vk_authorized=0;
var dance_move = 1;
var rate;

// Object.keys(myArray).length

// var busMapIcon = L.icon({
//     iconUrl: '/static/img/map-bus.png',
//     shadowUrl: '',
//     iconSize:     [24, 18], // size of the icon
//     iconAnchor:   [24, 9], // point of the icon which will correspond to marker's location
//     popupAnchor:  [0, 0] // point from which the popup should open relative to the iconAnchor
// });



// caniuse.com
// www.whatismybrowser.com

if (/mobile/i.test(navigator.userAgent)) {
    is_chrome = false;
}
var standalone = window.navigator.standalone,
    userAgent = window.navigator.userAgent.toLowerCase(),
    safari = /safari/.test(userAgent),
    is_ios = /iphone|ipod|ipad/.test(userAgent);

function sound_init() {
    if (us_sound) {
        sound_main = new Howl({
            src: ['/static/img/bus-lq.ogg', '/static/img/bus-lq.mp3'],
            sprite: {
                arriving: [0, 2700],
                one_plus: [2700, 2300],
                one_minus: [5100, 2700]
            }
        });
        if (us_speed_show) {
            sound_speed = new Howl({
                src: ['/static/js/snd/speed_limit.ogg', '/static/js/snd/speed_limit.mp3'],
            });
        }
    }
    audioinited = 1;
}

if (us_sound) {
  sound_init();
}
// if (!is_ios) {
// }

function getLocation() {
    console.log("getLocation");
    var options;
    if (navigator.geolocation) {
        // https://developer.mozilla.org/en-US/docs/Web/API/PositionOptions
        if (us_gps_off === 0) {
            options = {
                enableHighAccuracy: false,
                maximumAge: 0
            };
            navigator.geolocation.getCurrentPosition(usePosition, noPosition, options);
        }
        options = { enableHighAccuracy: true, maximumAge: 0 };
        navigator.geolocation.watchPosition(usePositionWatch, noPosition, options);
    }
}

function nearest_click(i) {
    NO_MORE_USE_POSITION = 0;
    stop_ids(NEAREST_STOPS[i].ids);
    $("#id_stops").val(NEAREST_STOPS[i].name);
}

function usePosition(position) {
    console.log("usePosition");
    // ajax_metric("stop_name_gps", 1);
    if (NO_MORE_USE_POSITION > 0) {
        // console.log("no more use position");
        return;
    }
    var request = $.ajax({
        url: "/ajax/stops_by_gps/",
        type: "post",
        data: {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            accuracy: position.coords.accuracy,
            bus_id: BUS_ID,
            bus_name: get_bname(BUS_ID)
        },
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        var s = "";
        if (msg.length > 0) {
            stop_ids(msg[0].ids);
            set_current_nbusstop(msg[0].current_nbusstop);
            $("#id_stops").val(msg[0].name);
            NEAREST_STOPS = [];

            for (var i = 0; i < msg.length; i++) {
                NEAREST_STOPS[i] = msg[i];
                ss = "<button class='ui tiny icon labeled button' onclick='nearest_click(" + i + ")'><i class='fa fa-arrows-h icon'></i> "+ msg[i].name +', ' + msg[i].d + "м </button> ";
                s = ss + s;
            }
        }
        $('.stop_sug').html(s);
        $('.stop_sug').show();
    });
}

function set_current_nbusstop(id_) {
    current_nbusstop = id_;
    $("tr.bhlight_border").removeClass('bhlight_border');
    $(".bst" + current_nbusstop).parent().parent().addClass('bhlight_border');
}

function speed_show(position) {
    var speed = position.coords.speed;
    if (!speed && speed !== 0) {
        $(".speed_show").html("? км/ч");
        return;
    }

    // convert m/s to km/h == x * 60*60/1000.0
    speed = parseInt(speed * 3.6, 10);
    if (speed >= 68) {
        $(".speed_show").css("background-color", "#d40000");
        $(".speed_show").css("color", "#fff");
        aplay("sound_speed");
        speed = "<img src='/static/img/speed_limit_mascot.png'>" + speed;
        // aplayfile("speed_limit");
    } else if (speed >= 60) {
        $(".speed_show").css("background-color", "#ffe216");
        $(".speed_show").css("color", "#333");
    } else {
        $(".speed_show").css("background-color", "#99ff99");
        $(".speed_show").css("color", "#333");
    }
    $(".speed_show").html(speed+" км/ч");
}


function usePositionWatch(position) {
    var now = new Date();
    if (us_gps_off === 0 && now.getTime() - usePositionWatch_last.getTime() > 30 * 1000) {
        usePositionWatch_last = now;
        usePosition(position);
    } else {
        if (us_speed_show) {
            speed_show(position);
        }
    }
}

function noPosition(error) {
    console.log("GPS error: "+ error.code);
    $(".speed_show").css("background-color", "#ffb6b6");
    $(".speed_show").css("color", "#333");

    switch (error.code) {
        case error.PERMISSION_DENIED:
            $(".speed_show").html("GPS запрещено");
            //ajax_metric("stop_name_gps_denied", 1);
            //"User denied the request for Geolocation."
            break;
        case error.POSITION_UNAVAILABLE:
            $(".speed_show").html("GPS недоступен");
            //"Location information is unavailable."
            break;
        case error.TIMEOUT:
            $(".speed_show").html("GPS таймаут");
            //"The request to get user location timed out."
            break;
        case error.UNKNOWN_ERROR:
           $(".speed_show").html("GPS ошибка "+error.code);
            break;
    }
}

String.prototype.endsWith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1;
};

function websconnect() {
    wconnection = new autobahn.Connection({
        url: wsuri,
        realm: 'realm1',
        max_retries: 2 * 60 * 24,
        max_retry_delay: 30
    });

    wconnection.onopen = function(session) {
        WSSUPPORT = 1;
        sess = session;
        var d = new Date();
        console.log("Connected to " + wsuri + d);
        // ajax_metric("wsocket_on", 1);
        $('.busnumber').removeClass('bw');
        if (BUS_ID) {
            sub_bus_id();
        } else {
            hashcheck();
        }
        if (timer_countable) { // run this only on main page
          sess.subscribe("ru.bustime.bus_amounts__" + us_city, onPubBus);
        }
        sess.subscribe("ru.bustime.us__" + us_id, onPubBus);
        sess.subscribe("ru.bustime.public", onPubBus);
        if (us_speed_show) {
          $('.updated_widget').css('display','inline').css('background', '#99ff99');
          $('#update-icon').remove();
        }
        update_notify(0);
        // sess.subscribe("http://www.bustime.ru/socket/rhythm/", onPubBus);
        // $(".bustable_head_update").html("режим непрерывного обновления");
        // $(".bustable_head_update").css("background-color", '#1d6d3d');
        // $(".bustable_head_update").css("color", '#4a5c4c');

        // $(".bustable_head_text").css("background-color", '#7067BB');

        // rpc_tcard();
        // rpc_stop_ids();
    };

    wconnection.onclose = function(reason, details) {
        if (reason == "lost") {
            console.log('Websocket lost');
            return;
        }
        if (reason == "closed") {
            console.log('Websocket closed');
            return;
        }
        // unsupported
        // unreachable
        sess = null;
        console.log('Websocket failed');
        WSSUPPORT = 0;
        update_notify(0);
        ajax_metric("wsocket_off", reason);
        hashcheck();
    };

    wconnection.open();
}

function sleepCheck() {
    var now = new Date().getTime();
    var diff = now - lastCheck;
    if (diff > 3000) {
        timeTravel = 1;
    } else {
        timeTravel = 0;
    }
    lastCheck = now;
}

function ticktack() {
    if (!(WSSUPPORT && sess) && autoupdate) {
        $('#update-icon').css('transform', 'rotate(-' + ticktackt / 1000 * 12 + 'deg)');
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
}


function update_routes(data, napr, ttype) {
    TTYPE = ttype;
    var r, t, is_stripes = us_theme_stripes ? "" : "";
    var h0 = "<table class='pad " + is_stripes + "'>";
    var h1 = "<table class='pad " + is_stripes + "'>";
    for (var i = 0; i < data.length; i++) {
        r = data[i];

        if (r['bst'] == current_nbusstop) {
            t = "<tr class='bhlight_border'>";
        } else {
            t = "<tr>";
        }
        t = t + '<td><div class="indicator" id="' + r['id'] +
            '" bst_id="' + r['bst'] + '"><div class="f f' +
            r['id'] + '"></div></td><td><span class="busstop_name" id="' + r['id'] +
            '" bst_name_id="' + r['bst'] + '"">' +  r['name'] + '</span>' + '<span class="bsleep bsleep' +
            r['id'] + '"></span>';

        if (us_premium) {
          t = t +'<span class="bst bst' + r['bst'] + '"></span>';
        } else {
          t = t +'<span class="bst bst' + r['bst'] + '"></span>';
        }

        t = t + '</td></tr>';
        if (r['d'] === 0) {
            h0 = h0 + t;
        } else {
            h1 = h1 + t;
        }
    }
    h0 = h0 + "</table>";
    h1 = h1 + "</table>";
    $('#html_a').html(h0);
    $('#html_b').html(h1);
    // headers
    $('#napr_a').html(napr[0]);
    $('#napr_b').html(napr[1]);

    $(".indicator").click(function() {
        // $(this).addClass('vehicle_here blink-fast-half');
        // $(this).addClass('anishower');
        // var classes = $(this).attr('class').split(/\s+/);
        if ( $(this).hasClass('vehicle_here') ) {
           vehicle_info($(this).attr('vehicle_id'), 0);
        } else {
          console.log("indicator click: ", $(this).attr('class'));
        }
    });

    $(".busstop_name").click(function() {
        busstop_click( $(this).attr('id') );
    });
}
function blink_clear(a,b) {
  $(".disappear_here").removeClass('vehicle_here blink-fast-half disappear_here').css('background', '').html('');
}

function gosnum_format(g) {
  if (us_city == 9) {
    g = g.replace(/(.+?) (59|81|159)$/, '$1');
  } else if (us_city == 5) {
    g = g.replace(/(.+?)(78|98|178)$/, '$1');
  }
  return g;
}

function update_bdata_mode0(data) {
    if (timeTravel) {
        return;
    }
    var z, t, r, i, side_img, sleep, vehicle, vehicle_old;
    var cat_change = 0;
    $(".bsleep").html("");
    // $(".indicator").removeClass("vehicle_here").css('background','');
    $(".indicator.vehicle_here").addClass("disappear_here");

    // var globus_old = globus;
    var globus_old = $.extend({}, globus);
    // var copiedObject = jQuery.extend(true, {}, originalObject)

    for (i = 0; i < data['l'].length; i++) {
        // console.log(vehicle);
        vehicle = data['l'][i];
        globus[ vehicle['u'] ] = vehicle;
        globus[ vehicle['u'] ]['id'] = BUS_ID;
        z = vehicle['b'];
        r = vehicle['r'];
        sleep = vehicle['sleep'];
        if (sleep) {
            z = "bslp" + vehicle['u'];

            html = "<img id='" + z + "' onclick='vehicle_info("+vehicle['u']+",0)' style='margin-bottom:-12px' src='/static/img/tea-cup-icon.png' />";
            $(".bsleep" + vehicle['b']).append(html);
        } else {
            side_img = side_compo(TTYPE, r, vehicle['g'], vehicle['s']);
            // vehicle_old = globus_old[ vehicle['u'] ];
            var gosnum_visi="", gosnum_visi_class="";
            if (us_premium && vehicle['g']) {
                gosnum_visi = "<div class='gosnum_visi'>"+gosnum_format(vehicle['g'])+"</div>";
                gosnum_visi_class = "gosnum_visi";
            }
            $("#"+z).addClass("vehicle_here ").removeClass("disappear_here time_prediction").attr("vehicle_id", vehicle['u']).css('background', side_img).html(gosnum_visi);
            if (side_img.split(",").length == 4) {
                $("#"+z).css('background-size', "auto, auto, auto, cover");
            } else if (side_img.split(",").length == 3) {
                $("#"+z).css('background-size', "auto, auto, cover");
            } else if (side_img.split(",").length == 2) {
                $("#"+z).css('background-size', "auto, cover");
            } else {
                $("#"+z).css('background-size', "cover");
            }

        }
        // force reload vehicle info if opened
        if (vehicle['u'] == current_vehicle_info) {
            vehicle_info(vehicle['u'], 1);
        }

        //var bst_id = $('#' +z).attr('bst_id');
        // aplayfile("busstop_"+bst_id);
        if (!sleep && cats[z]) {
            cats[z] = 0;
            cat_change = 1;
            if (z == mycat) {
                aplay("arriving");
                vibrate();
            }
        }
        if (current_nbusstop && current_nbusstop == $('#' + z).attr('bst_id') && current_nbusstop_notified != vehicle['u']) {
            aplay("arriving");
            vibrate();
            current_nbusstop_notified = vehicle['u'];
        }
    }
    $(".disappear_here").addClass('blink-fast-half');
    setTimeout(blink_clear, 1500);

    if (cat_change) {
        update_passenger(cats);
    }
    $('.bustable_head_last_time').html(data['updated']).addClass('bhlight');
    if (us_speed_show) {
      $('#updated_widget_time').html(data['updated']).addClass('bhlight');
    }
    setTimeout(function() {
        $('.bustable_head_last_time').removeClass('bhlight');
         if (us_speed_show) {
           $('#updated_widget_time').removeClass('bhlight');
         }
    }, 800);

    $('.updated_widget').removeClass('ajaxerror');
    $('#updated_widget_time').html(data['updated']);
    recalc_schedule();
    // console.log(map);
    // console.log(myCollection);
    if (map && data['l']) {
        update_bdata_mode2(data['l']);
    }
}


function side_compo(ttype, ramp, gosnum, speed) {
    var side_img;

    if (ttype === 0) {
        side_img = BUS_SIDE_IMG;
        if (is_retina && BUS_SIDE_IMG=="/static/img/side_bus_original.png") {
            side_img = "/static/img/side_bus_original@2x.png";
        }
    } else if (ttype == 1) {
        side_img = "/static/img/side_trolley_original.png";
        if (is_retina) {
          side_img = "/static/img/side_trolley_original@2x.png";
        }
    } else if (ttype == 2) {
        side_img = "/static/img/side_tram_original.png";
        if (is_retina) {
          side_img = "/static/img/side_tram_original@2x.png";
        }
    } else {
        side_img = BUS_SIDE_IMG;
    }

    // TS icon compositor
    var urlo = 'url("'+side_img+'") center center no-repeat';
    if (ramp) {
        urlo = "url(/static/img/ramp_icon_16.png) right 25% center no-repeat, " + urlo;
    }
    var sticker;
    if (gosnum in bus_design_map) {
        sticker = bus_design_map[gosnum];
        // http://www.w3schools.com/cssref/pr_background-position.asp
    }  else if ('special' in bus_design_map && gosnum in bus_design_map) {
        sticker = bus_design_map['special'];
    } else if ('all' in bus_design_map) {
        side_img = bus_design_map['all'];
        if (ttype == 1 || ttype == 2) {
            side_img = bus_design_map['all_train'];
        }
    }
    if (sticker && $(window).width() >= 767) {
        urlo = "url("+sticker+") center center no-repeat, " + urlo;
    }

    // if (speed>5 && speed<15) {
    //           // side_img = "/static/img/side_bus-1.gif";
    //           urlo = "url(/static/img/speed-1.gif) center center no-repeat, " + urlo;
    // } else if (speed>=15 && speed<=40) {
    //         urlo = "url(/static/img/speed-3.gif) center center no-repeat, " + urlo;
    //           // side_img = "/static/img/side_bus-2.gif";
    // } else if (speed>40) {
    //           // side_img = "/static/img/side_bus-3.gif";
    //           urlo = "url(/static/img/speed-5.gif) center center no-repeat, " + urlo;
    // }

    return urlo;
}

function update_bdata_mode1(data) {
    var html, extra_class;
    $(".bst").html("");
    for (var key in data) {
        html = "";
        for (var i = 0; i < data[key].length; i++) {
            if (data[key][i][0] == BUS_ID) {
                // no info for current route
                continue;
            }

            // use only favor
            if ($.inArray(data[key][i][0], busfavor) > -1 || us_multi_all) {
                extra_class = "";

                if (us_premium) {
                   extra_class = "multi_bus";
                } else {
                    extra_class = "orange circular";
                }
                if (data[key][i][5]) {
                    extra_class = extra_class + " micro_ramp";
                    if (!us_premium) {extra_class = extra_class + " blue";}
                }
                if (data[key][i][3]) {
                    extra_class = extra_class + " micro_sleep";
                    if (!us_premium) {extra_class = extra_class + " grey";}
                }
                if (us_multi_all && $.inArray(data[key][i][0], busfavor) > -1) {
                    extra_class = extra_class + " micro_favor";
                }
                // if (data[key][i][1] in bus_design_map) {
                //     extra_class = extra_class + " image";
                // }
                // html = html + "<span class='multi_bus " + extra_class + "' onclick='vehicle_info(" + data[key][i][4] + ",0)'>" + BID_BNAME[data[key][i][0]];
                html = html + "<div class='ui label " + extra_class + "' onclick='vehicle_info(" + data[key][i][4] + ",0)'>";

                if (us_premium && data[key][i][1] in bus_design_map) {
                    extra_side = bus_design_map[data[key][i][1]];
                    html = html + "<img src='" + extra_side + "'>";
                }
                html = html + BID_BNAME[data[key][i][0]];
                // I am so smart!
                if (data[key][i][1] && us_premium) {
                    html = html +"<span class='multi_gosnom'>"+ gosnum_format(data[key][i][1]) + "</span>";
                }
                html = html + "</div>";
                if (data[key][i][4] in globus) {
                    globus[data[key][i][4]]['g'] = data[key][i][1];
                    globus[data[key][i][4]]['s'] = data[key][i][2];
                    globus[data[key][i][4]]['id'] = data[key][i][0];
                } else {
                  globus[data[key][i][4]] = {'g':data[key][i][1], 's':data[key][i][2], 'id':data[key][i][0]};
                }
                if (data[key][i][3]) {
                    globus[data[key][i][4]]['s'] = 1;
                }
            }
        }
        // if (data[key].length > 3) {
        //     html = "<br/>" + html;
        // }
        $(".bst" + key).html(html);
    }
}

function update_bdata_mode2(data) {
    var ev, d, g, sleep, marker, polyline, MapIconDiv, latlngs, sc, extra_c;
    var bname = get_bname(BUS_ID);
    myCollection.clearLayers();

    for (var i = 0; i < data.length; i++) {
        ev = data[i];
        if (!("x" in ev)) {
            return;
        }
        if (ev['d'] === 0) {
            extra_c = "color-1-2-bg";
            sc = "#F04C83";
        } else {
            extra_c = "color-2-2-bg";
            sc = "#45B4CE";
        }
        if (ev['g'] && us_premium) {
            g = '<b>'+ev['g'] + '</b>, ';
        } else {
            g = "";
        }

        if (ev['sleep']) {
            sleep = '<br/><img src="/static/img/tea-cup-icon.png"/>на перерыве';
        } else {
            sleep = "";
        }

        MapIconDiv = L.divIcon({iconSize: [112,18], iconAnchor:[-3, 9],
            className: 'MapIconDiv '+extra_c,
            html: "<b>"+bname+":</b> "+ev['bn'].substr(0, 12)});

        marker = L.marker([ev['y'], ev['x']], {icon: MapIconDiv});
        marker.bindPopup(g + ev['s'] + "км/ч <br/>" + ev['bn'] + sleep);

        latlngs = [[ev['y'],ev['x']], [ev['py'],ev['px']]];
        polyline = L.polyline(latlngs, {color: sc, opacity:0.8});

        myCollection.addLayer(marker);
        myCollection.addLayer(polyline);
    }

    if (!map_is_centered) {
        map.fitBounds(myCollection.getBounds());
        map_is_centered = 1;
    }
}


function update_passenger(data) {
    cats = data;
    $('.cats').remove();
    for (var j in cats) {
        for (var i = 0; i < cats[j]; i++) {
            $("#"+j+".busstop_name").after('<img class="cats" src="' + CAT_IMG + '">');
        }
    }
}

function update_time_bst(data) {
    $(".indicator.time_prediction").removeClass('time_prediction').html('');
    for (var j in data) {
        if ( data[j] && !$("#"+j).hasClass('vehicle_here') ) {
          $("#"+j).addClass('time_prediction').html(data[j]);
        }
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

    request.fail(function(jqXHR, textStatus) {
        $('.bustable_head_text').html(textStatus).addClass('ajaxerror');
        $('#updated_widget_time').html(textStatus);
        $('.updated_widget').addClass('ajaxerror');
    });


    // request.error(function(xhr, status, errorThrown) {});
}

function get_bname(bus_id) {
    return BID_BNAME[bus_id];
    // var bname = $('[bus_id=' + bus_id + "]").attr('bname');
    // return bname;
}

function show_me_the_bus(bus_id) {
    if (us_sound && is_ios && audioinited === 0) {
        sound_init();
    }
    osd_splash("bustime-splash.png");
    $('.busnumber').removeClass('bus_selected');
    $('a[bus_id="' + bus_id + '"]').addClass('bus_selected');

    var ttype = BID_BTYPE[bus_id];
    if (ttype == "0") {
        ttype = '<i class="fa fa-bus"></i>';
    } else if (ttype == "1") {
        ttype = '<i class="fa fa-subway"></i>';
    } else if (ttype == "2") {
        ttype = '<i class="fa fa-train"></i>';
    }

    $('.bustable_head_text').html(ttype + " " + get_bname(bus_id)); // icon xxx


    $(".ui.grid.bustable").css('display','inline');
    $(".welcome-text").css('display','none');
    var busfavor_url = "/ajax/busfavor/?bus_id=";
    if (WSSUPPORT && sess) {
        if (BUS_ID) {
            if (us_mode === 0) {
                sess.unsubscribe(bus_mode0_subs);
            }
            if (us_mode == 1) {
                sess.unsubscribe(bus_mode0_subs);
                sess.unsubscribe(bus_mode1_subs);
            }
        }
        BUS_ID = bus_id;
        sub_bus_id();
        busfavor_url = busfavor_url + BUS_ID;
    } else {
        autoupdate = bus_id;
        autoupdate_force = 1;
        if (autoupdate) {
            $('.updated_widget').css('display','inline');
        }
        busfavor_url = busfavor_url + autoupdate;
    }
    $.ajax({
        url: busfavor_url,
        type: "GET"
    });
    // $('#vk_comments').html("");
    // var bname = $('[bus_id='+BUS_ID+']').attr('bname');
    // if (bname) {
    //     var page_url = "http://www.bustime.ru/#"+bname;
    //     VK.Widgets.Comments('vk_comments', {limit:"10",autoPublish:"0", pageUrl:page_url}, BUS_ID);
    // }
    map_is_centered = 0;
    $('html, body').delay(400).animate({
        scrollTop: $('.separ').offset().top
    }, 400, 'linear', function() {
        //$(".calc-go").removeClass('calc-mode_selected');
    });
}

function tcard_check() {
    tcard = $('#id_tcard').val();
    if (tcard.length < 12) {
        alert('Неправильный формат. Введите 12  или 16 цифр с карты.');
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
          $('.tcard_balance').html(msg['balance'] + " раз");
        } else {
          $('.tcard_balance').html(msg['balance'] + ' <i class="fa fa-rub"></i>');
        }
    });
}

function sub_bus_id() {
    if (us_mode === 0 || us_mode === 1) {
        sess.subscribe("ru.bustime.bus_mode0__" + BUS_ID, onPubBus).then(
            function(subscription) {
                bus_mode0_subs = subscription;
            });
        rpcBdata(BUS_ID, 0);
    }
    if (us_mode == 1) {
        sess.subscribe("ru.bustime.bus_mode1__" + BUS_ID, onPubBus).then(
            function(subscription) {
                bus_mode1_subs = subscription;
            });
        rpcBdata(BUS_ID, us_mode);
    }
}

function ajax_metric(metric, value) {
    request = $.ajax({
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


// function settings_set(setting, value) {
//     var request = $.ajax({
//         url: "http://www.bustime.ru/ajax/settings/",
//         data: {
//             "setting": setting,
//             "value": value
//         },
//         type: "GET",
//         cache: false
//     });
//     osd_show('wait_a_second.png');
//     request.done(function(msg) {
//         location.reload();
//     });
// }

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

// function settings_init() {
//     $('[name=us_theme]').change(function() {
//         settings_set("theme", $(this).val());
//     });

//     $('[name=us_mode]').change(function() {
//         settings_set("mode", $(this).val());
//     });

//     $('[name=us_city]').change(function() {
//         console.log(location.pathname);
//         if (location.pathname == "/") {
//           settings_set("city", $(this).val());
//        } else {
//           settings_set_silent("city", $(this).val());
//           window.location.href = '/';
//        }
//     });

// }

function update_stops(msg) {
    if (timeTravel) {
        return;
    }
    var created = 1;
    var i, si, half, target, htmlus;
    for (i = 0; i < STOP_IDS.length; i++) {
        if ($('.stop_header.' + STOP_IDS[i]).length < 1) {
            created = 0;
        }
    }
    if (created === 0) {
        $('.stopt').removeClass('stopt');
        $('.stopt_0').html("");
        $('.stopt_1').html("");
        $('.stopt_2').html("");
        $('.stopt_3').html("");
        for (i = 0; i < STOP_IDS.length; i++) {
            si = STOP_IDS[i];
            if (i < 4) {
                target = ".stopt_" + i;
            } else {
                target = ".stopt_3";
            }
            htmlus = '<table class="ui selectable compact unstackable table"><thead><tr><th colspan="2" class="stop_header '+si+'"></th></tr>';
            htmlus = htmlus + '<tr><th colspan="2" class="center aligned stop_updated ' + si + '"></th></tr>';
            htmlus = htmlus + '</thead><tbody class="stop_result '+si+'"></tbody></table>';
            $(target).append(htmlus);
        }
    }
    // fuf... going to fill in
    var ns = "";
    for (i = 0; i < msg.length; i++) { // stops
        m = msg[i];
        for (var j = 0; j < m['data'].length; j++) { // bus data
            z = m['data'][j];
            ns = ns+"<tr><td class='sr_busnum'>" + z['n'] + "</td><td class='sr_stime'>" + z['t'] + "</td></tr>";
        }

        if (m['tram_only']) {
          $(".stop_header." + m['nbid']).html("<i class='fa fa-subway'></i> " + m['nbname']);
        } else {
          $(".stop_header." + m['nbid']).html("<i class='fa fa-arrow-circle-o-right icon'></i> " + m['nbname']);
        }
        $(".stop_result." + m['nbid']).html(ns);
        $(".stop_updated." + m['nbid']).html(m['updated']);
        $(".stop_updated." + m['nbid']).css('background-color', 'red').css('color', 'white');
    }
    setTimeout(function() {
        $(".stop_updated").css('background-color', '').css('color', '');
    }, 600);
}

function update_city_rhythm(msg) {
    $(".osd_city_rhythm").html(msg);
}

function stop_ids(ids) {
    // ajax_metric("stop_ids", 1);
    var i;
    if (WSSUPPORT && sess) {
        if (STOP_IDS_SUBS) {
            for (i = 0; i < STOP_IDS_SUBS.length; i++) {
                try {
                    sess.unsubscribe(STOP_IDS_SUBS[i]);
                } catch (err) {}
            }
        }
        STOP_IDS = ids;
        for (i = 0; i < STOP_IDS.length; i++) {
            sess.subscribe("ru.bustime.stop_id__" + STOP_IDS[i], onPubBus).then(
                function(subscription) {
                    STOP_IDS_SUBS.push(subscription);
                });
        }
        ajax_stop_ids();
    } else {
        STOP_IDS = ids;
        ajax_stop_ids();
    }
    if (STOP_IDS.length>0) {
        if (STOP_DESTINATION_IDS.length > 0) {
            stop_destination();
        }
    }
}

function stop_destination_save(ids) {
    STOP_DESTINATION_IDS = ids;
    stop_destination();
}

function stop_destination() {
    if (STOP_IDS.length < 1 || STOP_DESTINATION_IDS.length < 1) {
        return;
    }
    var request = $.ajax({
        url: "/ajax/stop_destination/",
        type: "POST",
        data: {
            "ids": JSON.stringify(STOP_IDS),
            "destination": JSON.stringify(STOP_DESTINATION_IDS)
        },
        dataType: "json",
        cache: false
    });


    request.done(function(msg) {
        // update_stops(msg['stops']);
        var result = "";
        for (var i = 0; i < msg.length; i++) { //old school
            // console.log(msg[i]);
            result = result + "<div class='ui label orange'>" + msg[i]['name'] + "</div>";
        }
        $('.stop_destination_result').html(result);

    });
}

function flash_dance() {
    var els = $(".sr_busnum").toArray(), i;
    for (i=0;i<els.length;i++) {
      if (dance_move % 2 == i % 2) {
        $(els[i]).addClass("lightup");
      } else {
        $(els[i]).removeClass("lightup");
      }
    }
    dance_move++;
    if (dance_move<0) {
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
    var request = $.ajax({
        url: "/ajax/stop_ids/",
        type: "GET",
        data: {
            "ids": JSON.stringify(STOP_IDS)
        },
        dataType: "json",
        cache: false
    });

    request.done(function(msg) {
        update_stops(msg['stops']);
    });
}

function autocomplete_enter(name) {

    var lname = name.toLowerCase();
    for (var i = 0; i < stops.length; i++) { //old school
        if (stops[i].value.toLowerCase() == lname) {
            $("#id_stops").val(stops[i].value);
            stop_ids(stops[i].ids);
            return;
        }
    }
    alert('Остановка не найдена');
}

function matrix_inverto() {
    var html_ = '<i class="fa-table icon"></i> ';
    var cur = $(".matrix").css('display');
    if (cur=="none") {
        $(".matrix").css('display','block');
        // $(".show_matrix_button").css('display','none');
        $(".show_matrix_button").html(html_+'Скрыть');
        settings_set_silent("matrix_show", true);
        ajax_metric("show_matrix", 1);
        $(".modec_"+mode_selected).addClass('active');
        // $("[class^='item modec_']").removeClass('disabled');
    } else if (cur=="block") {
        $(".matrix").css('display','none');
        $(".show_matrix_button").html(html_+'Показать');
        settings_set_silent("matrix_show", false);
        $(".modec_"+mode_selected).removeClass('active');
        // $("[class^='item modec_']").addClass('disabled');
    }
}

document_ready = function() {
    var FastClick = require('fastclick');
    FastClick.attach(document.body);
    if (isOperaMini) {
        // $(".separ").html("Автообновление не поддерживается на Opera Mini").css('background-color', 'red');
        $("#hint").html("Автообновление не поддерживается на Opera Mini");
    }
    var bname, btype, nname, bus_id;
    $('.busnumber').each(function(index) {
        bus_id = $(this).attr('bus_id');
        bname = $(this).attr('bname');
        btype = $(this).attr('btype');
        BID_BNAME[bus_id] = bname;
        BNAME_BID[bname] = bus_id;
        BID_BTYPE[bus_id] = btype;

        // $(this).attr("href", '#' + bname);
        // nname = $(this).html();
        // BTYPE_NAME_BID[btype][nname] = bus_id;
    });
    $(".busnumber").click(function() {
        show_me_the_bus($(this).attr('bus_id'));
    });
    var d = new Date();
    window.console && console.log('Doc ready ' + d);
    if (us_device == "opera_mini") {
        WSSUPPORT = 0;
        ajax_metric("wsocket_off", "opera_mini");
        hashcheck();
    } else if (WSSUPPORT==1) {
        websconnect();
    } else {
        hashcheck();
    }
    // settings_init();
    // $(".form_stop_name").submit(function(event) {
    //     event.preventDefault();
    // });
    if (us_device != "opera_mini") {
        var autocomplete_min = 3;
        if (us_city == 5) {
            autocomplete_min = 3;
        }

        $("#id_stops").autocomplete({
            minLength: autocomplete_min,
            source: stops,
            select: function(a, b) {
                NO_MORE_USE_POSITION = 1;
                stop_ids(b.item.ids);
            }
        }).keypress(function(e) {
            if (e.keyCode === 13) {
                NO_MORE_USE_POSITION = 1;
                autocomplete_enter(this.value);
            }
        });
        $("#id_stops2").autocomplete({
            minLength: autocomplete_min,
            source: stops,
            select: function(a, b) {
                stop_destination_save(b.item.ids);
            }
        }).keypress(function(e) {
            if (e.keyCode === 13) {
                autocomplete_enter(this.value);
            }
        });
        if (us_gps_off === 0 || us_speed_show) {
            getLocation();
        }

        $('input.deletable').wrap('<span class="deleteicon" />').after($('<span/>').click(function() {
            $(this).prev('input').val('').focus();
        }));
    }
    load_extra();
    ticktack();

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
        var bus_id = busnumber.attr("bus_id");
        busnumber.remove();
        $.ajax({
            url: "/ajax/busdefavor/",
            type: "GET",
            data: {
                "bus_id": bus_id
            }
        });
    });

    lastCheck = new Date().getTime();
    setInterval(sleepCheck, 1000);
    if (!isiPad && !isAndroid) {
        $(document).tooltip();
    }

    $(".show_map_button").click(function() {
        show_map();
    });
    if (us_map_show) {
       show_map();
    }

    $(".show_matrix_button").click(function() {
       matrix_inverto();
    });

    // android 2.3 check
    if (check_float64() != 1) {
        $(".ilikepro").remove();
        $("#vk_like").show();
        $(".vk_share_helper").show();
    }

    $(".vk_like_pro_continue").click(function() {
        $(".ilikepro").hide();
        $("#vk_like").show();
        $(".vk_share_helper").show();
        ajax_vk_like_pro(2);
    });

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

    //hide or show the "back to top" link
    // $(window).scroll(function(){
    //     ( $(this).scrollTop() > 130 ) ? $(".back_to_top:not(.express)").removeClass('ui-helper-hidden') : $(".back_to_top:not(.express)").addClass('ui-helper-hidden');
    // });

    // for some reasone this speed things up
    setTimeout(function() {
        low_bootstrap();
    }, 500);
    // aplayfile("vf_id_13");
};
// $(document).ready(document_ready);

function count_down() {
    if (vk_like_pro_countdown > 0) {
        $(".count_down").html(vk_like_pro_countdown);
        $(".count_down").show();
        vk_like_pro_countdown--;
        setTimeout(count_down, 500);
    } else if (vk_like_pro_countdown === 0) {
        $(".ilikepro").hide();
        $("#vk_like").show();
        // $(".vk_share_helper").show();
    }
}

function vk_like_pro_like() {
    console.log("liked");
    var h = '<i class="fa fa-heart brand-red"></i> Спасибки! ';
    $(".ilikepro_message").html(h);
    $(".ilikepro_message").show();
    // $(".vk_like_pro_continue").show();
    vk_like_pro_countdown = 5;
    $(".vk_like_pro_continue").hide();
    count_down();
    ajax_vk_like_pro(1);
}

function vk_like_pro_unlike() {
    console.log("unliked");
    vk_like_pro_countdown = -5;
    $(".count_down").hide();
    $(".vk_like_pro_continue").hide();
    var h = 'Ой, вы сделали хуже!<br/>Лайкните скорее обратно :)';
    $(".ilikepro_message").html(h);
    $(".ilikepro_message").show();
    ajax_vk_like_pro(3);
}

function vk_like_pro_share() {
    console.log("shared");
    var h = '<i class="fa fa-heart brand-red"></i> Супер! ';
    $(".ilikepro_message").html(h);
    $(".ilikepro_message").show();
    vk_like_pro_countdown = 5;
    // $(".vk_like_pro_continue").hide();
    // count_down();
    ajax_vk_like_pro(4);
}

function rpcBdata(bus_id, mode) {
    sess.call("ru.bustime.rpc_bdata", [bus_id, mode, 0]).then(
        function(data) {
            if (data === null) {
              console.log("null rpcBdata!");
            } else {
              router(data);
            }
        },
        function(error) {
            console.log("rpc error!"); //JSON.stringify(error, null, 4)
            console.log(error);
        }
    );
}

// function rpc_tcard() {
//     sess.call("ru.bustime.rpc_tcard", [100000008282157]).then(
//         function(data) {
//             console.log(data);
//         },
//         function(error) {
//             console.log("rpc error!"); //JSON.stringify(error, null, 4)
//             console.log(error);
//         }
//     );
// }

// function rpc_stop_ids() {
//     var zzz = JSON.stringify([7634,7710]);
//     console.log(zzz);
//     sess.call("ru.bustime.rpc_stop_ids", [zzz]).then(
//         function(data) {
//             console.log(data);
//         },
//         function(error) {
//             console.log("rpc error!"); //JSON.stringify(error, null, 4)
//             console.log(error);
//         }
//     );
// }

function sseek() {
    var radio_curtime = $("#scwidget").attr("skip_seconds");
    radio_curtime = parseInt(radio_curtime, 10);
    if (radio_curtime === 0) {return;}

    if (isAndroid) {
        radio_curtime = 45 * 1000;
    } else {
        radio_curtime = radio_curtime * 1000;
    }
    swidget.seekTo(radio_curtime);
}

function radio_onpogress(e) {
    // if (radio_curtime === 0) {return;}
    // console.log(e.loadedProgress);
    //     widget.getCurrentSound(function(currentSound) {
    //   relativePreviousPlay = previousPlay / currentSound.duration; // ~0.204
    // });
    //if (e.loadedProgress && e.loadedProgress > radio_curtime/3597000) {
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
  radio_status = 2;
}


function radio_onpause() {
    $(".bustime-logo").removeClass("logorot");
    $(".fa-pause").removeClass('fa-pause').addClass('fa-music');
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
        swidget.bind(SC.Widget.Events.PAUSE, radio_onpause );
        swidget.bind(SC.Widget.Events.PLAY, radio_onplay );
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
}

function vehicle_info(vehicle_id, force) {
    var side_img, r, s, h, dir;
    if (current_vehicle_info) {
      $(".vehicle_selected").removeClass('vehicle_selected');
    }
    if (current_vehicle_info == vehicle_id && force === 0) {
        vehicle_info_close();
        return;
    }

    $(".vehicle_here[vehicle_id="+vehicle_id+"]").addClass('vehicle_selected');
    current_vehicle_info = vehicle_id;
    var vehicle = globus[vehicle_id];
    $(".vehicle_info").css('display','inline');
    if (vehicle["g"] === undefined) {
        $(".vehicle_info_uniqueid").html(vehicle['u']);
    } else if (us_premium || us_city != 3) {
        $(".vehicle_info_uniqueid").html(gosnum_format(vehicle['g']));
    } else {
        // гос. номер только в <a href='/pro/'>про версии</a>
        $(".vehicle_info_uniqueid").html("");
    }

    side_img = side_compo(TTYPE, vehicle['r'], vehicle['g'], vehicle['s']);
    $(".vehicle_info_img").addClass("vehicle_here").css('background', side_img); //.css('transform', 'scale(1.2)');

    $(".vehicle_info_name").html(get_bname(vehicle['id']));
    $(".vehicle_info_speed").html(vehicle['s']);
    h = vehicle['h'];
    if (h >= 337.5 || h < 22.5) {
        dir = "С";
    } else if (h >= 22.5 && h < 67.5) {
        dir = "СВ";
    } else if (h >= 67.5 && h < 112.5) {
        dir = "В";
    } else if (h >= 112.5 && h < 157.5) {
        dir = "ЮВ";
    } else if (h >= 157.5 && h < 202.5) {
        dir = "Ю";
    } else if (h >= 202.5 && h < 247.5) {
        dir = "ЮЗ";
    } else if (h >= 247.5 && h < 292.5) {
        dir = "З";
    } else if (h >= 292.5 && h < 337.5) {
        dir = "СЗ";
    }
    $(".vehicle_info_heading_w").html(dir);
    // console.log(h);
    h = h - 45; // it is 45 by default, so correct it
    $(".vehicle_info_heading").css('transform', 'rotate(' + h + 'deg)');

    $('.vehicle_info_speed').css('background-color', 'red').css('color', 'white');
    $('.vehicle_info_heading_w').css('background-color', 'red').css('color', 'white');
    setTimeout(function() {
        $('.vehicle_info_speed').css('background-color', '').css('color', '');
        $('.vehicle_info_heading_w').css('background-color', '').css('color', '');
    }, 400);
    if (force != 1) {
        var request = $.ajax({
            url: "/ajax/rating_get/",
            type: "post",
            data: {
                u: vehicle_id,
                g: vehicle['g']
            },
            dataType: "json",
            cache: false
        });

        request.done(function(msg) {
            rating_fill(msg, 1);
        });
    }
}

function vehicle_info_close() {
    rate = 0;
    var msg = $("[name=msg]").val("");
    $(".vehicle_selected").removeClass('vehicle_selected');
    current_vehicle_info = "";
    $(".vehicle_info").css('display','none');
}


function busstop_click(r_id) {
    r_id = parseInt(r_id, 10);
    if (!sess) {
        return;
    }
    if (mycat) {
        sess.call("ru.bustime.rpc_passenger", [-1, BUS_ID, mycat]);
    }
    mycat = r_id;
    sess.call("ru.bustime.rpc_passenger", [1, BUS_ID, r_id]).then(
        function(data) {
            // it returns empty on success
        },
        function(error) {
            console.log("rpc error: " + error);
            console.log(error);
        }
    );
    ajax_metric("catplace", 1);
}

function update_notify(st) {
  if (st === 0) {
    $(".button.settings").css("position", "absolute");
    $("i.setting").removeClass('loading').removeClass('yellow');
  } else {
    $(".button.settings").css("position", "fixed");
    $("i.setting").addClass('loading').addClass('yellow');
  }
}

function router(event) {
    if (timeTravel) {
        // alert("time travel fixed");
        return;
    }
    // console.log("up_r_1", window.performance.now());
    // $(".button.osd_update_notify").css('display','inline');
    update_notify(1);

    if (event['routes']) {
        update_routes(event["routes"], event["napr"], event["ttype"]);

    }
    if (event['bdata_mode0']) {
        update_bdata_mode0(event['bdata_mode0']);
        last_bdata_mode0 = event;
    }
    if (event['busamounts']) {
        update_bus_amount(event['busamounts']);
    }
    if (event['passenger']) {
        update_passenger(event['passenger']);
    }
    if (event['time_bst']) {
        update_time_bst(event['time_bst']);
    }
    if (event['stops']) {
        update_stops(event['stops']);
    }
    if (event['city_rhythm']) {
        update_city_rhythm(event['city_rhythm']);
    }
    if (event['bdata_mode1']) {
        update_bdata_mode1(event['bdata_mode1']);
    }
    if (event['first_last']) {
        update_schedule(event['first_last']);
    }
    if (event['city_monitor']) {
        update_city_monitor(event['city_monitor']);
    }
    if (event['us_cmd']) {
        update_cmd(event);
    }

    setTimeout(function() {
        update_notify(0);
        // $('.button.osd_update_notify').fadeOut('fast');
    }, 600);
    // console.log("up_r_2", window.performance.now());
}

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
    }
}



function bus_amount_hlight(key, amount) {
    $("." + key).addClass('bhlight');
    $("." + key).html(amount);

    var op_key;
    if (key.endsWith("_d0")) {
        op_key = key.replace(/_d0/, "_d1");
    } else {
        op_key = key.replace(/_d1/, "_d0");
    }
    op_key = $("." + op_key).html();

    if (op_key != "-") {
        op_key = parseInt(op_key, 10);
    } else {
        op_key = 0;
    }

    var kp = $("." + key).parent().parent().parent();
    var btype = $("." + key).parent().parent().parent().attr('btype');

    kp.removeClass('t' + btype + '_coloramount0').removeClass('t' + btype + '_coloramount1').removeClass('t' + btype + '_coloramount2');
    if ((amount + op_key) < 1) {
        kp.addClass('t' + btype + '_coloramount0');
    } else if ((amount + op_key) < 3) {
        kp.addClass('t' + btype + '_coloramount1');
    } else {
        kp.addClass('t' + btype + '_coloramount2');
    }
}

function update_bus_amount(data) {
    if (timeTravel) {
        return;
    }
    var t, bid, amount, old_amount;
    for (var key in data) {
        amount = parseInt(data[key], 10);
        bid = key.replace("_d0", '').replace("_d1", '');
        bid = parseInt(bid, 10);
        key = "busamount_" + key;

        if (bid == BUS_ID && us_sound_plusone) {
            old_amount = parseInt($("." + key).html(), 10);
            if (amount > old_amount) {
                osd_show('one_plus.png');
                aplay('one_plus');
            } else if (amount < old_amount) {
                osd_show('one_minus.png');
                aplay('one_minus');
            }
        }
        // t = parseInt(Math.random() * 800, 10);
        // setTimeout(bus_amount_hlight, t, key, amount);
        bus_amount_hlight(key, amount);
    }
    setTimeout(function() {
        $('.busamoun').removeClass('bhlight');
    }, 850);
}

function hashcheck() {
    if (HASHCHECK_DONE) {
        return;
    }
    var hashname = window.location.hash;
    if (hashname) {
        var bname = hashname.replace("#", "");
        var bus_id = $('.busnumber[bname="' + bname + '"]').not(".busfavor").attr('bus_id');
        if (bus_id) {
            show_me_the_bus(bus_id);
        }
    }
    HASHCHECK_DONE = 1;
}

function metric_checkt() {
    ajax_metric("checkt", 1);
}

function aplay(name) {
    if (!us_sound) {
        return;
    }

    if (name == "sound_speed") {
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
    $('.osd_message').css('display','inline');
    setTimeout(function() {
        // $('.osd_message').fadeOut(100);
        $('.osd_message').css('display','none');
    }, 500);
}

function flash_message(msg, delay) {
    $('.flash_message').html(msg);
    $('.flash_message').slideDown('fast');
    if (delay>0) {
        setTimeout(function() {
            $('.flash_message').fadeOut('fast');
        }, delay);
    }
}

function vibrate() {
    if (supportsVibrate) {
        // navigator.vibrate(1000);
        navigator.vibrate([700, 300, 700]);
    }
}

// function change_bmode(mode) {
//   if (mode==2) {
//     $(".info-table").show();
// }
// }
function map_data_go() {
    if (last_bdata_mode0) {
      router(last_bdata_mode0);
    }
    // else {
    //   map.setView([US_CITY_POINT_Y, US_CITY_POINT_X], 13);
    // }
}


function show_map() {
    var html_ = '<i class="fa-globe icon"></i>';
    if ($('.map').css("display") == "none") {
        $('.map').css("display", "block");
        $('.show_map_button').html(html_+'Скрыть карту');
        if (!map) {
            ajax_metric("show_map", 1);
            settings_set_silent("map_show", true);

            map = L.map('lmap', {scrollWheelZoom:false, fullscreenControl: true});
            myCollection = L.featureGroup().addTo(map);
            var osm = new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(map);

            map.on("viewreset", function() {
                map.invalidateSize(false);
                map_data_go();
            });
            map_data_go();

            // ymap - deprecated
            // $.getScript("http://api-maps.yandex.ru/2.1/?lang=ru-RU&coordorder=longlat&onload=ymap_load", function() {
                // done loading, run ymap_load?
            // });
        }
        // map.invalidateSize(false);

    } else {
        $('.map').css("display", "none");
        $('.show_map_button').html(html_+'Показать карту');
        settings_set_silent("map_show", false);
    }
}


function radar_init(ymaps) {
    map = L.map('lmap', {scrollWheelZoom:false, fullscreenControl: true});
    myCollection = L.featureGroup().addTo(map);
    var osm = new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 22}).addTo(map);
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
    map = L.map('lmap', {scrollWheelZoom:false, fullscreenControl: true});
    myCollection = L.featureGroup().addTo(map);
    var osm = new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(map);
    map.setView([US_CITY_POINT_Y, US_CITY_POINT_X], 12);
    L.Icon.Default.imagePath = '/static/img/';

    sess.subscribe("ru.bustime.city_monitor__" + us_city, onPubBus);
    console.log('city monitor');
}

function recalc_schedule() {
    var now = new Date();
    var i;

    for (i=0; i<schedule[0].length;i++) {
        if (schedule[0][i]>now)  {
          $(".schedule_0_1").html(schedule[0][i].toTimeString().substr(0,5));
          $(".schedule_0_1").addClass('bhlight_black');
          setTimeout(function() {
            $(".schedule_0_1").removeClass('bhlight_black');
          }, 400);
          break;
        }
    }

    for (i=0; i<schedule[1].length;i++) {
        if (schedule[1][i]>now)  {
          $(".schedule_1_1").html(schedule[1][i].toTimeString().substr(0,5));
          $(".schedule_1_1").addClass('bhlight_black');
          setTimeout(function() {
            $(".schedule_1_1").removeClass('bhlight_black');
          }, 400);
          break;
        }
    }
}

function update_schedule(msg) {
    $(".schedule").css('display', 'block');
    var now = new Date();
    var s1="";
    var i,d;
    schedule[0] = [];
    schedule[1] = [];

    if (msg["s0"] && msg["s0"].length > 0) {
        $(".schedule_0").css('display', 'table');
        for (i=0; i<msg["s0"].length;i++) {
            d = new Date(now.getFullYear(), now.getMonth(), now.getDate(), msg["s0"][i][0], msg["s0"][i][1]);
            if (i===0) {
              $(".schedule_0_0").html(d.toTimeString().substr(0,5));
            }

            if (d>now)  {
              schedule[0].push(d);
            }

            if (i===msg["s0"].length-1) {
                $(".schedule_0_2").html(d.toTimeString().substr(0,5));
            }
        }
    } else {
        $(".schedule_0").css('display', 'none');
    }


    if (msg["s1"] && msg["s1"].length > 0) {
        $(".schedule_1").css('display', 'table');
        for (i=0; i<msg["s1"].length;i++) {
          d = new Date(now.getFullYear(), now.getMonth(), now.getDate(), msg["s1"][i][0], msg["s1"][i][1]);
          if (i===0) {
            $(".schedule_1_0").html(d.toTimeString().substr(0,5));
          }
          if (d>now)  {
            schedule[1].push(d);
          }
          if (i===msg["s1"].length-1) {
              $(".schedule_1_2").html(d.toTimeString().substr(0,5));
          }
        }
    } else {
        $(".schedule_1").css('display', 'none');
    }
    recalc_schedule();
}

function update_city_monitor(msg) {
 var now = new Date();
 var marker;
 var date = msg[0];
 var sess_id = msg[1];
 var lon = msg[2];
 var lat = msg[3];
 var accuracy = msg[4];
 var bus_name = msg[5];


 if ( Math.abs(US_CITY_POINT_X-lon)>1 || Math.abs(US_CITY_POINT_Y-lat)>1) {
    return;
 }

 // clean up dots older then 2 minute
 for (var key in CITY_MONITOR_ONSCREEN) {
  if (now - CITY_MONITOR_ONSCREEN[key][0] > 70*1000) {
    myCollection.removeLayer(CITY_MONITOR_ONSCREEN[key][1]);
    delete CITY_MONITOR_ONSCREEN[key];
    $(".passengers_amount").html( myCollection.getLayers().length );
    aplayfile("barcode_out");
  }
 }
 // if already in array - update coords and time
 if (sess_id in CITY_MONITOR_ONSCREEN) {
    marker = CITY_MONITOR_ONSCREEN[sess_id][1];
    marker.setLatLng([lat,lon]);
    CITY_MONITOR_ONSCREEN[sess_id][0] = now;
    return;
 }
//  var myIcon = L.icon({
//     iconUrl: '/static/img/marker-icon-yellow.png',
//     iconSize: [25, 41],
//     iconAnchor: [12, 41],
//     popupAnchor: [0, -41],
//     shadowUrl: ''
// });
 // marker = L.marker([lat, lon], {icon: myIcon}).addTo(map);
 marker = L.marker([lat, lon]).addTo(map);

 if (bus_name) {
    // $(".leaflet-popup-close-button")[0].click();
    marker.bindPopup("<b>Жду "+bus_name+"</b>").openPopup();
 }
 myCollection.addLayer(marker);
 CITY_MONITOR_ONSCREEN[sess_id] = [now, marker];

 map.fitBounds(myCollection.getBounds());
 $(".passengers_amount").html(myCollection.getLayers().length);
 aplayfile("barcode");
}

function aplayfile(snd) {
    if (!us_sound) {
        return;
    }

    var sound_mini = new Howl({
      src: ["/static/js/snd/"+snd+'.mp3', "/static/js/snd/"+snd+'.ogg']
    }).play();
    return true;
}

function ajax_vk_like_pro(x) {
    request = $.ajax({
        url: "/ajax/vk_like_pro/",
        data: {
            "x": x
        },
        type: "GET",
        dataType: "json",
        cache: false
    });
}

// function authInfo(response) {
//   if (response.session) {
//     vk_authorized = response.session.mid;
//     $(".login_button").addClass('fhidden');
//     var profile = VK.api("users.get",{user_ids:""+vk_authorized, fields:["first_name", "last_name", "photo_200"]);
//     console.log(profile);
//     // https://vk.com/dev/users.get
//     // https://vk.com/dev/fields
//    // https://vk.com/dev/Javascript_SDK
//   } else {
//     $(".login_button").removeClass('fhidden');
//   }
// }

function low_bootstrap() {
    VK.init({
        apiId: 3767256,
        onlyWidgets: true
    });
    VK.Widgets.Like("vk_like", {
        type: "button",
        height: 24,
        pageUrl: "http://www.bustime.ru"
    });
    // VK.Auth.getLoginStatus(authInfo);

    // console.log(a);
    // VK.UI.button('login_button');

    // pageImage: "http://www.bustime.ru/static/img/bustime-2.0.png",
    // text: "Полезный сайт, на котором видно где сейчас едут автобусы"
    // var vk_share_helper = VK.Share.button({
    //     url: "http://www.bustime.ru/"
    // }, {
    //     type: "round",
    //     text: "Сохранить"
    // });
    // $('.vk_share_helper').html(vk_share_helper);

    VK.Observer.subscribe("widgets.like.liked", vk_like_pro_like);
    VK.Observer.subscribe("widgets.like.unliked", vk_like_pro_unlike);

    // VK.Widgets.Comments('vk_comments', {limit:"10",autoPublish:"0"});
    // addToHomescreen({maxDisplayCount: 2, skipFirstVisit: true});
    // android 2.3 check

    if (vk_like_pro && check_float64() == 1) {
        $("#vk_like").hide();
        VK.Widgets.Like("vk_like_pro", {
            type: "button",
            height: 24,
            pageUrl: "http://www.bustime.ru"
        });
        // var vk_share_helper_pro = VK.Share.button({
        //     url: "http://www.bustime.ru/",
        //     title: 'Время Автобуса',
        //     description: 'Узнайте где сейчас едет нужный вам автобус, троллейбус или трамвай в режиме онлайн. Информация о маршрутах и другие полезные сервисы для пассажиров.',
        //     image: "http://www.bustime.ru/static/img/bustime-2.0.png",
        //     noparse: true
        // }, {
        //     type: "round",
        //     text: "Сохранить"
        // });
        // $('.vk_share_helper_pro').html(vk_share_helper_pro);
        // VK.Observer.subscribe("widgets.like.shared", vk_like_pro_share);
        // $(".vk_share_helper").hide();
    }

    if (!us_premium || us_pro_demo) {
        // 1m delay before first minute
        if (us_city == 3) {
            setTimeout(function() {
                session_timer();
            }, 60 * 1000);
        }
    }
    $(".lucky_message").remove();
    if (us_theme == 11) {
        // game = new Phaser.Game("100", "100", Phaser.AUTO, 'ph_container', { preload: preload, create: create }, true);
    }
    // pixijs_load();
    if (city_monitor_mode) {
        city_monitor();
    }
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
            // $('.timer_warning').show();
            location.reload();
        }
        if (us_pro_demo === 1 && msg['pro_minutes'] >= 10) {
            location.reload();
        }
        if (us_premium === 0) {
           timer_minutes = msg['minutes'];
        }
    });

    setTimeout(function() {
        session_timer();
    }, 60 * 1 * 1000);
}

function radar_center(position) {
    if (!map) {return;}

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
    if (!map) {return;}
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
            sc = "#F04C83";
        } else {
            extra_c = "color-2-2-bg";
            sc = "#45B4CE";
        }
        if (event['gosnum'] && us_premium) {
            g = event['gosnum'] + '<br/>';
        } else {
            g = "";
        }

        MapIconDiv = L.divIcon({iconSize: [112,18], iconAnchor:[-3, 9],
            className: 'MapIconDiv '+extra_c,
            html: "<b>"+bname+":</b> "+event["bn"]});
        marker = L.marker([event['point_y'], event['point_x']], {icon: MapIconDiv});
        marker.bindPopup("<b>" + bname + "</b> " + g);

        latlngs = [[event['point_y'],event['point_x']], [event['point_prev_y'],event['point_prev_x']]];
        polyline = L.polyline(latlngs, {color: sc, opacity:0.8});

        myCollection.addLayer(marker);
        myCollection.addLayer(polyline);
    }
}

function express_dial_show() {
    $(".express_dial").addClass('express_dial_fixed');
}
function express_dial_hide() {
    $(".express_dial").removeClass('express_dial_fixed');
}

function change_mode(mode_new) {
    $(".mode_"+mode_selected).addClass("fhidden");
    $(".modec_"+mode_selected).removeClass('active');
    mode_selected = mode_new;
    $(".mode_"+mode_selected).removeClass("fhidden");
    $(".modec_"+mode_selected).addClass('active');
    var cur = $(".matrix").css('display');
    if (cur=="none") {
        matrix_inverto();
    }
}

function express_dial_init() {
    // mousedown touchstart click
    var eventus = "click";
    if (is_ios) {
        eventus = "touchstart";
    } else if (is_chrome) {
        eventus = "mousedown";
    }
    if ('webkitSpeechRecognition' in window) {
        $(".calc-backspace").html('<i class="microphone fa fa-microphone" title="Распознать голосовую команду"></i>');
    } else {
      $(".calc-backspace").html('<i class="fa fa-caret-left"></i>');
    }

    $(".calc").on(eventus, function(event) {
        var classes = $(this).attr('class').split(/\s+/);
        var cl = classes.pop().slice(5);
        var bt = "[btype="+express_dial_type+"]";

        if (cl == "go") {
          express_dial_go();
        } else {
          if (cl == "backspace") {
            // https://www.google.com/intl/en/chrome/demos/speech.html
            // http://shapeshed.com/html5-speech-recognition-api/
            // http://updates.html5rocks.com/2013/01/Voice-Driven-Web-Apps-Introduction-to-the-Web-Speech-API
            // flash_message("Голосовые команды работают только в Chrome", 2500);
            if ('webkitSpeechRecognition' in window) {
                if (!recognition_inited) {
                    recognition_init();
                }
                recognition.start();
                ajax_metric("recognition", 1);
                express_dial_hide();
            } else if (express_dial.length) {
              express_dial = express_dial.substring(0, express_dial.length - 1);
            }
          } else if (express_dial.length<3) {
            express_dial+=cl;
          }
          $(".busnumber").removeClass("calc-influence");
          if  (express_dial) {

              var express_dialz = bname_gen(express_dial_type, express_dial);
              var bus_ids = $(bt+"[bname^="+express_dialz+"]:not(.busfavor)");
              bus_ids.addClass("calc-influence");
              if ( bus_ids.length == 1) {
                express_dial_go();
              }
              // console.log(bus_ids);
          }
        }

        $(".calc-go").html(express_dial+' <i class="fa fa-bolt"></i>');
    });

     $(".calc-mode").on(eventus, function(event) {
        var classes = $(this).attr('class').split(/\s+/);
        var cl = classes.pop();

        if (cl=="calc-up") {
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
        if (cl=="calc-a") {
            express_dial_type=0;
        } else if (cl=="calc-t") {
            express_dial_type=1;
        } else if (cl=="calc-tv") {
            express_dial_type=2;
        }

    });
}

function bname_gen(ttype, n) {
    var bname = n;
    if (ttype == 1) {
        bname = "Т"+bname;
    } else if (ttype == 2) {
        bname = "ТВ"+bname;
    }
    return bname;
}

function express_dial_go() {
    var express_dial_fixed = $(".express_dial").hasClass('express_dial_fixed');
    express_dial_hide();
    if (!express_dial) {return;}

    var bt = "[btype="+express_dial_type+"]";
    var express_dialz = bname_gen(express_dial_type, express_dial);
    var bus_id = $(bt+"[bname="+express_dialz+"]:not(.busfavor)").attr('bus_id');
    express_dial="";
    $(".busnumber").removeClass("calc-influence");
    if (!bus_id) {return;}

    window.location.href = "#"+express_dialz;
    show_me_the_bus(bus_id);

    if (express_dial_fixed) {
      ajax_metric("express_dial", 1);
    } else{
      ajax_metric("express_dial_mini", 1);
    }
}

function rating_fill(data, force) {
  current_rating_data = data;
  var i;
  if (!reg_today) {
        $(".rate_cant_regday").removeClass('fhidden');
  }
  if ( data['error'] ) {
    $(".rating_scores").html(0);
    $(".rating_votes").html(0);
    $(".rating_status").html("нет оценки");
    $(".rating_comments").html(0);

    console.log(data['error']);
    return;
  }

  // console.log(data);
  var html_stars="";
  for (i=1; i<=5;i++) {
    if (data['rating_wilson'] > i || i-data['rating_wilson']<0.25) {
      html_stars = html_stars + '<i class="fa fa-star color-1"></i>';
    } else if ((i-data['rating_wilson']) > 0.25 && (i-data['rating_wilson'])<0.75) {
        console.log(i, data['rating_wilson'] );
        html_stars = html_stars + '<i class="fa fa-star-half-o color-1"></i>';
    } else {
      html_stars = html_stars + '<i class="fa fa-star-o"></i>';
    }
  }
  $(".rating_stars").html(html_stars);

  $(".rating_wilson").html("рейтинг: " + data['rating_wilson']);
  $(".votes_wilson").html(data['votes_wilson']);
  // $(".rating_comments").html(data['comments']);


  $(".rate_positive").html('<i class="fa-thumbs-o-up icon"></i>');
  $(".rate_negative").html('<i class="fa-thumbs-o-down icon"></i>');

  if ( data['myvote_ctime'] ) {
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

}

function rating_click(ev) {
    if (reg_today) {
        alert("Вы не можете голосовать в первый день");
        return;
    }

    if ( $(this).hasClass('rate_positive') ) {
        rate = 1;
        $(".rate_positive").html('<i class="fa-thumbs-up icon"></i>');
        $(".rate_negative").html('<i class="fa-thumbs-o-down icon"></i>');
    } else if ( $(this).hasClass('rate_negative') ) {
        rate = -1;
        $(".rate_negative").html('<i class="fa-thumbs-down icon"></i>');
        $(".rate_positive").html('<i class="fa-thumbs-o-up icon"></i>');
    }
}

function rating_submit(ev) {
    var msg = $("[name=msg]").val();
    if (msg === "" && rate !== 0) {
        alert("Оценка без сообщения не принимается");
        return;
    }
    if (msg !== "" && rate === 0) {
        alert("Сообщение без оценки не принимается");
        return;
    }

    vehicle = globus[current_vehicle_info];

    var request = $.ajax({
        url: "/ajax/vote_comment/",
        type: "post",
        data: {
            "u": current_vehicle_info,
            "g": vehicle['g'],
            "comment": msg,
            "rate": rate
        },
        dataType: "json",
        cache: false
    });
    request.done(function(msg) {
        if (msg['error']=="no gosnum") {
          alert("Извините, гос.номер не определен. Попробуйте позднее.");
        } else {
          rating_fill(msg, 1);
        }
    });
    vehicle_info_close();
    flash_message("Спасибо за отзыв!", 750);
    rate = 0;
}

function rating_statuser(rate, good) {
    var status;
    if (good) {
        if (rate>=4.9) {
            status = "высший класс";
        } else if (rate>=4.5) {
            status = "замечательный человек";
        } else if (rate>=3.5) {
            status = "хороший работник";
        } else if (rate>=2.5) {
            status = "работает посредственно";
        } else if (rate>=1.5) {
            status = "профессионально непригоден";
        } else if (rate>=1) {
            status = "мешает жить окружающим";
        } else {
            status = "нет оценки";
        }
    } else {
        if (rate>=5) {
            status = "замечательный человек";
        } else if (rate>=4) {
            status = "хороший работник";
        } else if (rate>=3) {
            status = "работает посредственно";
        } else if (rate>=2) {
            status = "профессионально непригоден";
        } else if (rate>=1) {
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
//         url: "http://www.bustime.ru/ajax/ava_change/",
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


function recognition_init() {
    recognition_inited = 1;
    recognition = new webkitSpeechRecognition();
    recognition.lang = "ru-RU";
    // recognition.continuous = true;
    // recognition.interimResults = true;
    recognition.onstart = function(event) {
      flash_message('Слушаю команду...<br/><br/>пример: автобус номер три', 0);
    };

    recognition.onresult = function(event) {
      // $('.flash_message').fadeOut('fast');
      for (var i = event.resultIndex; i < event.results.length; ++i) {
          var interim_transcript = '', parsed_num;
          if (event.results[i].isFinal) {
            recognition_result += event.results[i][0].transcript;
          } else {
            interim_transcript += event.results[i][0].transcript;
          }

          recognition_result = recognition_result.toLowerCase();
          var parsed = recognition_result.split(" ");
          var parse_fail = 0;
          var parsed_type = 0;

          if (parsed[0] == "автобус") {
            parsed_type = 0;
          } else if (parsed[0] == "троллейбус") {
            parsed_type = 1;
          } else if (parsed[0] == "трамвай") {
            parsed_type = 2;
          } else {
            parse_fail = 1;
          }

          if (parsed.length>2) {
            parsed_num = parseInt(parsed[2], 10);
          } else {
            parsed_num = parseInt(parsed[1], 10);
          }
          if (!parsed_num) {
           parse_fail = 1;
          }

          if (parse_fail) {
            flash_message('Не распознано: '+recognition_result, 1500);
          } else {
            var bname = bname_gen(parsed_type, parsed_num);
            var bus_id = $("[bname="+bname+"]:not(.busfavor)").attr('bus_id');
            if (!bus_id) {
              flash_message(parsed[0] +" " + parsed_num + " не найден", 2500);
              recognition_result = "";
              return;
            }
            flash_message(parsed[0] +" " + parsed_num, 1000);
            show_me_the_bus(bus_id);
            ajax_metric("mic_dial", 1);
          }
          recognition_result = "";
      }
    };
}

function check_float64() {
    if (typeof Float64Array != 'function' && typeof Float64Array != 'object') {
        return 0;
    }
    return 1;
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

// function preload() {
//     game.load.spritesheet('snowflakes', '/static/img/snowflakes.png', 17, 17);
//     game.load.spritesheet('snowflakes_large', '/static/img/snowflakes_large.png', 64, 64);

// }

// var max = 0;
// var front_emitter;
// var mid_emitter;
// var back_emitter;
// var update_interval = 4 * 60;
// var i = 0;

// function create() {
//     back_emitter = game.add.emitter(game.world.centerX, -32, 300);
//     back_emitter.makeParticles('snowflakes', [0, 1, 2, 3, 4, 5]);
//     back_emitter.maxParticleScale = 0.6;
//     back_emitter.minParticleScale = 0.2;
//     back_emitter.setYSpeed(20, 100);
//     back_emitter.gravity = 0;
//     back_emitter.width = game.world.width * 1.5;
//     back_emitter.minRotation = 0;
//     back_emitter.maxRotation = 40;

//     mid_emitter = game.add.emitter(game.world.centerX, -32, 120);
//     mid_emitter.makeParticles('snowflakes', [0, 1, 2, 3, 4, 5]);
//     mid_emitter.maxParticleScale = 1.2;
//     mid_emitter.minParticleScale = 0.8;
//     mid_emitter.setYSpeed(50, 150);
//     mid_emitter.gravity = 0;
//     mid_emitter.width = game.world.width * 1.5;
//     mid_emitter.minRotation = 0;
//     mid_emitter.maxRotation = 40;

//     front_emitter = game.add.emitter(game.world.centerX, -32, 25);
//     front_emitter.makeParticles('snowflakes_large', [0, 1, 2, 3, 4, 5]);
//     front_emitter.maxParticleScale = 0.75;
//     front_emitter.minParticleScale = 0.25;
//     front_emitter.setYSpeed(100, 200);
//     front_emitter.gravity = 0;
//     front_emitter.width = game.world.width * 1.5;
//     front_emitter.minRotation = 0;
//     front_emitter.maxRotation = 40;

//     changeWindDirection();

//     back_emitter.start(false, 14000, 20);
//     mid_emitter.start(false, 12000, 40);
//     front_emitter.start(false, 6000, 1000);

// }

// function update() {

//     i++;

//     if (i === update_interval)
//     {
//         changeWindDirection();
//         update_interval = Math.floor(Math.random() * 20) * 60; // 0 - 20sec @ 60fps
//         i = 0;
//     }

// }

// function changeWindDirection() {

//     var multi = Math.floor((max + 200) / 4),
//         frag = (Math.floor(Math.random() * 100) - multi);
//     max = max + frag;

//     if (max > 200) max = 150;
//     if (max < -200) max = -150;

//     setXSpeed(back_emitter, max);
//     setXSpeed(mid_emitter, max);
//     setXSpeed(front_emitter, max);

// }

// function setXSpeed(emitter, max) {
//     emitter.setXSpeed(max - 20, max);
//     emitter.forEachAlive(setParticleXSpeed, this, max);
// }

// function setParticleXSpeed(particle, max) {
//     particle.body.velocity.x = max - Math.floor(Math.random() * 30);

// }



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
        this._map.toggleFullscreen();
    },

    _toggleTitle: function() {
        this.link.title = this.options.title[this._map.isFullscreen()];
    }
});

L.Map.include({
    isFullscreen: function () {
        return this._isFullscreen || false;
    },

    toggleFullscreen: function () {
        var container = this.getContainer();
        if (this.isFullscreen()) {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.webkitCancelFullScreen) {
                document.webkitCancelFullScreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            } else {
                L.DomUtil.removeClass(container, 'leaflet-pseudo-fullscreen');
                this._setFullscreen(false);
                this.invalidateSize();
                this.fire('fullscreenchange');
            }
        } else {
            if (container.requestFullscreen) {
                container.requestFullscreen();
            } else if (container.mozRequestFullScreen) {
                container.mozRequestFullScreen();
            } else if (container.webkitRequestFullscreen) {
                container.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
            } else if (container.msRequestFullscreen) {
                container.msRequestFullscreen();
            } else {
                L.DomUtil.addClass(container, 'leaflet-pseudo-fullscreen');
                this._setFullscreen(true);
                this.invalidateSize();
                this.fire('fullscreenchange');
            }
        }
    },

    _setFullscreen: function(fullscreen) {
        this._isFullscreen = fullscreen;
        var container = this.getContainer();
        if (fullscreen) {
            L.DomUtil.addClass(container, 'leaflet-fullscreen-on');
        } else {
            L.DomUtil.removeClass(container, 'leaflet-fullscreen-on');
        }
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
        this.fullscreenControl = new L.Control.Fullscreen();
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