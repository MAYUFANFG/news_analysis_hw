from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from datetime import datetime, timedelta
import pandas as pd
import math
import re
from collections import Counter

# 使用新的數據集 pts_news_merged_all.csv
# global variable
def load_df_data():
    global df  # global variable
    # 注意這裡使用了新的CSV文件，並指定分隔符為'|'
    df = pd.read_csv('app_user_keyword/dataset/pts_news_merged_all.csv', sep='|')
    # 檢查並處理日期格式
    if 'date' in df.columns:
        # 確保日期格式正確，如果有問題可以在這裡轉換
        pass
    # 確保必要的列存在
    required_cols = ['date', 'category', 'title', 'content', 'top_key_freq', 'link', 'photo_link']
    for col in required_cols:
        if col not in df.columns:
            print(f"警告: 缺少必要的列 '{col}'，這可能會導致功能異常。")

# 初始化時加載數據
load_df_data()


# For the key association analysis
def home(request):
    return render(request, 'app_user_keyword_association/home.html')

# df_query should be global
@csrf_exempt
def api_get_userkey_associate(request):
    userkey = request.POST.get('userkey')
    cate = request.POST['cate']  # This is an alternative way to get POST data.
    cond = request.POST.get('cond')
    weeks = int(request.POST.get('weeks'))
    key = userkey.split()

    df_query = filter_dataFrame_fullText(key, cond, cate, weeks)
    print(key)
    print(len(df_query))

    if len(df_query) != 0:  # df_query is not empty
        newslinks = get_title_link_topk(df_query, k=25)
        related_words, clouddata = get_related_word_clouddata(df_query)
        same_paragraph = get_same_para(df_query, key, cond, k=30)  # multiple keywords
    else:
        newslinks = []
        related_words = []
        same_paragraph = []
        clouddata = []

    response = {
        'newslinks': newslinks,
        'related_words': related_words,
        'same_paragraph': same_paragraph,
        'clouddata': clouddata,
    }
    print(response)
    return JsonResponse(response)


# Searching keywords from "content" column
def filter_dataFrame_fullText(user_keywords, cond, cate, weeks):
    # 確保df是全局變數
    global df

    try:
        # end date: the date of the latest record of news
        end_date = df.date.max()

        # 檢查日期格式
        try:
            # 檢查日期格式是否正確
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            # 如果日期格式不是 '%Y-%m-%d'，嘗試其他格式或處理錯誤
            print(f"警告: 日期格式不是 'YYYY-MM-DD'，實際值為 '{end_date}'")
            # 這裡可以嘗試將日期轉換為正確格式
            # end_date = 正確格式的日期

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

    except Exception as e:
        print(f"過濾數據時出錯: {e}")
        # 返回空數據框
        df_query = pd.DataFrame()

    return df_query


# get titles and links from k pieces of news 
def get_title_link_topk(df_query, k=25):
    items = []
    try:
        for i in range(min(len(df_query), k)):  # 確保不超過實際數量
            # 使用get方法避免KeyError
            category = df_query.iloc[i].get('category', '')
            title = df_query.iloc[i].get('title', '')
            link = df_query.iloc[i].get('link', '')
            photo_link = df_query.iloc[i].get('photo_link', '')
            
            # 如果photo_link值為NaN，替換為空字符串
            if pd.isna(photo_link):
                photo_link = ''
            
            item_info = {
                'category': category,
                'title': title,
                'link': link,
                'photo_link': photo_link
            }
            
            items.append(item_info)
    except Exception as e:
        print(f"獲取標題和鏈接時出錯: {e}")
    
    return items


# Get related keywords by counting the top keywords of each news.
def get_related_word_clouddata(df_query):
    try:
        # 準備wf pairs
        counter = Counter()
        for idx in range(len(df_query)):
            # 檢查top_key_freq是否存在且不為空
            if 'top_key_freq' in df_query.iloc[idx] and not pd.isna(df_query.iloc[idx].top_key_freq):
                try:
                    # 嘗試解析top_key_freq
                    pair_dict = dict(eval(df_query.iloc[idx].top_key_freq))
                    counter += Counter(pair_dict)
                except Exception as e:
                    print(f"解析top_key_freq時出錯 (索引 {idx}): {e}")
        
        # 如果counter為空，添加一個默認值避免後續處理出錯
        if not counter:
            counter['暫無'] = 1
        
        wf_pairs = counter.most_common(20)  # 返回列表格式
        
        # 詞雲圖表數據
        # 頂部詞的最小和最大頻率
        min_ = wf_pairs[-1][1]  # 最後一行較小
        max_ = wf_pairs[0][1]
        
        # 根據詞頻值的文本大小，用於繪製詞雲圖表
        textSizeMin = 20
        textSizeMax = 120
        
        # 將頻率值縮放到20到120的區間。
        if max_ == min_:  # 防止除以零錯誤
            clouddata = [{'text': w, 'size': textSizeMin} for w, f in wf_pairs]
        else:
            clouddata = [{'text': w, 'size': int(textSizeMin + (f - min_) / (max_ - min_) * (textSizeMax - textSizeMin))}
                         for w, f in wf_pairs]
    
    except Exception as e:
        print(f"獲取相關詞和詞雲數據時出錯: {e}")
        wf_pairs = [('暫無', 1)]
        clouddata = [{'text': '暫無', 'size': textSizeMin}]
    
    return wf_pairs, clouddata


# Step1: split paragraphs in text 先將文章切成一個段落一個段落
def cut_paragraph(text):
    if pd.isna(text) or not isinstance(text, str):
        return []
    
    paragraphs = text.split('。')  # 遇到句號就切開
    paragraphs = list(filter(None, paragraphs))
    return paragraphs


# Step2: Select all paragraphs where multiple keywords occur.
def get_same_para(df_query, user_keywords, cond, k=30):
    same_para = []
    try:
        for text in df_query.content:
            if pd.isna(text) or not isinstance(text, str):
                continue
                
            paragraphs = cut_paragraph(text)
            for para in paragraphs:
                para += "。"
                try:
                    if cond == 'and':
                        if all([re.search(kw, para) for kw in user_keywords]):
                            same_para.append(para)
                    elif cond == 'or':
                        if any([re.search(kw, para) for kw in user_keywords]):
                            same_para.append(para)
                except re.error as e:
                    print(f"正則表達式錯誤: {e}")
    except Exception as e:
        print(f"獲取相同段落時出錯: {e}")
    
    return same_para[0:min(k, len(same_para))]


print("新視圖已加載: app_user_keyword_association with pts_news_merged_all.csv!")