var current=0;

function js_page_extra() {
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
    $("#current").change(current_change);
    $("#bus_drop").change(bus_change);
    $("[name=gosnum]").change(gosnum_change);
    $(".delete").click(del);
    $(".add_button").click(add_new);
    $(".clear").click(clear);
}   // function js_page_extra

function current_change() {
    current = $("#current").val();
    $(".current_info").removeClass("hidden");
    var cur_ma = ma[current];
    if (!cur_ma) {return}
    $("[name=xeno_id]").val(cur_ma["xeno_id"]);
    $(".xeno_id").html(cur_ma["xeno_id"]);
    $("[name=gosnum]").val(cur_ma["gosnum"]);
    $("#bus_drop").dropdown('set selected', cur_ma["bus_id"]);
    console.log(cur_ma["bus_id"]);
}

function bus_change() {
    var bus_id = $("#bus_drop").val();
    console.log(bus_id);
    ma[current]["bus_id"] = bus_id;
    ts_drop_update();
    $.ajax({
        url: "/ajax/mapping/",
        type: "get",
        data: {
            mapping_id: current,
            "bus_id": bus_id,
        },
        dataType: "json",
        cache: false
    }).done(function(res) {
      console.log(res);
    });
}

function gosnum_change() {
    var gosnum = $("[name=gosnum]").val();
    ma[current]["gosnum"] = gosnum;
    console.log(ma[current]["gosnum"]);
    ts_drop_update();
    $.ajax({
        url: "/ajax/mapping/",
        type: "get",
        data: {
            mapping_id: current,
            "gosnum": gosnum,
        },
        dataType: "json",
        cache: false
    }).done(function(res) {
      console.log(res);
    });
}

function del() {
    $.ajax({
        url: "/ajax/mapping/",
        type: "get",
        data: {
            "city_id": city_id,
             mapping_id: current,
            "delete": 1,
        },
        dataType: "json",
        cache: false
    });
    delete ma[current];
    current = "";
    ts_drop_update();
    $(".current_info").addClass("hidden");
}

function clear() {
    var c = confirm("Вы уверены что хотите очистить все назначения?");
    if (c) {
        console.log('clear');
        $.ajax({
            url: "/ajax/mapping/",
            type: "get",
            data: {
                "city_id": city_id,
                "clear": 1,
            },
            dataType: "json",
            cache: false
        }).done(function(res) {
          console.log(res);
          location.reload();
        });
    } else {
        console.log('cancel');
    }
}


function add_new() {
    var add = $("[name=add_new]").val();
    $.ajax({
        url: "/ajax/mapping/",
        type: "get",
        data: {
            "city_id": city_id,
            "add": add,
        },
        dataType: "json",
        cache: false
    }).done(function(res) {
      console.log(res);
      location.reload();
    });
}

function ts_drop_update() {
  var nvalues = [{value: "", name: "ТС"}];
  for (var key in ma) {
    nvalues.push({value: key, name: ma[key]["gosnum"] + " " + ma[key]["xeno_id"]});
  }
  nvalues = { values: nvalues };

  $('#current').dropdown('setup menu', nvalues);
  $("#current").dropdown('set selected', current);
}