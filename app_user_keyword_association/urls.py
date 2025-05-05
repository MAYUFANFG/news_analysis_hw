from django.urls import path
from app_user_keyword_association import views

app_name="app_user_keyword_association"

urlpatterns = [

    path('', views.home, name='home'),
    path('api_get_userkey_associate/', views.api_get_userkey_associate),

]


