from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q, Max, F
from django.db.models.functions import Cast
from django.db.models import TextField

from datetime import datetime, timedelta
import pandas as pd
import math
import re
import json
from collections import Counter

# Import the NewsData model
from .models import NewsData

# For the key association analysis
def home(request):
    return render(request, 'app_user_keyword_db/home.html')


@csrf_exempt
def api_get_userkey_data(request):
    userkey = request.POST.get('userkey')
    cate = request.POST['cate']  # This is an alternative way to get POST data.
    cond = request.POST.get('cond')
    weeks = int(request.POST.get('weeks'))
    key = userkey.split()

    # Get query results from database
    queryset = filter_database_fullText(key, cond, cate, weeks)
    print(f"Query returned {queryset.count()} results")

    # Check if the result is empty
    if not queryset.exists():  # queryset is not empty
        return JsonResponse({'error': 'No results found for the given keywords.'})

    # get the data for showing news articles, related words, and word cloud
    newslinks = get_title_link_topk(queryset, k=10)
    related_words, clouddata = get_related_word_clouddata(queryset)
    same_paragraph = get_same_para(queryset, key, cond, k=6)  # multiple keywords
    num_articles = queryset.count() # total number of articles (stories, items)
    response1 = {
        'newslinks': newslinks,
        'related_words': related_words,
        'same_paragraph': same_paragraph,
        'clouddata': clouddata,
        'num_articles': num_articles,
    }    

    # get the frequency data for trending chart
    #key_freq_cat, key_occurrence_cat = count_keyword(queryset, key) # OK
    key_freq_cat, key_occurrence_cat = count_keyword_with_orm(queryset, key) # OK
    
    print(key_occurrence_cat)
    
    # (5) get line chart data
    # key_time_freq = [
    # '{"x": "2019-03-07", "y": 2}',
    # '{"x": "2019-03-08", "y": 2}',
    # '{"x": "2019-03-09", "y": 13}']
    
    # key_time_freq = get_keyword_time_based_freq(queryset) # OK 使用 pandas 很方便
    # key_time_freq = get_keyword_time_based_freq_raw_sql(queryset) # OK 使用原生 SQL 整理時間次數資料也可以
    
    # 失敗
    key_time_freq = get_keyword_time_based_freq_with_orm(queryset)

    # (6) response all data to frontend home page
    response2 = {
    'key_occurrence_cat': key_occurrence_cat,
    'key_freq_cat': key_freq_cat,
    'key_time_freq': key_time_freq, 
    }
    
    # Combine dictionaries correctly
    combined_response = {**response1, **response2}
    return JsonResponse(combined_response)


# Searching keywords from "content" column
# This function now uses database queries instead of pandas
def filter_database_fullText(user_keywords, cond, cate, weeks):
# def filter_database_fullText_ORM(user_keywords, cond, cate, weeks):
    # Get the latest date in the database
    latest_date = NewsData.objects.aggregate(max_date=Max('date'))['max_date']
    
    # Calculate start date
    start_date = latest_date - timedelta(weeks=weeks)
    
    # Base query - filter by date range
    queryset = NewsData.objects.filter(date__gte=start_date, date__lte=latest_date)
    
    # Filter by category if not "全部"
    if cate != "全部":
        queryset = queryset.filter(category=cate)
    
    # Filter by keywords based on condition (AND or OR)
    if cond == 'and':
        # For AND condition, we need all keywords to be present
        for kw in user_keywords:
            queryset = queryset.filter(content__contains=kw)
    elif cond == 'or':
        # For OR condition, any keyword can be present
        q_objects = Q()
        for kw in user_keywords:
            q_objects |= Q(content__contains=kw)
        queryset = queryset.filter(q_objects)
    
    return queryset

'''
# 使用 Q 物件實現 AND 邏輯
q_objects = Q()
for kw in user_keywords:
    # 注意這裡使用 &= 而不是 |=，因為我們需要 AND 邏輯
    if q_objects == Q():  # 如果是第一個條件
        q_objects = Q(content__contains=kw)
    else:
        q_objects &= Q(content__contains=kw)
'''

