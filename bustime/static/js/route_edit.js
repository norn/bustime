const RouteEditApp = {
    map: null,
    delimiters: ["[[", "]]"],
    methods: {
        iconizer: function (url, iconSize) {
            return new L.icon({
                iconUrl: url,
                iconSize: iconSize,
                iconAnchor: [iconSize[0] / 2, iconSize[1]],
                popupAnchor: [0, -iconSize[1]],
                shadowUrl: ''
            });
        },

        setupLeafletMap: function () {
            let stop_icons = {
                0: this.iconizer('/static/img/bs_26_0.png', [26, 34]),
                1: this.iconizer('/static/img/bs_26_1.png', [26, 34])
            }
            let osm = new L.TileLayer('//{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                minZoom: 5, maxZoom: 18
            });
            let googleStreets = L.tileLayer('//{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
                maxZoom: 18, subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
            });
            let googleSat = L.tileLayer('//{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                maxZoom: 18, subdomains: ['mt0', 'mt1', 'mt1', 'mt3']
            });

            let baseMaps = {
                "Sputnik": googleSat, "Google": googleStreets, "OSM": osm
            }
            const mapDiv = L.map("lmap", {
                scrollWheelZoom: true,
                fullscreenControl: true,
                layers: [osm],
                center: [US_CITY_POINT_Y, US_CITY_POINT_X],
                zoom: 13
            });
            this.map = mapDiv;
            let osm_stops = []
            let osm_stops0 = L.featureGroup().addTo(mapDiv);
            let osm_stops1 = L.featureGroup().addTo(mapDiv);
            let all_stops = L.featureGroup();
            this.allStops = all_stops;
            osm_stops.push(osm_stops0, osm_stops1);

            this.iconStops = iconizer('/static/img/busstop_icon_24.png', [24, 24]);
            for (const [k, r] of Object.entries(this.route)) {
                let marker, stop = null;
                r.forEach(stop_id => {
                    stop = this.bus_stops[stop_id];
                    if (stop) {
                        marker = L.marker([stop["y"], stop["x"]], {icon: stop_icons[parseInt(k)]});
                        marker.bindTooltip(stop["name"] + "<br/>-><br/>" + stop["moveto"]);
                        osm_stops.at(parseInt(k)).addLayer(marker);
                    }
                });
            }
            let overlayMaps = {
                "Route 1": osm_stops0, "Route 2": osm_stops1, "Все остановки": this.allStops,
            }
            L.control.layers(baseMaps, overlayMaps).addTo(mapDiv);
            if (this.route[0].length > 0) {
                bounds = osm_stops0.getBounds()
                if (bounds.isValid()) {
                    mapDiv.fitBounds(bounds);
                }
            }
            mapDiv.on('click', this.onMapClick);
            mapDiv.on('zoomend', this.smartBusStopsDraw);
            mapDiv.on('moveend', this.smartBusStopsDraw);
        },

        centralizeMap: function () {
            if (navigator.geolocation) {
                let options = {
                    enableHighAccuracy: true, maximumAge: 0
                }
                navigator.geolocation.getCurrentPosition(location => {
                    let lat, lng;
                    lat = location.coords.latitude.toFixed(7);
                    lng = location.coords.longitude.toFixed(7);
                    this.map.panTo(new L.LatLng(lat, lng));
                    this.setBusStop(lng, lat);
                }, error => {
                    console.log("GPS error:", error.code);
                }, options);
            }
        },

        circle: function () {
            if (this.route[1].length === 0) {
                if (((this.route[0].length) % 2) === 0) {
                    for (let i = ((this.route[0].length) / 2); i < this.route[0].length; i++) {
                        this.route[1].push(this.route[0][i]);
                    }
                    this.route[0].splice(((this.route[0].length) / 2), ((this.route[0].length) / 2));
                } else {
                    for (let i = ((Math.floor((this.route[0].length) / 2)) + 1); i < this.route[0].length; i++) {
                        this.route[1].push(this.route[0][i]);
                    }
                    this.route[0].splice(((Math.floor((this.route[0].length) / 2)) + 1), (Math.floor((this.route[0].length) / 2)));
                }
            }
        },

        setBusStop: function (lng, lat) {
            let popup = L.popup();
            popup.setLatLng([lat, lng])
                .setContent("Остановка здесь")
                .openOn(this.map);
            this.form.point = lng + ";" + lat;
        },

        ajaxRouteCopyBusPart: function (dir) {
            //console.log("ajaxRouteCopyBusPart");
            // запрос на список маршрутов города с направлениями
            $.ajax({
                url: "/ajax/ajax_route_get_bus_city/",
                type: "post",
                data: {
                    place_id: $('#place_id').val(),
                    place_name: $('#place_name').val(),
                },
                dataType: "json",
                contentType: "application/x-www-form-urlencoded;charset=UTF-8",
                cache: false,
                success: function (data) {
                    $("#loader").hide();
                    $("#main_container").show();
                    const selector = $("#modal-bus-select")
                    selector.empty();    // $('#modal-bus-select li').remove();
                    selector.prop("disabled", false);
                    $.each(data, function (i, item) {
                        selector.append($('<option>', {
                            value: item[0],
                            text: item[1]
                        }));
                    });
                    selector.val(data[0][0]);
                    this.routeCopyBusPart(data, dir);  // обработчик ответа
                }.bind(this),
                error: function (jqXHR, sStatus, sErrorText) {
                    console.log("ajax_route_copy_bus_part: ajax:", sStatus, sErrorText);
                }
            });
        },

        routeCopyBusPart: function (data, direction) {
            this.modal.data = data;

            // заполняем меню маршрутов
            const selector = $("#modal-bus-select");
            selector.empty();    // $('#modal-bus-select li').remove();
            $.each(data, function (i, item) {
                $('#modal-bus-select').append($('<option>', {
                    value: item[0],
                    text: item[1]
                }));
            });
            selector.val(data[0][0]);

            // заполняем меню отсановок для первого маршрута для направления 0
            this.fillModalStops(data[0][3 + parseInt($("#modal-dir-select").val())]);

            // запоминаем destination route direction
            $("#bus-copy-dest-dir").val(direction);
            this.dirModal = direction;
            // заполняем меню выбора места вставки новых остановок
            this.fillModalInsertTypeSelect(this.route[direction]);
        },

        fillModalStops: function (stops) {
            this.modal.stops = stops;
            this.modal.stopsSelected = stops;
            $(this.$refs.master_stops_modal).checkbox("set checked");
        },

        fillModalInsertTypeSelect: function (sourceRoute) {
            const selector = $("#modal-insert-type-select");
            selector.empty();
            selector.append($('<option>', {
                value: "-1",
                text: "В конец"
            }));
            selector.append($('<option>', {
                value: "-2",
                text: "В начало"
            }));
            $.each(sourceRoute, function (i, item) {
                if (i > 0) { // ибо вставлять перед первым это "В начало"
                    selector.append($('<option>', {
                        value: item,
                        text: "Перед: " + this.bus_stops[item].name
                    }));
                }
            }.bind(this));
            selector.val("-1");
        },

        modalBusSelectChange: function (e) {
            let dirSelector = $("#modal-dir-select");
            let selectedIndex = e.target.selectedIndex;
            dirSelector.val("0");
            this.modal.busIndexSelected = selectedIndex;
            this.fillModalStops(this.modal.data[selectedIndex][3 + parseInt(dirSelector.val())]);
        },

        /**
         * меню направления
         * @param e
         */
        modalDirSelectChange: function (e) {
            let busSelector = $("#modal-bus-select");
            let selectedIndex = parseInt(busSelector.prop("selectedIndex"));
            let value = parseInt(e.target.value);
            // let selectedIndex = parseInt($("#modal-bus-select").prop('selectedIndex'));
            this.modal.directionSelected = value;
            this.fillModalStops(this.modal.data[selectedIndex][3 + value]);
        },

        /**
         * чекбокс "выбрать всё"
         * @param e
         */
        modalCbAllChange: function (e) {
            let checkBoxAll = e.target;
            jQuery("input[name='modal-stop[]']").each(function () {
                this.checked = checkBoxAll.checked;
            });
        },

        netErrorHandler: function(jqXHR, exception) {
            if (jqXHR.status === 0) {
                alert('Not connect. Verify Network.');
            } else if (jqXHR.status == 404) {
                alert('Requested page not found (404).');
            } else if (jqXHR.status == 500) {
                alert('Internal Server Error (500).');
            } else if (exception === 'parsererror') {
                alert('Requested JSON parse failed.');
            } else if (exception === 'timeout') {
                alert('Time out error.');
            } else if (exception === 'abort') {
                alert('Ajax request aborted.');
            } else {
                alert('Uncaught Error. ' + jqXHR.responseText);
            }
        },

        busCopyStart: function (e) {
            // вспоминаем в какое направление вставляем
            // var direction = parseInt($("#bus-copy-dest-dir").val());
            let direction = parseInt(this.modal.direction);
            let i, insertTypeValue = parseInt($("#modal-insert-type-select").prop('selectedIndex'));
            let bs_id;
            let stops = document.getElementsByName('modal-stop[]');
            let self = this;
            console.log("S", this.modal.stopsSelected, stops);
            // вставляем выбранные остановки в массив существующих, в зависимости от выбранного способа вставки:
            switch (insertTypeValue) {
                case 0: // В конец
                    this.modal.stopsSelected.forEach(function (value) {
                        let id = parseInt(value, 10);
                        self.route[direction].push(id);
                        self.userlog.push({
                            'city': place,
                            'bus': self.busId,
                            'direction': direction,
                            'nbusstop_id': id,
                            'name': self.bus_stops[id]['name'],
                            'order': self.route[direction].length - 1,
                            'note': `Копирование остановки ${id}: dir:${direction} order:${self.route[direction].length - 1}`
                        });
                    }, this);
                    break;
                default:    // в начало или перед выбранными элементом
                    this.modal.stopsSelected.slice().reverse()
                        .forEach(function (value) {
                            let id = parseInt(value, 10);
                            this.route[direction].splice(insertTypeValue - 1, 0, id);
                            this.userlog.push({
                                'city': place,
                                'bus': this.busId,
                                'direction': direction,
                                'nbusstop_id': id,
                                'name': this.bus_stops[id]['name'],
                                'order': insertTypeValue - 1,
                                'note': `Копирование остановки ${id}: dir:${direction} order:${insertTypeValue - 1}`
                            });
                        }, this);
            }
            window.sessionStorage.setItem("userlog", JSON.stringify(this.userlog));
            // Скрыть диалог копирования
            this.modal.show = false;
        },

        saveRoute: function () {
            // console.log(route);
            let self = this;
            $.ajax({
                url: "/ajax/route_edit_save/",
                type: "post",
                data: {
                    place_id: $('#place_id').val(),
                    bus_id: this.busId,
                    route: JSON.stringify(this.route),
                    userlog: JSON.stringify(this.userlog)
                },
                dataType: "json",
                cache: false,
                success: function (result) {
                    self.status_saving = false;
                    if( result.result > 0 ) {
                        self.userlog = [];
                        window.sessionStorage.setItem("userlog", JSON.stringify(self.userlog));
                        alert("Данные сохранены");
                    }
                    else {
                        alert(result.error ? result.error : "Ошибка сохранения");
                    }
                },
                error: function (jqXHR, exception) {
                    self.status_saving = false;
                    self.netErrorHandler(jqXHR, exception);
                }
            });
            this.status_saving = true;
        },

        smartBusStopsDraw: function () {
            let bounds = this.map.getBounds();
            if (this.map.getZoom() >= 14) {
                this.allStops.clearLayers();
                if (bounds.isValid() && !this.map.status_loading) {
                    this.map.status_loading = true;                
                    $.ajax({
                        url: '/ajax/stops_by_area/',
                        method: "GET",
                        data: `west=${bounds.getWest()}&south=${bounds.getSouth()}&east=${bounds.getEast()}&north=${bounds.getNorth()}`,
                        dataType: "json",
                        success: function(result) {
                            if (result.status == "error") {
                                console.error(result);
                            } else if (result.stops) {
                                for (let key in this.bus_stops) {
                                    if (this.route[0].indexOf(parseInt(key)) == -1 &&
                                        this.route[1].indexOf(parseInt(key)) == -1) {
                                        delete this.bus_stops[key];
                                    }
                                }
                                result.stops.forEach(s => {
                                    this.bus_stops[s['id']] = s;
                                });
                            }
                            setTimeout(() => { this.map.status_loading = false; }, 100, this);
                            
                        }.bind(this),
                        error: function (jqXHR, exception) {
                            self.form.status_loading = false;
                            self.netErrorHandler(jqXHR, exception);
                            setTimeout(() => { this.map.status_loading = false; }, 100, this);
                        }
                    });
                }    

                // console.log(bounds);
                for (let key in this.bus_stops) {
                    let b = this.bus_stops[key];
                    if (b['x'] > bounds['_southWest']['lng'] &&
                        b['x'] < bounds['_northEast']['lng'] &&
                        b['y'] > bounds['_southWest']['lat'] &&
                        b['y'] < bounds['_northEast']['lat']) {
                        L.marker([b['y'], b['x']], {
                            icon: this.iconStops,
                            title: b['name']
                        }).on('click', this.onMarkerClick).addTo(this.allStops).bindPopup(b['name']);
                    }
                }
                this.map.addLayer(this.allStops);
            } else {
                this.defaultStops.forEach(s => {
                    this.bus_stops[s['id']] = s;
                })
                this.map.removeLayer(this.allStops);
            }
        },

        submitForm: function (e) {
            let form = e.target;
            let self = this;
            if (!this.form.status_loading) {
                $.ajax({
                    url: $(form).attr("action"),
                    type: "POST",
                    data: $(form).serialize(),
                    dataType: "json",
                    cache: false,
                    success: function (result) {
                        if (result.status === "error") {
                            let errors = [];
                            Object.keys(result.data).forEach(function (value) {
                                if (this.$refs.hasOwnProperty(value)) {
                                    this.form.errors[value] = true;
                                    errors.push(result.data[value]);
                                }
                            }, self);
                            $(".ui .form").form("add errors", errors);
                        } else if (result.data) {
                            self.bus_stops[result.data.id] = result.data;
                        }
                        self.form.status_loading = false;
                    },
                    error: function (jqXHR, exception) {
                        self.form.status_loading = false;
                        self.netErrorHandler(jqXHR, exception);
                    }
                });
                this.form.status_loading = true;
                this.$refs.submit.enabled
                Object.keys(this.form.errors).forEach(function (key) {
                    this.form.errors[key] = false;
                }, this);
                $(form).form('reset');
            }
        },

        onMarkerClick: function (m) {
            let lng = m.latlng.lng, lat = m.latlng.lat, drops_current;
            for (let key in this.bus_stops) {
                let b = this.bus_stops[key];
                if (b['x'] === lng && b['y'] === lat) {
                    console.log(b);
                    // drops_current = $('.ui.dropdown').dropdown("get value");
                    // if (drops_current[0] == drops_current[1] &&
                    //     drops_current[0]== b['id'].toString()) {
                    //     var check = confirm("Добавить эту остановку?");
                    //     alert('Я не знаю в какой столбик добавить, поэтому пока не активно');
                    // } else {
                    $(".bs_selected").html(b['name'] + " id=" + b['id']);
                    $('.ui.dropdown').dropdown('set selected', b['id']);
                    // }
                }
            }
        },

        onMapClick: function (e) {
            let lat, lng = e.latlng;
            lat = e.latlng.lat.toFixed(7);
            lng = e.latlng.lng.toFixed(7);
            this.setBusStop(lng, lat);
        },

        onMasterStopModalChanged: function (e) {
            this.modal.stopsSelected = e.target.checked ? this.modal.stops : []
        },

        onStopModalChanged: function (e) {
            const compareArrays = (a, b) => {
                return a.length === b.length &&
                    a.every((element, index) => -1 !== b.findIndex(x => x === element));
            }
            if (this.modal.stopsSelected.length <= 0) {
                $(this.$refs.master_stops_modal).checkbox("set unchecked");
            } else if (compareArrays(this.modal.stops, this.modal.stopsSelected)) {
                $(this.$refs.master_stops_modal).checkbox("set checked");
            } else {
                $(this.$refs.master_stops_modal).checkbox("set indeterminate");
            }
        },

        onCentralizeMap: function () {
            this.centralizeMap();
        },

        onAddBusStop: function (dir) {
            if (dir === 0 && this.selectedStop0 != null) {
                let index = this.route[0].findIndex(x => x === parseInt(this.selectedStop0));
                if (index > 0) {
                    alert("Такая остановка уже есть в списке");
                } else {
                    if (this.anchoredIndex0 > -1) {
                        this.route[0].splice(this.anchoredIndex0 + 1, 0, this.selectedStop0);
                    } else {
                        this.route[0].push(this.selectedStop0);
                    }
                }
            } else if (dir === 1 && this.selectedStop1 != null) {
                let index = this.route[1].findIndex(x => x === parseInt(this.selectedStop1));
                if (index > 0) {
                    alert("Такая остановка уже есть в списке");
                } else {
                    if (this.anchoredIndex1 > -1) {
                        this.route[1].splice(this.anchoredIndex1 + 1, 0, this.selectedStop1);
                    } else {
                        this.route[1].push(this.selectedStop1);
                    }
                }
            } else {
                alert("Остановка не выбрана");
            }
        },

        onMoveBusStopUp: function (dir, stopId) {
            if (dir === 0) {
                this.anchoredIndex0 = -1;
                let index = this.route[0].findIndex(x => x === parseInt(stopId));
                if (index > 0) {
                    [this.route[0][index - 1], this.route[0][index]] =
                        [this.route[0][index], this.route[0][index - 1]];
                }
            } else {
                this.anchoredIndex1 = -1
                let index = this.route[1].findIndex(x => x === parseInt(stopId));
                if (index > 0) {
                    [this.route[1][index - 1], this.route[1][index]] =
                        [this.route[1][index], this.route[1][index - 1]];
                }
            }
        }
        ,

        onMoveBusStopDown: function (dir, stopId) {
            if (dir === 0) {
                this.anchoredIndex0 = -1;
                let index = this.route[0].findIndex(x => x === parseInt(stopId));
                if (index < this.route[0].length - 1) {
                    [this.route[0][index + 1], this.route[0][index]] =
                        [this.route[0][index], this.route[0][index + 1]];
                }

            } else {
                this.anchoredIndex1 = -1
                let index = this.route[1].findIndex(x => x === parseInt(stopId));
                if (index < this.route[1].length - 1) {
                    [this.route[1][index + 1], this.route[1][index]] =
                        [this.route[1][index], this.route[1][index + 1]];
                }
            }
        }
        ,

        onDeleteBusStop: function (stopId, dir) {
            // console.log(stopId, dir);
            let check = confirm("Убрать эту остановку из маршрута?");
            if (!check) return;
            let index;
            if (dir === 0) {
                index = this.route[0].findIndex(x => x === parseInt(stopId));
                this.route[0].splice(index, 1);
            } else {
                index = this.route[1].findIndex(x => x === parseInt(stopId));
                this.route[1].splice(index, 1);
            }
            this.userlog.push({
                'city': place,
                'bus': this.busId,
                'direction': dir,
                'nbusstop_id': stopId,
                'name': this.bus_stops[stopId]['name'],
                'order': index,
                'note': `Удаление остановки ${stopId}: dir:${dir} order:${index}`
            });
            window.sessionStorage.setItem("userlog", JSON.stringify(this.userlog));
        }
        ,

        onAnchorBusStop: function (stopId, dir) {
            if (dir === 0) {
                let index = this.route[0].findIndex(x => x === parseInt(stopId));
                this.anchoredIndex0 = this.anchoredIndex0 !== index ? this.anchoredIndex0 = index : -1;
            } else {
                let index = this.route[1].findIndex(x => x === parseInt(stopId));
                this.anchoredIndex1 = this.anchoredIndex1 !== index ? this.anchoredIndex1 = index : -1;
            }
        }
        ,

        onShowModal: function (dir) {
            $("#loader").show();
            $("#main_container").hide();
            this.modal.show = !this.modal.show;
            this.modal.direction = dir;
            this.ajaxRouteCopyBusPart(dir);
            // $("#modal-bus-select").prop("disabled", true);
        }
    },
    
    mounted() {
        let self = this;
        $('.ui.dropdown.busstop_selector_0').ready(function (e) {
            $('.ui.dropdown.busstop_selector_0').dropdown('setting', "onChange", function (value) {
                self.selectedStop0 = parseInt(value);
            });
        });
        $('.ui.dropdown.busstop_selector_1').ready(function (e) {
            $('.ui.dropdown.busstop_selector_1').dropdown('setting', "onChange", function (value) {
                self.selectedStop1 = parseInt(value);
            });
        });
        this.userlog = window.sessionStorage.getItem("userlog");
        if (this.userlog === 'undefined') { this.userlog = null; }
        this.userlog = (this.userlog ? JSON.parse(window.sessionStorage.getItem("userlog")) : []);
        if (this.userlog.length > 0) {
            if (this.userlog[0].bus !== this.busId || this.userlog[0].city !== this.busCityId) {    // сменился маршрут без сохранения старого
                this.userlog = [];
            }
        }
        this.$refs.circle_button.addEventListener("click", (e) => {
            this.circle();
        });
        this.$refs.save_button.addEventListener("click", (e) => {
            this.saveRoute()
        });
        this.setupLeafletMap();
    }
}