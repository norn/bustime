# -*- coding: utf-8 -*-

from __future__ import absolute_import
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import BaseInlineFormSet
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from leaflet.admin import LeafletGeoAdmin
from .models import *
from contextlib import contextmanager
from reversion.admin import VersionAdmin
from reversion_compare.admin import CompareVersionAdmin
from reversion_compare.mixins import CompareMixin
from reversion_compare.compare import DOES_NOT_EXIST
from reversion.models import Version
from django.db import transaction, router
from django.urls import include, re_path, resolve
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
import bustime.views
import inspect
import os.path
from .caching_paginator import CachingPaginator


class BustimeCompareVersionAdmin(CompareVersionAdmin):
    def has_add_permission(self, request, obj=None):
        # us = get_user_settings_mini(request)
        us = bustime.views.get_user_settings(request)
        staff_modify_check = obj.place.id in PLACE_STAFF_MODIFY.keys() if obj and hasattr(obj, "place") else False
        modify_allowed = True
        if staff_modify_check:
            # TODO it's a stub, because some objects doesn't have a Place, so we can't check editors, so just check that User is an editor in any Place
            modify_allowed = request.user.id in [user.id for user in obj.place.editors.all()] if hasattr(obj, "place") else request.user.place_set.exists()
        return (not us.is_banned() and (super().has_add_permission(request) or modify_allowed)) if us else False

    def has_change_permission(self, request, obj=None):
        # us = get_user_settings_mini(request)
        us = bustime.views.get_user_settings(request)
        staff_modify_check = obj.place.id in PLACE_STAFF_MODIFY.keys() if obj and hasattr(obj, "place") else False
        modify_allowed = True
        if staff_modify_check:
            # TODO it's a stub, because some objects doesn't have a Place, so we can't check editors, so just check that User is an editor in any Place
            modify_allowed = request.user.id in [user.id for user in obj.place.editors.all()] if hasattr(obj, "place") else request.user.place_set.exists()
        return (not us.is_banned() and (super().has_change_permission(request) or modify_allowed)) if us else False

    def has_delete_permission(self, request, obj=None):
        # us = get_user_settings_mini(request)
        us = bustime.views.get_user_settings(request)
        staff_modify_check = obj.place.id in PLACE_STAFF_MODIFY.keys() if obj and hasattr(obj, "place") else False
        modify_allowed = True
        if staff_modify_check:
            # TODO it's a stub, because some objects doesn't have a Place, so we can't check editors, so just check that User is an editor in any Place
            modify_allowed = request.user.id in [user.id for user in obj.place.editors.all()] if hasattr(obj, "place") else request.user.place_set.exists()
        return (not us.is_banned() and (super().has_delete_permission(request) or modify_allowed)) if us else False


class VersionListFilter(admin.SimpleListFilter):
    title = 'content type'

    content_types = set()
    parameter_name = 'content_type_id'

    def __init__(self, request, params, model, model_admin):
        # city_news_ct = ContentType.objects.get(id=112)
        # self.content_types = [(city_news_ct.id, city_news_ct)]
        self.content_type = []
        for key, value in admin.site._registry.items():
            if inspect.isclass(type(value)) and issubclass(type(value), CompareVersionAdmin):
                content_type = ContentType.objects.get_for_model(key)
                self.content_types.add((content_type.id, content_type))
        super().__init__(request, params, model, model_admin)

    def lookups(self, request, model_admin):
        return tuple(self.content_types)

    def queryset(self, request, queryset):
        if self.value() is None:
            ids = [x[0] for x in self.content_types]
            queryset = queryset.filter(content_type_id__in=ids)
        else:
            queryset = queryset.filter(content_type_id=self.value())
        return queryset


class CityListFilter(admin.SimpleListFilter):
    title = 'city'
    parameter_name = 'city_id'

    def lookups(self, request, model_admin):
        return tuple(City.objects.filter(active=True).values_list('id', 'name'))

    def queryset(self, request, queryset):
        # from django.http import Http404
        # from django.db.models import CharField
        # from django.db.models.functions import Cast
        # if self.value():
        #     content_type_id = int(request.GET.get('content_type_id', -1))
        #     if content_type_id > -1:
        #         if content_type_id == 111:
        #             qs = Vehicle.objects.filter(city_id=self.value(), uniqueid=models.OuterRef('object_id'))
        #         elif content_type_id == 91:
        #             qs = Chat.objects.annotate(uniqueid=Cast('id', CharField())).filter(Q(ms__city_id=self.value()) or Q(us__city_id=self.value()), uniqueid=models.OuterRef('object_id'))
        #         elif content_type_id == 110:
        #             qs = BusProvider.objects.annotate(uniqueid=Cast('id', CharField())).filter(city_id=self.value(), uniqueid=models.OuterRef('object_id'))
        #         elif content_type_id == 69:
        #             qs = Vote.objects.annotate(uniqueid=Cast('id', CharField())).filter(Q(ms__city_id=self.value()) or Q(us__city_id=self.value()), uniqueid=models.OuterRef('object_id'))
        #         else:
        #             raise Http404("ContentType does not exist")
        #         return queryset.annotate(
        #             joined_qs=models.Exists(qs)).filter(
        #                 (Q(joined_qs=True) & Q(content_type_id=content_type_id)))
        #     else:
        #         veh_qs = Vehicle.objects.filter(city_id=self.value(), uniqueid=models.OuterRef('object_id'))
        #         chat_qs = Chat.objects.annotate(uniqueid=Cast('id', CharField())).filter(Q(ms__city_id=self.value()) or Q(us__city_id=self.value()), uniqueid=models.OuterRef('object_id'))
        #         provider_qs = BusProvider.objects.annotate(uniqueid=Cast('id', CharField())).filter(city_id=self.value(), uniqueid=models.OuterRef('object_id'))
        #         vote_qs = Vote.objects.annotate(uniqueid=Cast('id', CharField())).filter(Q(ms__city_id=self.value()) or Q(us__city_id=self.value()), uniqueid=models.OuterRef('object_id'))
        #         return queryset.annotate(
        #             joined_veh=models.Exists(veh_qs), 
        #             joined_chat=models.Exists(chat_qs), 
        #             joined_provider=models.Exists(provider_qs), 
        #             joined_vote=models.Exists(vote_qs)).filter(
        #                 (Q(joined_veh=True) & Q(content_type_id=111)) |
        #                 (Q(joined_chat=True) & Q(content_type_id=91)) |               
        #                 (Q(joined_provider=True) & Q(content_type_id=110)) |
        #                 (Q(joined_vote=True) & Q(content_type_id=69)))
        # return queryset
        from django.db.models.expressions import RawSQL
        if self.value():
            '''SELECT reversion_version.*, bustime_versioncity.city_id
                FROM reversion_version 
                JOIN bustime_versioncity
                ON reversion_version.revision_id = bustime_versioncity.revision_id
                WHERE bustime_versioncity.city_id = %s;'''
            queryset = queryset.annotate(city_id=RawSQL(
                '''SELECT bustime_versioncity.city_id
                    FROM bustime_versioncity
                    WHERE reversion_version.revision_id = bustime_versioncity.revision_id''', [])
                    ).filter(city_id=self.value())
        return queryset


