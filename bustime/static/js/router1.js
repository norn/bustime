var all_stops;
var latlngDrag; // for drag&drop остановок
var car = null;

// https://leafletjs.com/examples/extending/extending-1-classes.html
// https://leafletjs.com/examples/custom-icons/
// https://github.com/Leaflet/Leaflet/blob/master/src/layer/marker/Marker.js
// https://leafletjs.com/examples
// https://github.com/bbecquet/Leaflet.RotatedMarker
function setMarkersRotate()
{
    // save these original methods before they are overwritten
    var proto_initIcon = L.Marker.prototype._initIcon;
    var proto_setPos = L.Marker.prototype._setPos;

    var oldIE = (L.DomUtil.TRANSFORM === 'msTransform');

    L.Marker.addInitHook(function () {
        var iconOptions = this.options.icon && this.options.icon.options;
        var iconAnchor = iconOptions && this.options.icon.options.iconAnchor;
        if (iconAnchor) {
            iconAnchor = (iconAnchor[0]/2 + 'px ' + iconAnchor[1]/2 + 'px');
        }
        this.options.rotationOrigin = this.options.rotationOrigin || iconAnchor || 'center bottom' ;
        this.options.rotationAngle = this.options.rotationAngle || 0;
        if( this.options.circle )
            this.options.circle.radius = this.options.circle.radius || 0;

        // Ensure marker keeps rotated during dragging
        this.on('drag', function(e) { e.target._applyRotation(); });
    });

    L.Marker.include({
        _circleLayer: null,

        _initIcon: function() {
            proto_initIcon.call(this);
        },

        _setPos: function (pos) {
            proto_setPos.call(this, pos);
            this._applyRotation();
        },

        _applyRotation: function () {
            if( this._circleLayer ){
                this._circleLayer.remove();
                this._circleLayer = null;
            }

            if(this.options.circle && this.options.circle.radius) {
                this._circleLayer = L.circle(this.getLatLng(), {
                                                color: this.options.circle.color || '#6F6F6F',
                                                fillColor: this.options.circle.fillColor || '#9F9F9F',
                                                fillOpacity: this.options.circle.fillOpacity || .5,
                                                radius: this.options.circle.radius
                });
                this._circleLayer.addTo(this._map);
            }

            if(this.options.rotationAngle) {
                this._icon.style[L.DomUtil.TRANSFORM+'Origin'] = this.options.rotationOrigin;

                if(oldIE) {
                    // for IE 9, use the 2D rotation
                    this._icon.style[L.DomUtil.TRANSFORM] = 'rotate(' + this.options.rotationAngle + 'deg)';
                } else {
                    // for modern browsers, prefer the 3D accelerated version
                    this._icon.style[L.DomUtil.TRANSFORM] += ' rotateZ(' + this.options.rotationAngle + 'deg)';
                }
            }
        },

        setRotationAngle: function(angle) {
            this.options.rotationAngle = angle;
            this.update();
            return this;
        },

        setRotationOrigin: function(origin) {
            this.options.rotationOrigin = origin;
            this.update();
            return this;
        },

        setRadius: function(radius) {
            this.options.circle.radius = radius;
            this.update();
            return this;
        }
    });
}   // function setMarkersRotate()

function onMapClick(e) {
    var lat,lng = e.latlng;
    lat = e.latlng.lat.toFixed(7);
    lng = e.latlng.lng.toFixed(7);
    //bus_stop_set(lng, lat);
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

    all_stops = L.featureGroup().addTo(map);

    var overlayMaps = {
        "Все остановки": all_stops,
    };
    L.control.layers(baseMaps, overlayMaps).addTo(map);

    // обработчики событий формы управления расчетом
    $("#id_dates").change(route_ajax_date_change);
    $("#id_dbs").change(route_ajax_database_change);

    setMarkersRotate(); // приготовим свой маркер
}   // function js_page_extra()

