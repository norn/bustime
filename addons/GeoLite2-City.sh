cd /r/bustime/bustime/addons
wget -4 https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz -O GeoLite2-City.tar.gz
tar xfz GeoLite2-City.tar.gz
cp `tar -z --list -f GeoLite2-City.tar.gz|grep mmdb` ./GeoLite2-City.mmdb