class PlaceCountryListFilter(admin.SimpleListFilter):
    title = 'country'
    parameter_name = "country_id"

    def lookups(self, request, model_admin):
        qs = Place.objects.filter(id__in=places_filtered())
        return tuple(Country.objects.filter(code__in=qs.values_list('country_code')).exclude(id=15).distinct().values_list('code', 'name'))
        # return super().lookups(request, model_admin)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country_code=self.value())
        return queryset


class UsefulPlaceListFilter(admin.SimpleListFilter):
    title = "place"
    parameter_name = "place_id"

    def lookups(self, request, model_admin):
        qs = Place.objects.filter(id__in=places_filtered())
        return tuple(Place.objects.filter(id__in=qs).values_list('id', 'name'))


class BusProviderPlaceListFilter(UsefulPlaceListFilter):
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(bus__places=self.value()).distinct()
        return queryset


class VehiclePlaceListFilter(UsefulPlaceListFilter):
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(datasource__places=self.value()).distinct()
        return queryset


class UserGroupListFilter(admin.SimpleListFilter):
    title = "group"
    parameter_name = "group_type"

    def lookups(self, request, model_admin):
        return (
            ("is_editor", _("Editor")),
            ("is_user", _("User"))
        )

    def queryset(self, request, queryset):
        if self.value() == "is_editor":
            group = Group.objects.filter(name="editor")
            queryset = queryset.filter(revision__user__groups__in=group)
        elif self.value() == "is_user":
            group = Group.objects.filter(name="editor")
            queryset = queryset.filter(~Q(revision__user__groups__in=group))
        return queryset


class UserListFilter(admin.SimpleListFilter):
    title = "user"
    parameter_name = "user_id"

    def lookups(self, request, model_admin):
        users = model_admin.get_for_user(request)
        return (
            (user.pk, user.username) for user in users
        )

    def queryset(self, request, queryset):
        if self.value():
            print(queryset)
            return queryset.filter(revision__user__id=self.value())
        return []


@admin.register(URLMover)
class URLMover(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'url_old', 'url_new')
    list_filter = ('ctime', )
    search_fields = ['url_old', "url_new"]


