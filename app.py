# -*- coding: utf-8 -*-
"""南京建武数据看板 — 主程序 v2"""
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
# CSS
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
    if labels is None: labels = ys
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

def gen_daily(n_days=30, seed=42, base_sales=10000, base_cost=3000, base_margin=3000):
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    np.random.seed(seed)
    return pd.DataFrame({
        '日期': dates,
        '销售额': np.random.randint(base_sales, base_sales*2, n_days).astype(float),
        '推广费': np.random.randint(base_cost, base_cost*2, n_days).astype(float),
        '毛利': np.random.randint(base_margin, base_margin*2, n_days).astype(float),
        '订单数': np.random.randint(20, 100, n_days).astype(int),
    })

# ============================================================
# 侧边栏 — 双层导航
# ============================================================
st.sidebar.markdown('# 📊 南京建武 数据看板')
st.sidebar.markdown('---')

layer = st.sidebar.radio(
    '', ['🏢 公司层', '📦 单品层', '🛒 天猫', '🎵 抖音', '💰 拼多多', '📦 京东'],
    label_visibility='collapsed',
)

# ============================================================
# 🏢 公司层
# ============================================================
if layer == '🏢 公司层':
    st.markdown("## 🏢 公司层看板")

    df = gen_daily(15, 42, 60000, 18000, 18000)
    df['毛利'] = df['销售额'] * 0.32
    df['毛利率'] = (df['毛利'] / df['销售额'] * 100).round(1)
    for s in ['天猫','抖音','拼多多','京东']:
        df[f'{s}销售额'] = np.random.randint(15000, 45000, 15).astype(float)

    today = df.iloc[-1]; yesterday = df.iloc[-2]; month_total = df['销售额'].sum()

    st.markdown('### 昨日数据汇总')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card('昨日销售额', f'¥{today["销售额"]:,.0f}',
            (today['销售额']/yesterday['销售额']-1)*100), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('昨日毛利', f'¥{today["毛利"]:,.0f}',
            (today['毛利']/yesterday['毛利']-1)*100, 'green'), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card('毛利率', f'{today["毛利率"]:.1f}%', color='blue'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card('本月累计', f'¥{month_total:,.0f}', color='orange'), unsafe_allow_html=True)

    st.markdown('### 分店铺昨日销售额')
    ccs = st.columns(4)
    store_colors = [('🛒 天猫', '天猫销售额', 'purple'), ('🎵 抖音', '抖音销售额', 'blue'),
                    ('💰 拼多多', '拼多多销售额', 'orange'), ('📦 京东', '京东销售额', 'green')]
    for c, (name, col, color) in zip(ccs, store_colors):
        with c:
            st.markdown(kpi_card(name, f'¥{today[col]:,.0f}', color=color), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(trend_line(df, '日期', '销售额', '近15天销售额趋势'), use_container_width=True)
        st.plotly_chart(trend_line(df, '日期', '毛利', '近15天毛利趋势'), use_container_width=True)
    with cr:
        store_keys = ['天猫销售额','抖音销售额','拼多多销售额','京东销售额']
        st.plotly_chart(multi_line(df, '日期', store_keys, ['天猫','抖音','拼多多','京东'],
            '近15天分店铺销售额趋势'), use_container_width=True)
        st.markdown('### 当月汇总 vs 目标')
        st.dataframe(pd.DataFrame({
            '指标': ['销售额', '毛利', '毛利率'],
            '本月实际': [f'¥{month_total:,.0f}', f'¥{month_total*0.32:,.0f}', '32.0%'],
            '本月目标': ['¥3,000,000', '¥960,000', '32%'],
            '完成率': [f'{month_total/3000000*100:.1f}%', f'{month_total*0.32/960000*100:.1f}%', '100%'],
        }), hide_index=True, use_container_width=True)

# ============================================================
# 📦 单品层
# ============================================================
elif layer == '📦 单品层':
    st.markdown("## 📦 单品层数据看板")

    products = ['CK01-平衡车','CK02-自行车14寸','CK03-自行车16寸',
                'CK05-滑板车','CK07-自行车12寸','CK08-三轮车',
                'CK09-电动童车','CK10-儿童头盔']
    df = pd.DataFrame({
        '单品': products,
        '昨日销售额': np.random.randint(2000, 15000, 8),
        '昨日销量': np.random.randint(10, 60, 8),
        '毛利率': np.random.uniform(25, 45, 8).round(1),
        '7日销售额': np.random.randint(15000, 80000, 8),
        '7日销量': np.random.randint(60, 300, 8),
        '库存': np.random.randint(50, 500, 8),
        '日均销量': np.random.randint(5, 30, 8),
    })

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(kpi_card('单品总数', f'{len(df)}个', color='purple'), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('昨日单品总销售', f'¥{df["昨日销售额"].sum():,.0f}',
            color='green'), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card('平均毛利率', f'{df["毛利率"].mean():.1f}%',
            color='blue'), unsafe_allow_html=True)

    st.markdown('### 单品销售明细')
    disp = df.copy()
    disp['库存天数'] = (disp['库存'] / disp['日均销量'].replace(0, 1)).round(0)
    disp['状态'] = disp['库存天数'].apply(
        lambda x: '⚠️ 缺货' if x < 7 else ('✅ 正常' if x < 60 else '📦 滞销'))
    st.dataframe(disp[['单品','昨日销售额','昨日销量','毛利率','7日销售额','7日销量','库存','库存天数','状态']],
                 hide_index=True, use_container_width=True,
                 column_config={'昨日销售额':'¥%d','7日销售额':'¥%d','毛利率':'%.1f%%'})

    st.markdown('---')
    st.markdown('### 库存预警')
    alert = df[df['库存']/df['日均销量'].replace(0,1) < 7]
    if len(alert):
        for _, r in alert.iterrows():
            st.warning(f"⚠️ **{r['单品']}** — 库存仅剩 {r['库存']} 件")
    else:
        st.success('✅ 所有单品库存充足')

    slow = df[df['库存']/df['日均销量'].replace(0,1) > 60]
    if len(slow):
        st.markdown('#### 滞销品')
        for _, r in slow.iterrows():
            st.info(f"📦 **{r['单品']}** — 库存 {r['库存']} 件，周转 {int(r['库存']/max(r['日均销量'],1))} 天")

    st.markdown('---')
    ca, cb = st.columns(2)
    with ca:
        fig = px.pie(df, values='昨日销售额', names='单品', title='昨日单品销售额占比')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    with cb:
        fig2 = px.bar(df, x='单品', y='毛利率', title='各单品毛利率对比', color='毛利率', color_continuous_scale='Blues')
        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# 🏬 四平台店铺层 — 天猫
# ============================================================
elif layer == '🛒 天猫':
    st.markdown("## 🛒 天猫平台看板")

    df = gen_daily(30, 101, 15000, 4000, 4500)

    t = df.iloc[-1]; y = df.iloc[-2]; m = df.iloc[-30:]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card('销售额', f'¥{t["销售额"]:,.0f}',
            (t['销售额']/y['销售额']-1)*100), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('毛利', f'¥{t["毛利"]:,.0f}',
            (t['毛利']/y['毛利']-1)*100, 'green'), unsafe_allow_html=True)
    with c3:
        roi = t['毛利']/max(t['推广费'],1)
        st.markdown(kpi_card('推广ROI', f'{roi:.1f}', color='blue'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card('订单数', f'{t["订单数"]}', color='orange'), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(multi_line(df, '日期', ['销售额','毛利'], ['销售额','毛利'],
            '近30天销售额/毛利趋势'), use_container_width=True)
    with cr:
        st.plotly_chart(multi_line(df, '日期', ['销售额','推广费'], ['销售额','推广费'],
            '销售额 vs 推广费'), use_container_width=True)

    st.markdown('---')
    msum = m['销售额'].sum(); mcost = m['推广费'].sum(); mmargin = m['毛利'].sum()
    st.markdown('### 月度汇总')
    st.dataframe(pd.DataFrame({
        '指标': ['销售额','毛利','推广费','订单数','推广ROI'],
        '本月': [f'¥{msum:,.0f}',f'¥{mmargin:,.0f}',f'¥{mcost:,.0f}',
                f'{m["订单数"].sum()}',f'{mmargin/max(mcost,1):.1f}'],
        '上月': [f'¥{msum*0.9:,.0f}',f'¥{mmargin*0.85:,.0f}',f'¥{mcost*1.05:,.0f}',
                f'{int(m["订单数"].sum()*0.88)}',f'{mmargin*0.85/max(mcost*1.05,1):.1f}'],
    }), hide_index=True, use_container_width=True)

# ============================================================
# 🎵 抖音
# ============================================================
elif layer == '🎵 抖音':
    st.markdown("## 🎵 抖音平台看板")

    df = gen_daily(30, 202, 20000, 6000, 6000)

    t = df.iloc[-1]; y = df.iloc[-2]; m = df.iloc[-30:]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card('销售额', f'¥{t["销售额"]:,.0f}',
            (t['销售额']/y['销售额']-1)*100), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('毛利', f'¥{t["毛利"]:,.0f}',
            (t['毛利']/y['毛利']-1)*100, 'green'), unsafe_allow_html=True)
    with c3:
        roi = t['毛利']/max(t['推广费'],1)
        st.markdown(kpi_card('推广ROI', f'{roi:.1f}', color='blue'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card('订单数', f'{t["订单数"]}', color='orange'), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(multi_line(df, '日期', ['销售额','毛利'], ['销售额','毛利'],
            '近30天销售额/毛利趋势'), use_container_width=True)
    with cr:
        st.plotly_chart(multi_line(df, '日期', ['销售额','推广费'], ['销售额','推广费'],
            '销售额 vs 推广费'), use_container_width=True)

    st.markdown('---')
    msum = m['销售额'].sum(); mcost = m['推广费'].sum(); mmargin = m['毛利'].sum()
    st.markdown('### 月度汇总')
    st.dataframe(pd.DataFrame({
        '指标': ['销售额','毛利','推广费','订单数','推广ROI'],
        '本月': [f'¥{msum:,.0f}',f'¥{mmargin:,.0f}',f'¥{mcost:,.0f}',
                f'{m["订单数"].sum()}',f'{mmargin/max(mcost,1):.1f}'],
        '上月': [f'¥{msum*0.92:,.0f}',f'¥{mmargin*0.88:,.0f}',f'¥{mcost*0.98:,.0f}',
                f'{int(m["订单数"].sum()*0.95)}',f'{mmargin*0.88/max(mcost*0.98,1):.1f}'],
    }), hide_index=True, use_container_width=True)

# ============================================================
# 💰 拼多多
# ============================================================
elif layer == '💰 拼多多':
    st.markdown("## 💰 拼多多平台看板")

    df = gen_daily(30, 303, 8000, 2000, 2500)

    t = df.iloc[-1]; y = df.iloc[-2]; m = df.iloc[-30:]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card('销售额', f'¥{t["销售额"]:,.0f}',
            (t['销售额']/y['销售额']-1)*100), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('毛利', f'¥{t["毛利"]:,.0f}',
            (t['毛利']/y['毛利']-1)*100, 'green'), unsafe_allow_html=True)
    with c3:
        roi = t['毛利']/max(t['推广费'],1)
        st.markdown(kpi_card('推广ROI', f'{roi:.1f}', color='blue'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card('订单数', f'{t["订单数"]}', color='orange'), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(multi_line(df, '日期', ['销售额','毛利'], ['销售额','毛利'],
            '近30天销售额/毛利趋势'), use_container_width=True)
    with cr:
        st.plotly_chart(multi_line(df, '日期', ['销售额','推广费'], ['销售额','推广费'],
            '销售额 vs 推广费'), use_container_width=True)

    st.markdown('---')
    msum = m['销售额'].sum(); mcost = m['推广费'].sum(); mmargin = m['毛利'].sum()
    st.markdown('### 月度汇总')
    st.dataframe(pd.DataFrame({
        '指标': ['销售额','毛利','推广费','订单数','推广ROI'],
        '本月': [f'¥{msum:,.0f}',f'¥{mmargin:,.0f}',f'¥{mcost:,.0f}',
                f'{m["订单数"].sum()}',f'{mmargin/max(mcost,1):.1f}'],
        '上月': [f'¥{msum*0.87:,.0f}',f'¥{mmargin*0.9:,.0f}',f'¥{mcost*0.95:,.0f}',
                f'{int(m["订单数"].sum()*0.83)}',f'{mmargin*0.9/max(mcost*0.95,1):.1f}'],
    }), hide_index=True, use_container_width=True)

# ============================================================
# 📦 京东
# ============================================================
elif layer == '📦 京东':
    st.markdown("## 📦 京东平台看板")

    df = gen_daily(30, 404, 12000, 3000, 3500)

    t = df.iloc[-1]; y = df.iloc[-2]; m = df.iloc[-30:]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card('销售额', f'¥{t["销售额"]:,.0f}',
            (t['销售额']/y['销售额']-1)*100), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card('毛利', f'¥{t["毛利"]:,.0f}',
            (t['毛利']/y['毛利']-1)*100, 'green'), unsafe_allow_html=True)
    with c3:
        roi = t['毛利']/max(t['推广费'],1)
        st.markdown(kpi_card('推广ROI', f'{roi:.1f}', color='blue'), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card('订单数', f'{t["订单数"]}', color='orange'), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(multi_line(df, '日期', ['销售额','毛利'], ['销售额','毛利'],
            '近30天销售额/毛利趋势'), use_container_width=True)
    with cr:
        st.plotly_chart(multi_line(df, '日期', ['销售额','推广费'], ['销售额','推广费'],
            '销售额 vs 推广费'), use_container_width=True)

    st.markdown('---')
    msum = m['销售额'].sum(); mcost = m['推广费'].sum(); mmargin = m['毛利'].sum()
    st.markdown('### 月度汇总')
    st.dataframe(pd.DataFrame({
        '指标': ['销售额','毛利','推广费','订单数','推广ROI'],
        '本月': [f'¥{msum:,.0f}',f'¥{mmargin:,.0f}',f'¥{mcost:,.0f}',
                f'{m["订单数"].sum()}',f'{mmargin/max(mcost,1):.1f}'],
        '上月': [f'¥{msum*0.91:,.0f}',f'¥{mmargin*0.86:,.0f}',f'¥{mcost*1.02:,.0f}',
                f'{int(m["订单数"].sum()*0.89)}',f'{mmargin*0.86/max(mcost*1.02,1):.1f}'],
    }), hide_index=True, use_container_width=True)

# ============================================================
st.markdown('---')
st.caption(f'数据更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