// отправка запроса на выборку маршрута из БД
function route_ajax_request(form)
{
    //console.log("route_ajax_request: ", form.car_ids.value);
    // http://jquery.page2page.ru/index.php5/Ajax-%D0%B7%D0%B0%D0%BF%D1%80%D0%BE%D1%81
    // https://ruseller.com/jquery?id=11

    // формируем список выбранных ID машин
    var car_ids = [];
    $.each($("#id_car_ids option:selected"), function(){
        car_ids.push("'" + $(this).val() + "'");
    });

    $.ajax({
        url: "/ajax/route_calc_request/",
        type: "post",
        data: {
            dbs: form.dbs.value,
            dates: form.dates.value,
            car_ids: car_ids.join(','),
            clock_start: form.clock_start.value,
            clock_end: form.clock_end.value,
            speed_max: form.speed_max.value,
            precis: form.precis.value,
            stop_radius: form.stop_radius.value,
            min_recs_in_bound: form.min_recs_in_bound.value,
        },
        dataType: "json",
        contentType: "application/x-www-form-urlencoded;charset=UTF-8",
        cache: false,
        success: function(data){
            route_ajax_response(data);  // отображаем ответ на карте
        },
        error: function(jqXHR, sStatus, sErrorText){
            console.log("route_ajax_request: ajax:", sStatus, sErrorText);
            $('#errors').html(sErrorText);
        }
    });
}   // function route_ajax_request

/* обработка ответа на запрос на выборку маршрута из БД
data - набор точек маршрута (пока только остановки)
Leaflet:
https://leafletjs.com/examples/quick-start/
https://leafletjs.com/reference-1.4.0.html
*/
function route_ajax_response(data)
{
    // TODO: рисовать путь маршрута
    //console.log( "route_ajax_response: ", data );
    var r, dot_radius = $('#id_stop_radius').val();

    // чистим уже нарисованное
    all_stops.clearLayers();

    // рисуем остановки
    for(r = 0; r < data.length; r++){
        setStop(data[r], dot_radius, all_stops);
    }   // for(r = 0; r < data.length; r++)

    // центрируем карту на первой остановке
    map.fitBounds(all_stops.getBounds());

}   // function route_ajax_response

// вывод остановки на карту
// https://www.wrld3d.com/wrld.js/latest/docs/leaflet/L.Circle/
// https://gis.stackexchange.com/a/111962
// drag&drop: https://stackoverflow.com/questions/33513404/leaflet-how-to-match-marker-and-polyline-on-drag-and-drop
function setStop(dot, dotRadius, layer = all_stops)
{
    var popupHtml = "<table><col width='10%'><col width='*'>"
                    + "<tr><td><b>lat:</b></td><td>" + dot['nlatitude'] + "</td></tr>"
                    + "<tr><td><b>lon:</b></td><td>" + dot['nlongitude'] + "</td></tr>"
                    + "<tr><td><b>Az:</b></td><td>" + dot['pnbear'] + " &ordm;</td></tr>"
                    + "<tr><td><b>V:</b></td><td>" + dot['pnsped'] + " км/ч</td></tr>"
                    /*+ "<tr><td><b>T:</b></td><td>" + dot['ctime'] + "</td></tr>"*/
                    + "<tr><td><b>N:</b></td><td>" + dot['cnt'] + "</td></tr>"
                    + "</table>";

    var labelHtml = "<b>lat</b>: " + dot['nlatitude'] + " <b>lon</b>: " + dot['nlongitude'] + " <b>N</b>: " + dot['cnt'];

    // icon стрелка направления движения
    var starSvgString = "<svg xmlns='http://www.w3.org/2000/svg' width='493.349px' height='493.349px'>"
    + "<path d='M354.034,112.488L252.676,2.853C250.771,0.95,248.487,0,245.82,0c-2.478,0-4.665,0.95-6.567,2.853l-99.927,109.636"
    + " c-2.475,3.049-2.952,6.377-1.431,9.994c1.524,3.616,4.283,5.424,8.28,5.424h63.954v356.315c0,2.663,0.855,4.853,2.57,6.564"
    + " c1.713,1.707,3.899,2.562,6.567,2.562h54.816c2.669,0,4.859-0.855,6.563-2.562c1.711-1.712,2.573-3.901,2.573-6.564V127.907h63.954"
    + " c3.806,0,6.563-1.809,8.274-5.424C356.976,118.862,356.498,115.534,354.034,112.488z' fill='#FF0033'/>"
    + "</svg>";
    var myIconUrl = encodeURI("data:image/svg+xml," + starSvgString).replace('#','%23');

    L.marker([dot['nlatitude'], dot['nlongitude']], {
        icon: new L.icon({
            iconUrl: myIconUrl,
            iconSize: 30,
        }),
        draggable: true,
        rotationAngle: dot['pnbear'],
        rotationOrigin: 'center',
        circle: {
            radius: dotRadius,
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.4,
        },
    })
    .bindPopup(popupHtml)
    .bindTooltip(labelHtml, {permanent: false, className: "stop-hint-label", offset: [20, -20] }) // hint при mouseover
    .on('dragstart', circleDragStartHandler)
    .on('drag', circleDragHandler)
    .on('dragend', circleDragEndHandler)
    .addTo(layer);
}   // function setStop

