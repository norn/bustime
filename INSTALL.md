# Installing the bustime app from scratch
# required python >= 3.10.12 and < 3.12

## Install python 3.10
```
sudo apt update && sudo apt upgrade -y
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.10-full python3.10-dev -y
```

## install libs:
```
sudo apt-get install python3-pip python3-dev build-essential libssl-dev libcurl4-openssl-dev zip git curl wget -y
```

## Install the GEOS library
```
sudo apt-get install geos-bin libgeos-dev binutils -y
```

## Installing Geospatial libraries
```
sudo apt-get install binutils libproj-dev gdal-bin -y
```

## Install services
```
sudo apt-get install cron supervisor nginx redis-server -y
```

## Install Node.js v12.22.9
### Install Node Version Manager
```
cd ~
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
source ~/.bashrc
```

### Install Node.js
```
nvm install v12.22.9
sudo ln -s /home/$(whoami)/.nvm/versions/node/v12.22.9/bin/node /usr/bin/node
sudo chgrp -R www-data /home/$(whoami)/.nvm/versions/node/v12.22.9
sudo chmod -R g+x /home/$(whoami)/.nvm/versions/node/v12.22.9
```

## Install Postgresql (v.16 in example)
```
sudo apt install postgresql -y
```

## Install Postgis
```
sudo apt install postgis postgresql-16-postgis-3 libpq-dev -y
```

## Generate password for DB user
```
openssl rand -base64 10
---this is a example password for user:
r7Z2T4PHXIQvew==
```

## Create database user
```
# for this interactive command need prepared user password
sudo -u postgres createuser -d -r -P bustime
```

# Create database & extensions
```
sudo -u postgres createdb -O bustime bustime
sudo -u postgres psql -d bustime -c "CREATE EXTENSION postgis;"
```

# Clone project:
```
sudo mkdir /bustime
cd /bustime
git clone https://github.com/norn/bustime.git
cd /bustime
```

## Create virtual Environment:
```
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Prepare node
```
npm config set python /usr/bin/python3.10
npm install zerorpc
npm install http
npm install https
npm install fs
npm install socket.io
npm install redis
npm install socket.io-redis
npm install -g grunt-cli
```

## Prepare GEOIP db
```
wget -P addons https://download.db-ip.com/free/dbip-city-lite-2024-09.mmdb.gz
gzip -dr addons/dbip-city-lite-2024-09.mmdb.gz
mv addons/dbip-city-lite-2024-09.mmdb addons/GeoLite2-City.mmdb
```

## Replace django database settings for actual user in file bustime/settings_local.py
example:
```
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'bustime',              # database name
        'USER': 'bustime',              # user name
        'PASSWORD': 'r7Z2T4PHXIQvew==', # generated password
        'HOST': '127.0.0.1',
        'PORT': '',
    },
