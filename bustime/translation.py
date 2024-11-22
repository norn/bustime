from modeltranslation.translator import translator, TranslationOptions
from .models import City, Country, Place, Feature

class CityTranslationOptions(TranslationOptions):
    fields = ('name', )
translator.register(City, CityTranslationOptions)

class CountryTranslationOptions(TranslationOptions):
    fields = ('name', )
translator.register(Country, CountryTranslationOptions)

class PlaceTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Place, PlaceTranslationOptions)

class FeatureTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Feature, FeatureTranslationOptions)


for f in City._meta.get_fields():
  if f.name.startswith("name_"):
      f=getattr(City, f.name)
      if getattr(f.field, 'cached_col'):
          del f.field.cached_col

for f in Country._meta.get_fields():
  if f.name.startswith("name_"):
      f=getattr(Country, f.name)
      if getattr(f.field, 'cached_col'):
          del f.field.cached_col
