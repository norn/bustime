#!/bin/bash

DBVER=v7
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DIR_STATIC="$(dirname $(dirname $(dirname "$DIR")))"

function is_greater_than_20 {
  is_greater=0
  if [ $# -eq 2 ]; then
    size1=$(stat --format=%s $1)
    size2=$(stat --format=%s $2)
    if [ $size2 -gt $(($size1 / 100 * 20)) ]; then
      is_greater=1
    fi
  fi
}

now=$(date +"%T")

cd $DIR/current
for i in $(ls *.dump); do
  if [ ! -e $DIR/$i.bz2 ]; then
    bzip2 -c $i >$DIR/$i.bz2
  fi
done

cd $DIR
# if diff of dump between base and current exist, then
# check if this diff is changed and, if so, replace it
bunzip2 -f -k *.dump.bz2
bunzip2 -f -k *.dump.diff.bz2
mkdir -p /tmp/$DBVER
for i in $(ls *.dump); do
  tmp_diff=$(/bin/tempfile)
  diff $i current/$i >$tmp_diff
  size=$(stat --format=%s $tmp_diff)
  # check that diff is greater than base on 20%
  is_greater_than_20 $i $tmp_diff
  if [ $is_greater -eq 1 ]; then
    echo "replacing old dump $i"
    rm $i
    bzip2 -c current/$i >$i.bz2
    rm $i.diff.bz2
  elif [ ! $size -eq 0 ]; then # [ $? != "0" ] и [ ! $? -eq 0 ] не работают
    cmp $tmp_diff ./$i.diff 2> /dev/null
    if [ "$?" != "0" ]; then
      echo $i diff! [overwrite $i.diff]
      bzip2 -c $tmp_diff > $i.diff.bz2
    fi
  fi
  rm $tmp_diff
done

# clean up
rm *.dump
rm *.diff
#rm $DIR/0diff.lock # Unlock

# sudo chown www-data:www-data * --> #### already run from www-data in crontab
cd ../../../../../ && ./4collect_static.sh
