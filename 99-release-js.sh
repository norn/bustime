#!/bin/bash

# time, atime, access, use
BROOT="/r/bustime/bustime"
cd $BROOT/bustime/static/js/
hg diff bustime-main.js
echo Continue?
read

CMD="ls --sort=time main-built-???.js"
LAST_JS=$($CMD|head -n1)
NUM=$(echo $LAST_JS|awk -F- {'print $3'}|sed "s/.js//")
let NUM=$NUM+1

#paths.jquery=some/other/jquery
# npm install -g requirejs
r.js -o baseURL=./ name=require-main out=main-built-$NUM.js
r.js -o baseURL=./ name=require-main-nosound out=main-built-nosound-$NUM.js
#r.js -o baseURL=./ name=require-page out=page-built-$NUM.js

echo New release: $NUM
echo 

echo Collecting...
cd $BROOT && ./4collect_static.sh