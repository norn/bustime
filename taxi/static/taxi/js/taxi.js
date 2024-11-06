/*
Audio library:
https://github.com/goldfire/howler.js#documentation
*/
var socket;
var city_id = parseInt(document.getElementById("taxi.js").getAttribute("data-city_id"));
var user_id = parseInt(document.getElementById("taxi.js").getAttribute('data-user_id'));
var taxiuser_id = parseInt(document.getElementById("taxi.js").getAttribute('data-taxiuser_id'));
var usePositionWatch_last = null;   // время последжней отправки координат
var csrftoken = null;
var position_last = null; // сохранённая позиция
var map_taxi = null; //
var layer_markers = null;
var layer_route = null;
const MAP_MODE_TAXI = 0;
const MAP_MODE_PASS = 1
const MAP_MODE_BOUNDS = 2
var map_mode = MAP_MODE_BOUNDS;


/* mobile device check */
window.ismobile = function() {
  var check = false;
  (function(a){if(/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce|xda|xiino|android|ipad|playbook|silk/i.test(a)||/1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(a.substr(0,4))) check = true;})(navigator.userAgent||navigator.vendor||window.opera);
  return check;
};


// Usage: let csrftoken = window.getCookie('csrftoken');
window.getCookie = function (name) {
    let cookieValue = null;
    if (document.cookie && document.cookie != '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


window.addEventListener('load', function () {
    console.log('taxi.js:load');
});


function audiocontext_enable(){
    //console.log('audiocontext_enable');
    let AudioContext = window.AudioContext || window.webkitAudioContext;
    if(AudioContext){
        new AudioContext().resume();
    }
}   // audiocontext_enable


function websconnect() {
    csrftoken = window.getCookie('csrftoken');

    socket = io();

    // http://stackoverflow.com/questions/10405070/socket-io-client-respond-to-all-events-with-one-handler
    var onevent = socket.onevent;
    socket.onevent = function (packet) {
        var args = packet.data || [];
        onevent.call (this, packet);    // original call
        packet.data = ["*"].concat(args);
        onevent.call(this, packet);      // additional call to catch-all
    };

    socket.on('connect', function() {
        //socket.emit('authentication', {username: user, password: "", os:"web"});
        socket.emit('join', `ru.bustime.taxi_${city_id}`);
        // socket.emit('join', "ru.bustime.us__" + us_id);
        //socket.emit('join', "ru.bustime.city__" + city);

        router(new Date() + ": Socket connected");
    });

    socket.on('disconnect', function() {
        router(new Date() + ": Socket disconnect");
    });

    socket.on("*", function(event, data) {
        if( typeof(data) == "string" ){
            data = JSON.parse(data);
        }
        //console.log('socket.on:', data);
        // {"app": "taxi", "to": [97267, 12], "cmd": "offer_add", "data": {"value": 39}}
        if(data.app == "taxi" && (data.to.indexOf(user_id) >= 0 || data.to.indexOf('*') >= 0 )){
            router(data);
        }
    });
}   // websconnect


// общий router
function router(data) {
    // страницы могут расширить функции роутера:
    if (typeof(routerExtend) == "function") {
        routerExtend(data);
    }
    else {
        console.log('router:', data);
    }
}   // router


function start_location_service() {
    console.log("Start location service");
    if (navigator.geolocation) {
        // https://developer.mozilla.org/en-US/docs/Web/API/PositionOptions
        // будет вызываться при каждом изменении position (в Firefox - с интервалом timeout и без изменений)
        navigator.geolocation.watchPosition(usePositionWatch, noPosition, {
                                            enableHighAccuracy: true,   // использовать систему GPS, если есть
                                            maximumAge: 0,              // не использовать кэширование данных о местоположении
                                            timeout: 5000 });   // период времени (ms), в течение которого страница будет ожидать получения данных геолокации, прежде чем считать попытку неудачной
    }
}   // start_location_service


// вызывается 1 раз в 5 секунд
function usePositionWatch(position) {
    let now = new Date();
    // если ни разу не передавали координаты, то time_delta = 31 чтобы отправить сразу
    let time_delta = usePositionWatch_last ? Math.round((now.getTime() - usePositionWatch_last.getTime()) / 1000) : 31;
    let speed = Math.round(position.coords.speed * 3.6, 2); // convert m/s to km/h == x * 60*60/1000.0
    if( speed > 10 ){
        speed = Math.round(speed, 0);
    }
    let heading = Math.round(position.coords.heading, 0);

    //console.log(`usePositionWatch timestamp=${position.timestamp} lat=${position.coords.latitude} lon=${position.coords.longitude} speed=${speed} time_delta=${time_delta}`);

    // передаём если скорость > пешехода (едем) или раз в 30 сек.
    if (speed > 6 || time_delta > 30) {
        usePositionWatch_last = now;
        position_last = {
            city_id: city_id,
            user_id: user_id,
            /* на время отладки
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            */
            lat: (user_id == 12 ? 59.93631 : 59.91489),
            lon: (user_id == 12 ? 30.23648 : 30.45792),

            accuracy: position.coords.accuracy, // точность определенного местоположения в метрах, чем меньше, тем лучше
            speed: speed,      // на данный момент эти свойства не поддерживаются ни одним браузером
            heading: heading,  // на данный момент эти свойства не поддерживаются ни одним браузером
            timestamp: position.timestamp,  // local time, NOT GPS for desktop browser!
            localtime: +now,
        };
        gps_send(position_last);
    }   // if (speed > 6 || time_delta > 30)
    // TODO: браузеры не заполняют поля "speed", "heading", сделать рассчет на основе сохранённой предыдущей отметки

    if (typeof(showOnMap) == "function") {
        showOnMap(position_last); // определить функцию показа на карте там, где необходимо
    }
}   // usePositionWatch


function gps_send(pos) {
    //console.log('gps_send', pos);
    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/gps_send/",
        data: pos,
    })
    .done(function(data) {
        if(data){
            if( !data.error ){
                Cookies.set('taxi_send', JSON.stringify(pos), { expires: 7, path: '/taxi', sameSite: 'lax' });   // https://github.com/js-cookie/js-cookie
            }
            else {
                console.log("gps_send", data.error);
            }
        }
        else {
            console.log("gps_send: no data");
        }
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.log("gps_send error:", errorThrown);
    });
}   // gps_send


