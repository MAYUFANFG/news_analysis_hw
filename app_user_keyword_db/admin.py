from django.contrib import admin
from .models import NewsData

# Register your models here.
@admin.register(NewsData)
class NewsDataAdmin(admin.ModelAdmin):
    list_display = ('category', 'title', 'date')
