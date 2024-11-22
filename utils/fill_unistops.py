from xmlrpc.client import ResponseError
import devinclude
from bustime.models import *
from django.contrib.gis.measure import D


def midpoint(p1, p2):
    if p1 is None:
        return p2
    elif p2 is None:
        return p1
    return Point((p1.x + p2.x) * 0.5, (p1.y + p2.y) * 0.5)



with connection.cursor() as cursor:
    cursor.execute("""SELECT id, ST_X(point) as x, ST_Y(point) as y, name, unistop_id FROM bustime_nbusstop""")
    stops = {stop['id']: (stop['name'], stop['x'], stop['y'], stop['unistop_id']) for stop in dictfetchall(cursor)}

    # cursor.execute("""SELECT id, name, ST_X(centroid) as x, ST_Y(centroid) as y FROM bustime_unistop""")
    # # unistops = {unistop['id']: (unistop['name'], unistop['x'], unistop['y']) for unistop in dictfetchall(cursor)}
    # all_unistops = {}
    # # tic = time.perf_counter()
    # for u in dictfetchall(cursor):
    #     if not all_unistops.get(u['name']):
    #         all_unistops[u['name']] = [{'id': u['id'], 'centroid': Point(u['x'], u['y'])}]
    #     else:
    #         all_unistops[u['name']].append({'id': u['id'], 'centroid': Point(u['x'], u['y'])})
    # all_unistops = {}
    # for u in Unistop.objects.iterator():
    #     if not all_unistops.get(u.name):
    #         all_unistops[u.name] = [u]
    #     else:
    #         all_unistops[u.name].append(u)

    tic = time.perf_counter()    
    for stop in NBusStop.objects.iterator():
        try:
            stop_ids = REDIS_W.georadius(name="geo_stops", 
                longitude=stop.point.x, latitude=stop.point.y, radius=1000, unit='m')
        except Exception as e:
            stop_ids = []
            print(traceback.format_exception(e))
            
        stops_filt = []
        for stop_id in stop_ids:
            if stops[int(stop_id)][0] == stop.name:
                stops_filt.append(stops[int(stop_id)])
        print(stops_filt)

        # unistop_ids = REDIS.georadius(name="geo_unistops", 
        #     longitude=stop.point.x, latitude=stop.point.y, radius=1000, unit='m')

        # print(unistop_ids)
        # unistop = None
        # for unistop_id in unistop_ids:
        #     if unistops[int(unistop_id)][0] == stop.name:
        #         unistop = unistops[int(unistop_id)

        # unistops = all_unistops.get(stop.name)
        unistops = Unistop.objects.filter(Q(centroid__distance_lte=(stop.point, D(m=1000)), name=stop.name))
        if not unistops:
            ustop = Unistop.objects.create(name=stop.name)
        else:
            for us in unistops:
                if distance_meters(us.centroid.x, us.centroid.y, stop.point.x, stop.point.y) < 1000:
                    # ustop = Unistop.objects.get(id=us['id'])
                    ustop = us
                    break
        # ustop = Unistop(name=stop.name)

        print("USTOP", stop.id, stop.name, ustop.centroid)
        for s in stops_filt:
            ustop.centroid = midpoint(ustop.centroid, Point(s[1], s[2]))
            ustop.save()
        # if not unistop:
        #     REDIS.geoadd("geo_unistop", (ustop.centroid.x, ustop.centroid.y, ustop.name))
        print(stop.id, ustop.name, ustop.centroid)
        stop.unistop = ustop
        stop.save()

    toc = time.perf_counter()
    print(f"EXECUTION TIME {toc-tic:0.4f}")