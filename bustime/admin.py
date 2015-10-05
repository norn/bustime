from django.contrib import admin

# Register your models here.
from models import *

class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'ttype', 'message', 'user')
    list_filter = ('ttype',)

class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_gde', 'slug', 'timediffk', 'wunderground', 'point')

class BusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'ttype', 'murl', 'napr_a', 'napr_b', 'city')
    search_fields = ['name']
    list_filter = ('ttype','city')

class RouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'bus', 'busstop', 'direction', 'order', 'endpoint')
    search_fields = ['bus__name']
    list_filter = ('direction', 'bus__ttype', 'bus__city', 'bus')

class NBusStopAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'moveto', 'city')
    search_fields = ['name']
    list_filter = ('city',)

class UserTimerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'minutes')
    search_fields = ['user']
    list_filter = ('date',)
    raw_id_fields = ("user")

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'end_time', 'user', 'value', 'fiat', 'phone', 'notified', 'comment')
    search_fields = ['user', 'comment']
    list_filter = ('ctime','end_time')
    raw_id_fields = ("user")
    date_hierarchy = 'ctime'

class TimetableAdmin(admin.ModelAdmin):
    list_display = ('id', 'bus', 'busstop', 'direction', 'time', 'holiday', 'xeno_title')
    search_fields = ['bus', 'busstop']
    list_filter = ('bus', 'holiday')

class BonusAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'mtime', 'pin', 'comment', 'days', 'activated')

class SpecialIconAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'gosnum', 'img', 'active')

class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'ctime', 'url', 'name_short', 'active')
    list_filter = ('active',)

admin.site.register(Log, LogAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Bus, BusAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(NBusStop, NBusStopAdmin)
admin.site.register(Sound)
admin.site.register(UserTimer, UserTimerAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Timetable, TimetableAdmin)
admin.site.register(Bonus, BonusAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(SpecialIcon, SpecialIconAdmin)
