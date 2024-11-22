# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django import forms
from .models import *
from django.contrib.gis.geos import Point


class BusStopNewForm(forms.Form):
    name = forms.CharField(label='Название', max_length=128)
    point = forms.CharField(label='Координаты', max_length=64)
    # city = forms.CharField(label='Your name', max_length=100)
    # city = forms.ModelChoiceField(queryset=City.objects.filter(available=True, active=True), widget=forms.Select(attrs={'disabled':'disabled'}))
    # name_alt = forms.CharField(label='Название альтернативное', max_length=128, required=False)

    def clean_point(self):
        data = self.cleaned_data['point']
        try:
            data = data.split(';')
            point = Point(float(data[0]), float(data[1]))
        except:
            raise forms.ValidationError("Ошибка обработки координат")
        return point


class BusNewForm(forms.Form):
    name = forms.CharField(label='Номер маршрута', max_length=128)
    type = forms.ChoiceField(choices=TTYPE_CHOICES)