'''
# 步驟 1：生成 q_list
q_list = [
    Q(content__contains="台積電"), 
    Q(content__contains="晶圓"), 
    Q(content__contains="半導體")
]

# 步驟 2：使用 reduce 組合
# 過程：
# 第一輪：Q(content__contains="台積電") & Q(content__contains="晶圓")
# 第二輪：結果 & Q(content__contains="半導體")
# 最終結果：Q(content__contains="台積電") & Q(content__contains="晶圓") & Q(content__contains="半導體")

final_q = reduce(and_, q_list)
queryset = queryset.filter(final_q)


and_ 和 and 的差別及使用原因
在 Python 中，and_ 和 and 有著根本性的差異，這就是為什麼在 reduce 函數中使用 and_ 而不是 and：

原因解釋
and 是 Python 關鍵字：

and 是 Python 的內置關鍵字運算符
它不能作為函數被傳遞給其他函數
它直接在表達式中使用：condition1 and condition2
and_ 是函數：

and_ 來自 operator 模組，是一個函數
它接受兩個參數並執行邏輯與操作：and_(a, b) 等價於 a & b
它可以作為參數傳遞給其他函數，例如 reduce

'''


def filter_database_fullText_SQL(user_keywords, cond, cate, weeks):
#def filter_database_fullText(user_keywords, cond, cate, weeks):
    from django.db import connection
    
    # Get the latest date using raw SQL
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT MAX(date) FROM {NewsData._meta.db_table}")
        latest_date_str = cursor.fetchone()[0]
        
        
    latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d').date()
    # Calculate start date
    start_date = latest_date - timedelta(weeks=weeks)
    
    # Format dates for SQL query (if necessary)
    start_date_str = start_date.strftime('%Y-%m-%d')
    latest_date_str = latest_date.strftime('%Y-%m-%d')
    
    # Build the base SQL query
    table_name = NewsData._meta.db_table
    params = [start_date_str, latest_date_str]
    
    sql = f"""
    SELECT item_id FROM {table_name}
    WHERE date >= %s AND date <= %s
    """
    
    # Add category filter if not "全部"
    if cate != "全部":
        sql += " AND category = %s"
        params.append(cate)
    
    # Add keyword filters based on condition
    if user_keywords:
        if cond == 'and':
            # For AND, add each keyword as a separate condition
            for kw in user_keywords:
                sql += " AND content LIKE %s"
                params.append(f'%{kw}%')
        elif cond == 'or':
            # For OR, combine all keywords with OR
            if user_keywords:
                sql += " AND ("
                or_conditions = []
                for kw in user_keywords:
                    or_conditions.append("content LIKE %s")
                    params.append(f'%{kw}%')
                sql += " OR ".join(or_conditions)
                sql += ")"
    
    # Execute the raw SQL query to get matching IDs
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        id_list = [row[0] for row in cursor.fetchall()]
    
    # Convert back to a queryset for compatibility with the rest of the code
    if id_list:
        queryset = NewsData.objects.filter(item_id__in=id_list)
    else:
        queryset = NewsData.objects.none()  # Empty queryset
    
    return queryset

# Get titles and links from k pieces of news
def get_title_link_topk(queryset, k=25):
    items = []
    # Limit to k results and get specific fields
    news_items = queryset.values('category', 'title', 'link', 'photo_link')[:k]
    
    for item in news_items:
        category = item['category']
        title = item['title']
        link = item['link'] or ''
        photo_link = item['photo_link'] or ''
        
        item_info = {
            'category': category,
            'title': title,
            'link': link,
            'photo_link': photo_link
        }
        
        items.append(item_info)
    return items


