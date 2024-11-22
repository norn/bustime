function websconnect() {
    socket = io(); // nice

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
        console.log(d + ": Socket connected");
        socket.emit('authentication', {username: us_id, password: "", os:"web"});
        socket.emit('join', "ru.bustime.select");
        // socket.emit('join', "ru.bustime.counters");
        // socket.emit('join', "ru.bustime.bus_amounts__" + us_city);
        // socket.emit('join', "ru.bustime.counters__" + us_city);
        // socket.emit('join', "ru.bustime.us__" + us_id);
        // socket.emit('join', "ru.bustime.city__" + us_city);
    });

    socket.on("*",function(event,data) {
        router(data);
    });

    socket.on('disconnect', function() {
        console.log("Disconnect");
    });
}

function js_page_extra() {
  console.log("Select");
  $('table').tablesort();
  websconnect();
}

function router(data) {
  // console.log(data);
  var dat = data['zbusupd'];
  var d, t, res;
  for(var key in dat) {
    d = data['zbusupd'][key];
    // console.log(d);
    t = d[0];
    res = d[1];
    if (res == true) {
      $("."+key+">.panic").html('<i class="green checkmark icon">');
      $("."+key).removeClass("error");
    } else {
      $("."+key+">.panic").html('<i class="red times icon">');
      $("."+key).removeClass("positive").addClass("error");
    }
    $(".zdur_"+key).attr("data-sort-value", ""+t).html(t).addClass('color-0-bg');
    if (t>10) {
      $(".zdur_"+key).addClass("color-1-bg color-0");
    } else {
      $(".zdur_"+key).removeClass("color-1-bg color-0");
    }
    setTimeout(function() {
        $(".zdur_"+key).removeClass('color-0-bg');
    }, 400);
  }
}