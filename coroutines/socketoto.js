/*
После правки этого файла выполнить:
sudo supervisorctl restart bustime_socketotos:*
Проверка:
sudo supervisorctl status bustime_socketotos:*
*/
var zerorpc = require("zerorpc");
var redis_host = process.env.REDIS_IP || "127.0.0.1";
var redis_port = process.env.REDIS_PORT || "6379";
var fs = require('fs');
var options = {}
var args = process.argv.slice(2);
var listen_port = parseInt(args[0]);
var listen_host = '127.0.0.1';
var zclient_port = parseInt(args[1]);
var zclient_addr = "tcp://127.0.0.1:"+zclient_port;
var http = args.length > 2 ? args[2] === 'http' : false;
var httplib = null;

if (process.env.SOCKETOTO_HTTP || http) {
    http = true;
    httplib = require('http')
}
else {
    http = false;
    httplib = require('https')
    options = {
        key: fs.readFileSync('/path/to/privkey.pem'),
        cert: fs.readFileSync('/path/to/cert.pem'),
    };
}
console.log(`Listen: ${http ? 'HTTP' : 'HTTPS'}:${listen_port}, RPC client: ${zclient_addr}, Redis: ${redis_host}:${redis_port}`);

var zclient = new zerorpc.Client({"heartbeatInterval":108000});
zclient.connect(zclient_addr);
zclient.on("error", function(error) {
    console.error("RPC client error:", error);
});

var server = httplib.createServer(options);
var io = require('socket.io')(server);
var redis = require('redis');
var redis_client = redis.createClient({host: redis_host, port: redis_port});
var redis_sio = require('socket.io-redis');
io.adapter(redis_sio({ host: redis_host, port: redis_port }));
// var sio_emitter = require('socket.io-emitter')({ host: '127.0.0.1', port: 6379 });

setInterval(function() {
    var server_date = new Date; // json date
    //var server_date = Date.now(); // secs sience epoch
    //io.emit('server_date', {"server_date": server_date});
}, 60000);

function process_data(data, uid, os) {
    if ( typeof(data) == "string" ) {
      data = JSON.parse(data);
    }
    if (uid) {
        if (os != "web") {
            data['ms_id'] = uid;
        } else {
            data['us_id'] = uid;
        }
    }
    return data;
}

function sresponser(fn, res, uid_chan) {
    if (fn) {
        fn(res);
    } else {
        io.to(uid_chan).emit("", res);
    }
}

function update_online(city_id, os) {
    var room;
    if (Math.random() < 0.95) {return} // quick fix for redis replica flood
    if ( os == "web" ) {
      room = io.sockets.adapter.rooms["cnt_online_"+city_id+"_web"];
      if (!room) {room = []}
      redis_client.set("counter_online_"+city_id+"_web", room.length, "EX", 60*60);
    } else if ( os == "android" || os == "ios" ) {
      room = io.sockets.adapter.rooms["cnt_online_"+city_id+"_app"];
      if (!room) {room = []}
      redis_client.set("counter_online_"+city_id+"_app", room.length, "EX", 60*60);
    }
    room = io.sockets.adapter.rooms["ru.bustime.bus_amounts__"+city_id];
    if (!room) {room = []}
    redis_client.set("counter_online__"+city_id, room.length, "EX", 60*60);
}

function update_online_chat(room) {
    var room_cnt = io.sockets.adapter.rooms[room];
    if (!room_cnt) {room_cnt = []}
    room_cnt = room_cnt.length;
    redis_client.set(room+"_cnt", room_cnt, "EX", 60*60);
    var bus_id = room.split("__")[1];
    bus_id = parseInt(bus_id, 10);
    io.to(room).emit("", {"chat_online": {"online":room_cnt, "bus_id":bus_id}});
}

