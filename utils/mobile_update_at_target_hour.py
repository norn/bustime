#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
import subprocess
from devinclude import *
from bustime.models import *
from bustime.update_utils import mobile_update_place
from turbo_json_dump_update import make_patch_for_json
from django import db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d-%m-%y %H:%M:%S",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def do_shell_command(path, *args):
    cmd = [path, *args]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result, err = p.communicate()
    for line in result.decode().split('\n'):
        if line:
            logger.info(line)
    for line in err.decode().split('\n'):
        if line:
            logger.warning(line)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update mobile db dumps for Places where current hour equals to target hour")
    parser.add_argument('hour', type=int, choices=range(0, 24), help="Target hour for mobile dump update")
    args = parser.parse_args()
    logger.info("Mobile dumps update start...")
    # query = """SELECT id FROM bustime_place bp
    #             WHERE id IN %s AND EXTRACT(HOUR FROM NOW() AT TIME ZONE bp.timezone) = %s AND 
    #             bp.timezone IS NOT NULL AND bp.timezone != '' ORDER BY name"""
    # pids = places_filtered()
    # for place in Place.objects.raw(query, (tuple(pids), args.hour)):


    # Find all Places with target hour
    for place in filter(lambda p: p.now.hour == args.hour,
                        Place.objects.filter(id__in=places_filtered()).order_by("name")):
        # v5, v7
        logger.info('\n'.join(mobile_update_place(place, reload_signal=False)))

        do_shell_command(f"{settings.PROJECT_DIR}/bustime/static/other/db/v5/0diff_one.sh",
                            str(place.id))
        do_shell_command(f"{settings.PROJECT_DIR}/bustime/static/other/db/v7/0diff_one.sh",
                            str(place.id))
        # v8
        logger.info('\n'.join(make_patch_for_json(place)))

    db.connection.close()

    do_shell_command(f"{settings.PROJECT_DIR}/4collect_static.sh")

    logger.info("Mobile dumps update done...\n")