// drag&drop: https://stackoverflow.com/questions/33513404/leaflet-how-to-match-marker-and-polyline-on-drag-and-drop
function circleDragStartHandler(e) {
    // Get the marker's start latlng
    latlngDrag = this.getLatLng();
    console.log('circleDragStartHandler');
}

function circleDragHandler(e) {
    // Get the marker's current latlng
    latlngDrag = this.getLatLng();
    console.log('circleDragHandler');
}

function circleDragEndHandler (e) {
    console.log('circleDragEndHandler');
}

// реакция выбор даты в меню dates
// установлена в функции js_page_extra строкой $("#id_dates").change(route_ajax_date_change);
function route_ajax_date_change(event)
{
    //console.log(event.target.value);

    $('#busy-indicator').show();

    $.ajax({
        url: "/ajax/route_calc_date_change/",
        type: "post",
        data: {
            db: $('#id_dbs').val(),
            data: event.target.value,
        },
        dataType: "json",
        contentType: "application/x-www-form-urlencoded;charset=UTF-8",
        cache: false,
        success: function(data){
            $('#busy-indicator').hide();
            route_date_change_response(data);   // меняем содержимое меню машин
        },
        error: function(jqXHR, sStatus, sErrorText){
            $('#busy-indicator').hide();
            console.log("route_ajax_date_change: ajax:", sStatus, sErrorText);
        }
    });
    $('#id_car_ids').empty(); // чистим меню машин
    $('#route_track').empty(); // чистим меню машин
}

// обработка ответа на запрос на выборку маршрута из БД
function route_date_change_response(response)
{
    //console.log( "route_date_change_response: ", response );
    $('#id_car_ids').append(response);    // вставляем содержимое меню машин
}   // function route_date_change_response

// реакция выбор БД в меню dbs
// установлена в функции js_page_extra строкой $("#id_dbs").change(route_ajax_database_change);
function route_ajax_database_change(event)
{
    //console.log( "route_ajax_database_change: ", event.target.value );

    $('#busy-indicator').show();

    // выбираем даты из новой БД
    $.ajax({
        url: "/ajax/route_calc_db_change/",
        type: "post",
        data: {
            db: event.target.value,
        },
        dataType: "json",
        contentType: "application/x-www-form-urlencoded;charset=UTF-8",
        cache: false,
        success: function(data){
            $('#busy-indicator').hide();
            route_db_change_response(data);   // меняем содержимое меню дат
        },
        error: function(jqXHR, sStatus, sErrorText){
            $('#busy-indicator').hide();
            console.log("route_ajax_database_change: ajax:", sStatus, sErrorText);
        }
    });
    $('#id_dates').empty(); // чистим меню дат
    $('#id_car_ids').empty(); // чистим меню машин
    $('#route_track').empty(); // чистим меню машин
}   // function route_ajax_database_change

function route_db_change_response(response)
{
    //console.log( "route_db_change_response: ", response );
    $('#id_dates').append(response);    // вставляем содержимое меню дат
    $('#id_dates :nth-child(0)').prop('selected', true); // To select via index
    // эмулируем изменение даты (для выборки списка машин)
    $( "#id_dates" ).trigger( "change" );
}   // function route_db_change_response

