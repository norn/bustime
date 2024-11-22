#!/bin/bash

DBVER=v5
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DIR_STATIC="$(dirname $(dirname $(dirname "$DIR")))"
cd $DIR
# if diff of dump between base and current exist, then
# check if this diff is changed and, if so, replace it
bunzip2 -f -k *.dump.bz2
bunzip2 -f -k *.dump.diff.bz2
mkdir -p /tmp/$DBVER
for i in `ls *.dump`; do
 diff $i current/$i > /tmp/$DBVER/$i.diff
 #echo $? diff $i ../$i
 if [ "$?" != "0" ]; then
    cmp /tmp/$DBVER/$i.diff ./$i.diff
    #echo $? /tmp/$i.diff ./$i.diff
    if [ "$?" != "0" ]; then
      echo $i diff! [overwrite $i.diff]
      cp /tmp/$DBVER/$i.diff ./
      bzip2 -c $i.diff > $i.diff.bz2
    fi
 fi
done

# clean up
rm *.dump; rm *.diff
sudo chown www-data:www-data *
sudo chmod g+w *
cd ../../../../../ && ./4collect_static.sh
