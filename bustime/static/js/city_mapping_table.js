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

        $(".clear").click(clear);

        $("input:text[name*=-xeno_id]").change(value_change);
        $("input:text[name*=-gosnum]").change(value_change);
        $("select[name*=-bus_id]").change(value_change);
        $("button[id*=-delete]").click(value_change);
        $("button[name=add]").click(add_new);

        websconnect();
}   // function js_page_extra

function value_change(e){
        var a = this.id.split("-");
        var id = this.id;
        //console.log('value_change', this.id, a[0], a[1], this.value);
        $.ajax({
                url: "/ajax/mapping/",
                type: "get",
                data: {
                        "city_id": city_id,
                        "mapping_id": a[0],
                        "cmd": a[1],
                        "val": this.value
                },
                dataType: "json",
                cache: false,
                success: function(data){
                        //console.log('value_change success:', data);
                        if( data && typeof(data) == 'string' && data.indexOf("duplicate") != -1 ){
                                $("#"+id).val("");
                                $("#"+id).focus();
                                flash("#"+a[0]+"_row", "error");
                                alert("Значение повторяется");
                        }
                }
        });
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
                    document.location.reload();
                });
        }
        else {
                console.log('cancel');
        }
}


function add_new() {
        console.log('add_new');
        $.ajax({
                url: "/ajax/mapping/",
                type: "get",
                data: {
                        "city_id": city_id,
                        "add": 'new',
                },
                dataType: "json",
                cache: false
        }).done(function(res) {
                console.log('add_new: done: res=', res);
                if( res && typeof(res) == 'string' && res.indexOf("duplicate") != -1 ){
                        alert("Значение повторяется");
                }
        }).fail(function(jqXHR, textStatus) {
                console.log( "error:" + textStatus );
        });
}

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
                //console.log(d + ": Socket connected");
                socket.emit('authentication', {username: us_id, password: "", os:"web"});
                socket.emit('join', "ru.bustime.city_mapping_table_"+city_id);
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
}   // function websconnect

function router(data) {
        //console.log('router:', data);
        switch(data.cmd){
        case 'add':
                add_mapping_row(data.id, data.fields);
                break;
        case 'clear':
                if(data.id == 0)
                        $("select[name*=-bus_id]").val('0');
                else {
                        $( "#"+data.id+"-xeno_id" ).val('');
                        $( "#"+data.id+"-gosnum" ).val('');
                        $( "#"+data.id+"-bus_id" ).val('0');
                }
                break;
        case 'edit':
                flash("#"+data.id+"_row");
                var id = "#"+data.id+"-"+data.field;
                if( $(document.activeElement) != $(id))
                        $(id).val(data.value);
                break;
        case 'delete':
                flash("#"+data.id+"_row", "error");
                setTimeout(function() {
                        del_mapping_row(data.id);
                }, 200);
        }   // switch(data.cmd)
}   // function router(data)

function add_mapping_row(id, fields){
        var num = parseInt( $('#mapping_table tbody tr:last td:first').text() ) + 1;
        var tableBody = $('#mapping_table').find("tbody"),
                trLast = tableBody.find("tr:last"),
                trNew = trLast.clone(),
                el = null;

        trNew.attr("id", id+"_row");
        trNew.find("td:first").text(num);
        trNew.find("td:first").attr("id", id+"_col");

        el = trNew.find("input:text[name*=-xeno_id]");
        el.attr("id", id+"-xeno_id");
        el.attr("name", id+"-xeno_id");
        el.val("new");
        el.change(value_change);

        el = trNew.find("input:text[name*=-gosnum]");
        el.attr("id", id+"-gosnum");
        el.attr("name", id+"-gosnum");
        el.val("");
        el.change(value_change);

        el = trNew.find("select[name*=-bus_id]");
        el.attr("id", id+"-bus_id");
        el.attr("name", id+"-bus_id");
        el.val("0");
        el.change(value_change);

        el = trNew.find("button[id*=-delete]");
        el.attr("id", id+"-delete");
        el.click(value_change);

        trLast.after(trNew);

        flash("#"+id+"_row");

        trNew.find("input:text[name*=-xeno_id]").select();
        trNew.find("input:text[name*=-xeno_id]").focus();
}   // function add_mapping_row

function del_mapping_row(id){
        $("#"+id+"_row").remove();


        var rows = $('#mapping_table').find('tbody > tr').get();
        $.each(rows, function(index, row) {
                $(row).find("td:first").text(index+1);
        });
}   // function add_mapping_row

function flash(id, classname){
        classname = classname || 'color-0-bg';
        $(id).addClass(classname);
        setTimeout(function() {
                $(id).removeClass(classname);
        }, 400);
}