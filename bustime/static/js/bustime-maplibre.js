"use strict";
var ML_COOKIE = 'ml_pos';
var ml_map = null;
var ml_inited = 0;
var to_place, from_place, bounds_map = "";
var stop_trip = [];
var coords_place = [];
var inf_road_from_json = '';
var all_stops_with_double = [];
var all_stops = [];
var style_map = 'https://demotiles.maplibre.org/styles/osm-bright-gl-style/style.json';

//загружаем файл со свойствами дорог
$.ajax({
    url: "/static/highway_on_map.json",
    dataType: "json",
    success: function(data) {
    inf_road_from_json = data;
    }
 });



function ml_init() {
    console.log('ml_init');
    /*
    Help:
    https://maplibre.org/maplibre-gl-js-docs/api/
    https://github.com/maplibre/maplibre-gl-js
    https://maplibre.org/maplibre-gl-js-docs/example/
    https://docs.mapbox.com/mapbox-gl-js/example/

    https://maplibre.org/maplibre-gl-js-docs/api/markers/

    Android, iOS:
    https://github.com/maplibre/maplibre-gl-native
    Свои надписи на карте:
    https://maplibre.org/maplibre-gl-js-docs/example/variable-label-placement/
    */

    if (document.addEventListener) {
        document.addEventListener('fullscreenchange', fullscreenHandler, false);
        document.addEventListener('mozfullscreenchange', fullscreenHandler, false);
        document.addEventListener('MSFullscreenChange', fullscreenHandler, false);
        document.addEventListener('webkitfullscreenchange', fullscreenHandler, false);
    }


    // читаем куку
    let position = typeof Cookies !== "undefined" ? Cookies.get(ML_COOKIE) : null;
    // если прочитали,    строка => объект       иначе - задаем позицию вручную
    if (position) {
        position = JSON.parse(position);
    } else if (US_CITY_POINT_X && US_CITY_POINT_Y) {
        position = {"center": {"lng": US_CITY_POINT_X, "lat": US_CITY_POINT_Y}, "zoom": 10};
    } else {
        position = {"center": {"lng": 30.33, "lat": 59.93}, "zoom": 10};
    }

    // инициализируем карту
    ml_map = new maplibregl.Map({
        container: "maplibre",   // привязка к контейнеру
        style: style_map,
        zoom: position.zoom,
        center: position.center
    });

    // отображение текущего положения на основе геопозиционирования браузера
    ml_map.addControl(
        new maplibregl.GeolocateControl({
            positionOptions: {
                enableHighAccuracy: true
            },
            trackUserLocation: true
        }), 'bottom-right'
    );

    ml_map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    ml_map.addControl(new maplibregl.ScaleControl({unit: 'metric'}), 'bottom-left');
    //ml_map.addControl(new maplibregl.FullscreenControl({container: document.querySelector('maplibre')}));

/*
    // карта закончила перемещаться
    ml_map.on('moveend', function () {
        // сохраним позицию в куку
        let position = {
            "center": ml_map.getCenter(),
            "zoom": Math.round(ml_map.getZoom())
        };
        // пишем куку
        if (typeof Cookies !== "undefined") {
            Cookies.set(ML_COOKIE, JSON.stringify(position), {expires: 365, path: '/'});
        }
        //Cookies.set('cookie_policy', "1", { expires: 3650, domain: '.bustime.loc' });
    });
*/


    // мышь движется по карте
    ml_map.on('mousemove', function (e) {
        // при движении мыши покажем lon/lat
        // https://learn.javascript.ru/searching-elements-dom
        if (document.getElementById('lonlatinfo')) {
          document.getElementById('lonlatinfo').innerHTML =
            `lat: ${e.lngLat.lat.toFixed(6)} lon: ${e.lngLat.lng.toFixed(6)}`;
        }
    });

    // получаем все остановки города для поиска и отображения на карте в виде маркеров
    for (var key in dbgetsafe('nbusstop')){
        var points = [dbget('nbusstop', key, 'point_x'), dbget('nbusstop', key, 'point_y')];
        all_stops_with_double.push({title: dbget('nbusstop', key, 'name'), id_stop: dbget('nbusstop', key, 'unistop'), points: points})
    }

    // убираем дубли остановок по названию
    all_stops = all_stops_with_double.reduce(function (p, c) {
        if (!p.some(function (el) { return el.title === c.title; })) p.push(c);
          return p;
    }, []);


    // добавление остановок в виде слоя
    let featuress = "";
    for (let i = 0; i < all_stops.length; i++) {
        if (i == (all_stops.length - 1)) {
            featuress = featuress + '{"type": "Feature", "properties": { "description": "' + all_stops[i].title + '"},"geometry": { "type": "Point", "coordinates": [' + all_stops[i].points + '] } }';
        } else {
            featuress = featuress + '{"type": "Feature", "properties": { "description": "' + all_stops[i].title + '"},"geometry": { "type": "Point", "coordinates": [' + all_stops[i].points + '] } },';
        }
     }

    featuress = "[" + featuress + "]";
    featuress = JSON.parse(featuress);

    ml_map.on('load', function () {
        ml_map.addSource('stops', {
            'type': 'geojson',
            'data': {
                'type': 'FeatureCollection',
                'features': featuress
            }
        });

        ml_map.addLayer({
            'id': 'stops',
            'type': 'circle',
            'source': 'stops',
            'paint': {
                'circle-color': '#4264fb',
                'circle-radius': 4,
                'circle-stroke-width': 1,
                'circle-stroke-color': '#ffffff'
            }
        });

         let popup = new maplibregl.Popup({
             closeButton: false,
             closeOnClick: false
         });

        //при клике на остановку показать ее название во всплывающем окне
        ml_map.on('mouseenter', 'stops', function (e) {
            ml_map.getCanvas().style.cursor = 'pointer';
            let coordinates = e.features[0].geometry.coordinates.slice();
            let description = e.features[0].properties.description;

            while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
            }

            popup.setLngLat(coordinates).setHTML(description).addTo(ml_map);
        });

        ml_map.on('mouseleave', 'stops', function () {
            ml_map.getCanvas().style.cursor = '';
            popup.remove();
        });

    });

    ml_inited = 1;
}   // init


