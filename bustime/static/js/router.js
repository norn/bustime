var osm_stops0, osm_stops1, icon_stop0, icon_stop1, vue, all_stops;
var wpos0=-1, wpos1=-1;
var userlog = window.sessionStorage.getItem("userlog");
userlog = (userlog ? JSON.parse(window.sessionStorage.getItem("userlog")) : []);
if( userlog.length > 0 ){
    if( userlog[0].bus != bus_id || userlog[0].city != bus_city_id ) {    // сменился маршрут без сохранения старого
        userlog = [];
    }
}

function onMapClick(e) {
        // alert("You clicked the map at " + e.latlng);
        var popup = L.popup();
        popup
                .setLatLng(e.latlng)
                .setContent("Click: " + e.latlng.toString())
                .openOn(map);
}
function markerOnClick(m) {
        var lng = m.latlng.lng, lat = m.latlng.lat, drops_current;
        for (var key in busstops) {
                b = busstops[key];
                if (b['x'] == lng && b['y'] == lat) {
                        console.log(b);
                        // drops_current = $('.ui.dropdown').dropdown("get value");
                        // if (drops_current[0] == drops_current[1] &&
                        //     drops_current[0]== b['id'].toString()) {
                        //     var check = confirm("Добавить эту остановку?");
                        //     alert('Я не знаю в какой столбик добавить, поэтому пока не активно');
                        // } else {
                                $(".bs_selected").html(b['name']+" id="+ b['id']);
                                $('.ui.dropdown').dropdown('set selected',  b['id']);
                        // }
                }
        }
}
function iconizer(url, iconSize) {
        return new L.icon({
                iconUrl: url,
                iconSize: iconSize,
                iconAnchor: [iconSize[0] / 2, iconSize[1]],
                popupAnchor: [0, -iconSize[1]],
                shadowUrl: ''
        });
}

function js_page_extra() {
        console.log("Route edit mode");

        var osm = new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                minZoom: 5,
                maxZoom: 18
        });
        var googleStreets = L.tileLayer('//{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                maxZoom: 18,
                subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
        });
        var googleSat = L.tileLayer('//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                maxZoom: 18,
                subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
        });
        icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
        icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);

        var baseMaps = {
                "Спутник": googleSat,
                "Google": googleStreets,
                "OSM": osm
        };

        map = L.map('lmap', {
                scrollWheelZoom: true,
                fullscreenControl: true,
                layers: [osm],
                center: [US_CITY_POINT_Y, US_CITY_POINT_X],
                zoom: 10
        });
        // map.on('click', onMapClick);

        osm_stops0 = L.featureGroup().addTo(map);
        osm_stops1 = L.featureGroup().addTo(map);
        all_stops = L.featureGroup();

        var marker, b, i;
        for (i = 0; i < route[0].length; i++) {
                b = busstops[route[0][i]];
                marker = L.marker([b['y'], b['x']], { icon: icon_stop0 });
                marker.bindTooltip(b['name'] + "<br/>-><br/>" + b['moveto']);
                osm_stops0.addLayer(marker);
        }
        for (i = 0; i < route[1].length; i++) {
                b = busstops[route[1][i]];
                marker = L.marker([b['y'], b['x']], { icon: icon_stop1 });
                marker.bindTooltip(b['name'] + "<br/>-><br/>" + b['moveto']);
                osm_stops1.addLayer(marker);
        }

        var overlayMaps = {
                "Направление 1": osm_stops0,
                "Направление 2": osm_stops1,
                "Все остановки": all_stops,
        };
        L.control.layers(baseMaps, overlayMaps).addTo(map);
        if (route[0].length > 0) {
                map.fitBounds(osm_stops0.getBounds());
        }

        icon_stops = iconizer('/static/img/busstop_icon_24.png', [24, 24]);
        console.log(Object.keys(busstops).length+" stops");
        //if (Object.keys(busstops).length < 20000) {
        //    for (var key in busstops) {
        //        b = busstops[key];
        //        L.marker([b['y'], b['x']], { icon: icon_stops, title: b['name'] }).on('click', markerOnClick).addTo(all_stops);
        //    }
        //}

        // http://vuejs.org/
        vue = new Vue({
                el: '.routes',
                data: {
                        route: route,
                        busstops: busstops
                }
        });


        $('.ui.dropdown').dropdown( {'fullTextSearch': 'exact'} ); //{'fullTextSearch': true}

        $(".add_button").click(busstop_add);
        $("#route0").on("click", ".delete_button", busstop_delete);
        $("#route1").on("click", ".delete_button", busstop_delete);
        $(".container").on("click", ".save_button", busstop_save);
        $(".container").on("click", ".up_button", busstop_move);
        $(".container").on("click", ".down_button", busstop_move);
        $(".container").on("click", ".anchor_button", busstop_anchor);
        $(".container").on("click", ".marker_button", busstop_marker);
        map.on('click', onMapClick);
        map.on('zoomend', smart_busstops_draw);
        map.on('moveend', smart_busstops_draw);
}
function smart_busstops_draw() {
                if (map.getZoom() >= 14) {
                    all_stops.clearLayers();
                    var bounds = map.getBounds();
                    //console.log(bounds);
                    for (var key in busstops) {
                            b = busstops[key];
                            if (b['x'] > bounds['_southWest']['lng'] &&
                                    b['x'] < bounds['_northEast']['lng'] &&
                                    b['y'] > bounds['_southWest']['lat'] &&
                                    b['y'] < bounds['_northEast']['lat']) {
                                        L.marker([b['y'], b['x']], { icon: icon_stops, title: b['name'] }).on('click', markerOnClick).addTo(all_stops).bindPopup(b['name']);
                                    }
                    }
                    map.addLayer(all_stops);
                } else {
                        map.removeLayer(all_stops);
                }
}