function noPosition(error) {
    if( !error.TIMEOUT ){
        console.log("noPosition", error);
    }
    /*
    $(".speed_show").css("background-color", '#f99');

    switch (error.code) {
        case error.PERMISSION_DENIED:
            $(".speed_show").html("GPS запрет");
            //ajax_metric("stop_name_gps_denied", 1);
            //"User denied the request for Geolocation."
            break;
        case error.POSITION_UNAVAILABLE:
            $(".speed_show").html("GPS нет");
            //"Location information is unavailable."
            break;
        case error.TIMEOUT:
            $(".speed_show").html("GPS таймаут");
            //"The request to get user location timed out."
            break;
        case error.UNKNOWN_ERROR:
            $(".speed_show").html("GPS ошибка " + error.code);
            break;
    }
    */
}   // noPosition


function get_user_pos(user_id){
    //console.log('get_user_pos', user_id);
    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/users/pos/",
        data: {
            'user_id': user_id,
        },
    })
    .done(function(data) {
        //console.log("get_user_pos", data);
        Cookies.set('taxi_pos', JSON.stringify(pos), { path: '/taxi', sameSite: 'lax' });   // seanse
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        //console.log("get_user_pos error:", errorThrown);
    });
}   // get_user_pos


// https://ruseller.com/lessons.php?rub=43&id=2726
function vibrate() {
    if ("vibrate" in navigator) {
        navigator.vibrate([700, 300, 700]);
    }
}   // vibrate


// мигание бордером j раз цветом color
function flashBorder(element, j, color, bstyle)
{
    let i = j * 2;
    color = color || "red";
    bstyle = bstyle || "1px solid";
    let border = element.css('border') || `${element.css('border-top-width')} ${element.css('border-top-style')} ${element.css('border-top-color')}` || 'none';
    let timer = setInterval(function () {
        if(i-- % 2){
            element.css('border', `${bstyle} ${color}`);
        }
        else {
            element.css('border', border);
        }
        if(i < 0){
            clearInterval(timer);
            element.css('border', border);
        }
    }, 100);
}   // flashBorder