function fullscreenHandler(e) {
    if (e.target.id === "maplibre") {
        if (!document.webkitIsFullScreen && !document.mozFullScreen && !document.msFullscreenElement) {
            // exit full screen
            ml_mapOff();
        } else {
            // enter full screen
        }
    }
}   // fullscreenHandler

function js_page_extra() {
    $('.maplibre_button').click(function(event) {
        $('#maplibre').toggle();
        $('.ui.container').toggle();
        $('.maplibre_button').toggleClass(['blue', 'red']);
        $('.lang_ftr').toggle();
        $('.drop_city').toggle();
        $('.message').toggle();
        $('.index_panel').toggle();
        $('.bustable').toggle();
        $('.adsense').toggle();
        $('.matrix.bus_hide').toggle();
        $('.yheader').toggle();
        if (ml_inited) {
            ml_map.resize();
        } else {
            ml_init();
        }


        //попап для информации о дорогах
        let popup_road = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false
        });

//вывод информации о дорогах

        ml_map.on('mousemove', function(e) {// при движении курсора
            var transportation = ml_map.queryRenderedFeatures(e.point)[0]; //берем точку, где курсор
            popup_road.remove();//удаляем предыдущее попап окно с инф о дороге

            if ((transportation) && (transportation.sourceLayer === 'transportation')) {// если курсор на дороге
                ml_map.getCanvas().style.cursor = 'pointer'; //меняем вид курсора
                console.log(transportation.properties);

                var inf_road = '';

                //если свойство дороги есть, то достаем его значение из файла и записываем в переменную inf_road
                if (transportation.properties.class) {
                    inf_road += inf_road_from_json.class[transportation.properties.class];
                }
                if (transportation.properties.subclass !== undefined) {
                    inf_road += '</br>' + inf_road_from_json.subclass[transportation.properties.subclass];
                }
                if (transportation.properties.surface) {
                    inf_road += '</br>' + inf_road_from_json.surface[transportation.properties.surface];
                }
                if (transportation.properties.turn) {
                    inf_road += '</br>' + inf_road_from_json.turn[transportation.properties.turn];
                }
                if (transportation.properties.oneway !== undefined ) {
                    inf_road += '</br>' + inf_road_from_json.oneway[transportation.properties.oneway];
                }
                if (transportation.properties.ramp !== undefined) {
                    inf_road += '</br>' + inf_road_from_json.ramp[transportation.properties.ramp];
                }


                //добавляем попап окно с этой информацией на карту
                popup_road.setLngLat(e.lngLat).setHTML(inf_road).addTo(ml_map);

            } else {
                ml_map.getCanvas().style.cursor = ''; //если курсор не на дороге, делаем его обычным
            }
        });


// Удаление POI с карты при ее открытии
        ml_map.on('style.load', () => { // Получение текущего стиля и его слоев
            const style = ml_map.getStyle();
            const layers = style.layers;

            // Перебираем слои и скрываем ненужные
            for (let i = 0; i < layers.length; i++) {
                const layer = layers[i];

                if (layer.id === 'poi-level-1') {
                    ml_map.setLayoutProperty(layer.id, 'visibility', 'none');
                }
            }

            //при нажатии чекбокса включаем слой
            $('.layers_checkbox').change(function() {
                var layerId = this.value;
                if (this.checked) {
                    ml_map.setLayoutProperty(layerId, 'visibility', 'visible');
                } else {
                    ml_map.setLayoutProperty(layerId, 'visibility', 'none');
                }
            });

        });

// Скрываем или открываем чекбоксы слоев при наведении
        $('.layers_selection').on('mouseover', function() {
            $('#layers_checkbox').css('display', '');
        });
        $('.layers_selection').on('mouseout', function() {
            $('#layers_checkbox').css('display', 'none');
        });


//Ввод Откуда и Куда с помощью кликов по карте

        $('#from_icon').click(function() {//при клике на иконку на поле ввода Откуда

            $('#from_icon').css('color', '#4264fb').css('opacity', '1').css('font-size', '15px');//меняем вид иконки на активный

            ml_map.once('click', function(e) { //единожды отслеживаем клик на карте
                if (from_place) { // если есть маркер Откуда, то удаляем его
                    from_place.remove();
                }
                var lngLat = e.lngLat; //координаты клика
                $('.from input').attr('id', [lngLat.lat, lngLat.lng]); //записываем координаты клика в поле откуда

                // Добавляем маркер начала маршрута на карту
                from_place = new maplibregl.Marker({draggable: true})
                    .setLngLat(lngLat)
                    .addTo(ml_map);
                // Если поле Куда не пустое, то ищем маршрут
                if ($('.to input').attr('id') !== undefined) {
                    line_on_map();
                }
                $('#from_icon').css('color', '#000').css('opacity', '.5').css('font-size', '12px');//после установки маркера возвращаем иконке обычный вид
            });

        });

        $('#to_icon').click(function() { // При клике на икноку ввода Куда

            $('#to_icon').css('color', '#4264fb').css('opacity', '1').css('font-size', '15px');//меняем вид иконки на активный

            ml_map.once('click', function(e) {
                if (to_place) {
                    to_place.remove();
                }

                var lngLat = e.lngLat; //координаты клика
                $('.to input').attr('id', [lngLat.lat, lngLat.lng]); //записываем координаты клика в поле откуда

                // Добавляем маркер начала маршрута на карту
                to_place = new maplibregl.Marker({color: 'black', draggable: true})
                    .setLngLat(lngLat)
                    .addTo(ml_map);
                //если поле Куда не пустое, то ищем маршрут
                if ($('.from input').attr('id') !== undefined) {
                    line_on_map();
                }
                $('#to_icon').css('color', '#000').css('opacity', '.5').css('font-size', '12px');//после установки маркера возвращаем иконке обычный вид
            });
        });


        ml_map.on('mouseup', function(e) {// перетаскивание маркера
                if (to_place) {
                    to_place.on('dragend', function() {//когда пользователь закончил перемещать маркер Куда
                        var lngLat = to_place.getLngLat(); //получаем координаты маркера
                        $('.to input').attr('id', [lngLat.lat, lngLat.lng]);//записываем их в поле Куда

                        if ($('.from input').attr('id') !== undefined) {//если поле Откуда не пустое, то ищем маршрут
                            line_on_map();
                        }
                    });
                }
                if (from_place) {
                    from_place.on('dragend', function() {
                        var lngLat = from_place.getLngLat();
                        $('.from input').attr('id', [lngLat.lat, lngLat.lng]);
                        console.log('f', lngLat);
                        if ($('.to input').attr('id') !== undefined) {
                            line_on_map();
                        }

                    });
                }
        });

/*
        ml_map.on('mouseup', function(e) {
            var lngLat = e.lngLat; //координаты клика

            if ($('.from input').attr('id') == undefined) {//если поле Откуда пустое
                $('.from input').attr('id', [lngLat.lat, lngLat.lng]); //то записываем туда координаты клика

                // Добавляем маркер начала маршрута на карту
                from_place = new maplibregl.Marker({draggable: true})
                    .setLngLat(lngLat)
                    .addTo(ml_map);
                //если поле Куда не пустое, то ищем маршрут
                if ($('.to input').attr('id') !== undefined) {
                    line_on_map();
                }

             } else if ($('.to input').attr('id') == undefined) {// если поле Куда пустое
                $('.to input').attr('id', [lngLat.lat, lngLat.lng]);//записываем координаты куда

                // Добавляем маркер конца маршрута на карту
                to_place = new maplibregl.Marker({color: 'black', draggable: true})
                    .setLngLat(lngLat)
                    .addTo(ml_map);

                //если поле Откуда не пустое, то ищем маршрут
                if ($('.from input').attr('id') !== undefined) {
                    line_on_map();
                }

            } else { //если оба поля заполнены, значит пользователь перемещает маркер
                if (to_place) {
                    to_place.on('dragend', function() {//когда пользователь закончил перемещать маркер Куда
                        lngLat = to_place.getLngLat(); //получаем координаты маркера
                        $('.to input').attr('id', [lngLat.lat, lngLat.lng]);//записываем их в поле Куда

                        if ($('.from input').attr('id') !== undefined) {//если поле Откуда не пустое, то ищем маршрут
                            line_on_map();
                        }
                    });
                }
                if (from_place) {
                    from_place.on('dragend', function() {
                        lngLat = from_place.getLngLat();
                        $('.from input').attr('id', [lngLat.lat, lngLat.lng]);
                        console.log('f', lngLat);
                        if ($('.to input').attr('id') !== undefined) {
                            line_on_map();
                        }

                    });
                }
            }
        });// ml_map.on('mouseup'

*/
        bounds_map = (ml_map.getBounds()).toArray(); //достаем географические границы карты, чтобы ограничить поиск текущим городом

//переключение вида транспорта при поиске проезда
        $('.selection_transport .item').click(function() {

            //удаление линии маршрута, если она есть
            if (ml_map.style.hasLayer('route')) {
                ml_map.removeLayer('route')
             }
            if (ml_map.style && ml_map.style.sourceCaches['route']) {
                ml_map.removeSource('route');
            }
            //удаление маркеров начала и конца
            if (from_place) {
                from_place.remove();
            }
            if ( to_place) {
                to_place.remove();
            }

            //удаление остановок маршрута
            if (stop_trip) {
                for (let i = 0; i < stop_trip.length; i++) {
                    stop_trip[i].remove();
                }
            }

            $('.selection_transport .active').removeClass('active');
            $(this).addClass('active');
            if ($(this).attr('id') == "bus") {
                $('.search_stop').css('display', '');
                $('.search_address').css('display', 'none');
                if (($('.search_stop input').attr('id') !== undefined) && ($('.search_stop input').attr('id') !== undefined)){ //если оба поля(откуда и ку
                    line_on_map();
                }
            } else {
                $('.search_stop').css('display', 'none');
                $('.search_address').css('display', '');
                if (($('.from input').attr('id') !== undefined) && ($('.to input').attr('id') !== undefined)){ //если оба поля(откуда и куда)
                    line_on_map();
                }
            }
        });

//поиск места по адресу и поиск маршрута по адресу
        $('.ui.search.address').search({
            minCharacters: 3,
            apiSettings: {
                onResponse: function (data) {
                    let response = {
                        results: []
                    };

                    $.each(data.features, function (index, feature) {
                        response.results.push({
                            title: feature.properties['display_name'],
                            feature: feature
                        });
                     });

                    return response;
                },
                url: 'https://nominatim.openstreetmap.org/search?q={query}&viewbox=' + bounds_map + '&bounded=1&format=geojson&addressdetails=1&polygon_geojson=1'
             },
            onSelect: function (data, response) {
                //если пользователь вводит данные в поля откуда и куда
                if ($(this).hasClass('from_to')) {
                    $('.selection_transport').css('display', '');//открывааем выбор транспорта

                    //если это микрорайон, то выдает один набор координат
                    if (data.feature.geometry.coordinates.length == 1) {
                        coords_place = data.feature.geometry.coordinates[0][0]; //записываем координаты введенного места
                    } else {
                        coords_place = data.feature.geometry.coordinates;
                    }

                    if ($(this).hasClass('to')) { //если пользователь изменяет поле куда
                        $('.to input').attr('id', [coords_place[1], coords_place[0]]); //записываем координаты найденной точки
                        if (to_place) {
                            to_place.remove();//удаляем маркер, если есть
                        }
                        to_place = new maplibregl.Marker({color: 'black'})//ставим маркер на найденную точку
                            .setLngLat(coords_place)
                            .addTo(ml_map);
                        ml_map.flyTo({center: coords_place, zoom: 17}); //наводим камеру на маркер

                    } else if ($(this).hasClass('from')) {
                        $('.from input').attr('id', [coords_place[1], coords_place[0]]);
                        if (from_place) {
                            from_place.remove();
                        }
                        from_place = new maplibregl.Marker()
                            .setLngLat(coords_place)
                            .addTo(ml_map);
                        ml_map.flyTo({center: coords_place, zoom: 17}); //наводим камеру на маркер
                    }

                    if (($('.from input').attr('id') !== undefined) && ($('.to input').attr('id') !== undefined)){ //если оба поля(откуда и куда) заполнены
                        line_on_map();
                    }
                } else { //обычный поиск

                    if (ml_map.style.hasLayer('state-borders')) {
                        ml_map.removeLayer('state-borders')
                    }
                    if (ml_map.style && ml_map.style.sourceCaches['borders']) {
                        ml_map.removeSource('borders');
                    }

                    ml_map.addSource('borders', {
                        'type': 'geojson',
                        'data': data.feature
                    });
                    ml_map.addLayer({
                        'id': 'state-borders',
                        'type': 'line',
                        'source': 'borders',
                        'layout': {},
                        'paint': {
                            'line-color': '#627BC1',
                            'line-width': 2
                        }
                    });

                    ml_map.flyTo({center: data.feature.geometry.coordinates[0][0], zoom: 17});
                }//else обычный поиск

                return true;
             }
        });//$('.ui.search.address').search




//поиск маршрута по названиям остановок
        $('.ui.search.search_stop').search({
            minLength: 3,
            ignoreDiacritics: true,
            source: all_stops,
            onSelect: function(response) {
                let for_marker_stops = all_stops.find(item => item.title === response.title);

                if ($(this).hasClass('stop_to')) { //если пользователь изменяет поле куда
                    $('.stop_to input').attr('id', response.id_stop); //записываем название найденной остановки
                    if (to_place) {
                        to_place.remove();//удаляем маркер, если есть
                    }
                    to_place = new maplibregl.Marker({color: 'black'})//ставим маркер на найденную точку
                        .setLngLat(for_marker_stops.points)
                        .addTo(ml_map);
                    ml_map.flyTo({center: for_marker_stops.points, zoom: 17}); //наводим камеру на маркер

                } else if ($(this).hasClass('stop_from')) {
                    $('.stop_from input').attr('id', response.id_stop);
                    if (from_place) {
                        from_place.remove();
                    }
                    from_place = new maplibregl.Marker()
                        .setLngLat(for_marker_stops.points)
                        .addTo(ml_map);
                    ml_map.flyTo({center: for_marker_stops.points, zoom: 17}); //наводим камеру на маркер
                 }

                if (($('.stop_from input').attr('id') !== undefined) && ($('.stop_to input').attr('id') !== undefined)){ //если оба поля(отк
                    line_on_map();
                }
            }
        });//$('.ui.search.search_stop').search({

    });//$('.maplibre_button').click(function(event)
}

