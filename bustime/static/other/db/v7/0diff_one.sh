#!/bin/bash

DBVER=v7
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DIR_STATIC="$(dirname $(dirname $(dirname "$DIR")))"

# check that diff is greater than base on 20%
function is_greater_than_20 {
  is_greater=0
  if [ $# -eq 2 ]; then
    size1=`stat --format=%s $1`
    # echo $size1
    size2=`stat --format=%s $2`
    # echo $size2
    if [ $size2 -gt $(($size1 / 100 * 20)) ]; then
      is_greater=1;
    fi
  fi
}

echo "$DIR/${0##*/} start:"
cd $DIR/current
for i in `ls $1.dump`; do
  if [ ! -e $DIR/$i.bz2 ]; then
    # echo $DIR/$i
    # cp $i $DIR/$i
    bzip2 -c $i > $DIR/$i.bz2
  fi
done

cd $DIR


# if diff of dump between base and current exist, then
# check if this diff is changed and, if so, replace it
bunzip2 -f -k $1.dump.bz2
bunzip2 -f -k $1.dump.diff.bz2 2> /dev/null
mkdir -p /tmp/$DBVER

for i in `ls $1.dump`; do
# diff $i current/$i > /tmp/$DBVER/$i.diff
 tmp_diff=$(/bin/tempfile)
 diff $i current/$i > $tmp_diff
 size=`stat --format=%s $tmp_diff`

 is_greater_than_20 $i $tmp_diff

 if [ $is_greater -eq 1 ]; then
    echo "Пересоздан дамп $i"
    rm $i
    cp current/$i ./
    bzip2 -c current/$i > $i.bz2
    rm $i.diff.bz2
 elif [ ! $size -eq 0 ]; then
    cmp $tmp_diff ./$i.diff 2> /dev/null
    if [ "$?" != "0" ]; then
      echo $i diff! [overwrite $i.diff]
      bzip2 -c $tmp_diff > $i.diff.bz2
      echo "Найдены и применены изменения"
    else
      echo "Изменений не найдено"
    fi
 else
  echo "Изменений не найдено"
  rm $tmp_diff
 fi
done

# clean up
rm $1.dump; rm $1.diff
if  [ "$USER" == "norn" ]; then
  sudo chown www-data:www-data *
fi

echo "$DIR/${0##*/} end"