// мигание бакграундом j раз цветом color
function flashBkg(element, j, color)
{
    let i = j * 2;
    color = color || "red";
    let bkg = element.css('background-color') || 'inherit';
    let timer = setInterval(function () {
        if(i-- % 2){
            element.css('background-color', color);
        }
        else {
            element.css('background-color', bkg);
        }
        if(i < 0){
            clearInterval(timer);
            element.css('background-color', bkg);
        }
    }, 100);
}   // flashBkg


function decodeCookie(cname){
    let retval = {},
        cval = Cookies.get(cname),
        aval = cval.split('|');
    if( !cval || !aval.length ) {
        return retval;
    }
    switch(cname){
        case 'taxi_user':{
            retval = {
                'user_id': parseInt(aval[0]),
                'taxiuser_id': parseInt(aval[1]),
                'driver': parseInt(aval[2]),
                'gps_on': parseInt(aval[3]),
            };
            break;
        }
        case 'taxi_send':{
            retval = JSON.parse(cval);
            break;
        }
    }   // switch(cname)
    return retval;
}   // decodeCookie


function set_taxi_user(who, active){
    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/setuser/",
        data: {
            'taxiuser_id': taxiuser_id,
            'who': who,
            'active': active,
        },
    })
    .done(function(data) {
        console.log("set_taxi_user", data);
        if( !data.error ){
            Cookies.set('taxi_user', data.result, { path: '/', sameSite: 'lax', expires: Infinity });
            taxiuser.driver = who == 'driver';
            taxiuser.gps_on = parseInt(active) > 0;
        }
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        //console.log("get_user_pos error:", errorThrown);
    });
}


function map_init(div_id){
    // https://bustime.loc/static/js/uevents-on-map.js?v=3
    // https://leafletjs.com/reference.html
    // https://jsfiddle.net/ew1jned8/1/
    // bustime/templates/transport.html
    let pos = position_last || decodeCookie('taxi_send');
    pos = (typeof(pos) == "string" ? JSON.parse(pos) : pos);
    pos = {'lat': pos.lat, 'lon': pos.lon};

    let baseMaps = {
        "OSM    ": new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                        minZoom: 5,
                        maxZoom: 18
                    }),
        "Спутник": L.tileLayer('//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                        maxZoom: 18,
                        subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
                    }),
        "Google ": L.tileLayer('//{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                        maxZoom: 18,
                        subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
                    })
    };

    map_taxi = L.map(div_id, {
        scrollWheelZoom: true,
        fullscreenControl: true,
        layers: [ baseMaps["OSM    "] ],
        center: [pos.lat, pos.lon],
        zoom: 13
    });

    L.control.layers(baseMaps).addTo(map_taxi);

    layer_markers = L.featureGroup().addTo(map_taxi);
    layer_route = L.featureGroup().addTo(map_taxi);
}   // map_init


function map_set_marker(pos, driver, marker){
    if(layer_markers){
        // https://leafletjs.com/reference.html#marker
        if(marker){
            marker.setLatLng([pos.lat, pos.lon]);
            if( marker.options.is_driver != driver) {
                marker.options.is_driver = driver;
                marker.setIcon(L.icon({
                            iconUrl: (driver ? '/static/taxi/img/icon_d_32.png' : '/static/taxi/img/icon_p_32.png'),
                            iconSize:     [32, 32], // size of the icon
                            iconAnchor:   [16, 16], // point of the icon which will correspond to marker's location
                            className: 'blinking',  // https://stackoverflow.com/questions/41884070/how-to-make-markers-in-leaflet-blinking
                        }));
            }
        }
        else {
            marker = L.marker([pos.lat, pos.lon], {
                    icon: L.icon({
                            iconUrl: (driver ? '/static/taxi/img/icon_d_32.png' : '/static/taxi/img/icon_p_32.png'),
                            iconSize:     [32, 32], // size of the icon
                            iconAnchor:   [16, 16], // point of the icon which will correspond to marker's location
                            className: 'blinking',  // https://stackoverflow.com/questions/41884070/how-to-make-markers-in-leaflet-blinking
                        }),
                    opacity: .8,
                    draggable: false,
                    // свои свойства (доступны в marker.options):
                    is_driver: driver,
                })                                                                    //   x   y
                .bindTooltip((driver ? 'Такси' : 'Пассажир'), {permanent: false, offset: [-16, 0]})
                .addTo(layer_markers);
        }
    }   // if(layer_markers)
    else {
        marker = null;
    }
    return marker;
}   // map_set_marker


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
function map_boundsto(layer){
    layer = layer || layer_markers;
    if(map_taxi && layer){
        map_taxi.flyToBounds(layer.getBounds());
    }
}   // map_boundsto


