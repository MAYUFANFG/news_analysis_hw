import os
import sys
import pandas as pd
import logging
from datetime import datetime
import pathlib
from django.db import transaction

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("import_news_data.log"),
        logging.StreamHandler()
    ]
)

# 獲取腳本所在的目錄
script_dir = os.path.dirname(os.path.abspath(__file__))

# 將上一層目錄加入 sys.path
parent_path = pathlib.Path(script_dir).parent
sys.path.insert(0, str(parent_path))

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django

django.setup()
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# 導入 Django 模型
from app_user_keyword_db.models import NewsData


def validate_row(row):
    """驗證資料列的必要欄位"""
    required_fields = ['item_id', 'date', 'category', 'title', 'content', 'sentiment']
    for field in required_fields:
        if field not in row or pd.isna(row[field]):
            return False, f"缺少必要欄位: {field}"

    try:
        datetime.strptime(row['date'], '%Y-%m-%d')
    except ValueError:
        return False, f"日期格式不正確: {row['date']}"

    return True, ""


def import_news_data(csv_file_path):
    """從CSV檔案匯入新聞資料"""
    try:
        logging.info(f"開始讀取CSV檔案: {csv_file_path}")
        df = pd.read_csv(csv_file_path, sep='|')
        logging.info(f"CSV檔案總行數: {len(df)}")

        success_count = 0
        error_count = 0

        for idx, row in df.iterrows():
            try:
                # 驗證資料
                is_valid, error_msg = validate_row(row)
                if not is_valid:
                    logging.error(f"資料驗證失敗 (第 {idx} 行): {error_msg}")
                    error_count += 1
                    continue

                # 轉換日期
                date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()

                # 建立或更新 NewsData 物件
                news_data, created = NewsData.objects.update_or_create(
                    item_id=row['item_id'],
                    defaults={
                        'date': date_obj,
                        'category': row['category'],
                        'title': row['title'],
                        'content': row['content'],
                        'sentiment': row['sentiment'],
                        'top_key_freq': row.get('top_key_freq', ''),
                        'tokens': row.get('tokens', ''),
                        'tokens_v2': row.get('tokens_v2', ''),
                        'entities': row.get('entities', ''),
                        'token_pos': row.get('token_pos', ''),
                        'link': row.get('link', ''),
                        'photo_link': row.get('photo_link', '') if row.get('photo_link', '') and not pd.isna(
                            row.get('photo_link', '')) else None,
                    }
                )

                if created:
                    logging.info(f"建立新的 NewsData 物件，item_id: {row['item_id']}")
                else:
                    logging.info(f"更新現有的 NewsData 物件，item_id: {row['item_id']}")

                success_count += 1

            except Exception as e:
                logging.error(f"處理第 {idx} 行時發生錯誤: {e}")
                error_count += 1

        logging.info(f"匯入完成，成功: {success_count}，失敗: {error_count}")

    except Exception as e:
        logging.error(f"匯入過程中發生錯誤: {e}")


if __name__ == "__main__":
    # 構建絕對路徑
    csv_file_path = os.path.join(script_dir, '..', 'app_user_keyword', 'dataset', 'sentiment_20250428_reindexed.csv')


    # 檢查檔案是否存在
    if os.path.exists(csv_file_path):
        import_news_data(csv_file_path)
    else:
        logging.error("無法找到任何CSV檔案")