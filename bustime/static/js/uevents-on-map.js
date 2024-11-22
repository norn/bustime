var cars = {};
var osm_stops0 = null;
var route_line = null;
var bus_lines = [];

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
    } else if (ttype == "5") {
        ttype_icon = '2bus';
    }
    return ttype_icon;
}


function js_page_extra() {
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
            center: [place_point_y, place_point_x],
            zoom: 10
    });
    // map.on('click', onMapClick);

    osm_stops0 = L.featureGroup().addTo(map);
    route_line = L.featureGroup().addTo(map);

    var overlayMaps = {
        "uevents": osm_stops0,
        "Маршрут": route_line,
    };
    L.control.layers(baseMaps, overlayMaps).addTo(map);

    showTransport(osm_stops0, uevents);

    if (uevents.length > 0) {
        map.fitBounds(osm_stops0.getBounds());
    }
}   // js_page_extra


function showTransport(layer, transport) {
    var big_icon, MapIconDiv, u, i, car;

    // удаляем машины с карты
    $.each(cars, function(uniqueid) {
        car = cars[uniqueid];
        car.closeTooltip();
        car.unbindTooltip();
        car.closePopup();
        car.unbindPopup();
        car.removeFrom(layer);
        cars[uniqueid] = null;  // delete object L.marker from memory
        delete cars[uniqueid];  // delete property of cars object
    });

    // добавляем машины на карту
    for (i = 0; i < transport.length; i++) {
        u = transport[i];
        /* {'bus': 9106,
          'gosnum': u'Z129',
          'heading': 87,
          'speed': 0,
          'timestamp': datetime.datetime(2019, 3, 10, 1, 20, 2, 612960),
          'uniqueid': u'Z129',
          'x': 71.5359,
          'y': 51.113007} */

        big_icon = bus_icon_chooser(dbget('bus', u['bus'], 'ttype'));
        big_icon = '<div class="sprite sprite-' + big_icon +' active"></div>';

        MapIconDiv = L.divIcon({
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            className: 'MapIconDiv',
            html: big_icon
        });

        cars[u.uniqueid] = L.marker([u['y'], u['x']], { icon: MapIconDiv, zIndexOffset: 100 });
        cars[u.uniqueid].bindPopup("<table border=0 class='vehicle_info'>"
            + "<tr><td><b>Маршрут</b></td><td><a href=\"javascript:getRoute(" + u['bus'] + ");\">" + u['bus_name'] + " (" + u['bus_city'] + ")</a></td></tr>"
            + "<tr><td><b>Время</b></td><td>" + u['timestamp'] + "</td></tr>"
            + "<tr><td><b>UID</b></td><td>" + u['uniqueid'] + "</td></tr>"
            + "<tr><td><b>Гос.№</b></td><td>" + u['gosnum'] + "</td></tr>"
            + "<tr><td><b>Скорость</b></td><td>" + u['speed'] + " км/ч</td></tr>"
            + "</table>"
        );
        layer.addLayer(cars[u.uniqueid]);
    }   // for (i = 0; i < transport.length; i++)

    setTimeout(freshTransport, 10000);
}   // showTransport


function freshTransport() {
    $.ajax({
        url: "/ajax/uevents-on-map/",
        type: "post",
        data: {'place_id': place_id},
        dataType: "json",
        timeout: 10000,
        error: function(jqXHR, status, error){
            console.log(error);
        },
        success: function(data, status, jqXHR){
            showTransport(osm_stops0, JSON.parse(data));
        }
    });
}   // freshTransport


function getRoute(bus_id) {
    $.ajax({
        url: "/ajax/route-line/",
        type: "get",
        data: {'bus_id': bus_id},
        dataType: "json",
        timeout: 10000,
        error: function(jqXHR, status, error){
            console.log(error);
        },
        success: function(data, status, jqXHR){
            showRoute(data);
        }
    });
}   // getRoute


function showRoute(data) {
    var d,color;

    for(d = 0; d < bus_lines.length; d++){
        if(bus_lines[d]) {
            bus_lines[d].removeFrom(route_line);
            bus_line = null;
        }
    }

    for (d = 0; d < 2; d++) {
       if (data[d]) {
          if (d === 0) {
              color = "#74c0ec";
          } else {
              color = "#5ec57c";
          }
          bus_lines[d] = L.polyline(lonlat2latlng(data[d]), {color: color});
          bus_lines[d].addTo(route_line);
       }
    }
}   // showRoute


function lonlat2latlng(lonlat) {
    var latlng = [];
    for (var i in lonlat) {
        latlng.push([lonlat[i][1], lonlat[i][0]]);
    }
    return latlng;
}   // lonlat2latlng
