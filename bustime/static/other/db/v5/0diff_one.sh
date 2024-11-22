#!/bin/bash

DBVER=v5
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DIR_STATIC="$(dirname $(dirname $(dirname "$DIR")))"
echo "$DIR/${0##*/} $1 start:"
cd $DIR
# if diff of dump between base and current exist, then
# check if this diff is changed and, if so, replace it
bunzip2 -f -k $1.dump.bz2
bunzip2 -f -k $1.dump.diff.bz2 2> /dev/null
mkdir -p /tmp/$DBVER

for i in $1.dump; do
    # Если файлы идентичны, никакие результаты не выдаются, получим /tmp/$DBVER/$1.dump.diff размером 0
    diff $i current/$i > /tmp/$DBVER/$i.diff
    if [ "$?" != "0" ]; then
        cmp ./$i.diff /tmp/$DBVER/$i.diff
        if [ "$?" != "0" ]; then
            cp /tmp/$DBVER/$i.diff ./
            bzip2 -c $i.diff > $i.diff.bz2
            cp current/$i ./
            bzip2 -c $i > $i.bz2
            echo "Найдены и применены изменения"
        else
            echo "Изменений не найдено"
            # обновим дату файлов
            touch $1.dump.bz2
            touch $1.dump.diff.bz2
        fi
    else
        echo "Изменений не найдено"
        # обновим дату файлов
        touch $1.dump.bz2
        touch $1.dump.diff.bz2
    fi
done

# clean up
rm $1.dump;
rm $1.dump.diff

user=$(whoami)
if [ "$user" != "www-data" ]; then
  sudo chown www-data:www-data *
  sudo chmod g+w *
fi

echo "$DIR/${0##*/} end"
