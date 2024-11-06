var osm_stops0, osm_stops1, icon_stop0, icon_stop1;
var map, emaps=[], bus_marks;
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

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
  console.log("Anomaly detector");
  L.Icon.Default.imagePath = '/static/img';
  map = L.map('lmap', {
  	scrollWheelZoom:true,
  	center: [US_CITY_POINT_Y, US_CITY_POINT_X],
  	zoom: 13
  });
  
  bus_marks = L.featureGroup().addTo(map);
  var icon_stop0 = iconizer('/static/img/busstop_icon_24.png', [24,24])
  var icon_stop1 = iconizer('/static/img/busstop_icon_24_100.png', [24,24])
  var marker, b, i;
  new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(map);


  var vm = new Vue({
	  el: '.pusher',
	  data: {
	   vue_data: vue_data
	  }
  });

  vm.$watch('vue_data.events', draw_minimaps);
  $(".get_events").click(get_events);
  get_events();
}


function get_events() {
  request = $.ajax({
        url: "/ajax/anomalies/",
        type: "post",
        dataType: "json",
        data: {
            city_id: city_id
        }
   });
  request.done(function(msg) {
        if (!msg) {return}
        console.log(msg.length);
        console.log(msg[0]);
        vue_data.events = msg;
  });
}

function draw_minimaps(evs) {
  for (var i=0; i<emaps.length;i++) {
    emaps[i].remove();
  }
  emaps = [];
  bus_marks.clearLayers();

  var emap, latlngs, polyline, e;
  for (var i=0;i<vue_data.events.length;i++) {
    e = vue_data.events[i];
    emap = L.map('emap_'+e['uniqueid']+"_"+e['x'], {scrollWheelZoom:false}).setView([e['y'], e['x']], 16);
    new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(emap); 
    if (e['x'] && e['y']) {
      L.marker([e['y'], e['x']]).addTo(emap);
      var popup = L.popup()
        .setLatLng([e['y'], e['x']])
        .setContent(e['gosnum'])
        .addTo(bus_marks);
    }
    if (e['x_prev'] && e['y_prev']) {
      L.marker([e['y_prev'], e['x_prev']]).addTo(emap);
      if (e['x'] && e['y']) {
        latlngs = [[e['y'], e['x']], [e['y_prev'], e['x_prev']]];
        polyline = L.polyline(latlngs, {color: '#fe1', opacity:0.9}).addTo(emap);
            // emap.fitBounds(polyline.getBounds());
          }
        }
        emaps.push(emap);
      }
}
