from bustime.models import *
from typing import Iterable


# 10 сек. выигрыша на больших расчётах (например по catalog 3)
def filter_places(point, radius=100):
    if fill_places_geospatial():    # models.py
        places = REDIS_W.georadius("geo_places", point.x, point.y, radius, "km")
        places = list(map(int, places))
    else:
        places = []
    return places
# filter_places


def find_places_by_points(points: Iterable[Point]) -> set[Place]:
    """Return set of places, that geometries has intersections with given points."""
    pnts = LineString(*points)
    pls = Place.objects.raw("""SELECT bp.id FROM bustime_place bp
        INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
        WHERE ST_Intersects(bpa.geometry, ST_SetSRID(ST_GeomFromWkb(%s), 4326)) LIMIT 10""", (pnts.wkb,))
    return {place for place in pls}



def update_bus_places(entity, id, turbo=False, DEBUG=False)->list:
    retval = [] # places ids
    excluded_city = [6, 183, 1674442]
    if entity == 'city':
        if id == 0:
            if DEBUG: print("All cities")
            buses = Bus.objects.exclude(city_id__in=excluded_city)
        elif id not in excluded_city:
            if DEBUG: print(f"City {id}")
            buses = Bus.objects.filter(city_id=id)
        else:
            print(f"Sorry, city {id} is not possibly")
            return retval
    elif entity == 'place':
        if id == 0:
            if DEBUG: print("All places")
            buses = Bus.objects.exclude(city_id__in=excluded_city)
        elif id < 0:
            if DEBUG: print("All buses with empty places")
            buses = Bus.objects.filter(places__isnull=True).exclude(city_id__in=excluded_city)
        else:
            if DEBUG: print(f"Place {id}")
            buses = Bus.objects.filter(places__id=id).exclude(city_id__in=excluded_city)
    elif entity == 'bus':
        if id == 0:
            if DEBUG: print("All buses")
            buses = Bus.objects.exclude(city_id__in=excluded_city)
        else:
            if DEBUG: print(f"Bus {id}")
            buses = Bus.objects.filter(id=id).exclude(city_id__in=excluded_city)
    elif entity == 'catalog':
        if id == 0:
            print(f"Sorry, catalog {id} is not possibly")
            return retval

        if DEBUG: print(f"Catalog {id}")
        # отфильровать маршруты только этого catalog_id
        scatalog_id = str(id)
        buses = []
        for bus in Bus.objects.exclude(city_id__in=excluded_city):
            if bus.xeno_id and '*' in bus.xeno_id and bus.xeno_id.split('*')[0] == scatalog_id:
                buses.append(bus)
            elif bus.murl and '*' in bus.murl:
                for xeno_id in bus.murl.split(','):
                    if xeno_id.split('*')[0] == scatalog_id:
                        buses.append(bus)
    else:
        print("Parameter entity must be 'city', 'bus', 'catalog' or 'place' only")
        return retval

    if len(buses) == 0:
        print(f"No buses found")
        return retval

    if DEBUG:
        print("buses:")
        start_time = time.time()

    for bus in buses:
        bus.places.clear()

        if turbo and bus.turbo == False:
            bus.turbo = True
            bus.save(update_fields=['turbo'])

        points = NBusStop.objects.filter(route__bus=bus).values_list('point', flat=True)

        if DEBUG:
            print(f"id:{bus.id}, name:{bus.name}, type:{bus.ttype}, stops:{len(points)}, city:{bus.city}")

        if len(points) == 0:    # остановок ещё нет у маршрута, случается при ручном создании/редактировании маршрута
            if bus.city:
                p = Place.objects.filter(id=bus.city.id).first()
                if p:
                    bus.places.add(p)
        else:
            # сначала заполнить set, потом из него один раз записать в бд быстрей, чем каждый раз писать в бд
            try:
                places = find_places_by_points(points)
            except:
                places = set()

            if not places:
                for stop in NBusStop.objects.filter(route__bus=bus).distinct():
                    pnt = stop.point
                    near_places = filter_places(pnt, 100)  # отфильтруем ближайшие через геокэш
                    #if DEBUG:
                    #    print(f'stop.point={stop.point}, {len(near_places)} near_places: {near_places}')
                    #    print(f'pnt.wkt={pnt.wkt}')

                    if near_places:
                        pls = Place.objects.raw("""
                            SELECT bp.id
                            FROM bustime_place bp
                            INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
                            WHERE bp.id = ANY(%s)
                            AND ST_Contains(bpa.geometry, ST_SetSRID(ST_GeomFromWkb(%s), 4326))
                            """, [near_places, pnt.wkb,])
                        #if DEBUG: print(f'1, pls={[x.id for x in pls]}')

                    else:
                        # геокэша нет, придётся весь список шерстить
                        pls = Place.objects.raw("""
                            SELECT bp.id FROM bustime_place bp
                                INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
                                WHERE ST_Contains(bpa.geometry, ST_SetSRID(ST_GeomFromWkb(%s), 4326))
                            """, [pnt.wkb,])
                        #if DEBUG: print(f'2, pls={[x.id for x in pls]}')

                    if not pls:
                        if near_places:
                            pls = Place.objects.raw("""
                                SELECT bp.id FROM bustime_place bp
                                INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
                                WHERE bp.id = ANY(%s)
                                AND bp.name IS NOT NULL
                                ORDER BY population desc, ST_SetSRID(ST_GeomFromWKb(%s), 4326) <-> bpa.geometry
                                LIMIT 1;
                            """, [near_places, pnt.wkb,])
                            #if DEBUG: print(f'3, pls={[x.id for x in pls]}')

                        if not pls: # последний рубеж, если не нашли в отфильрованных
                            # <-> — Returns the 2D distance between A and B
                            # https://access.crunchydata.com/documentation/postgis/3.0.1/pdf/postgis.pdf
                            pls = Place.objects.raw("""
                                SELECT bp.id FROM bustime_place bp
                                INNER JOIN bustime_placearea bpa ON (bp.osm_area_id = bpa.osm_id AND bp.osm_area_type = bpa.osm_type)
                                WHERE bp.name IS NOT NULL
                                ORDER BY ST_SetSRID(ST_GeomFromWKb(%s), 4326) <-> bpa.geometry asc, population desc
                                LIMIT 1;
                            """, [pnt.wkb,])
                            #if DEBUG: print(f'4, pls={[x.id for x in pls]}')

                        if not pls:
                            if DEBUG: print("PA not found!")
                    # if not pls

                    """
                    if DEBUG:
                        if not pls:
                            print(f'   stop: {stop.id} {stop.name}, near_places:')
                            for id in near_places:
                                p = Place.objects.filter(id=id).first()
                                dis = int(distance_meters(pnt.x, pnt.y, p.point.x, p.point.y))
                                print(f'      {p.id}: {p.name}, population={p.population}, dis={dis}')
                    """

                    for p in pls:
                        places.add(p)
                # for stop in NBusStop.objects.filter

            # теперь пишем в БД
            for p in places:
                bus.places.add(p)
                retval.append(p.id)
        # else if len(points) == 0

        if DEBUG:
            print("   bus.places: %s" % ','.join([x.name for x in bus.places.all()]))
    # for bus in buses

    if DEBUG:
        print("Duration: %.3f" % (time.time() - start_time))
    return retval
# def update_bus_places