BEGIN;
CREATE TABLE "bustime_city" (
    "id" integer NOT NULL PRIMARY KEY,
    "active" bool NOT NULL,
    "name" varchar(64) NOT NULL
)
;
CREATE TABLE "bustime_bus" (
    "id" integer NOT NULL PRIMARY KEY,
    "active" bool NOT NULL,
    "name" varchar(128) NOT NULL,
    "distance" real,
    "travel_time" real,
    "description" varchar(128),
    "order_" integer,
    "ttype" integer,
    "napr_a" varchar(128),
    "napr_b" varchar(128),
    "route_start" varchar(64),
    "route_stop" varchar(64),
    "route_real_start" datetime,
    "route_real_stop" datetime,
    "route_length" varchar(64),
    "city_id" integer REFERENCES "bustime_city" ("id"),
    "discount" bool NOT NULL
)
;
CREATE TABLE "bustime_nbusstop" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(128) NOT NULL,
    "name_alt" varchar(128),
    "point_x" real,
    "point_y" real,
    "moveto" varchar(128),
    "city_id" integer REFERENCES "bustime_city" ("id"),
    "tram_only" bool NOT NULL,
)
;
CREATE TABLE "bustime_route" (
    "id" integer NOT NULL PRIMARY KEY,
    "bus_id" integer NOT NULL REFERENCES "bustime_bus" ("id"),
    "busstop_id" integer NOT NULL REFERENCES "bustime_nbusstop" ("id"),
    "endpoint" bool NOT NULL,
    "direction" smallint,
    "order_" integer,
    "time_avg" integer
)
;
/*
CREATE TABLE "bustime_event" (
    "id" integer NOT NULL PRIMARY KEY,
    "uniqueid" varchar(12),
    "timestamp" datetime NOT NULL,
    "bus_id" integer NOT NULL REFERENCES "bustime_bus" ("id"),
    "heading" real,
    "speed" real,
    "busstop_next_id" integer REFERENCES "bustime_route" ("id"),
    "busstop_nearest_id" integer REFERENCES "bustime_route" ("id"),
    "busstop_prev_id" integer REFERENCES "bustime_route" ("id"),
    "direction" smallint,
    "dchange" smallint
)
;*/
CREATE INDEX "bustime_bus_68d25c7a" ON "bustime_bus" ("order_");
CREATE INDEX "bustime_bus_b376980e" ON "bustime_bus" ("city_id");
CREATE INDEX "bustime_nbusstop_b376980e" ON "bustime_nbusstop" ("city_id");
CREATE INDEX "bustime_route_2bac74a3" ON "bustime_route" ("bus_id");
CREATE INDEX "bustime_route_b4f1f4d4" ON "bustime_route" ("busstop_id");

COMMIT;
