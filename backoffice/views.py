from __future__ import absolute_import
from django.http import HttpResponse, Http404, HttpResponseRedirect
import subprocess
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from bustime.models import *
#import redis
CITIES = City.objects.all().order_by('id')
from django.contrib.auth.decorators import login_required


@login_required
def dash(request):
    return HttpResponse("ready")
    stats = backoffice_statlos()
    ctx = dict(cities=CITIES, stats=stats)
    return render(request, 'backoffice/dash.html', ctx)


@login_required
def all_events(request, city_id):
	city = City.objects.get(id=int(city_id))
	allevents = REDIS.get("allevents_%s"%city.id)
	if allevents:
		allevents = pickle.loads(allevents)
	ctx = dict(cities=CITIES, city=city,  allevents=allevents)
	return render(request, 'backoffice/allevents.html', ctx)


@login_required
def timer(request, city_id):
	city = City.objects.get(id=int(city_id))
	time_bst = REDIS.get("time_bst_%s"%city.id)
	if time_bst: time_bst=pickle.loads(time_bst)
	timer_bst = REDIS.get("timer_bst_%s"%city.id)
	if timer_bst: timer_bst=pickle.loads(timer_bst)
	ctx = dict(cities=CITIES, city=city,  time_bst=time_bst, timer_bst=timer_bst)
	return render(request, 'backoffice/timer.html', ctx)


@login_required
def bdata0(request, city_id):
	city = City.objects.get(id=int(city_id))
	buses = Bus.objects.filter(city=city.id)
	bdata0={}
	for b in buses:
		bd0 = REDIS.get("bdata_mode0_%s"%b.id)
		if bd0:
			bdata0[b.id] = pickle.loads(bd0)
	ctx = dict(cities=CITIES, city=city, bdata0=bdata0)
	return render(request, 'backoffice/bdata0.html', ctx)


@login_required
def bdata1(request, city_id):
	city = City.objects.get(id=int(city_id))
	buses = Bus.objects.filter(city=city.id)
	bdata1={}
	for b in buses:
		bd1 = REDIS.get("bdata_mode1_%s"%b.id)
		if bd1:
			bdata1[b.id] = pickle.loads(bd1)
	ctx = dict(cities=CITIES, city=city, bdata1=bdata1)
	return render(request, 'backoffice/bdata1.html', ctx)


@login_required
def bdata2(request, city_id):
	city = City.objects.get(id=int(city_id))
	buses = Bus.objects.filter(city=city.id)
	bdata2={}
	for b in buses:
		bd2 = REDIS.get("bdata_mode2_%s"%b.id)
		if bd2:
			bdata2[b.id] = pickle.loads(bd2)
	ctx = dict(cities=CITIES, city=city, bdata2=bdata2)
	return render(request, 'backoffice/bdata2.html', ctx)


@login_required
def bdata3(request, city_id):
	city = City.objects.get(id=int(city_id))
	bdata3 = REDIS.get("bdata_mode3_%s"%city.id)
	if bdata3:
		bdata3=pickle.loads(bdata3)
	ctx = dict(cities=CITIES, city=city, bdata3=bdata3)
	return render(request, 'backoffice/bdata3.html', ctx)
