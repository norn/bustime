#!/bin/bash

BROOT=$(pwd)
cd $BROOT/bustime/static/js/

# uncomment for see changes
#git diff bustime-main.js

# look last version of the bundle-built-X.js & get X
LAST_JS=`ls --sort=time|egrep "bundle-built-[[:digit:]]+.js"|head -n1`
NUM=$(echo $LAST_JS|awk -F- {'print $3'}|sed "s/.js//")

# pre version, it will be pre-pre version
let NUM_DEL=$NUM-1
# new version
let NUM=$NUM+1

# build new version
grunt --build=$NUM

# delete pre-pre version
PRE_LAST_JS="bundle-built-$NUM_DEL.js"
rm $PRE_LAST_JS 2> /dev/null

echo "collect static"
cd $BROOT && ./4collect_static.sh

echo New release: $NUM
echo
