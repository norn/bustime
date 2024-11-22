#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Back up event count for each place's datasource into DataSourcePlaceEventsCount table
# this data is used to sort most relevant providers 
# useful for turbo_mobile_update_v5_new (mobile can only show 1 provider)
# executed every 15 minutes
# https://gitlab.com/nornk/bustime/-/issues/3353
# https://git.bustime.loc/norn/bustime/pulls/2859


from devinclude import *
from bustime.models import *
import argparse
import time
from django.utils.timezone import now

"""
Testing:
python utils/update_event_counts.py --DEBUG

Checking status:
sudo supervisorctl status update_event_counts

Restarting after edit:
sudo supervisorctl restart update_event_counts
"""


def update_event_counts(DEBUG=False):
    """
    1. Fetches event UIDs and details from Redis.
    2. Iterates over active DataSources and their related Places to count events based on the DataSource's channel.
    3. Creates and bulk saves `DataSourcePlaceEventsCount` entries for each Place.

    Args:
        debug (bool): If True, enables debug output. Default is False.
    """

    now_start = now()
    bulk_create_list = []

    if DEBUG:
        print(f"START: {now_start}")

    # Get all event UIDs
    uids = REDIS.smembers("events")
    uids = [x.decode('utf8') for x in uids]
    to_get = [f'event_{uid}' for uid in uids]

    # Retrieve event details from Redis
    events = rcache_mget(to_get)
    if DEBUG:
        print(f"{now() - now_start}s Fetched {len(events)} events")

    # Filter active data sources
    datasources = {}
    for ds in DataSource.objects.filter():
        datasources[f"{ds.src}*{ds.channel}"] = ds

    if DEBUG:
        print(f"{now() - now_start}s | Fetched {len(datasources)} active datasources")

    uec={}
    for event in events:
        if not event: continue
        bus = bus_get(event.get('bus_id'))
        if not bus: continue
        place_ids = bus.places_all # Get list of place_ids for the bus_id
        ch = event.get('channel')
        src = event.get('src')
        if place_ids:
            for place_id in place_ids:
                if not uec.get(ch):
                    uec[ch] = {}
                if not uec[ch].get(src):
                    uec[ch][src] = defaultdict(int)
                uec[ch][src][place_id] +=1
        else:
            if DEBUG:
                print(f"----Warning: 'bus_id' {bus.id} not mapped to any places")

    bulk_create_list = []
    for ch,v in uec.items():
        for src,vv in v.items():
            for place,ecnt in vv.items():
                if DEBUG:
                    print(ch, src, place, ecnt)
                datasource = datasources[f"{src}*{ch}"]
                dspe = DataSourcePlaceEventsCount(
                         ctime=now_start,
                         ecnt=ecnt,
                         datasource=datasource,
                         place_id=place_id
                    )
                bulk_create_list.append(dspe)

    if bulk_create_list:
        DataSourcePlaceEventsCount.objects.bulk_create(bulk_create_list)
        print(f"{now() - now_start}s | Bulk created {len(bulk_create_list)} DataSourcePlaceEventsCount entries.")

    now_end = now()
    print(f"END: {now_end}")
    print(f"Elapsed: {now_end - now_start} s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update event counts for each DataSource and Place every 15 minutes')
    parser.add_argument('--DEBUG', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    while True:
        try:
            update_event_counts(DEBUG=args.DEBUG)
        except Exception as e:
            print(f"An error occurred: {e}")
        time.sleep(15 * 60)  # Sleep for 15 minutes
