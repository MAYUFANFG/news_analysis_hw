from django.urls import path
from . import views

app_name="app_user_keyword_llm_report"

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_userkey_data/', views.api_get_userkey_data, name='api_get_userkey_data'),
    path('api_get_userkey_llm_report/', views.api_get_userkey_llm_report, name='api_get_userkey_llm_report'),

]
