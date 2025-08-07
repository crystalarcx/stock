import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import time

# 設定頁面配置
st.set_page_config(
    page_title="股票投資組合 Dashboard",
    page_icon="📊",
    layout="wide"
)

# CSS 樣式設定
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .profit {
        color: #1f77b4 !important;
    }
    .loss {
        color: #d62728 !important;
    }
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 標題
st.title("📊 股票投資組合 Dashboard")
st.markdown("---")

# 快取函數來讀取 CSV 數據
@st.cache_data(ttl=60)  # 每60秒更新一次
def load_data():
    """讀取 Google Sheets CSV 數據"""
    try:
        csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ0ZOzpAWlnoXgbD8B58PYwbIDuLdKTHgKDYRFVD8CVmzox5iYfSuCpgx7FA5zyWncKhXvOegdlT7SM/pub?gid=1810241786&single=true&output=csv"
        df = pd.read_csv(csv_url)
        
        # 清理資料欄位名稱（去除空白）
        df.columns = df.columns.str.strip()
        
        # 假設的欄位名稱，請根據你的實際欄位名稱調整
        # 常見的欄位名稱：股票代號, 股票名稱, 持股數量, 成本價, 現價, 市值, 盈虧金額, 盈虧比例
        
        return df
    except Exception as e:
        st.error(f"無法讀取數據: {str(e)}")
        # 返回示例數據以供測試
        return create_sample_data()

def create_sample_data():
    """創建示例數據供測試使用"""
    sample_data = {
        '股票代號': ['2330', '2317', '2454', '3008', '2412', '2382'],
        '股票名稱': ['台積電', '鴻海', '聯發科', '大立光', '中華電', '廣達'],
        '持股數量': [100, 200, 50, 30, 150, 80],
        '成本價': [520, 95, 800, 2500, 120, 180],
        '現價': [580, 102, 750, 2800, 125, 190],
        '市值': [58000, 20400, 37500, 84000, 18750, 15200],
        '盈虧金額': [6000, 1400, -2500, 9000, 750, 800],
        '盈虧比例': [11.54, 7.37, -6.25, 12.0, 4.17, 5.56]
    }
    return pd.DataFrame(sample_data)

# 載入數據
df = load_data()

# 自動重新整理
if st.button("🔄 重新整理數據"):
    st.cache_data.clear()
    st.rerun()

