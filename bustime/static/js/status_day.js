var osm_stops0, osm_stops1, icon_stop0, icon_stop1,
    passengers_raw, cur_ctime, cur_p=0;
var map, emaps=[], markers={}, marker_times={}, os_events={};
var OSMURL='//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
var player=0, cnt_web=0, cnt_android=0, cnt_ios=0;
// todo https://github.com/Leaflet/Leaflet.heat

function addMinutes(date, minutes) {
    return new Date(date.getTime() + minutes*60000);
}
function supert(s) {
    s=s.split(":");
    return new Date(tm_year, tm_month, tm_day,parseInt(s[0],10),parseInt(s[1],10));
}


function human_time(t) {
    var hs="", ms="";
    if (t.getHours()<10) {hs="0"}
    if (t.getMinutes()<10) {ms="0"}
    s = hs+t.getHours()+":"+ms+t.getMinutes();
    return s;
}
function iskrodraw() {
   if (!player) {return}
   var i, p, marker, next_ctime, cnt=0;
   next_ctime = addMinutes(cur_ctime, 1);
   prev_ctime = addMinutes(cur_ctime, -5);
   $(".from").html(human_time(next_ctime));

   // passengers.clearLayers();
   // https://github.com/zetter/voronoi-maps
   for(marker in markers) {
     if ( marker_times[marker] < prev_ctime ) {
       passengers.removeLayer(markers[marker]);
       delete markers[marker];
       delete os_events[marker];
     }
   }
   var pass_icon = 'fa-user';
   while (passengers_raw[cur_p] && supert( passengers_raw[cur_p]['t'] ) < next_ctime) {
        if (!markers[ passengers_raw[cur_p]['i'] ]) {
           // console.log(passengers_raw[cur_p]);
           if (passengers_raw[cur_p]['o'] === 0) {
              pass_icon = 'fa-globe';
           } else if (passengers_raw[cur_p]['o'] == 1) {
              pass_icon = 'fa-android';
           } else if (passengers_raw[cur_p]['o'] == 2) {
              pass_icon = 'fa-apple';
           }
           pass_icon = L.divIcon({
               iconSize: [20, 20],
               iconAnchor: [10, 10],
               className: '',
               html: "<i class='fa " + pass_icon + "' style='font-size:20px'></i>"
           });
            marker =  L.marker([ passengers_raw[cur_p]['y'],  passengers_raw[cur_p]['x'] ], {icon: pass_icon, 'opacity':0.5});
            passengers.addLayer(marker);
            markers[ passengers_raw[cur_p]['i'] ] = marker;
            os_events[ passengers_raw[cur_p]['i'] ] = passengers_raw[cur_p]['o'];
            marker_times[ passengers_raw[cur_p]['i'] ] = supert( passengers_raw[cur_p]['t'] );
        } else {
            markers[ passengers_raw[cur_p]['i'] ].setLatLng([passengers_raw[cur_p]['y'], passengers_raw[cur_p]['x']]);
            marker_times[ passengers_raw[cur_p]['i'] ] = supert( passengers_raw[cur_p]['t'] );
        }
        cur_p ++;
        cnt ++;
   }

   $(".cnt").html( passengers.getLayers().length );

   cnt_web=0, cnt_android=0, cnt_ios=0;
   for(e in os_events) {
     if ( os_events[e] === 0 ) {
       cnt_web++;
     } else if (os_events[e] == 1) {
      cnt_android++;
     } else if (os_events[e] == 2) {
      cnt_ios++;
     }
   }
   $(".cnt_web").html(cnt_web);
   $(".cnt_android").html(cnt_android);
   $(".cnt_ios").html(cnt_ios);

   if (next_ctime.getDate() == tm_day) {
      cur_ctime = next_ctime;
      setTimeout(function() { iskrodraw() }, 100);
   } else {
      play_pause();
      cur_ctime = new Date(tm_year, tm_month, tm_day,0,0);
      cur_p=0;
   }

}

function play_pause() {
    if (player) {
        player=0;
        $(".playb").html('<i class="fa fa-play"></i>');
    } else {
        player=1;
        $(".playb").html('<i class="fa fa-pause"></i>');
        iskrodraw();
    }
}

function js_page_extra() {
  cur_ctime = new Date(tm_year, tm_month, tm_day,0,0);
  console.log("Status day " + tm);
  L.Icon.Default.imagePath = '/static/img/';
  map = L.map('lmap', {
    scrollWheelZoom:false,
    zoom: 12
  }).setView([CITY_POINT_Y, CITY_POINT_X], 12);
  passengers = L.featureGroup().addTo(map);
  var marker, stop, popup, tram_only;
  new L.TileLayer(OSMURL, {minZoom: 8, maxZoom: 20}).addTo(map);

    $.getJSON( "passengers.js", function( data ) {
        passengers_raw = data;
        play_pause();
    });

}
