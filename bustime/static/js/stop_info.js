var socket;
var myCollection;
var mrs = {};
var prs = {};

function js_page_extra() {
  console.log("Stop info mode: "+stop_id);
  connect_websocket_for_info_board();
  start_map_for_info_board();
  setInterval(server_date_info_board, 10000);
  if( $("#weather")[0] ) {
      setInterval(update_weather, 60000);
  }
}


function connect_websocket_for_info_board() {
    if (io_port) {
        socket = io(`http://127.0.0.1:${io_port}`);
    } else {
        socket = io("bustime.loc"); // wss://host:port/socket.io/
    }

    // http://stackoverflow.com/questions/10405070/socket-io-client-respond-to-all-events-with-one-handler
    var onevent = socket.onevent;
    socket.onevent = function (packet) {
        var args = packet.data || [];
        onevent.call (this, packet);    // original call
        packet.data = ["*"].concat(args);
        onevent.call(this, packet);      // additional call to catch-all
    };


    socket.on('connect', function() {
        var d = new Date();
        console.log(d + ": Socket connected STOP_INFO");
        socket.emit('authentication', {username: us_id, password: "p"});
        console.log("JOIN ", "ru.bustime.stop_id__", stop_id);
        socket.emit('join', "ru.bustime.stop_id__" + stop_id);
    });

    socket.on("*",function(event,data) {
        info_board_router(data);
    });

    socket.on('disconnect', function() {
        //console.log("Disconnect");
    });
}


function info_board_router(event) {
    var p = 0;
    console.log("ROUTER")
    if (event['stops']) {
        update_info_board_stops(event['stops']);
        server_date_info_board();
        p++;
    }
}

function server_date_info_board() {
  let d = new Date();   // local browser time
  if( tz_offset ) {     // calculating in views.py
      d.setTime(d.getTime() + (d.getTimezoneOffset() * 60000)); // UTC
      let uts = Math.floor(d.getTime() / 1000); // unix ts (UTC)
      let lts = uts + tz_offset; // local ts
      d = new Date(lts * 1000); // local place time
  }

  if( $("#now_date")[0] ) { // if element exists
      let formatter = new Intl.DateTimeFormat([], { year:'numeric', month:'long', day:'numeric'}); // []-browser default locale
      let sd = formatter.format(d); // '27 августа 2024 г.'
      $("#now_date").html(sd);
  }

  if( $(".stop_updated")[0] ) { // if element exists
      let t = d.toLocaleString('ru-RU');    // '27.08.2024, 12:06:40'
      let htime = t.split(", ")[1]; // '12:06:40'
      htime = htime.split(":").slice(0,2).join(':');    // '12:06'
      $(".stop_updated").html(htime);
  }
} // server_date_info_board

