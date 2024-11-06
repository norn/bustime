#!/usr/bin/env python

from devinclude import *
from bustime.models import *


def watch() -> None:
    duration = None
    pipe_io = REDIS_IO.pipeline()
    pipe = REDIS.pipeline()

    while True:
        tic = time.monotonic()

        # some stats for _kitchen (one second behind)
        if duration:
            dat = {"action": "eps", \
                   "duration": "%.4f" % duration, \
                   "eps_total": eps_total, \
                   "pids_total":pids_total, \
                   "pids": len(pids)}
            sio_pub("_kitchen", dat, pipe=pipe_io)

        pids = places_filtered()
        _ = [pipe.get(f"eps_{pid}_{datetime.datetime.now().second}") for pid in pids]
        all_events_count = pipe.execute()
        eps_total = 0
        pids_total = 0
        for pid, data in zip(pids, all_events_count):
            if data is not None:
                try:
                    eps = int(data)
                except Exception:
                    eps = 0
                # print(f"Events Count for eps_{pid}_{datetime.datetime.now().second}: {eps}")
                if eps > 0:
                    updater = {"state": CityUpdaterState.POST_TURBINE_UPDATE.name.lower(), "events_count": eps}
                    sio_pub(f"ru.bustime.updater__{pid}", {"updater": updater}, pipe=pipe_io)
                    eps_total += eps
                    pids_total += 1

        pipe_io.execute()
        duration = time.monotonic() - tic
        time.sleep(max(1.0 - duration, 0))


if __name__ == "__main__":
    watch()
