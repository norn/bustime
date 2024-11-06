var map, lmaps=[], bus_marks;
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
  console.log("Status offline");
  L.Icon.Default.imagePath = '/static/img/';
  // draw_minimaps(uevents);
  // ulayer = L.featureGroup().addTo(map);
}
  // icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
  // icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);

  // var vm = new Vue({
	 //  el: '.pusher',
	 //  data: {
	 //   vue_data: vue_data
	 //  }
  // });

  // vm.$watch('vue_data.events', draw_minimaps);
function draw_minimap(uev_id) {
  $("#lmap_"+uev_id).removeClass('hidden');
  $("#lmap_"+uev_id).next().html("");
  draw_minimaps([uevents[uev_id]]);
}

function draw_minimaps(uevents) {
  var emap, latlngs, polyline, e;
  for (var e in uevents) {
    e = uevents[e];
    emap = L.map('lmap_'+e['id'], {scrollWheelZoom:false}).setView([e['y'], e['x']], 16);
    new L.TileLayer(OSMURL, {minZoom: 10, maxZoom: 18}).addTo(emap);
    // e = vue_data.events[i];
    if (e['x'] && e['y']) {
      L.marker([e['y'], e['x']]).addTo(emap);
    }
    lmaps.push(emap);
  }
}

// function events_clear() {
//   vue_data.events = [];
//   vue_data.user_points = [];
//   vue_data.req_key = "";
// }