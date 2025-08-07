import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime
import time

# 設置頁面配置
st.set_page_config(
    page_title="定期定額投資儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS 樣式
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    text-align: center;
    color: #1f77b4;
    margin-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 0.5rem 0;
}

.success-text {
    color: #1f77b4;
    font-weight: bold;
}

.warning-text {
    color: #ff8c00;
    font-weight: bold;
}

.error-text {
    color: #ff4444;
    font-weight: bold;
}

.info-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
}

.investment-summary {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 15px;
    border-left: 5px solid #007bff;
    margin: 1rem 0;
}

.stDataFrame {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # 緩存5分鐘
def load_investment_data(csv_url):
    """載入定期定額投資資料"""
    try:
        # 設定請求標頭
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 使用 requests 獲取資料
        response = requests.get(csv_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 使用 StringIO 處理 CSV 資料
        from io import StringIO
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        # 清理欄位名稱
        df.columns = df.columns.str.strip()
        
        # 移除空白行
        df = df.dropna(how='all')
        df = df[df.iloc[:, 0].notna() & df.iloc[:, 1].notna()]  # 確保股票代號和名稱不為空
        
        # 標準化欄位名稱
        expected_columns = ['股票代號', '股票名稱', '每月投入金額', '扣款日', '券商折扣']
        if len(df.columns) >= len(expected_columns):
            df.columns = expected_columns[:len(df.columns)]
        
        # 確保數值欄位是數字格式
        if '每月投入金額' in df.columns:
            df['每月投入金額'] = pd.to_numeric(df['每月投入金額'], errors='coerce').fillna(0)
        
        if '扣款日' in df.columns:
            df['扣款日'] = pd.to_numeric(df['扣款日'], errors='coerce').fillna(0)
        
        if '券商折扣' in df.columns:
            df['券商折扣'] = pd.to_numeric(df['券商折扣'], errors='coerce').fillna(0)
        
        # 計算衍生欄位
        df['年度投入金額'] = df['每月投入金額'] * 12
        df['預估年度手續費'] = (df['券商折扣'] / 100) * df['年度投入金額']
        
        return df
        
    except requests.exceptions.RequestException as e:
        st.error(f"網路請求失敗: {str(e)}")
        return None
    except pd.errors.EmptyDataError:
        st.error("CSV 檔案是空的")
        return None
    except Exception as e:
        st.error(f"資料載入失敗: {str(e)}")
        return None

def format_currency(amount):
    """格式化貨幣顯示"""
    if pd.isna(amount) or amount == 0:
        return "NT$0"
    
    if abs(amount) >= 1_000_000:
        return f"NT${amount/1_000_000:.1f}M"
    elif abs(amount) >= 1_000:
        return f"NT${amount/1_000:.1f}K"
    else:
        return f"NT${amount:,.0f}"

def calculate_investment_summary(df):
    """計算投資摘要"""
    if df is None or df.empty:
        return {}
    
    summary = {}
    summary['總股票數'] = len(df)
    summary['每月總投入'] = df['每月投入金額'].sum()
    summary['年度總投入'] = df['年度投入金額'].sum()
    summary['平均券商折扣'] = df['券商折扣'].mean()
    summary['總預估手續費'] = df['預估年度手續費'].sum()
    
    # 計算與一般手續費的比較
    standard_fee = 0.1425  # 一般手續費 0.1425%
    if summary['平均券商折扣'] > 0:
        summary['手續費節省'] = ((standard_fee - summary['平均券商折扣']) / 100) * summary['年度總投入']
    else:
        summary['手續費節省'] = 0
    
    return summary

def create_monthly_investment_chart(df):
    """創建每月投入金額圖表"""
    if df is None or df.empty:
        return None
    
    # 準備圖表資料
    chart_data = df[df['每月投入金額'] > 0].copy()
    if chart_data.empty:
        return None
    
    # 創建長條圖
    fig = px.bar(
        chart_data,
        x='股票名稱',
        y='每月投入金額',
        title="每月投入金額分析",
        color='每月投入金額',
        color_continuous_scale='Blues',
        text='每月投入金額'
    )
    
    fig.update_traces(
        texttemplate='NT$%{text:,.0f}',
        textposition='outside'
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        xaxis_title="投資標的",
        yaxis_title="每月投入金額 (NT$)",
        font=dict(size=12)
    )
    
    return fig

def create_portfolio_pie_chart(df):
    """創建投資組合配置圓餅圖"""
    if df is None or df.empty:
        return None
    
    # 準備資料
    chart_data = df[df['每月投入金額'] > 0].copy()
    if chart_data.empty:
        return None
    
    # 創建圓餅圖
    fig = px.pie(
        chart_data,
        values='每月投入金額',
        names='股票名稱',
        title="投資組合配置比例"
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>金額: NT$%{value:,.0f}<br>比例: %{percent}<extra></extra>'
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_fee_comparison_chart(df):
    """創建手續費比較圖表"""
    if df is None or df.empty:
        return None
    
    standard_fee = 0.1425
    
    comparison_data = []
    for _, row in df.iterrows():
        if row['每月投入金額'] > 0:
            annual_amount = row['年度投入金額']
            standard_cost = (standard_fee / 100) * annual_amount
            discount_cost = (row['券商折扣'] / 100) * annual_amount
            
            comparison_data.append({
                '股票名稱': row['股票名稱'],
                '一般手續費': standard_cost,
                '優惠手續費': discount_cost
            })
    
    if not comparison_data:
        return None
    
    comparison_df = pd.DataFrame(comparison_data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='一般手續費',
        x=comparison_df['股票名稱'],
        y=comparison_df['一般手續費'],
        marker_color='lightcoral'
    ))
    
    fig.add_trace(go.Bar(
        name='優惠手續費',
        x=comparison_df['股票名稱'],
        y=comparison_df['優惠手續費'],
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title="年度手續費比較",
        xaxis_title="投資標的",
        yaxis_title="手續費 (NT$)",
        barmode='group',
        height=400
    )
    
    return fig

# 主程式
def main():
    # 頁面標題
    st.markdown('<h1 class="main-header">📊 定期定額投資儀表板</h1>', unsafe_allow_html=True)
    
    # CSV URL
    CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ0ZOzpAWlnoXgbD8B58PYwbIDuLdKTHgKDYRFVD8CVmzox5iYfSuCpgx7FA5zyWncKhXvOegdlT7SM/pub?gid=1810241786&single=true&output=csv"
    
    # 側邊欄控制
    st.sidebar.title("⚙️ 控制面板")
    st.sidebar.markdown("---")
    
    # 自動重新整理
    auto_refresh = st.sidebar.checkbox("自動重新整理 (每5分鐘)", value=False)
    
    if auto_refresh:
        time.sleep(300)  # 5分鐘
        st.rerun()
    
    # 手動重新整理
    if st.sidebar.button("🔄 立即重新整理"):
        st.cache_data.clear()
        st.rerun()
    
    # 資料來源資訊
    st.sidebar.markdown("### 📡 資料來源")
    st.sidebar.info("Google Sheets (即時同步)")
    st.sidebar.text(f"更新時間: {datetime.now().strftime('%H:%M:%S')}")
    
    # 載入資料
    with st.spinner("📊 載入投資資料中..."):
        df = load_investment_data(CSV_URL)
    
    if df is None:
        st.error("❌ 無法載入資料，請檢查網路連線和 CSV 連結")
        
        # 顯示連結測試按鈕
        if st.button("🔗 測試 CSV 連結"):
            with st.spinner("測試連結中..."):
                try:
                    response = requests.get(CSV_URL, timeout=10)
                    if response.status_code == 200:
                        st.success("✅ 連結正常，可以存取資料！")
                        st.text_area("CSV 內容預覽:", response.text[:500], height=100)
                    else:
                        st.error(f"❌ HTTP 錯誤: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ 連結測試失敗: {str(e)}")
        
        return
    
    if df.empty:
        st.warning("⚠️ CSV 檔案沒有有效的投資資料")
        return
    
    # 計算投資摘要
    summary = calculate_investment_summary(df)
    
    # 顯示投資摘要
    st.subheader("📈 投資概況總覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 投資標的數量",
            value=f"{summary['總股票數']} 檔",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💰 每月總投入",
            value=format_currency(summary['每月總投入']),
            delta=None
        )
    
    with col3:
        st.metric(
            label="📅 年度總投入",
            value=format_currency(summary['年度總投入']),
            delta=format_currency(summary['年度總投入'] - summary['每月總投入'])
        )
    
    with col4:
        st.metric(
            label="💸 年度手續費節省",
            value=format_currency(summary['手續費節省']),
            delta=f"{summary['平均券商折扣']:.2f}% 折扣"
        )
    
    # 詳細分析區域
    st.markdown("---")
    st.subheader("📊 詳細分析")
    
    # 圖表區域
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        monthly_chart = create_monthly_investment_chart(df)
        if monthly_chart:
            st.plotly_chart(monthly_chart, use_container_width=True)
    
    with chart_col2:
        pie_chart = create_portfolio_pie_chart(df)
        if pie_chart:
            st.plotly_chart(pie_chart, use_container_width=True)
    
    # 手續費比較圖
    fee_chart = create_fee_comparison_chart(df)
    if fee_chart:
        st.plotly_chart(fee_chart, use_container_width=True)
    
    # 投資明細表
    st.markdown("---")
    st.subheader("📋 投資明細")
    
    # 篩選選項
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        min_amount = st.number_input("最小投入金額", min_value=0, value=0, step=1000)
    
    with filter_col2:
        show_zero = st.checkbox("顯示零投入項目", value=True)
    
    # 應用篩選
    filtered_df = df.copy()
    
    if not show_zero:
        filtered_df = filtered_df[filtered_df['每月投入金額'] > 0]
    
    if min_amount > 0:
        filtered_df = filtered_df[filtered_df['每月投入金額'] >= min_amount]
    
    # 格式化顯示資料
    display_df = filtered_df.copy()
    
    # 格式化金額欄位
    if '每月投入金額' in display_df.columns:
        display_df['每月投入金額'] = display_df['每月投入金額'].apply(lambda x: f"NT${x:,.0f}")
    
    if '年度投入金額' in display_df.columns:
        display_df['年度投入金額'] = display_df['年度投入金額'].apply(lambda x: f"NT${x:,.0f}")
    
    if '預估年度手續費' in display_df.columns:
        display_df['預估年度手續費'] = display_df['預估年度手續費'].apply(lambda x: f"NT${x:,.0f}")
    
    # 顯示資料表
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # 投資建議區塊
    st.markdown("---")
    st.subheader("💡 投資建議")
    
    advice_col1, advice_col2, advice_col3 = st.columns(3)
    
    with advice_col1:
        st.markdown("""
        <div class="info-box">
            <h4>📈 定期定額策略</h4>
            <p>定期定額投資可以平均成本，降低市場波動風險。建議長期持有以獲得較佳報酬。</p>
        </div>
        """, unsafe_allow_html=True)
    
    with advice_col2:
        st.markdown(f"""
        <div class="info-box">
            <h4>💰 成本控制</h4>
            <p>目前享有平均 {summary['平均券商折扣']:.2f}% 的手續費折扣，每年可節省約 {format_currency(summary['手續費節省'])} 的交易成本。</p>
        </div>
        """, unsafe_allow_html=True)
    
    with advice_col3:
        st.markdown(f"""
        <div class="info-box">
            <h4>🎯 投資規模</h4>
            <p>年度總投入 {format_currency(summary['年度總投入'])}，建議設定明確的投資目標和檢視週期。</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 資料匯出功能
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 資料匯出")
    
    if not df.empty:
        # 匯出原始資料
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.sidebar.download_button(
            label="📊 下載投資明細 CSV",
            data=csv_data,
            file_name=f"定期定額投資明細_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )
        
        # 匯出摘要報告
        summary_text = f"""定期定額投資摘要報告
生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

投資概況:
- 投資標的數量: {summary['總股票數']} 檔
- 每月總投入: {format_currency(summary['每月總投入'])}
- 年度總投入: {format_currency(summary['年度總投入'])}
- 平均券商折扣: {summary['平均券商折扣']:.2f}%
- 年度手續費節省: {format_currency(summary['手續費節省'])}

投資明細:
{df.to_string(index=False)}
"""
        
        st.sidebar.download_button(
            label="📄 下載摘要報告 TXT",
            data=summary_text,
            file_name=f"投資摘要報告_{datetime.now().strftime('%Y%m%d')}.txt",
            mime='text/plain'
        )
    
    # 底部資訊
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        📅 資料來源: Google Sheets | 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        📊 此為投資規劃工具，實際投資請諮詢專業顧問
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