# Get related keywords by counting the top keywords of each news item
def get_related_word_clouddata(queryset):
    # Prepare counter for keywords
    counter = Counter()
    
    # Process each news item
    for news in queryset:
        if news.top_key_freq:
            try:
                # Convert the stored string representation to a dictionary
                pair_dict = dict(eval(news.top_key_freq))
                counter += Counter(pair_dict)
            except (SyntaxError, ValueError):
                # Skip if there's an error in the string format
                continue
    
    # Get the most common words
    wf_pairs = counter.most_common(20)
    
    # If no words found, return empty results
    if not wf_pairs:
        return [], []
    
    # Calculate cloud data
    min_ = wf_pairs[-1][1] if len(wf_pairs) > 0 else 0
    max_ = wf_pairs[0][1] if len(wf_pairs) > 0 else 0
    
    # Avoid division by zero
    if max_ == min_:
        clouddata = [{'text': w, 'size': 60} for w, f in wf_pairs]
    else:
        # Text size based on word frequency for drawing cloud chart
        textSizeMin = 20
        textSizeMax = 120
        # Scale the frequency value to a range from 20 to 120
        clouddata = [{'text': w, 'size': int(textSizeMin + (f - min_) / (max_ - min_) * (textSizeMax - textSizeMin))}
                    for w, f in wf_pairs]
    
    return wf_pairs, clouddata


# Split paragraphs in text
def cut_paragraph(text):
    if not text:
        return []
    
    paragraphs = text.split('。')  # 遇到句號就切開
    paragraphs = list(filter(None, paragraphs))
    return paragraphs


