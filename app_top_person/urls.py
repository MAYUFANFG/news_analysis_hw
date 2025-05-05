# from django.urls import path,include
# from app_top_person import views


# # declare a namespace for this APP
# # the name of namespace is 'app_top_person'
# # We will use the namespace in the future integrated website.

# #  使用app_name是讓各個APP的變數與方法名稱有區隔
# #  若名稱不衝突，不使用app_name也可以
# #  app_name是一種namespace的概念
# # 整合多個可獨立運作的APP成為一個大型專案必備知識
# # 在template中如何使用?
# # <a class="nav-link" href="{% url 'app_top_person:home' %}">熱門人物</a>

# app_name="app_top_person"

# urlpatterns = [
#     # top (popular) persons
#     path('', views.home, name='home'),
#     # ajax path
#     path('api_get_topPerson/', views.api_get_topPerson),
#     #path('api/get_top_words/', views.api_get_topWords, name='api_get_topWords'),
#     #path('topperson/', include('app_top_person.urls')),
# ]


from django.urls import path
from . import views

app_name = "app_top_person"  # 保持原有的 app 名稱

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_topPerson/', views.api_get_topPerson, name='api_get_topPerson'),
]


# from django.urls import path
# from . import views

# # 不使用命名空間
# # app_name = 'app_top_person'  # 移除或註釋此行

# urlpatterns = [
#     path('', views.home, name='home'),
#     path('api_get_topPerson/', views.api_get_topPerson, name='api_get_topPerson'),
#     path('api_get_categories/', views.api_get_categories, name='api_get_categories'),
# ]