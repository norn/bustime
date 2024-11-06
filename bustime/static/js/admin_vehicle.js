var socket;
function js_page_extra() {
    socket = io(); // nice
    var onevent = socket.onevent;
    socket.onevent = function (packet) {
        var args = packet.data || [];
        onevent.call (this, packet);    // original call
        packet.data = ["*"].concat(args);
        onevent.call(this, packet);      // additional call to catch-all
    };
    socket.on('connect', function() {
        console.log("Socket connected");
        socket.emit('authentication', {username: us_id, password: "", os:"web"});
        socket.emit('join', "ru.bustime.status__" + city_id);
    });
    socket.on("*", function(event, data) {
        if( data['status_log'] && data['status_log']["ups"] && data['status_log']["ups"][0] && data['status_log']["ups"][0]['message'] && data['status_log']["ups"][0]['message'].indexOf("принято") !== -1){
            msg = data['status_log']["ups"][0]['message'];
            $("#message").html( msg.replace("принято к обработке ", "") );
        }
    });

    // https://github.com/Semantic-Org/Semantic-UI/issues/3424#issuecomment-161754185
    $('.ui.dropdown').dropdown({
        fullTextSearch: true,
        ignoreCase: true,
        minCharacters: 1,
        match: 'text',
        message: {
            noResults: "Не найдено"
        }
    });   // for jQuery dropdown combos
    $("#vehicle").change(vehicle_change);
    $("#cities").change(cities_change);

    update_events();
}   // function js_page_extra

function vehicle_change() {
    window.location.href = '/admin/vehicle/?u='+$("#vehicle").val();
}
function cities_change() {
    window.location.href = '/admin/vehicle/?s='+$("#cities").val();
}