function busstop_move() {
    var hhh;
    var dir = $(this).parent().parent().parent().parent().prop('id');
    var direction = (dir == "route0" ? 0 : 1);
    var bs_id = $(this).parent().prop('id');
    var move = $(this).attr("class").split(' ');
    if (move.indexOf("up_button") > 0) {
        move = -1;
        hhh = $(this).parent().parent().prev();
    } else {
        move = 1;
        hhh = $(this).parent().parent().next();
    }

    hhh.addClass('color-0-bg');
    setTimeout(function() {
            hhh.removeClass('color-0-bg');
    }, 800);

    bs_id = bs_id.split('_')[1];
    bs_id = parseInt(bs_id, 10);
    console.log(dir); // route[0]
    console.log(bs_id); // 7910
    console.log(move); // 1 or -1
    var nr;

    if (dir == "route0") {
            nr =  route[0];
    } else {
            nr =  route[1];
    }
    var index = nr.indexOf(bs_id);
    var index_moved = index+move
    if (index_moved < 0 || index_moved >= nr.length ) {
        return
    }
    var b = nr[index];
    nr[index] = nr[index+move];
    nr[index+move] = b;
    // console.log(nr);
    if (dir == "route0") {
            vue.route = {0:nr, 1:route[1]};
    } else {
            vue.route = {1:nr, 0:route[0]};
    }
    userlog.push({'city':us_city, 'bus': bus_id, 'direction':direction, 'nbusstop_id':bs_id, 'name':busstops[bs_id]['name'], 'order':index_moved, 'note': `Перемещение остановки ${bs_id}: dir:${direction} order:${index}=>${index_moved}`});
    window.sessionStorage.setItem("userlog", JSON.stringify(userlog));
}


function busstop_add() {
    var dir = $(this).closest('table').parent().prop('id');
    var direction = (dir == "route0" ? 0 : 1);
    var bs_id;

    if (dir == "route0") {
        bs_id = $(".busstop_selector_0 > select").val();
        bs_id = parseInt(bs_id, 10);
        if (route[0].indexOf(bs_id)>-1) {
                alert("Такая остановка уже есть!");
                return;
        }
        if (wpos0 == -1) {
                route[0].push(bs_id);
        } else {
                route[0].splice(wpos0+1, 0, bs_id);
                wpos0++;
                wpos_blue();
        }
        alert("Остановка добавлена");
    }
    else {
        bs_id = $(".busstop_selector_1 > select").val();
        bs_id = parseInt(bs_id, 10);
        if (route[1].indexOf(bs_id)>-1) {
                alert("Такая остановка уже есть!");
                return;
        }
        if (wpos1 == -1) {
                route[1].push(bs_id);
        } else {
                route[1].splice(wpos1+1, 0, bs_id);
                wpos1++;
                wpos_blue();
        }
        alert("Остановка добавлена");
    }
    console.log(bs_id);

    var index = route[direction].indexOf(bs_id);
    userlog.push({'city':us_city, 'bus': bus_id, 'direction':direction, 'nbusstop_id':bs_id, 'name':busstops[bs_id]['name'], 'order':index, 'note': `Добавление остановки ${bs_id}: dir:${direction} order:${index}`});
    window.sessionStorage.setItem("userlog", JSON.stringify(userlog));
}

