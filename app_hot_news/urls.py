from django.urls import path
from app_hot_news import views

app_name='app_hot_news'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_hot_news_data/', views.api_get_hot_news_data),
]