class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'ttype', 'message_short', 'place')
    list_filter = ('ttype', 'place')
    raw_id_fields = ("user", 'ms', 'place')
    date_hierarchy = 'date'

    paginator = CachingPaginator

    def get_queryset(self, request):
        qs = super(LogAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(place__datasource__in=request.user.ddisps.all())
            # return qs.filter(city__in=request.user.rdisps.all(), ttype = 'get_bus_by_name')
        return qs.filter(place=us.place, ttype = 'get_bus_by_name')


    def get_list_filter(self, request):
        if not request.user.is_superuser:
            self.list_filter = ('')
        return self.list_filter


class GlonassdAdmin(admin.ModelAdmin):
    list_display = ('city', 'port', 'protocol')
    list_filter = ('protocol', 'city')
    ordering = ('city', )
    # предварительная инициализация полей
    def get_changeform_initial_data(self, request):
        from bustime.glonassd import get_awail_glonassd_port
        return {
            'port': get_awail_glonassd_port()   # свободный порт
        }
# class GlonassdAdmin
admin.site.register(Glonassd, GlonassdAdmin)

# https://django-extra-views.readthedocs.io/en/latest/pages/formset-customization.html
# https://yandex.ru/turbo/pythonist.ru/s/kastomizacziya-admin-paneli-django/
# https://qna.habr.com/q/753523
# https://gist.github.com/shymonk/5d4467bbc7d08dd7f6f4
# https://djangodoc.ru/3.1/ref/contrib/admin/
class ReceiverInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(ReceiverInlineFormSet, self).__init__(*args, **kwargs)
        # определяем имя и расположение обработчика города
        city = kwargs['instance']
        if city.crawler:
            path = settings.PROJECT_ROOT + '/coroutines'
        else:
            path = settings.PROJECT_ROOT + '/bustime/update'
        # сохраняем значение для инициализации поля handler
        self.handler = "%s/c%s.py" % (path, city.id)
        self.handler_exists = os.path.isfile(self.handler)
        # выбираем список портов glonassd для инициализации поля params
        plist = list(Glonassd.objects.filter(city=city).values_list('port', flat=True))
        self.ports = ", ".join([str(p) for p in plist])
    # __init__

    # это работает только при создании новой записи
    @property
    def empty_form(self):
        form = super(ReceiverInlineFormSet, self).empty_form
        # инициализируем поля
        form.fields['source'].help_text = self.ports
        form.fields['handler'].initial = self.handler
        form.fields['params'].initial = self.ports
        form.fields['params'].help_text = "Список портов через запятую"
        return form
    # empty_form
# ReceiverInlineFormSet


# admin.TabularInline
class ReceiverInline(admin.StackedInline):
    model = Receiver
    verbose_name_plural = "Обработчики"
    fields = ('source', 'handler', 'params',)
    extra = 0   # remove empty rows
    max_num = 1
    # remove "Add another..." link
    # https://stackoverflow.com/questions/1721037/remove-add-another-in-django-admin-screen
    formset = ReceiverInlineFormSet
    template = "admin/bustime/receiver_inline.html"


class PlaceInline(admin.StackedInline):
    model = Place.bus_set.through
    readonly_fields = ('place',)
    can_delete = False
    extra = 0
    
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        return self.readonly_fields


class CityAdmin(VersionAdmin, LeafletGeoAdmin):
    list_display = ('name', 'id', 'slug', 'timediffk', 'wunderground', 'crawler', 'available', 'check_url_', 'bus', 'trolleybus', 'tramway', 'bus_taxi')
    list_filter = ('bus_taxi_merged', 'source', 'crawler', 'country', 'block_info')
    search_fields = ['name', "id"]
    raw_id_fields = ("editors", "dispatchers")

    # exclude = ['point']
    def check_url_(self, obj):
        if obj.check_url:
            return '<a href="%s" target="_blank">check</a>' % (obj.check_url)
        else:
            return ''
    check_url_.allow_tags = True
    inlines = [ReceiverInline]


class PlaceAdmin(VersionAdmin, LeafletGeoAdmin):
    list_display = ('name', 'id', 'osm_id', 'slug', 'timezone')
    list_filter = (PlaceCountryListFilter, )
    search_fields = ['name', "id", "osm_id"]
    raw_id_fields = ("editors", "dispatchers")
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows':1})},
    }
    readonly_fields = ("osm_id", "osm_area_id", "osm_area_type", "stops_count", "buses_count", "dump_version", "patch_version", "country_code", "rev")
    # inlines = [ReceiverInline]


class BusAdmin(BustimeCompareVersionAdmin):
    list_display = ('id', 'name', 'all_places', 'ttype', 'napr_a', 'provider', 'active', 'ctime')
    search_fields = ['name', ]
    list_filter = ('ttype',)
    readonly_fields = ('napr_a', 'napr_b', 'distance', 'distance0', 'distance1',
                       'travel_time', 'inter_stops', 'order', 'mtime', 'slug',
                       'tt_start', 'tt_start_holiday', 'routes')
    ordering = ('order', 'name')
    exclude = ("only_season", "only_holiday", "only_working", "only_rush_hour", "only_special", "osm", "city")
    raw_id_fields = ("places", )
    # exclude = ("city", )
    #inlines = [PlaceInline]

    paginator = CachingPaginator

    @staticmethod
    def	all_places(row):
        return ','.join([x.name for x in row.places.all()])

    def get_queryset(self, request):
        qs = super(BusAdmin, self).get_queryset(request)
        # qs = super(BusAdmin, self).get_queryset(request)
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        revision_url_alias = "%s_%s_revision" % info
        match = resolve(request.path)
        if match and match.url_name == revision_url_alias:
            qs = qs.using(router.db_for_write(self.model))
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(places__datasource__in=request.user.ddisps.all())
        return qs.filter(places__id=us.place_id)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        us = get_user_settings_mini(request)
        bus_id = next(iter(request.resolver_match.args), None)
        try:
            if 'object_id' in request.resolver_match.kwargs:
                bus_id = request.resolver_match.kwargs['object_id']
            else:
                # quick fix
                if '/recover/' in request.path:
                    bus_id = int(request.path.split("/")[5])
                else:
                    bus_id = int(request.path.split("/")[4])
            bus = Bus.objects.get(id=bus_id)
        except:
            bus = None

        return super(BusAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser:
            if not self.exclude:
                self.exclude = ()
            self.exclude += ("xeno_id", "tt_xeno_reversed")
            #self.exclude += ("xeno_id", "tt_xeno_reversed")
            # self.readonly_fields += ('name',)
            self.readonly_fields = ('places', 'napr_a', 'napr_b', 'distance', 'distance0', 'distance1',
                       'travel_time', 'inter_stops', 'order', 'mtime', 'slug',
                       'tt_start', 'tt_start_holiday')
        form = super(BusAdmin, self).get_form(request, obj, **kwargs)
        us = get_user_settings_mini(request)
        if not us.is_banned():
            description_field = form.base_fields.get("description")
            if description_field:
                description_field.widget = forms.Textarea(attrs={"style":"width:47em;height:4em;", "maxlength":"256"})
        return form

    def get_list_filter(self, request):
        if request.user.is_superuser:
            self.list_filter = ('ttype', 'places')
            self.ordering = ('-id', )
        return self.list_filter

    @contextmanager
    def create_revision(self, request):
        from reversion.revisions import set_comment, create_revision, set_user, add_meta
        city_id = request.POST.get('city', None)
        with create_revision():
            set_user(request.user)
            if city_id:
                add_meta(VersionCity, place_id=city_id)
            yield


class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'bus', 'busstop', 'direction', 'order', 'endpoint')
    search_fields = ['bus__name']
    list_filter = ('direction', 'bus__ttype', 'bus__places', 'bus')
    raw_id_fields = ("bus", 'busstop')

    def get_queryset(self, request):
        qs = super(RouteAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(bus__places__in=request.user.place_set.all())


class NBusStopAdmin(VersionAdmin, LeafletGeoAdmin):
    class NBusStopInlineFeature(admin.StackedInline):
        class NBusStopInlineFormset(BaseInlineFormSet):
            def add_fields(self, form, index):
                form.fields['feature'].queryset = Feature.objects.filter(ttype=Feature.FeatureType.NBUS_STOP)
                super().add_fields(form, index)

        model = NBusStopFeature
        verbose_name_plural = "features"
        extra = 1
        formset = NBusStopInlineFormset

    list_display = ('id', 'xeno_id', 'name', 'moveto', 'city')
    search_fields = ['name', 'xeno_id']
    list_filter = ('city',)
    exclude = ('unistop',)

    inlines = [NBusStopInlineFeature]
    paginator = CachingPaginator


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'end_time', 'user', 'value', 'fiat', 'phone', 'notified', 'key', 'pin', 'comment')
    search_fields = ['comment', 'pin', 'ms__id', 'vip_name']
    list_filter = ('ctime','end_time')
    raw_id_fields = ("user", "ms", "bonus")
    date_hierarchy = 'ctime'


class BonusAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'mtime', 'pin', 'comment', 'agent_comment', 'days', 'activated')
    list_filter = ('agent', 'days', 'key')


class SpecialIconAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'gosnum', 'img', 'img_tag', 'active')
    search_fields = ['gosnum', ]
    list_filter = ('place', )
    raw_id_fields = ("us", )
    exclude = ('city',)

    paginator = CachingPaginator

    def get_queryset(self, request):
        qs = super(SpecialIconAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(place__datasource__in=request.user.ddisps.all())
        return qs.filter(place=us.place)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "place":
            pids = places_filtered()
            kwargs["queryset"] = Place.objects.filter(id__in=pids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_filter(self, request):
        if not request.user.is_superuser:
            self.list_filter = ('')
        return self.list_filter

    def img_tag(self, obj):
        if obj.img:
            return mark_safe(f'<img src="{obj.img}" width="50" height="50" />')
        return "-"
    img_tag.short_description = 'Image'


class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'url', 'name_short', 'active')
    list_filter = ('active',)


class MboxAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'hostname', 'public_key')


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'us', 'ms', 'amount', 'key', 'value', 'paid')
    list_filter = ('key', 'paid')
    raw_id_fields = ("us", 'ms')
    date_hierarchy = 'ctime'


class GosnumAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'us', 'ms', 'uniqueid', 'gosnum', 'countable')
    list_filter = ('countable', 'city', 'ramp')
    search_fields = ['uniqueid', 'gosnum']
    raw_id_fields = ("us", 'ms')
    date_hierarchy = 'date'

    def get_queryset(self, request):
        qs = super(GosnumAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(city__in=request.user.rdisps.all())


class AdGeoAdmin(LeafletGeoAdmin):
    list_display = ('id', 'city', 'name', 'link', 'radius', 'counter', 'active')
    list_filter = ('city', 'active')
    search_fields = ['name', 'id']


class FinanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'agent', 'fiat')
    list_filter = ('agent', )


class RouteLineAdmin(VersionAdmin, LeafletGeoAdmin):
    change_form_template = 'admin/bustime/change_route_line_form.html'
    map_template = 'admin/leaflet/widget.html'
    list_display = ('id', 'ctime', 'mtime', 'bus', 'direction', 'autofill')
    list_filter = ('autofill', 'direction') #'bus__places'
    search_fields = ['bus__name', ]
    raw_id_fields = ("bus", )
    readonly_fields = ('bus_napr', 'mtime')
    fieldsets = ((None, {
        'fields': ('mtime', 'bus', 'direction',
        'bus_napr', 'line', 'autofill'),
        }),)
    map_width = '100%'
    map_height = '800px'


    def get_queryset(self, request):
        qs = super(RouteLineAdmin, self).get_queryset(request)
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        revision_url_alias = "%s_%s_revision" % info
        match = resolve(request.path)
        if match and match.url_name == revision_url_alias:
            qs = qs.using(router.db_for_write(self.model))
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(bus__places__datasource__in=request.user.ddisps.all())
        return qs.filter(bus__places=us.place)


    @contextmanager
    def create_revision(self, request):
        from reversion.revisions import set_comment, create_revision, set_user, add_meta
        # TODO (turbo) Restore add_meta(VersionCity)
        # city_id = request.POST.get('city', None)
        with create_revision():
            set_user(request.user)
            # if city_id:
                # add_meta(VersionCity, city=CITY_MAP[int(city_id)])
            yield


class BusStopIconImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'fname', 'name', 'order')


class MetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'name', 'count')
    list_filter = ('name', )
    date_hierarchy = 'date'


class MetricTimeAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'name', 'count')
    list_filter = ('name', )
    date_hierarchy = 'date'


class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'bus_id', 'name', 'ms', 'message', 'deleted', 'deleted_by', 'warnings_count')
    list_filter = ('bus__places',)
    date_hierarchy = 'ctime'
    search_fields = ['name', 'message', 'us__user__username', 'ms__user__username']
    raw_id_fields = ('us', 'ms', 'bus', 'deleted_by')

    def get_queryset(self, request):
        qs = super(ChatAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(bus__places__datasource__in=request.user.ddisps.all())
        return qs.filter(bus__places=us.place)

    def get_list_filter(self, request):
        if not request.user.is_superuser:
            self.list_filter = ('')
        return self.list_filter


class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'vehicle_id', 'stars', 'positive', 'photo_tag')
    #list_filter = ('ms', 'us',)
    date_hierarchy = 'ctime'
    raw_id_fields = ("us", 'ms', 'vehicle')


@admin.register(Settings)
class SettingsAdmin(VersionAdmin):
    list_display = ('key', 'value','description', 'json', 'mtime')
    #readonly_fields = ('o', )


@admin.register(MobileSettings)
class MobileSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'uuid', 'name', 'os', 'version', 'ref_other', 'startups', 'user')
    list_filter = ('os', 'place', 'version')
    date_hierarchy = 'ctime'
    search_fields = ['id', 'uuid', 'name', 'user__id', 'user__username']
    readonly_fields = ('ctime', 'ltime', )
    raw_id_fields = ("user", "gps_send_bus")
    exclude = ('city',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "place":
            pids = places_filtered()
            kwargs["queryset"] = Place.objects.filter(id__in=pids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'name')
    #date_hierarchy = 'ctime'
    search_fields = ['id', ]
    readonly_fields = ('ctime', 'ltime')
    raw_id_fields = ("user", "gps_send_bus")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "place":
            pids = places_filtered()
            kwargs["queryset"] = Place.objects.filter(id__in=pids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)    


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'language', 'domain', 'available', 'register_phone')
    search_fields = ['name', 'code']
    list_filter = ('available', )


@admin.register(GameTimeTap)
class GameTimeTapAdmin(admin.ModelAdmin):
    list_display = ('ctime', 'mtime', 'ms', 'score')
    search_fields = ['ms']
    raw_id_fields = ("ms", )
    date_hierarchy = 'ctime'


@admin.register(Feature)
class FeatureAdmin(BustimeCompareVersionAdmin):
    list_display = ("name", "ttype")
    list_filter = ('ttype', )
    search_fields = ('name', )


@admin.register(VehicleBrand)
class VehicleBrandAdmin(BustimeCompareVersionAdmin):
    list_display = ('name', 'slug')
    readonly_fields = ('slug',)


@admin.register(VehicleModel)
class VehicleModelAdmin(BustimeCompareVersionAdmin):
    class VehicleModelInlineFeature(admin.StackedInline):
        class VehicleModelInlineFormset(BaseInlineFormSet):
            def add_fields(self, form, index):
                form.fields['feature'].queryset = Feature.objects.filter(ttype=Feature.FeatureType.VEHICLE_MODEL)
                super().add_fields(form, index)

        model = VehicleModelFeature
        verbose_name_plural = "features"
        extra = 1
        formset = VehicleModelInlineFormset

    list_display = ('name', 'brand', 'slug')
    readonly_fields = ('slug', )
    list_filter = ('brand',)
    search_fields = ('brand',)
    inlines = [VehicleModelInlineFeature]


@admin.register(Vehicle)
class VehicleAdmin(BustimeCompareVersionAdmin):
    class VehicleInlineFeature(admin.StackedInline):
        class VehicleInlineFormset(BaseInlineFormSet):
            def add_fields(self, form, index):
                form.fields['feature'].queryset = Feature.objects.filter(ttype=Feature.FeatureType.VEHICLE)
                super().add_fields(form, index)

        model = VehicleFeature
        verbose_name_plural = "features"
        extra = 1
        formset = VehicleInlineFormset

    list_display = ('uid_provider', 'uniqueid', 'gosnum', 'bortnum', 'created_date', 'modified_date','created_auto', 'gosnum_allow_edit', 'bortnum_allow_edit')
    readonly_fields = ('uid_provider', 'uniqueid', 'created_date', )
    search_fields = ['uid_provider', 'uniqueid', 'gosnum']
    # raw_id_fields = ("city", "provider", )
    list_filter = (
        VehiclePlaceListFilter,
    )
    raw_id_fields = ("provider", )
    date_hierarchy = 'created_date'
    ordering = ('uid_provider', 'uniqueid', 'created_date', )

    paginator = CachingPaginator
    inlines = [VehicleInlineFeature]

    def get_queryset(self, request):
        qs = super(VehicleAdmin, self).get_queryset(request)
        # qs = super(VehicleAdmin, self).get_queryset(request)
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        revision_url_alias = "%s_%s_revision" % info
        match = resolve(request.path)
        if match and match.url_name == revision_url_alias:
            qs = qs.using(router.db_for_write(self.model))

        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(datasource__in=request.user.ddisps.all())
        return qs.filter(datasource__in=us.place.datasource_set.all())

    def get_form(self, request, obj=None, **kwargs):
        if not request.user.is_superuser:
            if not self.exclude:
                self.exclude = ()
            self.exclude += ("uid_provider", )
        form = super(VehicleAdmin, self).get_form(request, obj, **kwargs)
        return form

    @contextmanager
    def create_revision(self, request):
        from reversion.revisions import set_comment, create_revision, set_user, add_meta
        city_id = request.POST.get('city', None)
        with create_revision():
            set_user(request.user)
            if city_id:
                add_meta(VersionCity, place_id=city_id)
            yield

    # def set_diff_as_comment(self, request, object_id):
    #     obj = self.get_object(request, object_id)
    #     versions = Version.objects.get_for_object_reference(Vehicle, object_id)
    #     version = versions[0]
    #     patch_html, _ = self.compare(obj, versions[1], versions[0])
    #     comment = ""
    #     for patch in patch_html:
    #         comment += patch.get('diff', '')
    #     version.revision.comment = comment
    #     version.revision.save()

    def save_model(self, request, obj, form, change):
        if not obj.uniqueid:
            obj.uniqueid = make_uid_(obj.uid_provider, obj.channel, obj.src)
        obj.save(request.user)
        super(VehicleAdmin, self).save_model(request, obj, form, change)

    # def fallback_compare(self, obj_compare):
    #     from reversion_compare.helpers import html_diff, EFFICIENCY
    #     value1, value2 = obj_compare.to_string()
    #     html = html_diff(value1, value2, EFFICIENCY)
    #     return html