function update_info_board_stops(msg) {
    var i, si, half, target, htmlus, j, m, ns, qs, somesugar;

    m = msg[0];
    qs = {};
    ns = "";

    var event;
    var d;
    var big_icon;
    var bname;
    var t2;

    myCollection.clearLayers();
    for (j = 0; j < m['data'].length; j++) { // bus data
        z = m['data'][j];
        //console.log(j, 'z=', z);

        // иконка автобуса
        try {
            big_icon = bus_icon_chooser( BUSES[z['bid']]['ttype'] );
        } catch(e) {
            big_icon = bus_icon_chooser( 0 );
        }
        /* https://gitlab.com/nornk/bustime/-/issues/3705
        somesugar = '<div class="tatu"><div class="sprite sprite-' + big_icon +' active"></div> '+z['n'];
        */
        // иконка маршрута
        somesugar = '<div class="ui blue huge label">'+z['n'];
        if ( z['l']['r'] ) {
          somesugar = somesugar + '&nbsp;<i class="fa-wheelchair-alt fa"></i>';
        }
        somesugar = somesugar+"</div>";

        if( z['t2'] && z['t2'] != z['t'] && z['t2'] != 'null' )
            t2 = z['t2'];
        else
            t2 = '';
        ns = ns + "<tr><td><b>" + z['t'] + "</b></td><td>" + somesugar + "</td><td><b>" + t2 + "</b></td></tr>";

        event = z['l'];
        d = event['d'];
        if (d === 0) {
            extra_c = "color-1-2-bg";
            sc = "#74c0ec";
        } else {
            extra_c = "color-2-2-bg";
            sc = "#5ec57c";
        }
        bname = "<b>" + z['n'] + "</b>";
        if (event['g'] && 0) {
            bname = bname + " " + event['g'];
        }
        big_icon = '<div class="sprite sprite-' + big_icon +' active" map_vehicle_id="' + event['u'] + '"></div>';
        bname = big_icon+bname;
        MapIconDiv = L.divIcon({
            iconSize: [112, 18],
            iconAnchor: [-3, 9],
            className: 'MapIconDiv ' + extra_c,
            html: bname
        });
        marker = L.marker([event['y'], event['x']], { icon: MapIconDiv, zIndexOffset: 100});
        myCollection.addLayer(marker);

        if (!isEmpty(event['py']) || !isEmpty(event['px'])) {
            latlngs = [
                [event['y'], event['x']],
                [event['py'], event['px']]
            ];

            polyline = L.polyline(latlngs, { color: sc, opacity: 0.8 });

            myCollection.addLayer(polyline);
        }
    }

    $(".stop_result." + m['nbid']).html(ns);

  if( $(".stop_updated")[0] ) { // if element exists
      $(".stop_updated").css('color', 'red');
      setTimeout(function() {
          $(".stop_updated").css('color', '');
      }, 500);
  }
}
function start_map_for_info_board() {
    myCollection = L.featureGroup();
    var map_exists = document.getElementById('lmap');
    if(map_exists){
        busstop_collection = L.featureGroup();
        var OSMURL = '//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
        var OSM_STYLE = 'https://demotiles.maplibre.org/style.json';
        // var OSMURL = '//osmtile.bustime.ru/{z}/{x}/{y}.png';
        // var osm = new L.TileLayer(OSMURL, { minZoom: 1,maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}); // , detectRetina:true
        // var osm = new L.TileLayer(OSMURL, { minZoom: 1, maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', detectRetina:true });
        var osm = L.maplibreGL({
            style: OSM_STYLE,
            minZoom: 1,maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        });

        var cx, cy, cz;
        if (typeof set_map_center !== "undefined" && set_map_center) {
            set_map_center = set_map_center.split(",");
            cx = parseFloat(set_map_center[0]);
            cy = parseFloat(set_map_center[1]);
            cz = parseInt(set_map_center[2], 10);
        } else {
            cy = stop_y
            cx = stop_x;
            cz = 15;
        }
        map = L.map('lmap', { center: [cy, cx], zoom:cz, scrollWheelZoom: true, layers: [osm, myCollection] });
        // map.on('click', function(ev) {
        //     alert(ev.latlng);
        // });
        map.on('moveend zoomend', function(ev) {
            var c = map.getCenter();
            var request = $.ajax({
                url: "/ajax/stop_id_set_map_center/",
                type: "get",
                data: {
                    stop_id: stop_id,
                    x: c.lng,
                    y: c.lat,
                    z: map.getZoom()
                }
            });
        });
        var baseLayers = {
            "Карта": osm,
        };
        var overlays = {
            "Транспорт": myCollection,
        };
            // "Остановки": busstop_collection,
        L.control.layers(baseLayers, overlays, { hideSingleBase: true }).addTo(map);
        // map.setView([stop_y, stop_x], 14);
        icon_stop0 = iconizer('/static/img/bs_26_0.png', [26, 34]);
        osm_stops0 = L.featureGroup().addTo(map);
        // marker.bindPopup(tram_only+stop['id']+"<br/>"+stop['name']+"<br/>сл. "+stop['moveto']);
        // marker.setContent("I am a standalone popup.")
        // popup = L.popup()
        marker = L.marker([stop_y, stop_x], {icon: icon_stop0}).addTo(osm_stops0);
        popup = L.popup()
                .setLatLng([stop_y, stop_x])
                .setContent(stop_name)
                .addTo(osm_stops0);
    }   // if(map_exists)
}   // function map_start

function bus_icon_chooser(ttype) {
    var ttype_icon;
    if (ttype == "0") {
        ttype_icon = 'bus';
    } else if (ttype == "1") {
        ttype_icon = 'trolleybus';
    } else if (ttype == "2") {
        // ttype = 'sprite-btype-tramway';
        ttype_icon = 'tramway';
    } else if (ttype == "3") {
        ttype_icon = 'bus-taxi';
    } else if (ttype == "5") {
        ttype_icon = '2bus';
    }
    return ttype_icon;
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

function isEmpty(value) {
    return (value == null || (typeof value === "string" && value.trim().length === 0));
}


function update_weather() {
    if( $("#weather")[0] ) {
        $.ajax({
            url: `/ajax/ajax_get_weather/?place_id=${us_city}`,
            type: "GET"
        }).done(function(msg) {
            if( $("#weather")[0] ) {
                msg = JSON.parse(msg);
                let html = msg.avg_temp > 0 ? '+' : '';
                html += `${msg.avg_temp}˚C&nbsp;`;
                html += msg.weather;
                $("#weather").html(html);
            }
        });
    }
}