# 顯示最後更新時間
st.markdown(f"**最後更新時間:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 檢查數據是否載入成功
if df is not None and not df.empty:
    # 數據處理
    # 確保數值欄位為數字格式
    numeric_columns = ['持股數量', '成本價', '現價', '市值', '盈虧金額', '盈虧比例']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 計算總體統計
    total_market_value = df['市值'].sum() if '市值' in df.columns else 0
    total_profit_loss = df['盈虧金額'].sum() if '盈虧金額' in df.columns else 0
    total_return_rate = (total_profit_loss / (total_market_value - total_profit_loss)) * 100 if total_market_value != total_profit_loss else 0
    
    # 獲利和虧損股票數量
    profit_stocks = len(df[df['盈虧金額'] > 0]) if '盈虧金額' in df.columns else 0
    loss_stocks = len(df[df['盈虧金額'] < 0]) if '盈虧金額' in df.columns else 0
    
    # 顯示總體摘要
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 總市值",
            value=f"NT$ {total_market_value:,.0f}",
            delta=None
        )
    
    with col2:
        profit_loss_color = "normal" if total_profit_loss >= 0 else "inverse"
        st.metric(
            label="📈 總盈虧",
            value=f"NT$ {total_profit_loss:,.0f}",
            delta=f"{total_return_rate:.2f}%",
            delta_color=profit_loss_color
        )
    
    with col3:
        st.metric(
            label="📊 獲利檔數",
            value=f"{profit_stocks} 檔",
            delta=None
        )
    
    with col4:
        st.metric(
            label="📉 虧損檔數",
            value=f"{loss_stocks} 檔",
            delta=None
        )
    
    st.markdown("---")
    
    # 創建兩個欄位用於圖表和表格
    chart_col, table_col = st.columns([1, 1])
    
    with chart_col:
        st.subheader("📊 投資組合分佈")
        
        # 圓餅圖 - 市值分佈
        if '股票名稱' in df.columns and '市值' in df.columns:
            fig_pie = px.pie(
                df, 
                values='市值', 
                names='股票名稱',
                title="市值分佈",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with table_col:
        st.subheader("💹 盈虧分析")
        
        # 長條圖 - 盈虧金額
        if '股票名稱' in df.columns and '盈虧金額' in df.columns:
            # 為盈虧設定顏色
            colors = ['blue' if x >= 0 else 'red' for x in df['盈虧金額']]
            
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=df['股票名稱'],
                    y=df['盈虧金額'],
                    marker_color=colors,
                    text=df['盈虧金額'],
                    textposition='auto',
                )
            ])
            
            fig_bar.update_layout(
                title="個股盈虧金額",
                xaxis_title="股票",
                yaxis_title="盈虧金額 (NT$)",
                showlegend=False
            )
            
            fig_bar.update_xaxis(tickangle=45)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # 詳細持股表格
    st.subheader("📋 詳細持股資訊")
    
    # 準備顯示用的 DataFrame
    display_df = df.copy()
    
    # 格式化數字欄位
    if '市值' in display_df.columns:
        display_df['市值'] = display_df['市值'].apply(lambda x: f"NT$ {x:,.0f}")
    if '盈虧金額' in display_df.columns:
        display_df['盈虧金額'] = display_df['盈虧金額'].apply(lambda x: f"NT$ {x:,.0f}")
    if '盈虧比例' in display_df.columns:
        display_df['盈虧比例'] = display_df['盈虧比例'].apply(lambda x: f"{x:.2f}%")
    if '成本價' in display_df.columns:
        display_df['成本價'] = display_df['成本價'].apply(lambda x: f"NT$ {x:.2f}")
    if '現價' in display_df.columns:
        display_df['現價'] = display_df['現價'].apply(lambda x: f"NT$ {x:.2f}")
    
    # 使用 styler 來設定顏色
    def color_profit_loss(val):
        """根據盈虧設定顏色"""
        if 'NT$' in str(val):
            # 提取數字部分
            num_str = str(val).replace('NT$ ', '').replace(',', '')
            try:
                num = float(num_str)
                if num > 0:
                    return 'color: blue; font-weight: bold'
                elif num < 0:
                    return 'color: red; font-weight: bold'
            except:
                pass
        elif '%' in str(val):
            try:
                num = float(str(val).replace('%', ''))
                if num > 0:
                    return 'color: blue; font-weight: bold'
                elif num < 0:
                    return 'color: red; font-weight: bold'
            except:
                pass
        return ''
    
    # 套用樣式
    if '盈虧金額' in display_df.columns and '盈虧比例' in display_df.columns:
        styled_df = display_df.style.applymap(
            color_profit_loss, 
            subset=['盈虧金額', '盈虧比例']
        )
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(display_df, use_container_width=True)
    
    # 績效分析
    st.markdown("---")
    st.subheader("📈 績效分析")
    
    perf_col1, perf_col2 = st.columns(2)
    
    with perf_col1:
        if '盈虧比例' in df.columns:
            avg_return = df['盈虧比例'].mean()
            max_gain = df['盈虧比例'].max()
            max_loss = df['盈虧比例'].min()
            
            st.metric("平均報酬率", f"{avg_return:.2f}%")
            st.metric("最大獲利", f"{max_gain:.2f}%")
            st.metric("最大虧損", f"{max_loss:.2f}%")
    
    with perf_col2:
        if '市值' in df.columns:
            # 找出最大和最小持股
            max_holding = df.loc[df['市值'].idxmax(), '股票名稱'] if '股票名稱' in df.columns else "未知"
            min_holding = df.loc[df['市值'].idxmin(), '股票名稱'] if '股票名稱' in df.columns else "未知"
            
            st.info(f"📊 **最大持股:** {max_holding}")
            st.info(f"📊 **最小持股:** {min_holding}")
            st.info(f"📊 **持股檔數:** {len(df)} 檔")

else:
    st.error("❌ 無法載入數據，請檢查 CSV 連結是否正確或網路連線是否正常。")
    
    # 顯示 CSV URL 供檢查
    st.info("📋 **CSV URL:** https://docs.google.com/spreadsheets/d/e/2PACX-1vQ0ZOzpAWlnoXgbD8B58PYwbIDuLdKTHgKDYRFVD8CVmzox5iYfSuCpgx7FA5zyWncKhXvOegdlT7SM/pub?gid=1810241786&single=true&output=csv")

# 頁腳
st.markdown("---")
st.markdown("📊 **股票投資組合 Dashboard** | 資料來源: Google Sheets | 即時更新")

# 自動重新整理選項
if st.sidebar.checkbox("🔄 自動重新整理 (每30秒)"):
    time.sleep(30)
    st.rerun()