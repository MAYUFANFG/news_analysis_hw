import pandas as pd
import os
from datetime import datetime


def reindex_csv_file(input_file, output_file=None, id_column='item_id', preserve_category=True):
    """
    重新索引 CSV 檔案中的 item_id，避免重複 ID

    參數:
    input_file (str): 輸入 CSV 檔案路徑
    output_file (str, optional): 輸出 CSV 檔案路徑，如果未提供，會自動生成
    id_column (str): ID 欄位名稱，預設為 'item_id'
    preserve_category (bool): 是否保留 ID 中的類別資訊，預設為 True

    返回:
    str: 輸出 CSV 檔案路徑
    """
    try:
        # 讀取 CSV 檔案
        print(f"正在讀取檔案: {input_file}")
        df = pd.read_csv(input_file, sep='|')
        original_count = len(df)
        print(f"原始檔案記錄數: {original_count}")

        # 檢查 ID 欄位是否存在
        if id_column not in df.columns:
            raise ValueError(f"找不到 {id_column} 欄位")

        # 檢查類別欄位是否存在
        has_category = 'category' in df.columns
        if preserve_category and not has_category:
            print("警告: 無法保留類別資訊，因為找不到 'category' 欄位")
            preserve_category = False

        # 儲存原始 ID 和類別對應
        original_ids = df[id_column].tolist()

        # 創建新的 ID
        if preserve_category and has_category:
            # 獲取所有唯一類別
            categories = df['category'].unique()
            category_index = {cat: 1 for cat in categories}

            # 創建新 ID 的函數
            def create_new_id(row):
                cat = row['category']
                cat_prefix = cat[:3].lower()  # 取類別前三個字元作為前綴
                new_id = f"{cat_prefix}_{datetime.now().strftime('%Y%m%d')}_{category_index[cat]}"
                category_index[cat] += 1
                return new_id

            # 應用函數創建新 ID
            df[id_column] = df.apply(create_new_id, axis=1)
        else:
            # 簡單的數字 ID
            df[id_column] = [f"item_{i + 1}" for i in range(len(df))]

        # 創建 ID 映射表
        id_mapping = dict(zip(original_ids, df[id_column]))

        # 如果未提供輸出檔案名稱，則自動生成
        if output_file is None:
            file_dir = os.path.dirname(input_file)
            file_name = os.path.basename(input_file)
            name, ext = os.path.splitext(file_name)
            output_file = os.path.join(file_dir, f"{name}_reindexed{ext}")

        # 寫入結果
        df.to_csv(output_file, sep='|', index=False)
        print(f"已將重新索引的檔案寫入: {output_file}")
        print(f"共處理 {len(df)} 筆記錄")

        # 保存 ID 映射表
        mapping_file = os.path.splitext(output_file)[0] + "_id_mapping.csv"
        mapping_df = pd.DataFrame({
            'original_id': original_ids,
            'new_id': [id_mapping[id] for id in original_ids]
        })
        mapping_df.to_csv(mapping_file, index=False)
        print(f"ID 映射表已保存至: {mapping_file}")

        return output_file

    except Exception as e:
        print(f"發生錯誤: {e}")
        return None


def check_id_duplicates(file_path, id_column='item_id'):
    """
    檢查 CSV 檔案中是否有重複的 ID

    參數:
    file_path (str): CSV 檔案路徑
    id_column (str): ID 欄位名稱，預設為 'item_id'

    返回:
    bool: 如果有重複則返回 True，否則返回 False
    """
    try:
        df = pd.read_csv(file_path, sep='|')
        duplicates = df[id_column].duplicated().any()

        if duplicates:
            dup_ids = df[df[id_column].duplicated(keep=False)][id_column].unique()
            print(f"發現重複的 ID: {dup_ids}")
            print(f"共有 {len(dup_ids)} 個不同的 ID 有重複")
        else:
            print("沒有發現重複的 ID")

        return duplicates

    except Exception as e:
        print(f"檢查重複 ID 時發生錯誤: {e}")
        return None


# 直接執行部分 - 使用預設值
if __name__ == "__main__":
    # 設定檔案路徑 - 請修改為您的實際路徑
    input_file = 'D:\\bigdata\\hw\\news_analysis_hw\\news_analysis_hw\\app_user_keyword\\dataset\\sentiment_20250428.csv'

    # 檢查是否有重複 ID
    print("檢查檔案中是否有重複的 ID...")
    has_duplicates = check_id_duplicates(input_file)

    # 如果有重複，進行重新索引
    if has_duplicates:
        print("發現重複 ID，開始進行重新索引...")
        # 自動生成輸出檔案名稱
        output_file = None  # 讓函數自動生成

        # 執行重新索引
        reindex_csv_file(
            input_file=input_file,
            output_file=output_file,
            id_column='item_id',
            preserve_category=True
        )
    else:
        print("檔案中沒有重複的 ID，無需重新索引。")