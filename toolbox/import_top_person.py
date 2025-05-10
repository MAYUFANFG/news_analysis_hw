#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import logging
import pathlib
from django.db import transaction

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("import_top_person.log"),
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
from app_top_person_db.models import TopPerson


def import_top_person_data(csv_file_path):
    """從CSV檔案匯入熱門人物資料到TopPerson模型"""
    try:
        logging.info(f"開始讀取CSV檔案: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        logging.info(f"CSV檔案總行數: {len(df)}")

        success_count = 0
        error_count = 0

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # 取得資料
                    category = row['category']
                    top_keys = row['top_keys']

                    # 檢查必要欄位
                    if pd.isna(category) or pd.isna(top_keys):
                        logging.error(f"第 {idx} 行缺少必要欄位")
                        error_count += 1
                        continue

                    # 建立或更新TopPerson物件
                    top_person, created = TopPerson.objects.update_or_create(
                        category=category,
                        defaults={
                            'top_keys': top_keys
                        }
                    )

                    if created:
                        logging.info(f"建立新的TopPerson物件，類別: {category}")
                    else:
                        logging.info(f"更新現有的TopPerson物件，類別: {category}")

                    success_count += 1

                except Exception as e:
                    logging.error(f"處理第 {idx} 行時發生錯誤: {e}")
                    error_count += 1

        logging.info(f"匯入完成，成功: {success_count}，失敗: {error_count}")

    except Exception as e:
        logging.error(f"匯入過程中發生錯誤: {e}")


if __name__ == "__main__":
    # 構建絕對路徑
    csv_file_path = os.path.join(script_dir, '..', 'app_top_person', 'dataset', 'top_person_data.csv')

    # 檢查檔案是否存在
    if os.path.exists(csv_file_path):
        import_top_person_data(csv_file_path)
    else:
        logging.error(f"無法找到CSV檔案: {csv_file_path}")