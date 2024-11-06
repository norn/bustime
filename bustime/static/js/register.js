function websconnect() {
    socket = io();
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
        socket.emit('join', "ru.bustime.us__" + us_id);
    });

    socket.on("*",function(event,data) {
        router(data);
    });

    socket.on('disconnect', function() {
        console.log("Disconnect");
    });
}

function js_page_extra() {
  websconnect();
  setTimeout(function() {
        url_dance();
   }, 1500);
}

function router(event) {
    if (event['us_cmd']) {
        update_cmd(event);
    }
}

function update_cmd(msg) {
    if (msg["us_cmd"] == "reload") {
            location.reload();
    }
}

function url_dance() {
    var queryDict = {};
    location.search.substr(1).split("&").forEach(function(item) {queryDict[item.split("=")[0]] = item.split("=")[1]});
    if (queryDict['next'] && us_user) {
        window.location.href = queryDict['next'];
    }
}
