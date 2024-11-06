var osm_stops0, osm_stops1, icon_stop0, icon_stop1;
var localmap, bus_marks;
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var OSM_STYLE = 'https://demotiles.maplibre.org/style.json';


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

function lonlat2latlng(lonlat) {
    var latlng = [];
    for (var i in lonlat) {
      latlng.push([lonlat[i][1], lonlat[i][0]]);
    }
    return latlng;
}

function js_page_extra() {
  L.Icon.Default.imagePath = '/static/img';

  var cities = L.layerGroup();
  var osm_stops0 = L.featureGroup().addTo(cities);
  var osm_stops1 = L.featureGroup().addTo(cities);
  var route_lines = L.featureGroup().addTo(cities);
  bus_marks = L.featureGroup().addTo(cities);
  // var da_mapa = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
  var da_mapa = L.maplibreGL({
    style: OSM_STYLE,
    minZoom: 5,
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  });

  var osm = new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        minZoom: 5, maxZoom: 18
  });

  localmap = L.map('lmap', {
    scrollWheelZoom:true,
    layers: [da_mapa, cities],
  });
  localmap.setView([US_CITY_POINT_Y, US_CITY_POINT_X], 12);


  var baseLayers = {
    "Карта": da_mapa,
  };
  var overlays = {};
  overlays[trans_text_online] = bus_marks;
  overlays[trans_text_stops +" 1"] = osm_stops0;
  overlays[trans_text_stops +" 2"] = osm_stops1;
  overlays[trans_text_rlines] = route_lines;
  L.control.layers(baseLayers, overlays, {hideSingleBase:true}).addTo(localmap);

  icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
  icon_stop1 = iconizer('/static/img/bs_26_1.png', [26, 34]);
  var marker, b, i;
  for(i=0; i<route0.length;i++) {
    b=busstops[route0[i]];
    marker = L.marker([b['y'], b['x']], {icon: icon_stop0, zIndexOffset: 50}).addTo(osm_stops0);
    marker.bindPopup("<b>"+b['name']+"</b><br/>=> "+b['moveto']);
  }
  localmap.fitBounds(osm_stops0.getBounds());
  for(i=0; i<route1.length;i++) {
    b=busstops[route1[i]];
    marker = L.marker([b['y'], b['x']], {icon: icon_stop1, zIndexOffset: 1}).addTo(osm_stops1);
    marker.bindPopup("<b>"+b['name']+"</b><br/>=> "+b['moveto']);
  }

    // vue2 init
    //var vm = new Vue({
    // vue3 init
    var vm = Vue.createApp({
        el: '#app',
        data: {
            vue_data: vue_data
        },
        mounted() {
            // vue3
            this.$watch('vue_data.events', draw_bus_marks)
        }
    });

  //vm.$watch('vue_data.events', draw_bus_marks); - vue2

  // $(".get_events").click(get_events);
  get_events();
  var request = $.ajax({
            url: "/ajax/route-line/",
            type: "get",
            data: {
                bus_id: city_monitor_bus
            },
            dataType: "json"
  });
  request.done(function(msg) {
        var d,color;
        for (d = 0; d < 2; d++) {
           if (msg[d]) {
              if (d === 0) {
                  color = "#74c0ec";
              } else {
                  color = "#5ec57c";
              }
              L.polyline(lonlat2latlng(msg[d]), {color: color}).addTo(route_lines);
           }
        }
  });
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
        vue_data.events = msg;
  });
}

function draw_bus_marks(evs) {
  // bus_marks.clearLayers();

  var latlngs, polyline, e, big_icon, html_ready, MapIconDiv;
  for (var i=0;i<vue_data.events.length;i++) {
    e = vue_data.events[i];
    big_icon = bus_icon_chooser( BUSES[e['bus_id']]['ttype'] );
    big_icon = '<div class="sprite-icons sprite-' + big_icon +' active"></div>';
    html_ready = big_icon;// +"<b>" + e['bus_name'] + "</b>";

    MapIconDiv = L.divIcon({
            iconSize: [187, 43],
            iconAnchor: [20, 20],
            className: 'MapIconDiv',
            html: html_ready
    });
    if (e['x'] && e['y']) {
      // console.log(e);
      L.marker([e['y'], e['x']], { icon: MapIconDiv, zIndexOffset: 100 }).addTo(bus_marks);
    }
  }
}

var enableSubmit = false;
/*
сохранение одного поля одного из  направлений расписания
*/
function saveField(bus_id, input_id){
    var value = document.getElementById(input_id).value;
    console.log('saveField: bus.id=', bus_id, input_id, value);
    enableSubmit = value.length > 0 || confirm('Сохранить пустое поле?');
    return enableSubmit;
}   // function saveField

/*
сохранение одного или обоих направлений расписания
index = 0 первое
index = 1 второе
index = 2 оба
*/
function saveNapr(bus_id, index){
    if( index < 2 ){
        var tt_start = document.getElementById('tt_start['+index+']').value;
        var holiday = document.getElementById('holiday['+index+']').value;
        enableSubmit = (tt_start.length > 0 && holiday.length > 0) || confirm('Есть пустые поля. Сохранить?');
    }
    else {
        enableSubmit = true;
        for(var i = 0; i < 2; i++){
            var tt_start = document.getElementById('tt_start['+i+']').value;
            var holiday = document.getElementById('holiday['+i+']').value;
            if( !tt_start.length || !holiday.length ) {
                enableSubmit = confirm('Есть пустые поля. Сохранить?');
                break;
            }
        }
    }

    console.log(`saveNapr: bus_id=${bus_id}, index=${index}, enableSubmit=${enableSubmit}`);
    return enableSubmit;
}   // function saveNapr

function setTextareaValue(id, value){
    document.getElementById(id).value = value;
}
