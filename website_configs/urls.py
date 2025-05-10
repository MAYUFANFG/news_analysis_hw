from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    #path('admin/', admin.site.urls),
    # 熱門詞語分析
    path('topword/', include('app_top_keyword.urls')),  # 這裡要改對應的 app
    # 熱門人物分析
    path('topperson/', include('app_top_person.urls')),
    # user keyword analysis
    path('userkeyword/', include('app_user_keyword.urls')),
    # app trump
    path('trump/', include('app_trump.urls')),
    # full text search and associated keyword display
    path('userkeyword_assoc/', include('app_user_keyword_association.urls')),
    # app user keyword association
    path('userkeyword_senti/', include('app_user_keyword_sentiment.urls')),
    # hot news analysis
    path('hot_news/', include('app_hot_news.urls')),
    #app userkeyword
    path('userkeyword_db/', include('app_user_keyword_db.urls')),
    # full text search and associated keyword display using db
    path('topperson_keyword_db/', include('app_top_person_db.urls')),
    # user keyword sentiment 
    path('userkeyword_report/', include('app_user_keyword_llm_report.urls')),
    
    # admin 後台資料庫管理
    path('admin/', admin.site.urls),


]
