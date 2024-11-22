var osm_stops0, osm_stops1, icon_stop0, icon_stop1, vue, all_stops;
var p1, p2, result;

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
        console.log("Detector tester");

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
        map.on('click', onMapClick);

        osm_stops0 = L.featureGroup().addTo(map);
        osm_stops1 = L.featureGroup().addTo(map);
        all_stops = L.featureGroup();

        var marker, b, i;
        for (i = 0; i < route[0].length; i++) {
                b = busstops[route[0][i]];
                marker = L.marker([b['y'], b['x']], { icon: icon_stop0 });
                marker.bindPopup(b['name'] + "<br/>-><br/>" + b['moveto']);
                osm_stops0.addLayer(marker);
        }
        for (i = 0; i < route[1].length; i++) {
                b = busstops[route[1][i]];
                marker = L.marker([b['y'], b['x']], { icon: icon_stop1 });
                marker.bindPopup(b['name'] + "<br/>-><br/>" + b['moveto']);
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
}

function bus_stop_set(lng, lat) {
    var current;
    if (p1 && p2) {
        p1 = "";
        p2 = "";
        $("[name=p1]").val("");
        $("[name=p2]").val("");
        current = 1;
        $(".result").html("");
    } else if (p1) {
        current = 2;
    } else {
        current = 1;
    }
    var popup = L.popup();
    popup
            .setLatLng([lat, lng])
            .setContent("Точка " + current)
            .openOn(map);
    $("[name=p"+current+"]").val( lng+";"+lat );
    if (current == 1) {
        p1 = [lng, lat];
    } else {
        p2 = [lng, lat];
        var request = $.ajax({
            url: "/ajax/detector/",
            type: "get",
            data: {
                p1_lon: p1[0],
                p1_lat: p1[1],
                p2_lon: p2[0],
                p2_lat: p2[1],
                bus_id: bus_id,
            }
        });

        request.done(function(msg) {
            $(".result").html(msg).addClass('positive');
            setTimeout(function() {
                $(".result").removeClass('positive');
        }, 800);
        });
    }
}

function onMapClick(e) {
        var lat,lng = e.latlng;
        lat = e.latlng.lat.toFixed(7);
        lng = e.latlng.lng.toFixed(7);
        bus_stop_set(lng, lat);
}