function busstop_delete() {
    var check = confirm("Убрать эту остановку из маршрута?");
    if (!check) {return}
    var dir = $(this).parent().parent().parent().prop('id');
    var direction = (dir == "route0" ? 0 : 1);
    var bs_id = $(this).prev().prop('id');
    bs_id = bs_id.split('_')[1];
    bs_id = parseInt(bs_id, 10);

    console.log("delete " + bs_id + ", " + dir);

    if (dir == "route0") {
            var index = route[0].indexOf(bs_id);
            route[0].splice(index, 1);
    } else {
            var index = route[1].indexOf(bs_id);
            route[1].splice(index, 1);
    }
    userlog.push({'city':us_city, 'bus': bus_id, 'direction':direction, 'nbusstop_id':bs_id, 'name':busstops[bs_id]['name'], 'order':index, 'note': `Удаление остановки ${bs_id}: dir:${direction} order:${index}`});
    window.sessionStorage.setItem("userlog", JSON.stringify(userlog));
}

function wpos_blue() {
        $('.blue').removeClass('blue');
        if (wpos0 != -1) {
                $('#route0>.list>.item>.buttons>.anchor_button:eq('+wpos0+')').addClass('blue');
        }
        if (wpos1 != -1) {
                $('#route1>.list>.item>.buttons>.anchor_button:eq('+wpos1+')').addClass('blue');
        }
}

function busstop_anchor() {
        var dir = $(this).parent().parent().parent().parent().prop('id');
        var bs_id = $(this).parent().prop('id');
        bs_id = bs_id.split('_')[1];
        bs_id = parseInt(bs_id, 10);
        if (dir == "route0") {
                wpos0 = route[0].indexOf(bs_id);
        } else {
                wpos1 = route[1].indexOf(bs_id);
        }
        wpos_blue();
        console.log("anchor " + bs_id + ", " + dir);

        var hhh = $(this).parent().parent();
        hhh.addClass('color-0-bg');

        setTimeout(function() {
                hhh.removeClass('color-0-bg');
        }, 800);
}

function busstop_marker() {
        // $('.color-1-bg').removeClass('color-1-bg');
        var hhh = $(this).parent().parent();
        if (hhh.hasClass('color-1-bg')) {
                hhh.removeClass('color-1-bg');
        } else {
                hhh.addClass('color-1-bg');
        }
}

function busstop_save() {
    // console.log(route);
    var request = $.ajax({
                url: "/ajax/route_edit_save/",
                type: "post",
                data: {
                        bus_id: bus_id,
                        route: JSON.stringify(route),
                        userlog: JSON.stringify(userlog)
                },
                dataType: "json",
                cache: false
    });
    userlog=[];
    window.sessionStorage.setItem("userlog", JSON.stringify(userlog));
    alert("Данные сохранены");
}

function map_center_me() {
        if (navigator.geolocation) {
                var options = {
                                        enableHighAccuracy: true,
                                        maximumAge: 0 };
                navigator.geolocation.getCurrentPosition(usePosition, noPosition, options);
        }

}

function bus_stop_set(lng, lat) {
        var popup = L.popup();
        popup
                .setLatLng([lat, lng])
                .setContent("Остановка здесь")
                .openOn(map);
        $("[name=point]").val( lng+";"+lat );
}

function onMapClick(e) {
        var lat,lng = e.latlng;
        lat = e.latlng.lat.toFixed(7);
        lng = e.latlng.lng.toFixed(7);
        bus_stop_set(lng, lat);
}

function usePosition(location) {
    //alert(location.coords.accuracy);
    var lat,lng;
    lat = location.coords.latitude.toFixed(7);
    lng = location.coords.longitude.toFixed(7);
    map.panTo(new L.LatLng(lat, lng));
    bus_stop_set(lng, lat);
}

function noPosition(error) {
        console.log("GPS error: " + error.code);
}

// 31.01.19 отправка запроса на копирование части маршрута
// direction = 0 | 1 - в какое направление будем вставлять скопированное
function ajax_route_copy_bus_part(direction)
{
        //console.log("ajax_route_copy_bus_part: city_name=", $('#city_name').val());

        // запрос на список маршрутов города с направлениями
        $.ajax({
                url: "/ajax/ajax_route_get_bus_city/",
                type: "post",
                data: {
                        city_id: $('#city_id').val(),
                        city_name: $('#city_name').val(),
                },
                dataType: "json",
                contentType: "application/x-www-form-urlencoded;charset=UTF-8",
                cache: false,
                success: function(data){
                        response_route_copy_bus_part(data, direction);  // обработчик ответа
                },
                error: function(jqXHR, sStatus, sErrorText){
                        console.log("ajax_route_copy_bus_part: ajax:", sStatus, sErrorText);
                }
        });
}   // function ajax_route_copy_bus_part