function ml_mapOn() {
    $("#maplibre").css("display", "block");
    if (ml_map) {
        if (!document.fullscreenElement) {
            document.querySelector('#maplibre').requestFullscreen();
        }
        ml_map.resize();
    }
}


function ml_mapOff() {
    if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen();
    }
    $("#maplibre").css("display", "none");
}


function line_on_map() { //рисует линию маршрута на карте
    let address_from, address_to, stop_from, stop_to = "";
    let transport = $('.selection_transport .active').attr('id');

    if (transport == "bus") {//если тип транспорта автобус, берем названия остановок
        stop_from = $('.stop_from input').attr('id');
        stop_to = $('.stop_to input').attr('id');

    } else {//ессли любой другой тип, берем координаты
        address_from = $('.from input').attr('id');
        address_to = $('.to input').attr('id');
    }

    //ajax возвращает найденный путь между 2 точками или 2 остановками
    $.ajax({
        url: "/ajax/from_to/",
        type: "GET",
        data: {
            address_from: address_from, address_to: address_to, stop_from: stop_from, stop_to: stop_to, transport: transport, csrfmiddlewaretoken: '{{csrftoken}}'
        }
    }).done(function (resp) {
        if (resp.length > 0) {
            let response = JSON.parse(resp);
            let coords = "";

            //удаление линии маршрута, если она есть
            if (ml_map.style.hasLayer('route')) {
                ml_map.removeLayer('route')
             }
            if (ml_map.style && ml_map.style.sourceCaches['route']) {
                ml_map.removeSource('route');
            }

            //удаление остановок маршрута
            for (let i = 0; i < stop_trip.length; i++) {
                stop_trip[i].remove();
            }

            //удаление всех остановок города, если они есть
            if (ml_map.style.hasLayer('stops')) {
                ml_map.removeLayer('stops')
             }
            if (ml_map.style && ml_map.style.sourceCaches['stops']) {
                ml_map.removeSource('stops');
            }

            //удаление маркеров начала и конца маршрута
            from_place.remove();
            to_place.remove();

            //если тип транспорта автобус, то добавляем остановки на маршрут и записываем координаты линии
            if (response.type_transport == 'bus') {
                coords = response.coords;
                for (let i = 0; i < response.all_stops_trip.length; i++) {
                    stop_trip[i] = new maplibregl.Marker({scale:0.3})
                        .setLngLat(response.all_stops_trip[i].points)//добавляем маркер
                        .setPopup(new maplibregl.Popup().setHTML(response.all_stops_trip[i].name))//добавляем попап с названием остановки
                        .addTo(ml_map);
                }
                //добавление неперетаскиваемых маркеров начала и конца маршрута
                from_place = new maplibregl.Marker()
                    .setLngLat(coords[0])
                    .addTo(ml_map);
                to_place = new maplibregl.Marker({color: 'black'})
                    .setLngLat(coords[coords.length-1])
                    .addTo(ml_map);

            } else { //если другой тип транспорта, то записываем только координаты линии
                coords = response.coords;
                //добавление перетаскиваемых маркеров начала и конца маршрута
                from_place = new maplibregl.Marker({draggable: true})
                    .setLngLat(coords[0])
                    .addTo(ml_map);
                to_place = new maplibregl.Marker({color: 'black', draggable: true})
                    .setLngLat(coords[coords.length-1])
                    .addTo(ml_map);
            }

            //добалвние линии маршрута на карту
            ml_map.addSource('route', {
                'type': 'geojson',
                'data': {
                    'type': 'Feature',
                    'properties': {},
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': coords
                    }
                }
            });
            ml_map.addLayer({
                'id': 'route',
                'type': 'line',
                'source': 'route',
                'layout': {},
                'paint': {
                    'line-color': '#627BC1',
                    'line-width': 8
                }
            });

            //наводим камеру на найденный маршрут
            ml_map.fitBounds([coords[0], coords[(coords.length-1)]], { padding: {top: 50, bottom: 30, left: 50, right: 50}});
        }
    }).fail(function (xhr, status, errorThrown) {
        console.log("Error: " + errorThrown);
    });
    return true;
}