function update_events() {
    var u = $("#vehicle").val();
    if( !u || u.length == 0 )
        return;

    var uniques = [u];

    $('#current_info tr').each(function() {
        var t = $(this).find("td:first").html();
        if( t && t != u )
            uniques[uniques.length] = t;
    });
    //console.log('update_events: uniques=', uniques);

    $.ajax({
        url: "/ajax/admin_vehicle_get_events/",
        type: "post",
        data: {
            "city_id": city_id,
            "events": JSON.stringify(uniques),
        },
        dataType: "json",
        cache: false,
        success: function(data, textStatus, jqXHR) {
            //console.log("update_events: result=", data);

            if( data ){
                var formatter = new Intl.DateTimeFormat("ru", {
                  year: "numeric",
                  month: "numeric",
                  day: "numeric",
                  hour: "numeric",
                  minute: "numeric",
                  second: "numeric"
                });
                var message = "";
                var city_time = new Date(data["time_city"]);

                $("#time_city").html( formatter.format(city_time) );

                data["uevents"].forEach(function(item, i, arr) {
                    var uevent_time = new Date(item.timestamp);
                    var dt = formatter.format(uevent_time);

                    $("#"+item.uniqueid+"_update").html(dt);
                    if( buses[item.bus] )
                        $("#"+item.uniqueid+"_bus").html(buses[item.bus]["name"] ? '<div class="ui label">'+buses[item.bus]["name"]+'</div>' : '&nbsp;');
                    else
                        $("#"+item.uniqueid+"_bus").html('id:' + item.bus + ' ?');

                    if(u == item.uniqueid){
                        // uevents
                        $("#uevent\\.uniqueid").html(item.uniqueid);
                        $("#uevent\\.uid_original").html(item.uid_original);
                        $("#uevent\\.gosnum").html(item.gosnum);
                        $("#uevent\\.timestamp").html(dt);
                        $("#uevent\\.src").html(item.channel+"/"+item.src);
                        $("#uevent\\.bus").html(item.bus);
                        $("#uevent\\.bus_uevent").html(item.bus_bame+" "+item.bus_city_id+":"+item.bus_city_name);

                        // vehicle
                        $("#v_"+item.uniqueid+"_update").html(dt);
                        $("#v_"+item.uniqueid+"_bus").html(item.bus_bame.length > 0 ? '<div class="ui label">'+buses[item.bus]["name"]+'</div>' : '&nbsp;');

                        // Analitic
                        if( Math.round(Math.abs(city_time - uevent_time) / 1000 / 60) >= 15 ){
                            message += "Время события отличается от времени города более чем на 15 минут, событие не попадёт в allevents<br>";
                            $("#uevent\\.timestamp").css("color", "#CC0066");
                        }
                        else{
                            $("#uevent\\.timestamp").css("color", "black");
                        }

                    }   // if(data["uniqueid"] == item.uniqueid)
                }); // data["uevents"].forEach(function(item, i, arr)

                // allevents
                if( data["allevent"] && u == data["allevent"]["uniqueid"]){

                    $("#allevent\\.uniqueid").html(data["allevent"]["uniqueid"]);
                    $("#allevent\\.uid_original").html(data["allevent"]["uid_original"]);
                    $("#allevent\\.gosnum").html(data["allevent"]["gosnum"]);
                    $("#allevent\\.timestamp").html( formatter.format(new Date(data["allevent"]["timestamp"])) );
                    $("#allevent\\.src").html(data["allevent"]["channel"]+"/"+data["allevent"]["src"]);
                    if( data["allevent"]["bus"] ){
                        $("#allevent\\.bus").html(data["allevent"]["bus"]);
                        $("#allevent\\.bus_allvent").html(data["allevent"]["bus_bame"]+" "+data["allevent"]["bus_city_id"]+":"+data["allevent"]["bus_city_name"]);
                    }
                    else {
                        $("#allevent\\.bus").html('&nbsp;');
                        $("#allevent\\.bus_allvent").html('&nbsp;');
                    }

                    $("#allevent\\.timestamp_prev").html( formatter.format(new Date(data["allevent"]["timestamp_prev"])) );
                    $("#allevent\\.x_prev").html(data["allevent"]["x_prev"]);
                    $("#allevent\\.y_prev").html(data["allevent"]["y_prev"]);
                    $("#allevent\\.last_point_update").html( formatter.format(new Date(data["allevent"]["last_point_update"])) );

                    $("#allevent\\.x").html(data["allevent"]["x"]);
                    $("#allevent\\.x_label").css("color", data["allevent"]["x"]==data["allevent"]["x_prev"] && data["allevent"]["y"]==data["allevent"]["y_prev"] ? "#CC0066" : "black");

                    $("#allevent\\.y").html(data["allevent"]["y"]);
                    $("#allevent\\.y_label").css("color", data["allevent"]["x"]==data["allevent"]["x_prev"] && data["allevent"]["y"]==data["allevent"]["y_prev"] ? "#CC0066" : "black");

                    $("#allevent\\.distance").html(data["allevent"]["distance"]);
                    $("#allevent\\.speed").html(data["allevent"]["speed"]);

                    $("#allevent\\.sleeping").html(data["allevent"]["sleeping"] ? "True" : "False");
                    $("#allevent\\.sleeping_label").css("color", data["allevent"]["sleeping"] ? "#CC0066" : "black");

                    $("#allevent\\.zombie").html(data["allevent"]["zombie"] ? "True" : "False");
                    $("#allevent\\.zombie_label").css("color", data["allevent"]["zombie"] ? "#CC0066" : "black");

                    $("#allevent\\.away").html(data["allevent"]["away"] ? "True" : "False");
                    $("#allevent\\.away_label").css("color", data["allevent"]["away"] ? "#CC0066" : "black");

                    $("#allevent\\.busstop_nearest").html(data["allevent"]["busstop_nearest"]["busstop_name"]);
                    $("#allevent\\.busstop_nearest_label").css("color", !data["allevent"]["busstop_nearest"] || !data["allevent"]["busstop_nearest"]["busstop_name"] ? "#CC0066" : "black");
                    if( !data["allevent"]["busstop_nearest"] || !data["allevent"]["busstop_nearest"]["busstop_name"] )
                        message += "busstop_nearest пуст, машина не будет показана на маршруте<br>";

                    $("#allevent\\.last_changed").html( formatter.format(new Date(data["allevent"]["last_changed"])) );
                }   // if( data["allevent"] && data["allevent"].length )

                $("#uevent\\.messages").html(message);

                data["gevents"].forEach(function(item, i, arr) {
                    if( item.uniqueid == u ){
                        var gevent_time = new Date(item.timestamp);
                        var dt = formatter.format(gevent_time);
                        $("#gevent\\.uniqueid").html(item.uniqueid);
                        $("#gevent\\.uid_original").html(item.uid_original);
                        $("#gevent\\.gosnum").html(item.gosnum);
                        $("#gevent\\.timestamp").html(dt);
                        $("#gevent\\.src").html(item.channel+"/"+item.src);
                        $("#gevent\\.custom").html(item.custom);
                        $("#gevent\\.x").html(item.x);
                        $("#gevent\\.y").html(item.y);
                        $("#gevent\\.speed").html(item.speed);
                        $("#gevent\\.bus").html(item.bus);
                        $("#gevent\\.bus_gevent").html(item.bus_bame+" "+item.bus_city_id+":"+item.bus_city_name);
                    }   // if( item.uniqueid == u )
                }); // data["item."].forEach(function(item, i, arr)

                if( data["to_ignore"] )
                    $("#to_ignore").html(data["to_ignore"]);

                if( data["anomalies"] )
                    $("#anomalies").html(data["anomalies"]);
            }   // if( data.length )
        },  // success
        error: function(jqXHR, textStatus, errorThrown) {
            console.log("update_events:", textStatus, errorThrown);
        }
    }); // $.ajax

    setTimeout(update_events, 5000);
}   // function update_events

function delVehicle(id) {
    //console.log('delVehicle:', id);
    if( !confirm('Удаляем машину '+id+', вы уверены?') )
        return;

    $.ajax({
        url: "/ajax/admin_vehicle_del_vehicle/",
        type: "post",
        data: {
            "city_id": city_id,
            "uniqueid": id,
        },
        dataType: "json",
        cache: false,
        success: function(data, textStatus, jqXHR) {
            if( data["error"] )
                alert(data["error"]);
            else
                window.location.reload(true);   // force request page from server
        },  // success
        error: function(jqXHR, textStatus, errorThrown) {
            console.log("delVehicle:", textStatus, errorThrown);
            alert(errorThrown);
        }
    }); // $.ajax
}   // function delVehicle

function openInNewTab(url) {
  var win = window.open(url, '_blank');
  win.focus();
}
