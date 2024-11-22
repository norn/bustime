for i in `ls *.dump`; do
 if [ ! -e $i.bz2 ];then
     echo $i
     bzip2 -c $i > $i.bz2
 fi
done
sudo chown www-data:www-data *
sudo chmod g+w *
echo "Run collect static!"
cd ../../../../../ && ./4collect_static.sh
