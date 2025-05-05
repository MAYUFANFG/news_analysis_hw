from django.http import JsonResponse
import pandas as pd
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

def load_data_pk():
    # 讀取 hot_news 的資料集
    df_data_pk = pd.read_csv('app_hot_news/dataset/pk_political_parties.csv')
    
    global data
    data={}
    for k,v in zip(df_data_pk.name, df_data_pk.value):
        data[k]=eval(v)
    
    # 沒用到的變數刪除之
    del df_data_pk

# 載入資料
load_data_pk()

def home(request):
    return render(request, 'app_hot_news/home.html')

# csrf_exempt is used for POST
# 單獨指定這一支程式忽略csrf驗證
@csrf_exempt
def api_get_hot_news_data(request):
    return JsonResponse(data)

print('Load app hot news leaderboard...')