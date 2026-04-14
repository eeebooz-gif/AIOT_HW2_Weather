import os
import json
import sqlite3
import requests
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv

# 讀取 .env 檔案中的環境變數
load_dotenv()
API_KEY = os.getenv("CWA_API_KEY")

DB_NAME = "data.db"

# ==========================================
# 準備台灣各區域的概略經緯度字典
# ==========================================
REGION_COORDS = {
    "北部地區": [25.0330, 121.5654],
    "中部地區": [24.1477, 120.6736],
    "南部地區": [22.6273, 120.3014],
    "東北部地區": [24.7562, 121.7588],
    "東部地區": [23.9872, 121.6012],
    "東南部地區": [22.7583, 121.1444],
    "離島地區": [23.5711, 119.5848]
}

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
    needs_fetch = True
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM TemperatureForecasts")
            if cursor.fetchone()[0] > 0:
                needs_fetch = False
            conn.close()
        except Exception:
            pass

    if needs_fetch:
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
            # 建立三個 Tabs：一個放折線圖，一個放地圖，一個放表格
            tab1, tab2, tab3 = st.tabs(["📈 氣溫趨勢圖", "🗺️ 全台今日氣溫地圖", "📋 詳細資料表"])
            
            with tab1:
                st.markdown(f"### {selected_region} 未來一週氣溫趨勢")
                # 這裡可以放你原本的 st.line_chart 或剛才升級的 plotly 圖表
                chart_data = df.set_index('dataDate')
                st.line_chart(chart_data[['MinT', 'MaxT']])
                
            with tab2:
                st.markdown("### 🗺️ 今日全台氣象預報概況")
                # 抓取資料庫裡面的「第一天 (通常是今天)」來畫全台地圖
                first_date = pd.read_sql_query("SELECT MIN(dataDate) FROM TemperatureForecasts", conn).iloc[0, 0]
                map_df = pd.read_sql_query(f"SELECT regionName, MinT, MaxT FROM TemperatureForecasts WHERE dataDate = '{first_date}'", conn)
                
                # 建立 Folium 地圖，中心點設定在台灣中心 (南投附近)
                m = folium.Map(location=[23.6978, 120.9605], zoom_start=7, tiles="CartoDB positron")
                
                # 把各個地區的氣溫圖釘加到地圖上
                for _, row in map_df.iterrows():
                    r_name = row['regionName']
                    if r_name in REGION_COORDS:
                        # 設定圖釘彈出視窗的內容
                        popup_html = f"<b>{r_name}</b><br>最高溫: {row['MaxT']}°C<br>最低溫: {row['MinT']}°C"
                        
                        folium.Marker(
                            location=REGION_COORDS[r_name],
                            popup=folium.Popup(popup_html, max_width=200),
                            tooltip=f"{r_name} (點擊查看氣溫)",
                            icon=folium.Icon(color="blue", icon="info-sign")
                        ).add_to(m)
                
                # 將 Folium 地圖渲染到 Streamlit 上
                st_folium(m, width=700, height=500)
                
            with tab3:
                st.markdown(f"### {selected_region} 原始預報資料")
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("該地區目前沒有資料。")
            
    conn.close()

if __name__ == "__main__":
    main()
