var osm_stops0, osm_stops1, icon_stop0, icon_stop1, vue;

// function onMapClick(e) {
//     // alert("You clicked the map at " + e.latlng);
//     var popup = L.popup();
//     popup
//         .setLatLng(e.latlng)
//         .setContent("Click: " + e.latlng.toString())
//         .openOn(map);
// }

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
    console.log("Редактор остановок 0.6");

    var osm = new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        minZoom: 10,
        maxZoom: 20
    });
    var googleStreets = L.tileLayer('//{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
    });
    var googleSat = L.tileLayer('//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
    });
    // icon_stop0 = iconizer('/static/img/busstop_icon_24.png', [24,24])
    // icon_stop1 = iconizer('/static/img/busstop_icon_.png', [24,24])
    icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34])
    icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34])

    // icon_stop0 = L.icon({
    //     iconUrl: '/static/img/marker-icon-yellow.png',
    //     iconSize: [25, 41],
    //     iconAnchor: [12, 41],
    //     popupAnchor: [0, -41],
    //     shadowUrl: ''
    // });

    // icon_stop1 = L.icon({
    //     iconUrl: '/static/img/busstop_icon_24.png',
    //     iconSize: [24, 24],
    //     iconAnchor: [12, 24],
    //     popupAnchor: [0, -24],
    //     shadowUrl: ''
    // });

        // "Спутник": googleSat,
        // "Google": googleStreets,
    var baseMaps = {
        "OSM": osm,
        "Спутник": googleSat
    };

    map = L.map('lmap', {
        scrollWheelZoom: false,
        layers: [osm],
        center: [stop_y, stop_x],
        zoom: 17
    });
    // map.on('click', onMapClick);
    osm_stops0 = L.featureGroup().addTo(map);
    osm_stops1 = L.featureGroup().addTo(map);

    var marker, b, i;
    marker = L.marker([stop_y, stop_x], { icon: icon_stop0, draggable: true, title: 't1', opacity: 0.9 });
    marker.on('moveend', function(ev) {
        var x,y;
        x = ev.target._latlng.lng.toFixed(7);
        y = ev.target._latlng.lat.toFixed(7);
        $("[name=point_x]").val(x);
        $("[name=point_y]").val(y);
        $(".point").html(x+"; "+ y);
    });
    osm_stops0.addLayer(marker);

    var overlayMaps = {
        "Остановка": osm_stops0,
        "Группа остановок": osm_stops1,
    };
    L.control.layers(baseMaps, overlayMaps).addTo(map);

    // if (route[0].length > 0) {
    //     map.fitBounds(osm_stops0.getBounds());
    // }

    // http://vuejs.org/
    // vue = new Vue({
    //     el: '.routes',
    //     data: {
    //         route: route,
    //         busstops: busstops
    //     }
    // });

    // $(".add_button").click(busstop_add);
    // $("#route0").on("click", ".delete_button", busstop_delete);
    // $("#route1").on("click", ".delete_button", busstop_delete);
    // $(".container").on("click", ".save_button", busstop_save);
    // $(".container").on("click", ".up_button", busstop_move);
    // $(".container").on("click", ".down_button", busstop_move);
}


// function busstop_save() {
//   // console.log(route);
//   var request = $.ajax({
//         url: "/ajax/route_edit_save/",
//         type: "post",
//         data: {
//             bus_id: bus_id,
//             route: JSON.stringify(route)
//         },
//         dataType: "json",
//         cache: false
//   });
//   alert("Данные отправлены");
// }