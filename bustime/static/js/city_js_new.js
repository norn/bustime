var stops = {};
var BUSES = {};
var BUS_PROVIDERS = {};
var dump_from_server;

var path_dump = '/static/other/db/v8/current/' + us_city + '.json';
var path_diff = '/static/other/db/v8/' + us_city + '_ver_' + us_city_rev + '.json.patch';

//загружаем json файл с исходной бд
fetch(path_dump).then(response => response.json())
  .then(data => {
    dump_from_server = data;
    diff_dump(dump_from_server); // после загрузки вызываем ф-ю применения дифа
  })
  .catch(error => console.error(error));


function diff_dump(dump_from_server) {
    fetch(path_diff).then(response => response.json())
        .then(diff_from_server => {
            console.log("разница с сервера", diff_from_server);

            //var starttime = performance.now();
            // применяем разницу к исходной бд
            jsonpatch.applyPatch(dump_from_server, diff_from_server);


            //var endtime = performance.now();
            //var executiontime = endtime - starttime;
            //console.log("Время выполнения", executiontime, "мс");


            // новая бд сохраняется в ту же переменную, выводим новую бд
            //console.log("новая бд", dump_from_server);

            // словарь stops
            var fields_stops = dump_from_server["nbusstop"];
            for (var key in fields_stops) {
                var id_stops = key;
                var value_stops = fields_stops[key][0];
                var ids_stops = [];
                ids_stops.push(fields_stops[key][1], fields_stops[key][2]);
                //stops.push({"id": id_stops, "value": value_stops, "ids": ids_stops});
                stops[id_stops] = {"value": value_stops, "ids": ids_stops};
            }
            //console.log('stops',stops);
            
            // словарь BUS_PROVIDERS
            var fields_provider = dump_from_server["busprovider"];
            for (var key in fields_provider) {
                var id_provider = key;
                var name_provider = fields_provider[key][3];
                BUS_PROVIDERS[id_provider] = {"name": name_provider}
            }
            //console.log('BUS_PROVIDERS', BUS_PROVIDERS);
            
            // словарь BUSES
            var fields_bus = dump_from_server["bus"];
            for (var key in fields_bus) {
                var id_bus = key;
                var name_bus = fields_bus[key][1];
                var slug_bus = fields_bus[key][2];
                var ttype_bus = fields_bus[key][5];
                var price_bus = fields_bus[key][19];
                var provider_id_bus = fields_bus[key][11];
                BUSES[id_bus] = {"name": name_bus, "slug": slug_bus, "ttype": ttype_bus, "price": price_bus, "provider_id": provider_id_bus};
            }
            //console.log('BUSES', BUSES);
        })
        .catch(error => console.error(error));
} // function diff_dump()