// ответ на запрос на копирование части маршрута
// data: [][bus.id, bus.name, bus.slug, rout0[], rout1[]]
var modalBusArray = null;
function response_route_copy_bus_part(data, direction)
{
    modalBusArray = data;

    // заполняем меню маршрутов
    $("#modal-bus-select").empty();    // $('#modal-bus-select li').remove();
    $.each(data, function (i, item) {
            $('#modal-bus-select').append($('<option>', {
                    value: item[0],
                    text : item[1]
            }));
    });
    $("#modal-bus-select").val(data[0][0]);

    // заполняем меню отсановок для первого маршрута для направления 0
    fillModalStops(data[0][3 + parseInt($("#modal-dir-select").val())]);

    // запоминаем destination route direction
    $("#bus-copy-dest-dir").val(direction);
    // заполняем меню выбора места вставки новых остановок
    fillModalInsertTypeSelect(route[direction]);

    // Показать диалог копирования
    document.getElementById('bus-copy-dialog').style.display = "block";
}   // function response_route_copy_bus_part

// заполняем меню выбора места вставки новых остановок
function fillModalInsertTypeSelect(sourceRoute)
{
        $("#modal-insert-type-select").empty();

        $('#modal-insert-type-select').append($('<option>', {
                value: "-1",
                text : "В конец"
        }));

        $('#modal-insert-type-select').append($('<option>', {
                value: "-2",
                text : "В начало"
        }));

        $.each(sourceRoute, function (i, item) {
                if( i > 0 ){ // ибо вставлять перед первым это "В начало"
                        $('#modal-insert-type-select').append($('<option>', {
                                value: item,
                                text : "Перед: " + busstops[item].name
                        }));
                }
        });

        $("#modal-insert-type-select").val("-1");
}   // function fillModalInsertTypeSelect

function fillModalStops(stops)
{
        var li, name;

        $("#modal-stops-ul").empty();
        $.each(stops, function (i, item) {
                name = typeof(busstops[item]) === 'undefined' ? 'undefined' : busstops[item].name;

                li = '<table style="border-collapse: collapse"><tr>';
                li += '<td style="width:2em;padding:4px"><input name="modal-stop[]" type="checkbox" value="'+item+'" checked="checked"></td>';
                li += '<td style="padding:4px">'+name+'</td>';
                li += '</tr></table>';

                $("#modal-stops-ul").append('<li class="ui divided">'+li+'</li>');
        });
        $('#modal-cb-all').prop('checked', 'checked');
}   // function fillModalStops

// меню маршрута
function modalBusSelectChange(selectedIndex)
{
        $("#modal-dir-select").val("0");
        fillModalStops(modalBusArray[selectedIndex][3 + parseInt($("#modal-dir-select").val())]);
}   // function modalBusSelectChange

// меню направления
function modalDirSelectChange(value)
{
        var selectedIndex = parseInt($("#modal-bus-select").prop('selectedIndex'));
        fillModalStops(modalBusArray[selectedIndex][3 + parseInt(value)]);
}   // function modalDirSelectChange

// чекбокс "выбрать всё"
function modalCbAllChange(checkboxall)
{
        jQuery("input[name='modal-stop[]']").each(function() {
                this.checked = checkboxall.checked;
        });
}   // function modalCbAllChange

function busCopyStart()
{
    // вспоминаем в какое направление вставляем
    var direction = parseInt($("#bus-copy-dest-dir").val());
    var i, insertTypeValue = parseInt($("#modal-insert-type-select").prop('selectedIndex'));
    var bs_id;

    stops = document.getElementsByName('modal-stop[]');
    // вставляем выбранные остановки в массив существующих, в зависимости от выбранного способа вставки:
    switch( insertTypeValue ){
    case 0: // В конец
        for(i = 0; i < stops.length; i++){
            if( stops[i].checked ){
                bs_id = parseInt(stops[i].value, 10);
                route[direction].push(bs_id);
                userlog.push({'city':us_city, 'bus': bus_id, 'direction':direction, 'nbusstop_id':bs_id, 'name':busstops[bs_id]['name'], 'order':route[direction].length-1, 'note': `Копирование остановки ${bs_id}: dir:${direction} order:${route[direction].length-1}`});
            }
        }
        break;
    default:    // в начало или перед выбранными элементом
        for(i = stops.length - 1; i > -1 ; i--){
            if( stops[i].checked ){
                bs_id = parseInt(stops[i].value, 10);
                route[direction].splice(insertTypeValue - 1, 0, bs_id);
                userlog.push({'city':us_city, 'bus': bus_id, 'direction':direction, 'nbusstop_id':bs_id, 'name':busstops[bs_id]['name'], 'order':insertTypeValue - 1, 'note': `Копирование остановки ${bs_id}: dir:${direction} order:${insertTypeValue - 1}`});
            }
        }
    }   // switch( $("#modal-insert-type-select").val() )

    // Скрыть диалог копирования
    document.getElementById('bus-copy-dialog').style.display = "none";

    window.sessionStorage.setItem("userlog", JSON.stringify(userlog));
}   // function busCopyStart
