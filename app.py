# -*- coding: utf-8 -*-
"""南京建武数据看板 v3 — 接入 WPS 云盘实时数据"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import data_loader as dl

st.set_page_config(page_title='南京建武数据看板', page_icon='📊', layout='wide')

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    .kpi-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px; padding: 20px; color: white; text-align: center; }
    .kpi-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .kpi-card.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .kpi-card.blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .kpi-value { font-size: 28px; font-weight: bold; margin: 8px 0; }
    .kpi-label { font-size: 13px; opacity: 0.9; }
    .kpi-change { font-size: 12px; margin-top: 4px; }
    .kpi-change.up { color: #38ef7d; } .kpi-change.down { color: #ff6b6b; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 工具函数
# ============================================================
def kpi_card(label, value, change=None, color='purple'):
    ch = ''
    if change is not None:
        cls = 'up' if change >= 0 else 'down'
        ch = f'<div class="kpi-change {cls}">{("▲" if change >= 0 else "▼")} {abs(change):.1f}% 环比</div>'
    return f'<div class="kpi-card {color}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{ch}</div>'

def _fmt(v):
    if isinstance(v, (int, float)):
        return f'¥{v:,.0f}' if abs(v) >= 100 else f'{v:.1f}'
    return str(v)

def trend_line(df, x, y, title='', height=300):
    if df.empty: return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='lines+markers',
        line=dict(width=2), marker=dict(size=5), name=y))
    fig.update_layout(title=title, height=height, margin=dict(l=20,r=20,t=40,b=20),
        template='plotly_white', hovermode='x unified')
    return fig

def multi_line(df, x, ys, labels=None, title='', height=300):
    if df.empty: return go.Figure()
    if labels is None: labels = ys
    fig = go.Figure()
    for y, label in zip(ys, labels):
        if y in df.columns:
            fig.add_trace(go.Scatter(x=df[x], y=df[y], mode='lines+markers',
                name=label, line=dict(width=2), marker=dict(size=4)))
    fig.update_layout(title=title, height=height, margin=dict(l=20,r=20,t=40,b=20),
        template='plotly_white', hovermode='x unified')
    return fig

def daily_kpis(df, cols=['销售额','毛利','订单数']):
    """从每日数据 DataFrame 提取昨日 KPI + 环比（以机器日期昨日为准）"""
    if df.empty:
        return {}
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    day_before = yesterday - timedelta(days=1)

    df_yd = df[df['日期'] == yesterday]
    if df_yd.empty:
        # 昨天数据未更新，全部填充 0
        result = {}
        for c in cols:
            if c in df.columns:
                result[c] = (0, 0)
        return result

    cur_row = df_yd.iloc[0]
    df_bd = df[df['日期'] == day_before]
    prev_row = df_bd.iloc[0] if not df_bd.empty else None

    result = {}
    for c in cols:
        if c in df.columns:
            cur = cur_row[c] if not pd.isna(cur_row[c]) else 0
            prev = prev_row[c] if prev_row is not None and not pd.isna(prev_row[c]) else 0
            chg = (cur / prev - 1) * 100 if prev else 0
            result[c] = (cur, chg)
    return result

# ============================================================
# 侧边栏
# ============================================================
st.sidebar.markdown('# 📊 南京建武 数据看板')
st.sidebar.markdown('---')

# 每日 10:00 自动刷新 + 手动刷新
now = datetime.now()
today_str = now.strftime('%Y%m%d')
if 'last_auto_refresh' not in st.session_state:
    st.session_state.last_auto_refresh = None

if now.hour >= 10 and st.session_state.last_auto_refresh != today_str:
    st.cache_data.clear()
    st.session_state.last_auto_refresh = today_str
    st.rerun()

if st.sidebar.button('🔄 手动刷新数据', use_container_width=True):
    st.cache_data.clear()
    st.session_state.last_auto_refresh = None
    st.rerun()

layer = st.sidebar.radio('',
    ['🏢 公司层', '📦 单品层', '🛒 天猫', '🎵 抖音', '💰 拼多多', '📦 京东'],
    label_visibility='collapsed')
st.sidebar.markdown('---')
st.sidebar.caption('数据来源: WPS 云盘')

# ============================================================
# 🏢 公司层
# ============================================================
if layer == '🏢 公司层':
    st.markdown("## 🏢 公司层看板")
    st.caption('从 001-公司经营销售数据 实时加载...')

    try:
        kpis = dl.load_company_daily()
        stores = dl.load_company_store_breakdown()
        df_tmall = dl.load_tmall_daily()
        df_dy = dl.load_douyin_daily()
        df_pdd = dl.load_pdd_daily()
        df_jd = dl.load_jd_daily()

        # 汇总每日数据
        all_dfs = []
        for df_s, col_sales in [(df_tmall, '销售额'), (df_dy, '销售额'), (df_pdd, '销售额'), (df_jd, '销售额')]:
            if not df_s.empty and col_sales in df_s.columns:
                sub = df_s[['日期', col_sales]].copy()
                all_dfs.append(sub.rename(columns={col_sales: '销售额'}))
        if all_dfs:
            company_daily = all_dfs[0]
            for d in all_dfs[1:]:
                company_daily = pd.merge(company_daily, d, on='日期', how='outer', suffixes=('','_dup'))
            company_daily['销售额'] = company_daily.filter(like='销售额').sum(axis=1)
            company_daily['毛利'] = company_daily['销售额'] * 0.30
        else:
            company_daily = pd.DataFrame()
    except Exception as e:
        st.error(f'数据加载失败: {e}')
        kpis = {}; stores = {}; company_daily = pd.DataFrame()

    # KPI cards
    cols = st.columns(4)
    daily_kpi = daily_kpis(company_daily, ['销售额','毛利']) if not company_daily.empty else {}
    for c, (label, key, color) in zip(cols, [
        ('昨日总销售额', '销售额', 'purple'),
        ('昨日总毛利', '毛利', 'green'),
    ]):
        with c:
            if key in daily_kpi:
                v, ch = daily_kpi[key]
                st.markdown(kpi_card(label, _fmt(v), ch, color), unsafe_allow_html=True)
            else:
                st.markdown(kpi_card(label, _fmt(kpis.get(label, '--')), color=color), unsafe_allow_html=True)
    with cols[2]:
        margin_rate = (kpis.get('毛利率', 0) or 30)
        st.markdown(kpi_card('毛利率', f'{margin_rate:.1f}%', color='blue'), unsafe_allow_html=True)
    with cols[3]:
        monthly = company_daily['销售额'].sum() if not company_daily.empty else 0
        st.markdown(kpi_card('本月累计', _fmt(monthly), color='orange'), unsafe_allow_html=True)

    # 分店铺
    st.markdown('### 分店铺昨日')
    ccs = st.columns(4)
    for c, (name, color) in zip(ccs, [('天猫', 'purple'), ('抖音', 'blue'), ('拼多多', 'orange'), ('京东', 'green')]):
        with c:
            st.markdown(kpi_card(name, _fmt(stores.get(f'{name}销售额', 0)), color=color), unsafe_allow_html=True)

    st.markdown('---')
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(trend_line(company_daily, '日期', '销售额', '近15天销售额趋势'), use_container_width=True)
    with cr:
        store_dfs = {'天猫': df_tmall, '抖音': df_dy, '拼多多': df_pdd, '京东': df_jd}
        st.plotly_chart(multi_line(company_daily, '日期', ['销售额'], ['总销售额'], '近期销售趋势'), use_container_width=True)

# ============================================================
# 📦 单品层
# ============================================================
elif layer == '📦 单品层':
    st.markdown("## 📦 单品层数据看板")
    st.caption('从 001-单品数据统计表 + 009-进销存 实时加载...')

    try:
        products = dl.load_product_stats()
        inventory = dl.load_inventory()
        if not products.empty and not inventory.empty:
            # 合并库存
            products['型号_clean'] = products['单品'].str.extract(r'(CK\d+)', expand=False)
            inventory['型号_clean'] = inventory['型号'].str.extract(r'(CK\d+)', expand=False)
            products = products.merge(inventory[['型号_clean','当前库存','日均销量']],
                                      on='型号_clean', how='left')
            products['当前库存'] = products['当前库存'].fillna(0)
            products['日均销量'] = products['日均销量'].fillna(1)
    except Exception as e:
        st.error(f'数据加载失败: {e}')
        products = pd.DataFrame()

    if products.empty:
        st.warning('暂无单品数据')
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(kpi_card('单品数', f'{len(products)}', color='purple'), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi_card('总销售', _fmt(products['销售额'].sum()), color='green'), unsafe_allow_html=True)
        with c3:
            st.markdown(kpi_card('平均毛利率', f'{products["毛利率"].mean():.1f}%', color='blue'), unsafe_allow_html=True)

        st.markdown('### 单品销售明细')
        disp = products[['单品','销售额','销量','毛利率','推广费','当前库存','日均销量']].copy()
        disp = disp[disp['销售额'] > 0]
        disp['库存天数'] = (disp['当前库存'] / disp['日均销量'].replace(0,1)).round(0)
        disp['状态'] = disp['库存天数'].apply(
            lambda x: '⚠️ 缺货' if x < 7 else ('✅ 正常' if x < 60 else '📦 滞销'))
        st.dataframe(disp, hide_index=True, use_container_width=True)

        st.markdown('---')
        st.markdown('### 库存预警')
        alert = disp[disp['库存天数'] < 7]
        if len(alert):
            for _, r in alert.iterrows():
                st.warning(f"⚠️ {r['单品']} — 库存仅剩 {int(r['当前库存'])} 件")
        else:
            st.success('✅ 所有单品库存充足')

# ============================================================
# 🛒 天猫
# ============================================================
elif layer in ['🛒 天猫', '🎵 抖音', '💰 拼多多', '📦 京东']:
    store_name = layer.split()[-1]
    st.markdown(f"## {layer} 平台看板")
    st.caption(f'从 WPS 云盘实时加载...')

    loaders = {
        '天猫': dl.load_tmall_daily,
        '抖音': dl.load_douyin_daily,
        '拼多多': dl.load_pdd_daily,
        '京东': dl.load_jd_daily,
    }

    try:
        df = loaders[store_name]()
    except Exception as e:
        st.error(f'数据加载失败: {e}')
        df = pd.DataFrame()

    if df.empty:
        st.warning(f'{store_name}暂无每日数据，尝试从公司总表中提取...')
        try:
            df = dl.load_company_store_daily(store_name)
        except:
            pass

    if df.empty:
        st.error(f'无法获取{store_name}数据，请检查 WPS 云盘文件')
    elif store_name == '天猫':
        # ====== 天猫专属看板 ======
        tm_m = dl.load_tmall_monthly()
        tm_gsv = tm_m.get('GSV', 0)
        tm_profit = tm_m.get('利润目标', 0)
        tm_cost = tm_m.get('站内推广费', 0) + tm_m.get('站外推广费', 0)

        # 昨日/近7天/本月数据
        yd = df[df['日期'] == df['日期'].max()] if not df.empty else pd.DataFrame()
        yd_s = float(yd['销售额'].sum()) if not yd.empty and '销售额' in yd.columns else 0
        yd_p = float(yd['毛利'].sum()) if not yd.empty and '毛利' in yd.columns else 0
        yd_c = float(yd['推广费'].sum()) if not yd.empty and '推广费' in yd.columns else 0

        today_d = datetime.now().date()
        d7 = df[df['日期'] >= today_d - timedelta(days=7)]
        d7_s = float(d7['销售额'].sum()) if not d7.empty and '销售额' in d7.columns else 0
        d7_p = float(d7['毛利'].sum()) if not d7.empty and '毛利' in d7.columns else 0
        d7_c = float(d7['推广费'].sum()) if not d7.empty and '推广费' in d7.columns else 0

        # 三个月度KPI表
        def _t(v):
            if isinstance(v,(int,float)):
                if abs(v)>=100: return f'\u00a5{v:,.0f}'
                return f'{v:.1f}'
            return str(v)
        def _ch(v): return f'{v:.1f}%'

        st.markdown('### \u5929\u732b\u5e97\u94fa\u6570\u636e')
        c0,c1,c2,c3,c4,c5 = st.columns([1.2,1,1,1,1,1])
        with c0: st.caption('')
        with c1: st.caption('GSV')
        with c2: st.caption('\u5229\u6da6\u989d')
        with c3: st.caption('\u5229\u6da6\u7387')
        with c4: st.caption('\u63a8\u5e7f\u603b\u989d')
        with c5: st.caption('\u63a8\u5e7f\u5360\u6bd4')

        c0,c1,c2,c3,c4,c5 = st.columns([1.2,1,1,1,1,1])
        with c0: st.markdown('**\u5f53\u6708**')
        with c1: st.metric('', _t(tm_gsv))
        with c2: st.metric('', _t(tm_profit))
        with c3: st.metric('', _ch(tm_profit/tm_gsv*100 if tm_gsv else 0))
        with c4: st.metric('', _t(tm_cost))
        with c5: st.metric('', _ch(tm_cost/tm_gsv*100 if tm_gsv else 0))

        c0,c1,c2,c3,c4,c5 = st.columns([1.2,1,1,1,1,1])
        with c0: st.markdown('**\u8fd17\u5929**')
        with c1: st.metric('', _t(d7_s))
        with c2: st.metric('', _t(d7_p))
        with c3: st.metric('', _ch(d7_p/d7_s*100 if d7_s else 0))
        with c4: st.metric('', _t(d7_c))
        with c5: st.metric('', _ch(d7_c/d7_s*100 if d7_s else 0))

        c0,c1,c2,c3,c4,c5 = st.columns([1.2,1,1,1,1,1])
        with c0: st.markdown('**\u6628\u65e5**')
        with c1: st.metric('', _t(yd_s))
        with c2: st.metric('', _t(yd_p))
        with c3: st.metric('', _ch(yd_p/yd_s*100 if yd_s else 0))
        with c4: st.metric('', _t(yd_c))
        with c5: st.metric('', _ch(yd_c/yd_s*100 if yd_s else 0))

        st.markdown('---')
        # 7天趋势
        cl, cr = st.columns(2)
        with cl:
            if not d7.empty:
                fig7 = go.Figure()
                fig7.add_trace(go.Scatter(x=d7['日期'], y=d7['销售额'], mode='lines+markers',
                    name='GSV', line=dict(width=2, color='#667eea')))
                if '毛利' in d7.columns:
                    fig7.add_trace(go.Scatter(x=d7['日期'], y=d7['毛利'], mode='lines+markers',
                        name='\u6bdb\u5229', line=dict(width=2, color='#38ef7d')))
                fig7.update_layout(title='\u8fd17\u5929\u9500\u552e\u989d&\u6bdb\u5229\u8d8b\u52bf', height=300,
                    margin=dict(l=20,r=20,t=40,b=20), template='plotly_white', hovermode='x unified')
                st.plotly_chart(fig7, use_container_width=True)
        with cr:
            # 月度柱状图
            if not df.empty and '销售额' in df.columns:
                df['_m'] = df['日期'].apply(lambda x: x.strftime('%y/%m'))
                ms = df.groupby('_m')['销售额'].sum().tail(6)
                mm = df.groupby('_m')['毛利'].sum().tail(6) if '毛利' in df.columns else ms*0.3
                fig_m = go.Figure()
                fig_m.add_trace(go.Bar(x=ms.index.tolist(), y=ms.values.round(0).tolist(), name='GSV', marker_color='#667eea'))
                fig_m.add_trace(go.Bar(x=mm.index.tolist(), y=mm.values.round(0).tolist(), name='\u6bdb\u5229', marker_color='#38ef7d'))
                fig_m.update_layout(title='\u8fd16\u4e2a\u6708GSV\u4e0e\u6bdb\u5229\u5bf9\u6bd4', height=300, barmode='group',
                    margin=dict(l=20,r=20,t=40,b=20), template='plotly_white', legend=dict(orientation='h', y=1.15))
                st.plotly_chart(fig_m, use_container_width=True)

        # 30天趋势
        st.plotly_chart(trend_line(df, '日期', '销售额', f'{store_name}\u8fd130\u5929\u9500\u552e\u989d\u8d8b\u52bf'), use_container_width=True)

        # 月度汇总表
        monthly = df[df['日期'] >= df['日期'].max() - timedelta(days=30)]
        if not monthly.empty:
            st.markdown('### \u6708\u5ea6\u6c47\u603b')
            msum = monthly['销售额'].sum()
            mcost = monthly['推广费'].sum() if '推广费' in monthly.columns else 0
            mmargin = monthly['毛利'].sum() if '毛利' in monthly.columns else msum * 0.3
            st.dataframe(pd.DataFrame({
                '\u6307\u6807': ['\u9500\u552e\u989d','\u6bdb\u5229','\u63a8\u5e7f\u8d39','\u8ba2\u5355\u6570'],
                '\u672c\u6708': [_fmt(msum), _fmt(mmargin), _fmt(mcost),
                        f'{int(monthly["\u8ba2\u5355\u6570"].sum()) if "\u8ba2\u5355\u6570" in monthly.columns else "--"}'],
            }), hide_index=True, use_container_width=True)
    else:
        # ====== 其他平台 ======
        kpis_d = daily_kpis(df, ['销售额','毛利','订单数'])

        cols = st.columns(4)
        for c, (label, key, color) in zip(cols, [
            ('销售额', '销售额', 'purple'),
            ('毛利', '毛利', 'green'),
            ('推广ROI', '推广费', 'blue'),
            ('订单数', '订单数', 'orange'),
        ]):
            with c:
                if key in kpis_d:
                    v, ch = kpis_d[key]
                    if key == '推广费':
                        sales_v = kpis_d.get('销售额', (0,0))[0]
                        roi = sales_v / max(v, 1)
                        st.markdown(kpi_card('推广ROI', f'{roi:.1f}', color=color), unsafe_allow_html=True)
                    elif key == '订单数':
                        st.markdown(kpi_card(label, f'{int(v)}', color=color), unsafe_allow_html=True)
                    else:
                        st.markdown(kpi_card(label, _fmt(v), ch, color), unsafe_allow_html=True)
                else:
                    st.markdown(kpi_card(label, '--', color=color), unsafe_allow_html=True)

        st.markdown('---')
        cl, cr = st.columns(2)
        with cl:
            st.plotly_chart(trend_line(df, '日期', '销售额', f'{store_name}近30天销售额趋势'), use_container_width=True)
        with cr:
            available_cols = [c for c in ['推广费','毛利'] if c in df.columns]
            if available_cols:
                st.plotly_chart(multi_line(df, '日期', ['销售额'] + available_cols,
                    ['销售额'] + available_cols, f'{store_name}趋势对比'), use_container_width=True)

        # 月度汇总
        monthly = df[df['日期'] >= df['日期'].max() - timedelta(days=30)]
        if not monthly.empty:
            st.markdown('### 月度汇总')
            msum = monthly['销售额'].sum()
            mcost = monthly['推广费'].sum() if '推广费' in monthly.columns else 0
            mmargin = monthly['毛利'].sum() if '毛利' in monthly.columns else msum * 0.3
            st.dataframe(pd.DataFrame({
                '指标': ['销售额','毛利','推广费','订单数'],
                '本月': [_fmt(msum), _fmt(mmargin), _fmt(mcost),
                        f'{int(monthly["订单数"].sum()) if "订单数" in monthly.columns else "--"}'],
            }), hide_index=True, use_container_width=True)

# ============================================================
st.markdown('---')
st.caption(f'更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