# @admin.register(VehicleStatus)
# class VehicleStatusAdmin(admin.ModelAdmin):
#     list_display = ('city_time', 'uniqueid', 'gosnum', 'status')
#     search_fields = ['uniqueid', 'gosnum']
#     list_filter = ('city', 'status', )
#     raw_id_fields = ("endpoint", "bus", )
#     date_hierarchy = 'city_time'


@admin.register(SmartUser)
class SmartUserAdmin(admin.ModelAdmin):
    list_display = ('ctime', 'uid', 'city', 'registered')
    search_fields = ['uid', ]
    list_filter = ('city', 'registered', )


@admin.register(SMS)
class SMSAdmin(admin.ModelAdmin):
    list_display = ('ctime', 'src', 'text')
    search_fields = ['src', ]
    date_hierarchy = 'ctime'

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('ctime', 'ms', 'like', 'content_type', 'object_id')
    search_fields = ['ms', ]
    date_hierarchy = 'ctime'

@admin.register(BusProvider)
class BusProviderAdmin(BustimeCompareVersionAdmin, LeafletGeoAdmin):
    list_display = ('id', 'name', 'phone', 'mtime')
    fields = ('name','address','phone','email','www','logo','xeno_id')
    readonly_fields = ('ctime','mtime')
    search_fields = ['name']
    #list_filter = ('place', )
    list_filter = (
        BusProviderPlaceListFilter,
    )
    ordering = ('name',)
    exclude = ('point',)

    def get_places(self, row):
        places = set()
        for bus in row.bus_set.all():
            for place in bus.places.all():
                places.add(place)
        return places

    def places(self, row):
        places = self.get_places(row)
        return format_html(
                    ', '.join(
                            [f'<a href="/wiki/bustime/place/{p.id}/change/" target="_blank">{p.name}</a>' for p in places]
                        )
                )

    def get_queryset(self, request):
        qs = super(BusProviderAdmin, self).get_queryset(request)
        opts = self.model._meta
        info = opts.app_label, opts.model_name,
        revision_url_alias = "%s_%s_revision" % info
        match = resolve(request.path)
        if match and match.url_name == revision_url_alias:
            qs = qs.using(router.db_for_write(self.model))
        """
        if request.user.is_superuser:
            return qs
        us = get_user_settings_mini(request)
        if not us or not us.place:
            return qs.filter(place__datasource__in=request.user.ddisps.all())
        uplace = None
        if us:
            uplace = us.place_id
        return qs.filter(place_id=uplace)
        """
        return qs

    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "place" and not request.user.is_superuser:
            us = get_user_settings_mini(request)
            if not us or not us.place:
                kwargs["queryset"] = Place.objects.filter(id__in=request.user.ddisps.all())
            else:
                kwargs["queryset"] = Place.objects.filter(id=us.place_id)
        return super(BusProviderAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
    """


    # def save_model(self, request, obj, form, change):
    #     us = get_user_settings_mini(request)
    #     obj.save(us)

    @contextmanager
    def create_revision(self, request):
        from reversion.revisions import set_comment, create_revision, set_user, add_meta
        with create_revision():
            set_user(request.user)
            yield


@admin.register(CityNews)
class CityNewsAdmin(admin.ModelAdmin):
    list_display = ('place', 'ctime', 'author', 'title', 'body', 'etime')
    search_fields = ['body', 'title']
    date_hierarchy = 'ctime'
    list_filter = ('etime', 'news_type', 'place', )
    '''
    def get_queryset(self, request):
        qs = super(CityNewsAdmin, self).get_queryset(request)
        return qs.filter(news_type=1)
    '''
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["queryset"] = User.objects.filter(id=request.user.id)
        return super(CityNewsAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        obj.save()


class BusVersionLogInline(admin.TabularInline):
    model = BusVersionLog
    verbose_name_plural = "Actions"
    fields = ['note', 'nbusstop_id', 'name',]
    readonly_fields=('note', 'nbusstop_id', 'name',)
    ordering = ('id', )
    fk_name = "busversion"

    can_delete = False  # remove "Delete" button
    extra = 0   # remopve last empty rows
    # remove "Add another..." link
    # https://stackoverflow.com/questions/1721037/remove-add-another-in-django-admin-screen


@admin.register(BusVersion)
class BusVersionAdmin(admin.ModelAdmin):
    verbose_name_plural = "Bus editions"
    can_delete = False
    list_display = ('id', 'bus', 'city', 'place', 'user', 'ctime')
    readonly_fields = ('version_actions', 'id', 'city', 'place', 'bus', 'user', 'ctime', 'stops_before', 'stops_after', 'routes_before', 'routes_after')
    search_fields = ['bus', 'user']
    list_filter = (
        ('bus', admin.RelatedOnlyFieldListFilter),
        ('city', admin.RelatedOnlyFieldListFilter),
        ('user', admin.RelatedOnlyFieldListFilter)
    )
    date_hierarchy = 'ctime'
    fields = ['id', 'city', 'place', 'bus', 'user', 'ctime', 'version_actions']
    exclude = ('stops_before', 'stops_after', 'routes_before', 'routes_after')
    inlines = [BusVersionLogInline]    # Gateway timeout ???

    def get_queryset(self, request):
        qs = super(BusVersionAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    # remove "Add another..." link
    # https://stackoverflow.com/questions/1721037/remove-add-another-in-django-admin-screen

    # Revert button:
    def get_urls(self):
        urls = super(BusVersionAdmin, self).get_urls()
        my_urls = [
            re_path(r'^(?P<bus_id>[\d]+)/revert/(?P<version_id>[\d]+)/$', bustime.views.bus_route_revert, name='bus_route_revert'),
        ]
        return my_urls + urls

    # add 'version_actions' to list_display for view button in list of versions
    # add 'version_actions' to readonly_fields AND fields for view butthon in version page
    def version_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Revert</a>',
            reverse('admin:bus_route_revert', args=[obj.bus.pk, obj.pk]),
        )
    version_actions.short_description = 'Revert:'
    version_actions.allow_tags = True
# class BusVersionAdmin


class ReviewVersionAdmin(admin.ModelAdmin, CompareMixin):
    change_list_template = "admin/bustime/change_version_list.html"
    list_display = ("create_date", "get_object_id", "get_diff", "get_user", "content_type")
    # list_display_links = ("children_display")
    date_hierarchy = 'revision__date_created'
    list_filter = (
        VersionListFilter,
        UserGroupListFilter,
        UserListFilter,
        CityListFilter)
    search_fields = ("revision__user__username",)
    raw_id_fields = ("revision",)

    def get_for_user(self, request):
        user_id = request.GET.get("user_id", None)
        print(user_id)
        if not user_id:
            return ()
        return User.objects.filter(id=user_id)

    def compare_DateTimeField(self, obj_compare):
        return ""

    def compare_provider(self, obj_compare):
        if obj_compare.value1 == DOES_NOT_EXIST and obj_compare.value2 == DOES_NOT_EXIST:
            return ""
        return self.fallback_compare(obj_compare)

    def get_user(self, obj):
        user = obj.revision.user
        display_text = None
        if user:
            display_text = "<a href={}>{}</a>".format(
                        reverse('admin:{}_{}_change'.format(user._meta.app_label, user._meta.model_name),
                        args=(user.id,)), user)
        if display_text:
            return mark_safe(display_text)
        return "-"

    def get_object_id(self, obj):
        display_text = "<a href={}>{}</a>".format(
                    reverse('admin:{}_{}_change'.format(obj._model._meta.app_label, obj._model._meta.model_name),
                    args=(obj.object_id,)), obj.object_id)

        if display_text:
            return mark_safe(display_text)
        return "-"

    # def get_model_fields(self, obj):
    #     return obj._model
    #
    def create_date(self, obj):
        return obj.revision.date_created

    def get_diff(self, obj):
        from django.db.models.expressions import Window
        from django.db.models.functions import RowNumber
        # return obj.revision.get_comment()

        data = obj._model.objects.get(pk=obj.object_id)
        versions = obj.__class__.objects.get_for_object_reference(obj._model, obj.object_id)
        # match = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}[,:.] '
        if len(versions) > 1:
            index = list(versions.filter(object_id=obj.object_id)).index(obj)
            if len(versions) > index + 1:
                patch_html, _ = self.compare(data, versions[index + 1], obj)
            else:
                patch_html = [{"diff": '<pre class="highlight"><ins>+ %s</ins></pre>' % obj.object_repr}]
                # patch_html = [{"diff": re.sub(match, '', '<pre class="highlight"><ins>+ %s</ins></pre>' % obj.object_repr)}]
        else:
            patch_html = [{"diff": '<pre class="highlight"><ins>+ %s</ins></pre>' % obj.object_repr}]
            # patch_html = [{"diff": re.sub(match, '', '<pre class="highlight"><ins>+ %s</ins></pre>' % obj.object_repr)}]
        comment = ""
        for patch in patch_html:
            comment += patch.get('diff', '')

        return mark_safe(comment)

    get_user.short_description = "User"
    get_object_id.short_description = "Object ID"
    get_diff.short_description = "Difference"
    get_diff.admin_order_field = "diff"


admin.site.unregister(User)


class UserAdmin(DjangoUserAdmin):
    change_form_template = "admin/bustime/change_user_form.html"

    def response_change(self, request, obj):
        admin_us = get_user_settings_mini(request)
        if "_block-user" in request.POST:
            mss, uss = belongs_to_user(obj)
            Chat.objects.filter(Q(deleted=False) & (Q(ms_id__in=[ms.id for ms in mss]) | Q(us_id__in=[us.id for us in uss]))).update(
                deleted_by=admin_us.user,
                deleted=True
            )
        elif "_block-user-for-year" in request.POST:
            mss, uss = belongs_to_user(obj, 365)
            Chat.objects.filter(Q(deleted=False) & (Q(ms_id__in=[ms.id for ms in mss]) | Q(us_id__in=[us.id for us in uss]))).update(
                deleted_by=admin_us.user,
                deleted=True
            )
        elif "_unblock-user" in request.POST:
            for ms in MobileSettings.objects.filter(user=obj):
                ms.ban = None
                ms.save(update_fields=["ban"])
                Chat.objects.filter(deleted=True, ms=ms).update(deleted=False)
            for us in UserSettings.objects.filter(user=obj):
                us.ban = None
                us.save(update_fields=["ban"])
                Chat.objects.filter(deleted=True, us=us).update(deleted=False)
        # elif "_unblock-user"
        elif "_rollback-changes" in request.POST:
            return redirect(f"/wiki/reversion/version/?user_id={obj.id}")
            # return self.rollback_user_versions_changes(request, obj)
            # print(super().delete_selected_confirmation_template(request, ))
            # return super().delete_confirmation_template(request, obj)
        return super().response_change(request, obj)

    def get_urls(self):
        urls = super(UserAdmin, self).get_urls()
        my_urls = [
            re_path(r'^auth/user/(?P<user_id>[\d]+/rollback_all)/$', self.rollback_user_versions_changes)
        ]
        return my_urls + urls
    # response_change

    def rollback_user_versions_changes(self, request, user):
        print(user)
        versions = Version.objects.filter(revision__user=user)
        ctx = {"versions": versions}
        return TemplateResponse(request, "admin/bustime/rollback_user_version_changes.html", ctx)


# Источники данных gtfs
class GtfsCatalogAdmin(VersionAdmin, LeafletGeoAdmin):
    change_list_template = "admin/bustime/change_list_gtfs_catalog.html"
    list_display = ('id', 'name', 'active', 'updater', 'cnt_buses', 'view', 'tools', 'load', 'imprt')
    search_fields = ['name', 'url_schedule']
    list_filter = ('active',)
    readonly_fields = ('user_id', 'cnt_buses',)

    # https://docs.djangoproject.com/en/4.1/topics/db/multi-db/#exposing-multiple-databases-in-django-s-admin-interface
    using = "gtfs"  # Tell Django to save objects to the 'gtfs' database.

    def save_model(self, request, obj, form, change):
        obj.user_id = request.user.id
        obj.save(using=self.using)

    def delete_model(self, request, obj):
        obj.delete(using=self.using)

    def get_queryset(self, request):
        #self.us = bustime.views.get_user_settings(request)
        return super().get_queryset(request).using(self.using)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        return super().formfield_for_foreignkey(db_field, request, using=self.using, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        return super().formfield_for_manytomany(db_field, request, using=self.using, **kwargs)

    def updater(self, obj):
        return 'Y' if REDIS.exists(f'gtfs_updater_{obj.id}') else ''

    def view(self, obj):
        # see buttons_switcher() in templates/admin/bustime/change_list_gtfs_catalog.html
        # TODO: определить как-то city_slug в зависимости от пользователя или избавиться от него совсем
        return format_html(
            '<a href="javascript:void(0)" class="button" onclick="buttons_switcher(\'view\', \'{0}\', {1})" title="Визуализация маршрутов">View</a>',
            'spb', obj.id
        )

    def tools(self, obj):
        return format_html(
            '<a href="javascript:void(0)" class="button" onclick="buttons_switcher(\'tools\', \'{0}\', {1})" title="Проверка коррекности">Test</a>',
            'spb', obj.id
        )

    def load(self, obj):
        return format_html(
            '<a href="javascript:void(0)" class="button" onclick="buttons_switcher(\'load\', \'{0}\', {1})" title="Загрузка schedule">Load</a>',
            'spb', obj.id
        )

    def imprt(self, obj):
        return format_html(
            '<a href="javascript:void(0)" class="button" onclick="buttons_switcher(\'import\', \'{0}\', {1})" title="Импорт загруженного schedule в маршруты bustime.loc">Import</a>',
            'spb', obj.id
        )
# class GtfsCatalogAdmin


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'active', 'channel', 'src')
    search_fields = ['channel', 'src', ]
    list_filter = ('active', 'channel')
    ordering = ('channel', 'src',)
    raw_id_fields = ("dispatchers", "places", )


admin.site.register(GtfsCatalog, GtfsCatalogAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Place, PlaceAdmin)
admin.site.register(Bus, BusAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(NBusStop, NBusStopAdmin)
admin.site.register(Sound)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Bonus, BonusAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(SpecialIcon, SpecialIconAdmin)
admin.site.register(Mbox, MboxAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Gosnum, GosnumAdmin)
admin.site.register(AdGeo, AdGeoAdmin)
admin.site.register(Finance, FinanceAdmin)
admin.site.register(BusStopIconImage, BusStopIconImageAdmin)
admin.site.register(Metric, MetricAdmin)
admin.site.register(MetricTime, MetricTimeAdmin)
admin.site.register(Chat, ChatAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(RouteLine, RouteLineAdmin)
admin.site.register(MoTheme)
admin.site.register(Version, ReviewVersionAdmin)