from django.contrib.sitemaps import Sitemap
from blog.models import Entry


#https://docs.djangoproject.com/en/1.8/ref/contrib/sitemaps/
class BlogSitemap(Sitemap):
    changefreq = "never"
    priority = 0.5

    def items(self):
        return Entry.objects.filter(is_draft=False)

    def lastmod(self, obj):
        return obj.pub_date