function ml_search_search() {
    let value = $("#ml_search_input").val();
    if (value.length) {
        // nominatim request
        let url = `https://nominatim.openstreetmap.org/search?q=${value}&format=geojson&addressdetails=1&polygon_geojson=1`
        // console.log(url);
        if (ml_map.style.hasLayer('state-borders')) {
            ml_map.removeLayer('state-borders')
        }
        if (ml_map.style && ml_map.style.sourceCaches['borders']) {
            ml_map.removeSource('borders');
        }
        $.ajax({
            url: url,
        }).done(function (data) {
            console.log("done: ", data);
            if (data.features.length > 1) {
                // let names = {
                //     "results": data.features.map(feature => ({"title": feature.properties['display_name']}))
                // };
                // $(".ui.search").search({
                //     ignoreDiacritics: true,
                //     fullTextSearch: 'exact',
                //     source: names,
                // });
                // console.log(names)

                // $('.ui.search').search('get value', value);
            } else if (data.features.length > 0) {
                ml_map.addSource('borders', {
                    'type': 'geojson',
                    'data': data.features[0]
                });
                ml_map.addLayer({
                    'id': 'state-borders',
                    'type': 'line',
                    'source': 'borders',
                    'layout': {},
                    'paint': {
                        'line-color': '#627BC1',
                        'line-width': 2
                    }
                });

                let bbox = data.features[0].bbox;
                const midpoint = ([x1, y1], [x2, y2]) => [(x1 + x2) / 2, (y1 + y2) / 2];
                ml_map.center = midpoint([bbox[0], bbox[2]], [bbox[1], bbox[3]]);
                ml_map.fitBounds(bbox)
            }
        }).fail(function (xhr, status, errorThrown) {
            console.log("Error: " + errorThrown);
        });

    }
}