// добавление объекта GeoJSON на слой
function map_addObject(geojson, layer, color){
    layer = layer || layer_route;
    color = color || "#0033FF";
    try {
        layer.clearLayers();    // TODO: функция должна возвращать объект, который потом и удалять, а не все объекты слоя
        L.geoJSON(geojson, {
            style: function (feature) {
                return {color: color};
            }
        }).addTo(layer);
    }
    catch (err) {
        return err;
    }
    return null;
}   // map_addObject


// https://nominatim.org/release-docs/develop/api/Reverse/
// success, error - callbacks
function map_LonLat2Addr(lon, lat, success, error){
    if( lon && lat && typeof(success) == "function"){
        $.ajax({
            method: "GET",
            url: `/ajax/nominatim/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=ru&addressdetails=1`,
        })
        .done(function(data) {
            if(data.Exception){
                if( typeof(error) == "function" ){
                    error(data.Exception);
                }
            }
            else {
                if( success ){
                    success(data);
                }
            }
        })
        .fail(function(jqXHR, textStatus, errorThrown) {
            $("#messages").html(`<div class="ui error message">${errorThrown}</div>`);
        });
    }   // if( lon && lat )
}   // map_LonLat2Addr


// https://nominatim.org/release-docs/develop/api/Search/
// https://www.geoapify.com/nominatim-geocoder
// https://bustime.loc/ajax/nominatim/search?q="1, улица салавата юлаева, Курган, Россия"
// https://bustime.loc/ajax/nominatim/search?q=аптека+in+Ленина+in+Курган+in+Россия
// https://bustime.loc/ajax/nominatim/search?q=лиговский+in+Санкт-Петербург+in+Россия
// success, error - callbacks
function map_Addr2LonLat(addr, success, error){
    if( addr && typeof(addr) == "string" && addr.length > 4 ){
        // TODO: доделать поиск координат по адресу (см. bustime/views.py::ajax_nominatim())
    }   // if( addr
}   // map_LonLat2Addr


function deleteOrders(order_id){
    $.ajax({
        method: "POST",
        headers: {'X-CSRFToken': csrftoken},
        url: "/carpool/api/orders/delete/",
        data: {
            user_id: user_id,
            order_id: order_id,
        }
    })
    .done(function(data) {
        if(data.error){
            $("#messages").html(`<div class="ui error message">${data.error}</div>`);
        }
        else {
            window.location.href = "/carpool/orders/";
        }
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        if(errorThrown){
            $("#messages").html(`<div class="ui error message">${errorThrown}</div>`);
        }
    });
}   // deleteOrders


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

   /* угловое расстояние в радианах */
   let a = Math.acos(Math.sin(lat1) * Math.sin(lat2) + Math.cos(lat1) * Math.cos(lat2) * Math.cos(deltalon));
   let retval = {
       'distance': Math.round(EARTH_RADIUS * a),    /* метры */
       'heading': 0,
       'speed': 0
   }

    /* расчет направления
    http://edu.dvgups.ru/METDOC/ITS/GEOD/LEK/l2/L3_1.htm
    Обратная геодезическая задача
    заключается в том, что при известных координатах точек А( XA, YA ) и В( XB, YB )
    необходимо найти длину AB и направление линии АВ: румб и  дирекционный угол
    */
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
    else if( deltalat = 0 ) {
        if( deltalon > 0 ) {      // 1 четверть (СВ)
            retval['heading'] = 90;
        }
        else if( deltalon < 0 ) { // 3 четверть (ЮЗ)
            retval['heading'] = 270;
        }
    }

    deltatime = deltatime || 0;
    if( deltatime > 0 ){
        let speed = retval['distance'] / deltatime * 3.6;   /* км/ч */
        retval['speed'] = parseFloat(speed.toFixed( speed > 10 ? 0 : 2 ));
    }

   return retval;
}   // distance