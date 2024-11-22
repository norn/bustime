var osm_stops0, osm_stops1, icon_stop0, icon_stop1;
var map, emaps=[], bus_marks;
var OSM_STYLE = 'https://demotiles.maplibre.org/style.json';
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

// function onMapClick(e) {
//      var popup = L.popup();
//      popup
//         .setLatLng(e.latlng)
//         .setContent("Click: " + e.latlng.toString())
//         .openOn(map);
//     vue_data.user_points.push(vue_data.user_points.length+": "+e.latlng.lng+", "+e.latlng.lat);
// }

function iconizer(url, iconSize) {
  return new L.icon({
      iconUrl: url,
      iconSize: iconSize,
      iconAnchor: [iconSize[0]/2, iconSize[1]],
      popupAnchor: [0, -iconSize[1]],
      shadowUrl: ''
  });
}


function js_page_extra() {
//console.log("Stop mode");
    L.Icon.Default.imagePath = '/static/img';
    map = L.map('lmap', {
        scrollWheelZoom:true,
        center: {"lng":stop_selected.x, "lat":stop_selected.y},
        zoom: 18
    });
    // map.on('click', onMapClick);
    bus_marks = L.featureGroup().addTo(map);
    icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
    icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);

    if (stop_selected['tram_only']) {
        tram_only = '<i class="fa fa-subway"></i> ';
    } else {
        tram_only = "";
    }

    marker = L.marker([stop_selected['y'], stop_selected['x']], {icon: icon_stop0});
    marker.bindPopup(tram_only+stop_selected['id']+"<br/>"+stop_selected['name']+"<br/>сл. "+stop_selected['moveto']);
    marker.addTo(map);

    popup = L.popup()
        .setLatLng([stop_selected['y']+0.00008, stop_selected['x']])
        .setContent(tram_only+trans_text_moveto+":<br/>" + stop_selected['moveto'])
        .addTo(map);


    /*
    osm_stops0 = L.featureGroup().addTo(map);

    var marker, stop, popup, tram_only;
    for(stop in astops) {
        stop = astops[stop];
        if (stop['tram_only']) {
            tram_only = '<i class="fa fa-subway"></i> ';
        } else {
            tram_only = "";
        }

        marker = L.marker([stop['y'], stop['x']], {icon: icon_stop0});
        marker.bindPopup(tram_only+stop['id']+"<br/>"+stop['name']+"<br/>сл. "+stop['moveto']);

        popup = L.popup()
            .setLatLng([stop['y']+0.00008, stop['x']])
            .setContent(tram_only+trans_text_moveto+":<br/>" + stop['moveto'])
            .addTo(map);

        osm_stops0.addLayer(marker);

        // draw_minimap(stop);
    }   // for(stop in astops)

    map.fitBounds(osm_stops0.getBounds(), {maxZoom: 18});
    */

    // new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(map);
    L.maplibreGL({
        style: OSM_STYLE,
        minZoom: 1,maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}   // js_page_extra


function draw_minimap(stop) {
  var map, latlngs, polyline, e;
  map = L.map('emap_'+stop['id'], {scrollWheelZoom:false}).setView([stop['y'], stop['x']], 18);
  // new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(emap);
  new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(emap); // , detectRetina:true
//  L.maplibreGL({
//    style: OSM_STYLE,
//    minZoom: 1,maxZoom: 19,
    // attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  // }).addTo(map);
  L.marker([stop['y'], stop['x']], {icon: icon_stop0}).addTo(map);
  // var popup = L.popup()
  //   .setLatLng([stop['y'], stop['x']])
  //   .setContent("-> " + stop['moveto'])
  //   .addTo(emap);

}
