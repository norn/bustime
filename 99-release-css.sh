#!/bin/bash

#time, atime, access, use
CSS_ROOT="bustime/static/css"

cd $CSS_ROOT
hg diff bustime-main.css
hg diff bustime-page.css
echo "Continue?"
read

CMD="ls --sort=time base-page-???.css"
LAST_NUM=$($CMD|head -n1)
NUM=$(echo $LAST_NUM|awk -F- {'print $3'}|sed "s/.css//")
BASE=$(echo $LAST_NUM|awk -F- {'print $1'})
#echo Previous was $NUM

let NUM=$NUM+1

# just base page
cat leaflet.css   > base-page-$NUM.css
cat semantic-page.css  >> base-page-$NUM.css
cat font-awesome.min.css >> base-page-$NUM.css
cat bustime-page.css >> base-page-$NUM.css

# for main
cat leaflet.css   > base-main-$NUM.css
cat semantic-main.css  >> base-main-$NUM.css
cat font-awesome.min.css >> base-main-$NUM.css
cat bustime-page.css >> base-main-$NUM.css
cat bustime-main.css >> base-main-$NUM.css
r.js -o cssIn=base-main-$NUM.css out=base-main-$NUM.css

cd -
./4collect_static.sh
echo New release number is: $NUM
echo

# http://cssminifier.com/
# http://www.giftofspeed.com/defer-loading-css/
# http://stackoverflow.com/questions/19374843/css-delivery-optimization-how-to-defer-css-loading