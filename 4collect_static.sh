#!/bin/sh

# compression
#addons/brotldown.sh $(pwd)

./manage.py collectstatic -l --noinput

#echo dead links:
find static/ -type l -xtype l

#remove dead links:
find static/ -type l -xtype l -exec rm {} \;