// запрос на прогон трека
function route_ajax_request_track(form)
{
    //console.log("route_ajax_request_track: ", form.car_ids.value);
    if( form.car_ids.value.length == 0 ){
        alert('Выберите машину');
        return;
    }

    $('#busy-indicator').show();

    $.ajax({
        url: "/ajax/route_track_request/",
        type: "post",
        data: {
            dbs: form.dbs.value,
            dates: form.dates.value,
            car_ids: form.car_ids.value,
            clock_start: form.clock_start.value,
            clock_end: form.clock_end.value,
        },
        dataType: "json",
        contentType: "application/x-www-form-urlencoded;charset=UTF-8",
        cache: false,
        success: function(data){
            $('#busy-indicator').hide();
            route_ajax_response_track(data);  // отображаем ответ на карте
        },
        error: function(jqXHR, sStatus, sErrorText){
            $('#busy-indicator').hide();
            console.log("route_ajax_request_track: ajax:", sStatus, sErrorText);
            $('#errors').html(sErrorText);
        }
    });

    $("#route_track").empty(); // чистим меню
}   // function route_ajax_request_track

// обработка ответа на запрос на прогон трека
function route_ajax_response_track(data)
{
    //console.log("route_ajax_response_track: ", data);
    for(var i = 0; i < data.length; i++){
        var row = data[i];
        //                1                 2                       3                   4                     5
        var label = row['ctime']+' '+row['nspeed']+'км/ч '+row['nheading']+' '+row['nlatitude']+' '+row['nlongitude'];
        //               0                                6
        var val = row['cimei']+' '+ label + ' '+row['delta_time'];
        $("#route_track").append(new Option(label, val));
    }
}   // function route_ajax_response_track

// изменение меню трека
function route_draw_car(route_track, layer = all_stops)
{
    if( car ){
        car.closeTooltip();
        car.unbindTooltip();
        car.closePopup();
        car.unbindPopup();
        car.removeFrom(layer);
        car = null;
    }

    var dot = route_track.value.split(' ');

    var popupHtml = "<table><col width='10%'><col width='*'>"
                    + "<tr><td><b>T:</b></td><td>" + dot[1] + "</td></tr>"
                    + "<tr><td><b>lat:</b></td><td>" + dot[4] + "</td></tr>"
                    + "<tr><td><b>lon:</b></td><td>" + dot[5] + "</td></tr>"
                    + "<tr><td><b>Az:</b></td><td>" + dot[3] + " &ordm;</td></tr>"
                    + "<tr><td><b>V:</b></td><td>" + dot[2] + " км/ч</td></tr>"
                    + "<tr><td><b>&Delta;T:</b></td><td>" + dot['cnt'] + "</td></tr>"
                    + "</table>";

    var labelHtml = "<b>T:</b>: " + dot[1] + " <b>V:</b>: " + dot[2];

    // icon стрелка направления движения
    var starSvgString = "<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 50 50' version='1.1' width='100px' height='100px'>"
    + "<g id='surface1'>"
    + " <path style=' ' d='M 25 0 C 24.609375 0 24.257813 0.238281 24.09375 0.59375 L 2.1875 48.59375 C 2.019531 48.960938 2.097656 49.390625 2.375 49.6875 C 2.566406 49.890625 2.824219 50 3.09375 50 C 3.214844 50 3.351563 49.984375 3.46875 49.9375 L 25 41.65625 L 46.53125 49.9375 C 46.914063 50.082031 47.347656 49.984375 47.625 49.6875 C 47.902344 49.390625 47.980469 48.960938 47.8125 48.59375 L 25.90625 0.59375 C 25.742188 0.238281 25.390625 0 25 0 Z M 24 5.59375 L 24 39.90625 L 5.03125 47.1875 Z '/>"
    + " </g>"
    + "</svg>";
    var myIconUrl = encodeURI("data:image/svg+xml," + starSvgString).replace('#','%23');

    car = L.marker([dot[4], dot[5]], {
        icon: new L.icon({
            iconUrl: myIconUrl,
            iconSize: 30,
        }),
        draggable: false,
        rotationAngle: dot[3],
        rotationOrigin: 'center',
    })
    .bindPopup(popupHtml)
    .bindTooltip(labelHtml, {permanent: false, className: "stop-hint-label", offset: [20, -20] }); // hint при mouseover

    car.addTo(layer);

    if( $("#route_track_pan_map").prop("checked") )
        map.panTo([dot[4], dot[5]]);
}   // function route_draw_car