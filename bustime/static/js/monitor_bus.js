var osm_stops0, osm_stops1, icon_stop0, icon_stop1;
var map, emaps=[], bus_marks;
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

function onMapClick(e) {
     var popup = L.popup();
     popup
        .setLatLng(e.latlng)
        .setContent("Click: " + e.latlng.toString())
        .openOn(map);
    vue_data.user_points.push(vue_data.user_points.length+": "+e.latlng.lng+", "+e.latlng.lat);
}

function iconizer(url, iconSize) {
  return new L.icon({
      iconUrl: url,
      iconSize: iconSize,
      iconAnchor: [iconSize[0]/2, iconSize[1]],
      popupAnchor: [0, -iconSize[1]],
      shadowUrl: ''
  });
}

// copy-paste from main js
function bus_icon_chooser(ttype) {
    var ttype_icon;
    if (ttype == "0") {
        ttype_icon = 'icon_bus';
    } else if (ttype == "1") {
        ttype_icon = 'icon_trolleybus';
    } else if (ttype == "2") {
        // ttype = 'sprite-btype-tramway';
        ttype_icon = 'icon_tramway';
    } else if (ttype == "3") {
        ttype_icon = 'icon_bus-taxi';
    }
    return ttype_icon;
}


function js_page_extra() {
  console.log("Monitorro");
  L.Icon.Default.imagePath = '/static/img';
  map = L.map('lmap', {
  	scrollWheelZoom:true,
  	center: [US_CITY_POINT_Y, US_CITY_POINT_X],
  	zoom: 12
  });
  map.on('click', onMapClick);

  bus_marks = L.featureGroup().addTo(map);
  icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
  icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);

  osm_stops0 = L.featureGroup().addTo(map);
  osm_stops1 = L.featureGroup().addTo(map);

  var marker, b, i;
  for(i=0; i<route0.length;i++) {
    b=busstops[route0[i]];
    if (i==0) {console.log(b)}
    marker = L.marker([b['y'], b['x']], {icon: icon_stop0});
    marker.bindPopup(b['id']+"<br/>"+b['name']+"<br/>сл. "+b['moveto']);
    // marker.setContent("I am a standalone popup.")
    osm_stops0.addLayer(marker);
  }
  for(i=0; i<route1.length;i++) {
    b=busstops[route1[i]];
    marker = L.marker([b['y'], b['x']], {icon: icon_stop1});
    marker.bindPopup(b['id']+"<br/>"+b['name']+"<br/>сл. "+b['moveto']);
    osm_stops1.addLayer(marker);
  }
  map.fitBounds(osm_stops0.getBounds());
  new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(map);

  // var overlayMaps = {
  //     "Остановки #0": osm_stops0,
  //     "Остановки #1": osm_stops1,
  // };

  var vm = new Vue({
	  el: '.pusher',
	  data: {
	   vue_data: vue_data
	  }
  });

  vm.$watch('vue_data.events', draw_minimaps);

  $(".events_clear").click(events_clear);
  $(".get_events").click(get_events);
  get_events();
}

function busstop_add0() {
  // route1.pop();
}

function busstop_add1() {
  // alert( $('.busstop_add1').val() );
}

function get_events() {
  request = $.ajax({
        url: "/ajax/bus/monitor/",
        type: "post",
        dataType: "json",
        data: {
            bus_id: city_monitor_bus,
            req_key: vue_data.req_key
        }
   });
  request.done(function(msg) {
        if (!msg) {return}
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


  var emap, latlngs, polyline, e, big_icon, html_ready, MapIconDiv;
  for (var i=0;i<vue_data.events.length;i++) {
    e = vue_data.events[i];
    // console.log(e);
    big_icon = bus_icon_chooser( BUSES[e['bus_id']]['ttype'] );
    big_icon = '<div class="sprite-icons sprite-' + big_icon +' active"></div>';
    html_ready = big_icon; //+"<b>" + e['bus_name'] + "</b>";

    MapIconDiv = L.divIcon({
            iconSize: [187, 43],
            iconAnchor: [0, 0],
            className: 'MapIconDiv',
            html: html_ready
    });

    emap = L.map('emap_'+e['k'], {scrollWheelZoom:false}).setView([e['y'], e['x']], 16);
    new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(emap);
    if (e['x'] && e['y']) {
      L.marker([e['y'], e['x']], { icon: MapIconDiv }).addTo(emap);
//        .setContent(e['uniqueid']+'-'+e['gosnum'])
      var popup = L.popup()
        .setLatLng([e['y'], e['x']])
        .addTo(bus_marks);
      if (e['gosnum']) {
        popup.setContent(e['gosnum']);
      } else {
        popup.setContent(e['uniqueid']);
      }
    }
    if (e['x_prev'] && e['y_prev']) {
      L.marker([e['y_prev'], e['x_prev']], { icon: MapIconDiv }).addTo(emap);
      if (e['x'] && e['y']) {
        latlngs = [[e['y'], e['x']], [e['y_prev'], e['x_prev']]];
        polyline = L.polyline(latlngs, {color: '#414afd', opacity:0.9}).addTo(emap);
            // emap.fitBounds(polyline.getBounds());
          }
        }
        emaps.push(emap);
      }
}

function events_clear() {
  vue_data.events = [];
  vue_data.user_points = [];
  vue_data.req_key = "";
}