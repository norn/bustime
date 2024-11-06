#!/bin/bash

BROOT=$(pwd)
cd $BROOT/bustime/static/css/

# uncomment for see changes
#hg diff bustime-main.css
#hg diff bustime-page.css

# look last version of the base-union-X.css & get X
LAST_NUM=`ls --sort=time|egrep "base-union-[[:digit:]]+.css"|head -n1`
NUM=$(echo $LAST_NUM|awk -F- {'print $3'}|sed "s/.css//")

# pre version, it will be pre-pre version
let NUM_DEL=$NUM-1
# new version
let NUM=$NUM+1

grunt cssmin --build=$NUM

# delete pre-pre version
PRE_LAST_CSS="base-union-$NUM_DEL.css"
rm $PRE_LAST_CSS 2> /dev/null

echo "collect static"
cd $BROOT && ./4collect_static.sh

echo New release number is: $NUM
echo
