# -*- coding: utf-8 -*-
"""南京建武数据看板 — 主程序"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(
    page_title='南京建武数据看板',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ============================================================
# 样式
# ============================================================
st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px; padding: 20px; color: white; text-align: center;
    }
    .kpi-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .kpi-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .kpi-card.blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .kpi-value { font-size: 28px; font-weight: bold; margin: 8px 0; }
    .kpi-label { font-size: 13px; opacity: 0.9; }
    .kpi-change { font-size: 12px; margin-top: 4px; }
    .kpi-change.up { color: #38ef7d; }
    .kpi-change.down { color: #ff6b6b; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 模拟数据（后续接入 WPS 云盘实时数据）
# ============================================================
def generate_company_data():
    dates = pd.date_range(end=datetime.now(), periods=15, freq='D')
    np.random.seed(42)
    df = pd.DataFrame({
        '日期': dates,
        '销售额': np.random.randint(80000, 150000, 15).astype(float),
        '毛利': np.random.randint(25000, 50000, 15).astype(float),
        '天猫销售额': np.random.randint(20000, 40000, 15).astype(float),
        '抖音销售额': np.random.randint(25000, 50000, 15).astype(float),
        '拼多多销售额': np.random.randint(10000, 25000, 15).astype(float),
        '京东销售额': np.random.randint(15000, 30000, 15).astype(float),
    })
    df['毛利'] = df['销售额'] * 0.32
    df['毛利率'] = (df['毛利'] / df['销售额'] * 100).round(1)
    return df

def generate_product_data():
    products = ['CK01-平衡车', 'CK02-自行车14寸', 'CK03-自行车16寸',
                'CK05-滑板车', 'CK07-自行车12寸', 'CK08-三轮车',
                'CK09-电动童车', 'CK10-儿童头盔']
    np.random.seed(42)
    return pd.DataFrame({
        '单品': products,
        '昨日销售额': np.random.randint(2000, 15000, 8),
        '昨日销量': np.random.randint(10, 60, 8),
        '毛利率': np.random.uniform(25, 45, 8).round(1),
        '7日销售额': np.random.randint(15000, 80000, 8),
        '7日销量': np.random.randint(60, 300, 8),
        '库存': np.random.randint(50, 500, 8),
        '日均销量': np.random.randint(5, 30, 8),
    })

def generate_store_data(store_name):
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    np.random.seed(hash(store_name) % 10000)
    return pd.DataFrame({
        '日期': dates,
        '销售额': np.random.randint(3000, 20000, 30).astype(float),
        '推广费': np.random.randint(500, 5000, 30).astype(float),
        '毛利': np.random.randint(1000, 6000, 30).astype(float),
        '订单数': np.random.randint(10, 80, 30).astype(int),
    })

# ============================================================
# 工具函数
# ============================================================
def kpi_card(label, value, change=None, color='purple'):
    change_html = ''
    if change is not None:
        cls = 'up' if change >= 0 else 'down'
        arrow = '▲' if change >= 0 else '▼'
        change_html = f'<div class="kpi-change {cls}">{arrow} {abs(change):.1f}% 环比</div>'
    return f"""
    <div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {change_html}
    </div>
    """

def trend_line(df, x, y, title='', height=300):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y], mode='lines+markers',
        line=dict(width=2), marker=dict(size=5),
        name=y, hovertemplate='%{x|%m-%d}<br>%{y:,.0f}'
    ))
    fig.update_layout(
        title=title, height=height, margin=dict(l=20, r=20, t=40, b=20),
        template='plotly_white', hovermode='x unified',
    )
    return fig

def multi_line(df, x, ys, labels=None, title='', height=300):
    if labels is None:
        labels = ys
    fig = go.Figure()
    for y, label in zip(ys, labels):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[y], mode='lines+markers',
            name=label, line=dict(width=2), marker=dict(size=4),
        ))
    fig.update_layout(
        title=title, height=height, margin=dict(l=20, r=20, t=40, b=20),
        template='plotly_white', hovermode='x unified',
    )
    return fig

# ============================================================
# 侧边栏 — 看板层级导航
# ============================================================
st.sidebar.markdown('# 📊 南京建武 数据看板')
st.sidebar.markdown('---')

layer = st.sidebar.radio(
    '看板层级',
    ['🏢 公司层', '📦 单品层', '🏬 四平台店铺层'],
    label_visibility='collapsed',
)

# ============================================================
# 🏢 公司层看板
# ============================================================
if layer == '🏢 公司层':
    st.markdown("## 🏢 公司层看板")

    df = generate_company_data()
    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    # 昨日汇总 KPI
    st.markdown('### 昨日数据汇总')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card(
            '昨日销售额', f'¥{today["销售额"]:,.0f}',
            change=(today['销售额'] / yesterday['销售额'] - 1) * 100, color='purple'
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(
            '昨日毛利', f'¥{today["毛利"]:,.0f}',
            change=(today['毛利'] / yesterday['毛利'] - 1) * 100, color='green'
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card(
            '昨日毛利率', f'{today["毛利率"]:.1f}%', color='blue'
        ), unsafe_allow_html=True)
    with c4:
        monthly = df['销售额'].sum()
        st.markdown(kpi_card(
            '本月累计', f'¥{monthly:,.0f}', color='orange'
        ), unsafe_allow_html=True)

    # 分店铺昨日
    st.markdown('### 分店铺昨日销售额')
    cc1, cc2, cc3, cc4 = st.columns(4)
    stores = [
        ('天猫', today['天猫销售额'], 'purple'),
        ('抖音', today['抖音销售额'], 'blue'),
        ('拼多多', today['拼多多销售额'], 'orange'),
        ('京东', today['京东销售额'], 'green'),
    ]
    for c, (name, val, color) in zip([cc1, cc2, cc3, cc4], stores):
        with c:
            st.markdown(kpi_card(
                f'{name}销售额', f'¥{val:,.0f}', color=color
            ), unsafe_allow_html=True)

    # 趋势图
    st.markdown('---')
    col_left, col_right = st.columns(2)
    with col_left:
        st.plotly_chart(trend_line(df, '日期', '销售额', '近15天销售额趋势'), use_container_width=True)
        st.plotly_chart(trend_line(df, '日期', '毛利', '近15天毛利趋势'), use_container_width=True)
    with col_right:
        st.plotly_chart(multi_line(df, '日期',
            ['天猫销售额', '抖音销售额', '拼多多销售额', '京东销售额'],
            ['天猫', '抖音', '拼多多', '京东'],
            '近15天分店铺销售额趋势'
        ), use_container_width=True)

        # 月度对比表
        st.markdown('### 当月汇总 vs 目标')
        goal_data = pd.DataFrame({
            '指标': ['销售额', '毛利', '毛利率'],
            '本月实际': [f'¥{monthly:,.0f}', f'¥{monthly*0.32:,.0f}', '32.0%'],
            '本月目标': ['¥3,000,000', '¥960,000', '32%'],
            '完成率': [f'{monthly/3000000*100:.1f}%', f'{monthly*0.32/960000*100:.1f}%', '100%'],
        })
        st.dataframe(goal_data, hide_index=True, use_container_width=True)

# ============================================================
# 📦 单品层看板
# ============================================================
elif layer == '📦 单品层':
    st.markdown("## 📦 单品层数据看板")

    df = generate_product_data()

    # Top KPIs
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card(
            '单品总数', f'{len(df)} 个', color='purple'
        ), unsafe_allow_html=True)
    with c2:
        total_sales = df['昨日销售额'].sum()
        st.markdown(kpi_card(
            '昨日单品总销售', f'¥{total_sales:,.0f}', color='green'
        ), unsafe_allow_html=True)
    with c3:
        avg_margin = df['毛利率'].mean()
        st.markdown(kpi_card(
            '平均毛利率', f'{avg_margin:.1f}%', color='blue'
        ), unsafe_allow_html=True)

    # 单品明细表
    st.markdown('### 单品销售明细')
    display_df = df.copy()
    display_df['7日日均售价'] = (display_df['7日销售额'] / display_df['7日销量']).round(0)
    display_df['库存天数'] = (display_df['库存'] / display_df['日均销量'].replace(0, 1)).round(0)
    display_df['状态'] = display_df['库存天数'].apply(
        lambda x: '⚠️ 缺货' if x < 7 else ('✅ 正常' if x < 60 else '📦 滞销')
    )
    display_df = display_df[['单品', '昨日销售额', '昨日销量', '毛利率',
                               '7日销售额', '7日销量', '库存', '库存天数', '状态']]
    st.dataframe(display_df, hide_index=True, use_container_width=True,
                 column_config={
                     '昨日销售额': st.column_config.NumberColumn(format='¥%d'),
                     '7日销售额': st.column_config.NumberColumn(format='¥%d'),
                     '毛利率': st.column_config.NumberColumn(format='%.1f%%'),
                 })

    # 库存预警
    st.markdown('---')
    st.markdown('### 库存预警')
    alert_df = df[df['库存'] / df['日均销量'].replace(0, 1) < 7].copy()
    if len(alert_df) > 0:
        for _, row in alert_df.iterrows():
            days = row['库存'] / max(row['日均销量'], 1)
            st.warning(f"⚠️ **{row['单品']}** — 库存仅剩 {row['库存']} 件，预计 {days:.0f} 天售罄")
    else:
        st.success('✅ 所有单品库存充足')

    slow_df = df[df['库存'] / df['日均销量'].replace(0, 1) > 60].copy()
    if len(slow_df) > 0:
        st.markdown('#### 滞销品')
        for _, row in slow_df.iterrows():
            st.info(f"📦 **{row['单品']}** — 库存 {row['库存']} 件，库存周转 {int(row['库存']/max(row['日均销量'],1))} 天")

    # 单品占比饼图
    st.markdown('---')
    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.pie(df, values='昨日销售额', names='单品', title='昨日单品销售额占比')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig2 = px.bar(df, x='单品', y='毛利率', title='各单品毛利率对比',
                      color='毛利率', color_continuous_scale='Blues')
        fig2.update_layout(margin=dict(l=0, r=0, t=40, b=40))
        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# 🏬 四平台店铺层
# ============================================================
else:
    st.markdown("## 🏬 四平台店铺层看板")

    platform = st.selectbox('选择平台', ['天猫', '抖音', '拼多多', '京东'])
    df = generate_store_data(platform)

    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    month = df.iloc[-30:]

    st.markdown(f'### {platform} — 昨日核心指标')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card(
            '销售额', f'¥{today["销售额"]:,.0f}',
            change=(today['销售额']/yesterday['销售额']-1)*100, color='purple'
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(
            '毛利', f'¥{today["毛利"]:,.0f}',
            change=(today['毛利']/yesterday['毛利']-1)*100, color='green'
        ), unsafe_allow_html=True)
    with c3:
        roi = today['毛利'] / max(today['推广费'], 1)
        st.markdown(kpi_card(
            '推广ROI', f'{roi:.1f}', color='blue'
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card(
            '订单数', f'{today["订单数"]}', color='orange'
        ), unsafe_allow_html=True)

    # 30天趋势
    st.markdown('---')
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(multi_line(df, '日期',
            ['销售额', '毛利'], ['销售额', '毛利'],
            f'{platform} - 近30天销售额/毛利趋势'
        ), use_container_width=True)
    with col_b:
        st.plotly_chart(multi_line(df, '日期',
            ['销售额', '推广费'], ['销售额', '推广费'],
            f'{platform} - 销售额 vs 推广费'
        ), use_container_width=True)

    # 月度对比
    st.markdown('---')
    st.markdown('### 月度汇总')
    monthly_summary = pd.DataFrame({
        '指标': ['销售额', '毛利', '推广费', '订单数', '推广ROI'],
        '本月': [f'¥{month["销售额"].sum():,.0f}', f'¥{month["毛利"].sum():,.0f}',
                f'¥{month["推广费"].sum():,.0f}', f'{month["订单数"].sum()}',
                f'{month["毛利"].sum()/max(month["推广费"].sum(),1):.1f}'],
        '上月': [f'¥{month["销售额"].sum()*0.9:,.0f}', f'¥{month["毛利"].sum()*0.85:,.0f}',
                f'¥{month["推广费"].sum()*1.05:,.0f}', f'{int(month["订单数"].sum()*0.88)}',
                f'{month["毛利"].sum()*0.85/max(month["推广费"].sum()*1.05,1):.1f}'],
    })
    st.dataframe(monthly_summary, hide_index=True, use_container_width=True)

# ============================================================
# 底部
# ============================================================
st.markdown('---')
st.caption(f'数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}  |  数据来源: WPS 云盘')
