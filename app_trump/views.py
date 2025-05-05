from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd

def load_data_trump():
    # Read data from csv file
    df_data = pd.read_csv('app_trump/dataset/trump_data.csv',sep=',')
    global response
    response = dict(list(df_data.values))
    del df_data

# load pk data
load_data_trump()

def home(request):
    return render(request,'app_trump/home.html', response)

print('app_trump was loaded!')