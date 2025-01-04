from django.contrib import admin
from .models import Article

# Register your models here.
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'sum_of_rating', 'count_of_rates')
    search_fields = ('title', 'description')

admin.site.register(Article, ArticleAdmin)