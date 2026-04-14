import os
import json
import sqlite3
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# 讀取 .env 檔案中的環境變數
load_dotenv()
API_KEY = os.getenv("CWA_API_KEY")

DB_NAME = "data.db"

# ==========================================
# HW2-1 & HW2-2: 獲取與分析天氣預報資料
# ==========================================
def fetch_and_parse_weather_data():
    """從 CWA API 獲取資料並解析出最高與最低氣溫"""
    # F-C0032-001: 一般天氣預報-今明36小時天氣預報 (全台22縣市)
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}"
    
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        raw_data = response.json()
        
        # 觀察獲得的資料 (HW2-1 評分要求)
        # print(json.dumps(raw_data, indent=2, ensure_ascii=False))
        
        parsed_data = []
        
        # 將22個縣市對應到大地區分類
        region_mapping = {
            "臺北市": "北部地區", "新北市": "北部地區", "桃園市": "北部地區",
            "基隆市": "北部地區", "新竹市": "北部地區", "新竹縣": "北部地區",
            "臺中市": "中部地區", "彰化縣": "中部地區", "南投縣": "中部地區",
            "苗栗縣": "中部地區", "雲林縣": "中部地區",
            "臺南市": "南部地區", "高雄市": "南部地區", "屏東縣": "南部地區",
            "嘉義市": "南部地區", "嘉義縣": "南部地區",
            "宜蘭縣": "東部地區", "花蓮縣": "東部地區", "臺東縣": "東部地區",
            "金門縣": "離島地區", "澎湖縣": "離島地區", "連江縣": "離島地區",
        }
        
        locations = raw_data['records']['location']
        
        for loc in locations:
            city_name = loc['locationName']
            region_name = region_mapping.get(city_name, "其他地區")
            
            if region_name == "其他地區":
                continue
                
            weather_elements = loc['weatherElement']
            
            # 尋找 MinT (最低溫) 和 MaxT (最高溫)
            min_t_data = next(item for item in weather_elements if item["elementName"] == "MinT")["time"]
            max_t_data = next(item for item in weather_elements if item["elementName"] == "MaxT")["time"]
            
            for i in range(len(min_t_data)):
                # 提取日期 (只取 YYYY-MM-DD 部分)
                data_date = min_t_data[i]["startTime"].split(" ")[0]
                min_t_val = int(min_t_data[i]["parameter"]["parameterName"])
                max_t_val = int(max_t_data[i]["parameter"]["parameterName"])
                
                parsed_data.append({
                    "regionName": region_name,
                    "dataDate": data_date,
                    "MinT": min_t_val,
                    "MaxT": max_t_val
                })
        
        # HW2-2 評分要求：觀察提取的資料
        # print(json.dumps(parsed_data[:5], indent=2, ensure_ascii=False))
        
        return parsed_data
    except Exception as e:
        st.error(f"資料獲取或解析失敗: {e}")
        return []

# ==========================================
# HW2-3: 將氣溫資料儲存到 SQLite3 資料庫
# ==========================================
def init_db(data):
    """建立資料庫、Table 並寫入資料"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 創建 Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT,
            dataDate TEXT,
            MinT INTEGER,
            MaxT INTEGER
        )
    ''')
    
    # 檢查是否已有資料，若無則寫入 (避免重複執行時重複寫入)
    cursor.execute("SELECT COUNT(*) FROM TemperatureForecasts")
    if cursor.fetchone()[0] == 0 and data:
        # 為了避免同地區同日期重複，先用 Pandas 進行分區平均或去重
        df = pd.DataFrame(data)
        # 將同地區、同日期的氣溫做平均 (因為前面把多個縣市歸類到同一個大區)
        grouped_df = df.groupby(['regionName', 'dataDate']).mean().astype(int).reset_index()
        
        for _, row in grouped_df.iterrows():
            cursor.execute('''
                INSERT INTO TemperatureForecasts (regionName, dataDate, MinT, MaxT)
                VALUES (?, ?, ?, ?)
            ''', (row['regionName'], row['dataDate'], row['MinT'], row['MaxT']))
        
        conn.commit()
    
    # 檢查測試查詢 (HW2-3 評分要求)
    # print("所有地區:", cursor.execute("SELECT DISTINCT regionName FROM TemperatureForecasts").fetchall())
    # print("中部地區資料:", cursor.execute("SELECT * FROM TemperatureForecasts WHERE regionName='中部地區'").fetchall())
    
    conn.close()

# ==========================================
# HW2-4: 實作氣溫預報 Web App (Streamlit)
# ==========================================
def main():
    # 1. 系統初始化：拉取資料並建置資料庫
    if not os.path.exists(DB_NAME):
        with st.spinner('正在從 CWA API 獲取天氣資料並建立資料庫...'):
            weather_data = fetch_and_parse_weather_data()
            init_db(weather_data)
            
    # 2. 建立資料庫連線
    conn = sqlite3.connect(DB_NAME)
    
    st.title("Temperature Forecast Web App")
    
    # 查詢所有可用的地區名稱以供下拉選單使用
    regions_df = pd.read_sql_query("SELECT DISTINCT regionName FROM TemperatureForecasts", conn)
    regions = regions_df['regionName'].tolist()
    
    if not regions:
        st.warning("資料庫中沒有地區資料，請檢查 API 金鑰或連線狀態。")
        return

    # 下拉選單 (Select a Region)
    selected_region = st.selectbox("Select a Region", regions)
    
    if selected_region:
        # 從資料庫查詢選定地區的資料
        query = f"SELECT dataDate, MinT, MaxT FROM TemperatureForecasts WHERE regionName = '{selected_region}'"
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.markdown(f"### Temperature Trends for {selected_region}")
            
            # 設定折線圖的 X 軸為 dataDate，符合截圖規格
            chart_data = df.set_index('dataDate')
            st.line_chart(chart_data[['MinT', 'MaxT']])
            
            st.markdown(f"### Temperature Data for {selected_region}")
            # 顯示資料表
            st.dataframe(df, use_container_width=True)
        else:
            st.info("該地區目前沒有資料。")
            
    conn.close()

if __name__ == "__main__":
    main()