# Select all paragraphs where multiple keywords occur
def get_same_para(queryset, user_keywords, cond, k=30):
    same_para = []
    
    # Process each news item content
    for news in queryset:
        if not news.content:
            continue
            
        paragraphs = cut_paragraph(news.content)
        
        for para in paragraphs:
            para += "。"  # Add the period back
            
            if cond == 'and':
                if all([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
            elif cond == 'or':
                if any([re.search(kw, para) for kw in user_keywords]):
                    same_para.append(para)
                    
            # If we've got enough paragraphs, break out
            if len(same_para) >= k:
                break
                
    return same_para[:k]


# ** How many pieces of news were the keyword(s) mentioned in?
# ** How many times were the keyword(s) mentioned?

# For the query_df, count the occurence and frequency for each category.

# (1) cate_occurence={}  被多少篇新聞報導 How many pieces of news contain the keywords.
# (2) cate_freq={}       被提到多少次? How many times are the keywords mentioned

news_categories = ['政治', '政經', '全球','全部']

def count_keyword(queryset, query_keywords):

    cate_occurrence = {}
    cate_freq = {}
    
    # 字典初始化
    for cate in news_categories:
        cate_occurrence[cate] = 0   # {'政治':0, '科技':0}
        cate_freq[cate] = 0
        

    for row in queryset:
        # count the number of articles各類別篇數統計
        cate_occurrence[row.category] += 1  #   {'政治':+1, '科技':0}
        cate_occurrence['全部'] += 1
        
        # count the keyword frequency各類別次數統計
        # 計算這一篇文章的content中重複含有多少個這些關鍵字(頻率)
        freq = sum([ len(re.findall(keyword, row.content, re.I)) for keyword in query_keywords] ) 
        cate_freq[row.category] += freq # 在該新聞類別中累計頻率
        cate_freq['全部'] += freq  # 在"全部"類別中累計頻率

    return cate_freq, cate_occurrence


'''
# ORM Optimization:
Reduced Database Queries:
The ORM efficiently counts articles per category in a single query
This eliminates the need to increment counters for each row individually

Partial ORM Optimization:
Article counts per category are done using Django's values() and annotate(Count())
This moves aggregation work to the database

Limitation:
For keyword frequency counting, we still need Python processing
This is because complex regex pattern matching across multiple keywords can't be easily expressed in pure ORM/SQL
The improved code organizes articles by category first to reduce redundant category lookups

Further Improvements (Optional):
For databases that support regex functions (like PostgreSQL), you could potentially push more of the keyword counting to the database level using annotations, but this would be database-specific and complex. The current approach offers a good balance between optimization and readability.
'''
from django.db.models import Count, F, Func, Value, IntegerField, Sum
from django.db.models.functions import Coalesce

def count_keyword_with_orm(queryset, query_keywords):
    # Dictionary for all categories
    news_categories_with_all = news_categories.copy()
    
    # Count articles per category (occurrence)
    category_counts = queryset.values('category').annotate(count=Count('item_id'))
    
    # Initialize dictionaries with zeros
    cate_occurrence = {cate: 0 for cate in news_categories_with_all}
    cate_freq = {cate: 0 for cate in news_categories_with_all}
    
    # Fill occurrence counts from the query results
    total_count = 0
    for item in category_counts:
        category = item['category']
        count = item['count']
        cate_occurrence[category] = count
        total_count += count
    
    # Set the total count for all categories
    cate_occurrence['全部'] = total_count
    
    # For frequency counts, we need to use annotations for each keyword
    # This part still requires iterating through news items in Python
    # because regex-based counting across multiple keywords isn't easily
    # expressible in pure ORM
    
    # Group articles by category
    category_groups = {}
    for row in queryset:
        category = row.category
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(row)
    
    # Count frequencies by category
    total_freq = 0
    for category, articles in category_groups.items():
        category_freq = 0
        for article in articles:
            # Count keyword occurrences in each article
            freq = sum([len(re.findall(keyword, article.content, re.I)) for keyword in query_keywords])
            category_freq += freq
        
        cate_freq[category] = category_freq
        total_freq += category_freq
    
    # Set total frequency
    cate_freq['全部'] = total_freq
    
    return cate_freq, cate_occurrence

def get_keyword_time_based_freq(queryset):
    # Extract all dates from the queryset
    dates = list(queryset.values_list('date', flat=True))
    
    # Create DataFrame from the dates
    query_freq = pd.DataFrame({'date_index': pd.to_datetime(dates), 'freq': [1 for _ in range(len(dates))]})
    
    # Group by date and count occurrences
    data = query_freq.groupby(pd.Grouper(key='date_index', freq='D')).sum()
    
    # Format the data for the frontend
    time_data = []
    for i, idx in enumerate(data.index):
        row = {'x': idx.strftime('%Y-%m-%d'), 'y': int(data.iloc[i].freq)}
        time_data.append(row)
    
    return time_data



'''
Key Advantages of the ORM Approach:
Performance: The aggregation happens at the database level, which is much faster when dealing with large datasets
Memory Efficiency: You're not loading all dates into memory
Less Code: No need for the intermediate pandas DataFrame conversion
Additional Notes:
TruncDate truncates a datetime field to its date component, allowing you to group by day
You can use other truncation functions like TruncHour, TruncWeek, or TruncMonth for different time resolutions
This approach works with any SQL database supported by Django (PostgreSQL, MySQL, SQLite)
The ORM approach is generally preferred when working with Django applications, as it leverages the database's optimization capabilities and maintains consistency with your Django models.
'''
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.db.models.functions import Cast
from django.db.models import DateField

def get_keyword_time_based_freq_with_orm(queryset):

    # Use date string extraction (works on SQLite)
    # This uses Cast to convert date field to string in YYYY-MM-DD format
    date_counts = (
        queryset
        .annotate(day=Cast('date', DateField()))  # Extract just the date part
        .values('day')
        .annotate(count=Count('item_id'))
        .order_by('day')
    )
    
    time_data = []
    for item in date_counts:
        # Format may vary depending on database
        if isinstance(item['day'], str):
            date_str = item['day']
        else:
            date_str = item['day'].strftime('%Y-%m-%d') # Convert to string 
            
        row = {
            'x': date_str,
            'y': item['count']
        }
        time_data.append(row)
    
    return time_data

'''
Considerations When Using Raw SQL:
Database Portability: Raw SQL syntax varies between database backends (PostgreSQL, MySQL, SQLite)
Security: Be careful with SQL injection when constructing queries (use parameterized queries)
Maintainability: Raw SQL is harder to maintain than ORM code
Integration with Django: You lose some of Django's automatic handling of connections and transactions
When Raw SQL Might Be Better:
For highly complex queries that are difficult to express in ORM
When you need to use database-specific features or optimizations
When performance is critical and ORM overhead is a concern
'''
import sqlite3
from django.db import connections
import sqlite3
def get_keyword_time_based_freq_raw_sql(queryset):
    if not queryset.exists():
        return []
        
    table_name = NewsData._meta.db_table
    ids = tuple(queryset.values_list('item_id', flat=True))  # Convert to tuple
    
    # Handle empty queryset case
    if not ids:
        return []
    
    # Handle single item case
    if len(ids) == 1:
        ids = (ids[0],)  # Add comma to make it a tuple
    
    # Fix: Use correct SQL parameterization
    sql = f"""
    SELECT 
        date(date) as day,
        COUNT(*) as count
    FROM 
        {table_name}
    WHERE 
        item_id IN {ids}
    GROUP BY 
        date(date)
    ORDER BY 
        day
    """
    
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute(sql)  # No need to pass ids separately
            rows = cursor.fetchall()
        
        time_data = []
        for day, count in rows:
            row = {'x': day, 'y': count}
            time_data.append(row)
        return time_data
        
    except Exception as e:
        print(f"SQL Error: {e}")



# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment(request):

    userkey = request.POST['userkey']
    cate = request.POST['cate']
    cond = request.POST['cond']
    weeks = int(request.POST['weeks'])
    print(weeks)

    query_keywords = userkey.split()
    # Proceed filtering
    df_query = filter_database_fullText(query_keywords, cond, cate, weeks)
    
    # if df_query is empty, return an error message
    if len(df_query) == 0:
        return JsonResponse({'error': 'No results found for the given keywords.'})
    
    sentiCount, sentiPercnt = get_article_sentiment(df_query)

    if weeks <= 4:
        freq_type = 'D'
    else:
        freq_type = 'W'

    line_data_pos = get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type=freq_type)
    line_data_neg = get_daily_basis_sentiment_count(df_query, sentiment_type='neg', freq_type=freq_type)

    response = {
        'sentiCount': sentiCount,
        'data_pos':line_data_pos,
        'data_neg':line_data_neg,
    }
    return JsonResponse(response)

def get_article_sentiment(df_query):
    sentiCount = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiPercnt = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    numberOfArticle = len(df_query)
    for senti in df_query.sentiment:
        # determine sentimental polarity
        if float(senti) >= 0.6:
            sentiCount['Positive'] += 1
        elif float(senti) <= 0.4:
            sentiCount['Negative'] += 1
        else:
            sentiCount['Neutral'] += 1
    for polar in sentiCount :
        try:
            sentiPercnt[polar]=int(sentiCount[polar]/numberOfArticle*100)
        except:
            sentiPercnt[polar] = 0 # 若分母 numberOfArticle=0會報錯
    return sentiCount, sentiPercnt


def get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type='D'):

    # 自訂正負向中立的標準，sentiment score是機率值，介於0~1之間
    # Using lambda to determine if an article is postive or not.
    if sentiment_type == 'pos':
        lambda_function = lambda senti: 1 if senti >= 0.6 else 0 #大於0.6為正向 
    elif sentiment_type == 'neg':
        lambda_function = lambda senti: 1 if senti <= 0.4 else 0 #小於0.4為負向
    elif sentiment_type == 'neutral':
        lambda_function = lambda senti: 1 if senti > 0.4 & senti < 0.4 else 0 #介於中間為中立
    else:
        return None 
        
    freq_df = pd.DataFrame({'date_index': pd.to_datetime(df_query.date),
                             'frequency': [lambda_function(senti) for senti in df_query.sentiment]})
    # Group rows by the date to the daily number of articles. 加總合併同一天新聞，篇數就被計算好了
    freq_df_group = freq_df.groupby(pd.Grouper(key='date_index',freq=freq_type)).sum()
    
    # 'date_index'為index(索引)，將其變成欄位名稱，inplace=True表示原始檔案會被異動
    freq_df_group.reset_index(inplace=True)
    
    # x,y，用於畫趨勢線圖
    xy_line_data = [{'x':date.strftime('%Y-%m-%d'),'y':freq} for date, freq in zip(freq_df_group.date_index,freq_df_group.frequency)]
    return xy_line_data


print("app_user_keyword_association (DB version) was loaded!")