```

## Migrations
```
python manage.py makemigrations
python manage.py migrate
```

## Create first user (interactive)
```
python manage.py createsuperuser
```

## Load initial data to DB
```
sudo -u postgres psql -d bustime -f addons/init.sql
```

## Prepare directories & files
```
ln -s /bustime/bustime/.venv/bin /bustime/bin
cp addons/activate_this.py .venv/bin/
sudo mkdir -p static/logs
sudo mkdir -p bustime/static/other/db/v5/current
sudo mkdir -p bustime/static/other/db/v7/current
sudo mkdir -p bustime/static/other/db/v8/current
sudo chown -R www-data:www-data /bustime
sudo chmod -R g+w /bustime
sudo mkdir -p /var/log/bustime
sudo chown -R www-data:www-data /var/log/bustime
sudo chmod -R g+w /var/log/bustime
sudo mkdir -p /var/log/uwsgi/app
sudo chown -R www-data:www-data /var/log/uwsgi/app
sudo chmod -R g+w /var/log/uwsgi/app
sudo -u www-data touch /var/log/uwsgi/app/bustime.log
```

## Prepare supervisor
```
sudo ln -s /bustime/bustime/addons/supervisor/bustime_uwsgi.conf /etc/supervisor/conf.d/bustime_uwsgi.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_rpc_server.conf /etc/supervisor/conf.d/bustime_rpc_server.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_socketoto.conf /etc/supervisor/conf.d/bustime_socketoto.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_statusd.conf /etc/supervisor/conf.d/bustime_statusd.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_statusv.conf /etc/supervisor/conf.d/bustime_statusv.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_turbo_sync.conf /etc/supervisor/conf.d/bustime_turbo_sync.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_turbos.conf /etc/supervisor/conf.d/bustime_turbos.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_uevent_saver.conf /etc/supervisor/conf.d/bustime_uevent_saver.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_update_event_count.conf /etc/supervisor/conf.d/bustime_update_event_count.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_eps.conf /etc/supervisor/conf.d/bustime_eps.conf
sudo ln -s /bustime/bustime/addons/supervisor/bustime_rainbeam.conf /etc/supervisor/conf.d/bustime_rainbeam.conf
sudo supervisorctl reread
sudo supervisorctl update
# wait 5 sec.
sudo supervisorctl status
```

## Prepare correct domain names
### 1 in project files: replace 'bustime.loc' to your domain name
```
find . -not -path '*/\.venv/*' -not -path '*/\.git/*' \( -name '*.py' -o -name '*.html' -o -name '*.js' \) -exec sed -i 's|bustime.loc|your.domain.name|g' '{}' \;
```
### 2 in project files: replace 'tiles.server.free' to your tiles server
```
find . -not -path '*/\.venv/*' -not -path '*/\.git/*' \( -name '*.py' -o -name '*.html' -o -name '*.js' \) -exec sed -i 's|tiles.server.free|tiles.server.your|g' '{}' \;
```
### 3 in nginx file /bustime/bustime/addons/nginx/bustime.loc
If necessary, replace everything that includes "bustime.loc" with your domain.
Replace the value of the variable 'server_name' with the value of your domain.

## Prepare Nginx
```
sudo ln -s /bustime/bustime/addons/nginx/bustime.loc /etc/nginx/sites-enabled/bustime.loc
sudo nginx -t
sudo nginx -s reload
```

# Run application
Run:
```
./6-release-js.sh
```
Replace value of "js_ver" with value of output "New release" in file bustime/templates/base.html

Run:
```
./4collect_static.sh
./1restart
```

## At the moment, the application is fully ready to work, and the site can be seen by http://site_ip

## Load first data for work - GTFS data of Lietuva, Vilnius
```
python utils/gtfs_loader.py 1 --debug
python utils/gtfs_importer.py 1 --upd --reset --debug
```

## Restart this routines after change routes
```
sudo supervisorctl restart bustime_turbos:*
sudo supervisorctl restart bustime_turbo_sync
```

## Start realtime updater for GTFS data
```
sudo ln -s /bustime/bustime/addons/supervisor/bustime_gtfs_updaters.conf /etc/supervisor/conf.d/bustime_gtfs_updaters.conf
sudo supervisorctl reread
sudo supervisorctl update
```

## At this stage, the application should work and display data in real time using http://site_ip

## The last step - configure cron
```
sudo sh -c "echo '30 2 * * *     www-data   /bustime/bustime/utils/piprunner.sh clean.py >> /tmp/clean.cron.log 2>&1' >> /etc/crontab"
sudo sh -c "echo '59 16 * * *    www-data   /bustime/bustime/utils/piprunner.sh metric_save.py >> /tmp/metric_save.log 2>&1' >> /etc/crontab"
sudo sh -c "echo '15 2 * * *     www-data   /bustime/bustime/utils/piprunner.sh places_fresh_counters.py >> /tmp/places_fresh_counters.cron.log 2>&1' >> /etc/crontab"
sudo sh -c "echo '31 */1 * * *   www-data   /bustime/bustime/utils/piprunner.sh mobile_update_at_target_hour.py 3 >> /tmp/mobile_update_at_target_hour.log 2>&1' >> /etc/crontab"
sudo sh -c "echo '#0 */3 * * *    www-data   /bustime/bustime/utils/piprunner.sh sms_email.py >> /tmp/sms_email.py.log 2>&1' >> /etc/crontab"
sudo sh -c "echo '58 * * * *     www-data   /bustime/bustime/coroutines/gtfs_alerts.py > /tmp/gtfs_alerts.log 2>&1' >> /etc/crontab"
sudo service cron reload
```

## Ready.


# For add places to application:
1. Add links to gtfs data to: http://site_ip/wiki/bustime/gtfscatalog/
2. Load data: ```python utils/gtfs_loader.py <ID_NEW_RECORD> --debug```
3. Import routes: ```python utils/gtfs_importer.py <ID_NEW_RECORD> --upd --reset --debug```
4. Add updater to /bustime/bustime/addons/supervisor/bustime_gtfs_updaters.conf
5. Restart this routines after change routes
```
sudo supervisorctl restart bustime_turbos:*
sudo supervisorctl restart bustime_turbo_sync
```
