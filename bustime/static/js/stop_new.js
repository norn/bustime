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

function js_page_extra() {
    console.log("Новая остановка");

    var osm = new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        minZoom: 10,
        maxZoom: 20
    });
    var googleSat = L.tileLayer('//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
    });

    var baseMaps = {
        "OSM": osm,
        "Спутник": googleSat
    };

    map = L.map('lmap', {
        scrollWheelZoom: true,
        layers: [osm],
        center: [US_CITY_POINT_Y, US_CITY_POINT_X],
        zoom: 15
    });
    map.on('click', onMapClick);
    L.control.layers(baseMaps).addTo(map);
}

function map_center_me() {
    if (navigator.geolocation) {
        var options = {
                    enableHighAccuracy: true,
                    maximumAge: 0 };
        navigator.geolocation.getCurrentPosition(usePosition, noPosition, options);
    }

}
