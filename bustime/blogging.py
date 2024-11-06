# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging

def get_logger(name, prefix=None):
	if prefix:
		prefix="-%s"%prefix
	else:
		prefix=""
	path_to_log = '/tmp'
	formatter = logging.Formatter('%(asctime)s %(levelname)-5s (%(name)s) %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

	LOGGER = logging.getLogger(name, )

	# df = logging.FileHandler('%s/bustime-debug%s.txt'%(path_to_log, prefix))
	# df.setLevel(logging.DEBUG)
	# df.setFormatter(formatter)

	wi = logging.FileHandler('%s/bustime-info%s.log'%(path_to_log, prefix))
	wi.setLevel(logging.INFO)
	wi.setFormatter(formatter)

	wf = logging.FileHandler('%s/bustime-warn%s.log'%(path_to_log, prefix))
	wf.setLevel(logging.WARN)
	wf.setFormatter(formatter)

	ef = logging.FileHandler('%s/bustime-error%s.log'%(path_to_log, prefix))
	ef.setLevel(logging.ERROR)
	ef.setFormatter(formatter)

	LOGGER.addHandler(df)
	LOGGER.addHandler(wi)
	LOGGER.addHandler(wf)
	LOGGER.addHandler(ef)

	return LOGGER

# logging.basicConfig(filename='%s/bustime-debug.txt'%path_to_log, level=logging.DEBUG,
#                     format='%(asctime)s %(levelname)-5s (%(name)s) %(message)s', datefmt='%Y-%m-%d %H:%M:%S')