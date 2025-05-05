from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from datetime import datetime, timedelta
import pandas as pd
import math
import re
from collections import Counter

# (1) we can load data using read_csv() 自己app的csv檔案
# global variable
# df = pd.read_csv('dataset/cna_news_200_preprocessed.csv', sep='|')


# (2) we can load data using reload_df_data() function 隔壁app的csv檔案
# global variable
def load_df_data_v1():
    # global variable
    global  df
    df = pd.read_csv('app_user_keyword/dataset/cna_news_200_preprocessed.csv', sep='|')

# (3) df can be import from app_user_keyword 隔壁app的變數
# To save memory, we just import df from the other app as follows.
# from app_user_keyword.views import df

# (4) df can be import from app_user_keyword  隔壁app的變數
import app_user_keyword.views as userkeyword_views
def load_df_data():
    # import and use df from app_user_keyword 
    global df # global variable
    df = userkeyword_views.df

load_df_data()


# For the key association analysis
def home(request):
    return render(request, 'app_user_keyword_association/home.html')

# df_query should be global
@csrf_exempt
def api_get_userkey_associate(request):

    userkey = request.POST.get('userkey')
    cate = request.POST['cate'] # This is an alternative way to get POST data.
    cond = request.POST.get('cond')
    weeks = int(request.POST.get('weeks'))
    key = userkey.split()

    #global  df_query # global variable It's not necessary.

    df_query = filter_dataFrame_fullText(key, cond, cate,weeks)
    print(key)
    print(len(df_query))

    if len(df_query) != 0:  # df_query is not empty
        newslinks = get_title_link_topk(df_query, k=25)
        related_words, clouddata = get_related_word_clouddata(df_query)
        same_paragraph = get_same_para(df_query, key, cond, k=30) # multiple keywords

    else:
        newslinks = []
        related_words = []
        same_paragraph = []
        clouddata = []

    response = {
        'newslinks': newslinks,
        'related_words': related_words,
        'same_paragraph': same_paragraph,
        'clouddata':clouddata,
    }
    print(response)
    return JsonResponse(response)


# Searching keywords from "content" column
# Here this function uses df.content column, while filter_dataFrame() uses df.tokens_v2
def filter_dataFrame_fullText(user_keywords, cond, cate, weeks):

    # end date: the date of the latest record of news
    end_date = df.date.max()

    # start date
    start_date = (datetime.strptime(end_date, '%Y-%m-%d').date() -
                  timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    # (1) proceed filtering: a duration of a period of time
    # 期間條件
    period_condition = (df.date >= start_date) & (df.date <= end_date)

    # (2) proceed filtering: news category
    # 新聞類別條件
    if (cate == "全部"):
        condition = period_condition  # "全部"類別不必過濾新聞種類
    else:
        # category新聞類別條件
        condition = period_condition & (df.category == cate)

    # (3) proceed filtering: news category
    # and or 條件
    if (cond == 'and'):
        # query keywords condition使用者輸入關鍵字條件and
        condition = condition & df.content.apply(lambda text: all(
            (qk in text) for qk in user_keywords))  # 寫法:all()
    elif (cond == 'or'):
        # query keywords condition使用者輸入關鍵字條件
        condition = condition & df.content.apply(lambda text: any(
            (qk in text) for qk in user_keywords))  # 寫法:any()
    # condiction is a list of True or False boolean value
    df_query = df[condition]

    return df_query


# get titles and links from k pieces of news 
def get_title_link_topk(df_query, k=25):
    items = []
    for i in range( len(df_query[0:k]) ): # show only 10 news
        category = df_query.iloc[i]['category']
        title = df_query.iloc[i]['title']
        link = df_query.iloc[i]['link']
        photo_link = df_query.iloc[i]['photo_link']
        # if photo_link value is NaN, replace it with empty string 
        if pd.isna(photo_link):
            photo_link=''
        
        item_info = {
            'category': category, 
            'title': title, 
            'link': link, 
            'photo_link': photo_link
        }

        items.append(item_info)
    return items 

# Get related keywords by counting the top keywords of each news.
# Notice:  do not name function as  "get_related_keys",
# because this name is used in Django
def get_related_word_clouddata(df_query):

    # wf_pairs = get_related_words(df_query)
    # prepare wf pairs 
    counter=Counter()
    for idx in range(len(df_query)):
        pair_dict = dict(eval(df_query.iloc[idx].top_key_freq))
        counter += Counter(pair_dict)
    wf_pairs = counter.most_common(20) #return list format

    # cloud chart data
    # the minimum and maximum frequency of top words
    min_ = wf_pairs[-1][1]  # the last line is smaller
    max_ = wf_pairs[0][1]
    # text size based on the value of word frequency for drawing cloud chart
    textSizeMin = 20
    textSizeMax = 120
    # Scaling frequency value into an interval of from 20 to 120.
    clouddata = [{'text': w, 'size': int(textSizeMin + (f - min_) / (max_ - min_) * (textSizeMax - textSizeMin))}
                 for w, f in wf_pairs]

    return   wf_pairs, clouddata 


# Step1: split paragraphs in text 先將文章切成一個段落一個段落
def cut_paragraph(text):
    paragraphs = text.split('。')  # 遇到句號就切開
    #paragraphs = re.split('。', text) # 遇到句號就切開
    #paragraphs = re.split('[。！!？?]', text) # 遇到句號(也納入問號、驚嘆號、分號等)就切開
    paragraphs = list(filter(None, paragraphs))
    return paragraphs

# Step2: Select all paragraphs where multiple keywords occur.


def get_same_para(df_query, user_keywords, cond, k=30):
    same_para = []
    for text in df_query.content:
        #print(text)
        paragraphs = cut_paragraph(text)
        for para in paragraphs:
            para += "。"
            if cond == 'and':
                if all([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
            elif cond == 'or':
                if any([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
    return same_para[0:k]


    
print("app_user_keyword_association was loaded!")
