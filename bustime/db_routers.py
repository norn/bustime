class BStoreRouter:

    route_apps = ['bustime']    #, 'taxi'
    route_model_labels = {'citystatus', 'vehiclestatus', 'uevent', 'jam', 'passengerstat'}  #, 'tevent'
    route_model_gtfs = {'gtfscatalog', 'gtfsagency', 'gtfsroutes', 'gtfsshapes', 'gtfstrips', 'gtfscalendar', 'gtfscalendardates', 'gtfsstops', 'gtfsstoptimes'}
    #route_model_gtfs = {}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_apps:
            if model._meta.model_name in self.route_model_labels:
                return 'bstore'
            elif model._meta.model_name in self.route_model_gtfs:
                return 'gtfs'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_apps:
            if model._meta.model_name in self.route_model_labels:
                return 'bstore'
            elif model._meta.model_name in self.route_model_gtfs:
                return 'gtfs'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label in self.route_apps or obj2._meta.app_label in self.route_apps:
            if obj1._meta.model_name in self.route_model_labels or obj2._meta.model_name in self.route_model_labels:
                return True
            elif obj1._meta.model_name in self.route_model_gtfs or obj2._meta.model_name in self.route_model_gtfs:
                return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_apps:
            if model_name in self.route_model_labels:
                return 'bstore'
            elif model_name in self.route_model_gtfs:
                return 'gtfs'
        return None


class ReplicaRouter:
    def db_for_read(self, model, **hints):
        return "replica"

    def db_for_write(self, model, **hits):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'default':
            return True
        return None