io.on('connection', function(socket) {
    var headers = socket['handshake']['headers'];
    var client_ip = headers['x-forwarded-for'];

    var user_city_id;
    var uid;
    var uid_chan;
    var chat_chan;
    var os;
    var version;

    socket.on('disconnect', function() {
        if (uid) {
            if (os != "web") {
                redis_client.srem("ms_online", uid);
                redis_client.srem("ms_online_"+os, uid);
            } else {
                redis_client.srem("us_online", uid);
            }
        }
        update_online(user_city_id, os);
        if (chat_chan) {
            update_online_chat(chat_chan);
        }
    });

    socket.on('authentication', function(data) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        uid = data['username'];
        if (!uid) { uid = client_ip; }
        os = data['os'];
        var password = data['password'];
        version = data['version'];
        if (os != "web") {
            uid_chan = 'ru.bustime.ms__'+uid;
            socket.join(uid_chan);
            io.to(uid_chan).emit("auth", {"auth":1});
            redis_client.sadd("ms_online_"+os, uid);
            redis_client.sadd("ms_online", uid);
        } else {
            redis_client.sadd("us_online", uid);
        }
    });

    socket.on('join', function(room) {
        if (!room) {console.log("no room?");return}
        socket.join(room);
        var prefix = "ru.bustime.bus_amounts__";
        if ( room.startsWith(prefix) ) {
            user_city_id = room.split(prefix)[1];
            if (os == "web") {
                socket.join("cnt_online_"+user_city_id+"_"+os);
            } else if (os == "android" || os == "ios" || os == "mac") {
               socket.join("cnt_online_"+user_city_id+"_app");
            } else {
               console.log("join unknown os! "+os);
            }
            update_online(user_city_id, os);
        }
        prefix = "ru.bustime.chat__";
        if ( room.startsWith(prefix) ) {
            chat_chan = room;
            update_online_chat(chat_chan);
        }
    });
    socket.on('leave', function(room) {
        if (!room) {return}
        socket.leave(room);
        var prefix = "ru.bustime.chat__";
        if ( room.startsWith(prefix) ) {
            chat_chan = null;
            update_online_chat(room);
        }
    });

    socket.on('rpc_bdata', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        var bus_id = data['bus_id'];
        var mode = data['mode'];
        var mobile = data['mobile'];
        zclient.invoke("rpc_bdata", bus_id, mode, mobile, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });

    });


    socket.on('rpc_passenger', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        data = process_data(data, uid, os || "web");

        zclient.invoke("rpc_passenger", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });


    socket.on('rpc_gps_send', function(data, fn) {
        data = process_data(data, uid, os);
        // rpc server will do deserialize by himself
        zclient.invoke("rpc_gps_send", data, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_download', function(data, fn) {
        // rpc server will do deserialize by himself
        zclient.invoke("rpc_download", data, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });


    socket.on('rpc_peer_set', function(data, fn) {
        var us_id = data['us_id'], peer_id = data['peer_id'];
        redis_client.set("us_"+us_id+"_peer", peer_id, "EX", 60*60*24);
    });

    // mobile
    socket.on('rpc_bootstrap_amounts', function(data, fn) {
        zclient.invoke("rpc_bootstrap_amounts", data, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
               sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_tcard', function(data, fn) {
        data = {'tcard_num': data}
        data = process_data(data, uid, os || "web");
        zclient.invoke("rpc_tcard", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
               sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_stop_ids', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        var ids = data['ids'];
        var mobile = data['mobile'];
        zclient.invoke("rpc_stop_ids", ids, mobile, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_status_server', function(fn) {
        zclient.invoke("rpc_status_server", function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_buses_by_radius', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        var city_id = data['city_id'];
        var x = data['x'];
        var y = data['y'];
        var buses = data['buses'];
        var radius = data['radius'];
        zclient.invoke("rpc_buses_by_radius", city_id, x, y, buses, radius, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_buses_by_radius_v2', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        var city_id = data['city_id'];
        var x = data['x'];
        var y = data['y'];
        var buses = data['buses'];
        var radius = data['radius'];
        zclient.invoke("rpc_buses_by_radius_v2", city_id, x, y, buses, radius, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_city_monitor', function(data, fn) {
        if ( typeof(data) == "string" ) {
          data = JSON.parse(data);
        }
        var city_id, sess, lon, lat, bus_name, nb_id, nb_name, mob_os, bus_id;
        city_id = data['city_id'];
        sess = data['sess'];
        x = data['x'];
        y = data['y'];
        bus_name = data['bus_name'];
        bus_id = data['bus_id'];
        nb_id = data['nb_id'];
        nb_name = data['nb_name'];
        mob_os = data['mob_os'];
        zclient.invoke("rpc_city_monitor", city_id, sess, x, y, bus_name, bus_id, nb_id, nb_name, mob_os, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_rating_get', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_rating_get", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });
    socket.on('rpc_rating_set', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_rating_set",
            JSON.stringify(data),
            function(error, res, more) {
                if (error) {
                    console.error(error);
                } else {
                    sresponser(fn, res, uid_chan);
                }
            }
        );
    });

    socket.on('rpc_chat_get', function(data, fn) {
        data = process_data(data, uid, os);
        var bus_id = data['bus_id'];
        zclient.invoke("rpc_chat_get", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_chat', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_chat", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_gosnum_set', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_gosnum_set", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_like', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_like", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_radio', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_radio", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_upload', function(data, fn) {
            data = process_data(data, uid, os);
            zclient.invoke("rpc_upload", JSON.stringify(data), function(error, res, more) {
                if (error) {
                    console.error(error);
                } else {
                    sresponser(fn, res, uid_chan);
                }
            });
        });

    socket.on('rpc_set_my_bus', function(data, fn) {
        data = process_data(data, uid, os);
            zclient.invoke("rpc_set_my_bus", JSON.stringify(data), function(error, res, more) {
                if (error) {
                    console.error(error);
                } else {
                    sresponser(fn, res, uid_chan);
                }
            });
        });

    socket.on('rpc_city_error', function(data, fn) {
        zclient.invoke("rpc_city_error", data, function(error, res, more) {
                if (error) {
                    console.error(error);
                } else {
                    sresponser(fn, res, uid_chan);
                }
            });
        });

    socket.on('rpc_status_counter', function(data, fn) {
        zclient.invoke("rpc_status_counter", data, function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
               sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_provider', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_provider", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_bus', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_bus", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_gosnum', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_gosnum", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_mobile_bootstrap', function(fn) {
        zclient.invoke("rpc_mobile_bootstrap", function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    /* get list of bus icons for city
    data: {
        ms_id: ...,
        us_id: ...,
        city_id ...
    }
    at least one field MUST be!
    */
    socket.on('rpc_get_city_icons', function(data, fn) {
        data = process_data(data, uid, os);
        zclient.invoke("rpc_get_city_icons", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_vehicle', function(data, fn) {
        data = process_data(data, uid, os || "web");
        zclient.invoke("rpc_vehicle", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

    socket.on('rpc_vehicle_info', function(data, fn) {
        data = process_data(data, uid, os || "web");
        zclient.invoke("rpc_vehicle_info", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });


    socket.on('rpc_busstop_info', function(data, fn) {
        data = process_data(data, uid, os || "web");
        zclient.invoke("rpc_busstop_info", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });


    socket.on('rpc_schedule', function(data, fn) {
        data = process_data(data, uid, os || "web");
        zclient.invoke("rpc_schedule", JSON.stringify(data), function(error, res, more) {
            if (error) {
                console.error(error);
            } else {
                sresponser(fn, res, uid_chan);
            }
        });
    });

});

server.listen(listen_port, listen_host);
