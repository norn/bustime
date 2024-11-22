chown -R www-data:www-data *
chmod g+rw -R *
chown -R www-data:www-data zbusd/supervisor/*
chmod g+rw -R zbusd/supervisor/*
chown www-data:www-data /var/run/uwsgi/app/bustime/reload
chown -R www-data:www-data /var/log/uwsgi/app
chmod g+w /var/run/uwsgi/app/bustime/reload
chown -R www-data:www-data /mnt/reliable/repos/bustime/bustime/.venv
chmod -R g+w /mnt/reliable/repos/bustime/bustime/.venv
