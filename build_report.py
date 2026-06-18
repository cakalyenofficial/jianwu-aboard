# -*- coding: utf-8 -*-
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import data_loader as dl
from wps_client import read_xlsx
from datetime import datetime, timedelta
import pandas as pd, numpy as np

today = datetime.now().date()
yesterday = today - timedelta(days=1)

print('Loading data...')
kpis = dl.load_company_daily()
stores = dl.load_company_store_breakdown()
df_tm = dl.load_tmall_daily(); df_dy = dl.load_douyin_daily()
df_pdd = dl.load_pdd_daily(); df_jd = dl.load_jd_daily()
products = dl.load_product_stats(); inventory = dl.load_inventory()

# Tmall monthly from 002
tm_monthly = {}
try:
    fmap = dl._get_file_id_map()
    fn2 = [k for k in fmap if '002' in k and k.endswith('.xlsx')][0]
    wb2 = read_xlsx(fmap[fn2])
    ws2 = wb2['店铺销售数据源']
    r2 = list(ws2.iter_rows(values_only=True))
    for row in r2[2:10]:
        k = str(row[1] or '').strip(); v = row[3]
        if k and isinstance(v, (int, float)): tm_monthly[k] = float(v)
except Exception as e:
    print(f'  WARN: 002 failed: {e}')

# ---- helpers ----
def F(v):
    if isinstance(v, (int, float)):
        if abs(v) >= 100: return '\u00a5' + f'{v:,.0f}'
        return f'{v:.1f}'
    return str(v)

def CH(v):
    if v > 0: return '<span class=up>\u25b2' + f'{v:.1f}%</span>'
    if v < 0: return '<span class=down>\u25bc' + f'{abs(v):.1f}%</span>'
    return ''

def LK(df, col):
    if df.empty or col not in df.columns or len(df) < 2: return 0, 0
    a, b = df.iloc[-1], df.iloc[-2]
    av = a[col] if not pd.isna(a[col]) else 0
    bv = b[col] if not pd.isna(b[col]) else 0
    chg = (av / bv - 1) * 100 if bv else 0
    return float(av), chg

def LD(df):
    if df.empty: return today
    return df.iloc[-1][df.columns[0]]

def CJ(df, name, title=''):
    if df.empty or len(df.columns) < 2: return '{}'
    xc, yc = df.columns[0], df.columns[1]
    return json.dumps(dict(data=[dict(x=df[xc].astype(str).tolist(), y=df[yc].fillna(0).round(2).tolist(),
        type='scatter', mode='lines+markers', name=name, line=dict(width=2), marker=dict(size=5))],
        layout=dict(title=title, height=300, margin=dict(l=50, r=20, t=40, b=30),
        template='plotly_white', hovermode='x unified')))

def MC(df, title=''):
    if df.empty: return '{}'
    sc = [c for c in df.columns if c not in ['date', 'sales', 'margin', '_mth']]
    clrs = ['#667eea', '#4facfe', '#f5576c', '#38ef7d']
    tr = []
    for i, c in enumerate(sc):
        tr.append(dict(x=df['date'].astype(str).tolist(), y=df[c].fillna(0).round(2).tolist(),
            type='scatter', mode='lines+markers', name=c, line=dict(width=2, color=clrs[i % 4]), marker=dict(size=4)))
    return json.dumps(dict(data=tr, layout=dict(title=title, height=300,
        margin=dict(l=50, r=20, t=40, b=30), template='plotly_white', hovermode='x unified',
        legend=dict(orientation='h', y=1.15))))

# ---- company daily ----
parts = []
for dfs, tag in [(df_tm, 'TM'), (df_dy, 'DY'), (df_pdd, 'PDD'), (df_jd, 'JD')]:
    if not dfs.empty and len(dfs.columns) >= 2:
        s = dfs.iloc[:, [0, 1]].copy(); s.columns = ['date', 'sales']; parts.append(s)
if parts:
    raw = pd.concat(parts)
    cd = raw.groupby('date', as_index=False)['sales'].sum().sort_values('date').reset_index(drop=True)
    cd['margin'] = cd['sales'] * 0.30
    for dfs, tag in [(df_tm, 'TM'), (df_dy, 'DY'), (df_pdd, 'PDD'), (df_jd, 'JD')]:
        if not dfs.empty and len(dfs.columns) >= 2:
            s2 = dfs.iloc[:, [0, 1]].copy(); s2.columns = ['date', tag]
            cd = pd.merge(cd, s2, on='date', how='left')
    cd = cd.fillna(0)
else:
    cd = pd.DataFrame()

cy = kpis.get('昨日销售', 0)
cm = kpis.get('本月达成', 0)
mr = kpis.get('毛利率', 0) or 30
ldate = max([LD(df) for df in [df_tm, df_dy, df_pdd, df_jd] if not df.empty] + [today])

# ---- platform KPIs ----
pk = {}
for tag, name, df in [('TM', '天猫', df_tm), ('DY', '抖音', df_dy), ('PDD', '拼多多', df_pdd), ('JD', '京东', df_jd)]:
    c1 = df.columns[1] if not df.empty and len(df.columns) > 1 else None
    c2 = df.columns[2] if not df.empty and len(df.columns) > 2 else None
    c3 = df.columns[3] if not df.empty and len(df.columns) > 3 else None
    s, sc = LK(df, c1) if c1 else (0, 0)
    c, _ = LK(df, c2) if c2 else (0, 0)
    o, _ = LK(df, c3) if c3 else (0, 0)
    bo = stores.get(name, s)
    mo = df[c1].sum() if c1 else 0
    mc = df[c2].sum() if c2 else 0
    mg = df[df.columns[4]].sum() if not df.empty and len(df.columns) > 4 else mo * 0.3
    roi = bo / max(c, 1) if c else 0
    pk[tag] = dict(sales=bo, change=sc, cost=c, orders=int(o), roi=roi, month=mo, mcost=mc, mg=mg, df=df)

# ---- Tmall KPI table ----
tg = tm_monthly.get('GSV', 0)
tp = tm_monthly.get('利润目标', 0)
tpp = (tp / tg * 100) if tg else 0
tc = tm_monthly.get('站内推广费', 0) + tm_monthly.get('站外推广费', 0)
tcp = (tc / tg * 100) if tg else 0

def SC(df, c):
    if df is None or df.empty or c >= len(df.columns): return 0
    return float(df.iloc[:, c].sum())

tdc = df_tm.columns if not df_tm.empty else []
ydf = df_tm[df_tm[tdc[0]] == yesterday] if not df_tm.empty and len(tdc) > 0 else None
ys = SC(ydf, 1); yp = SC(ydf, 4); yc = SC(ydf, 2)
d7f = df_tm[df_tm[tdc[0]] >= yesterday - timedelta(days=7)] if not df_tm.empty and len(tdc) > 0 else None
d7s = SC(d7f, 1); d7p = SC(d7f, 4); d7c = SC(d7f, 2)

def KR(lbl, g, pr, pct_p, ct, pct_c, chg=0):
    return '<tr><td class=rl>{}</td><td class=num>{}<br><span class=sc>{}</span></td><td class=num>{}</td><td class=num>{}%</td><td class=num>{}</td><td class=num>{}%</td></tr>'.format(
        lbl, F(g), CH(chg), F(pr), round(pct_p, 1), F(ct), round(pct_c, 1))

tm_tbl = '<table class=kt><thead><tr><th></th><th>GSV</th><th>利润额</th><th>利润率</th><th>推广总额</th><th>推广占比</th></tr></thead><tbody>'
tm_tbl += KR('当月', tg, tp, tpp, tc, tcp, 0)
tm_tbl += KR('近7天', d7s, d7p, d7p/d7s*100 if d7s else 0, d7c, d7c/d7s*100 if d7s else 0)
tm_tbl += KR('昨日', ys, yp, yp/ys*100 if ys else 0, yc, yc/ys*100 if ys else 0)
tm_tbl += '</tbody></table>'

# ---- charts ----
cc = CJ(cd.tail(30), '总销售额', '近30天总销售额趋势')
cmc = MC(cd.tail(30), '各平台30天销售额对比')
ct = CJ(df_tm.tail(30) if not df_tm.empty else pd.DataFrame(), '天猫', '天猫近30天趋势')
cdy = CJ(df_dy.tail(30) if not df_dy.empty else pd.DataFrame(), '抖音', '抖音近30天趋势')
cp = CJ(df_pdd.tail(30) if not df_pdd.empty else pd.DataFrame(), '拼多多', '拼多多近30天趋势')
cj = CJ(df_jd.tail(30) if not df_jd.empty else pd.DataFrame(), '京东', '京东近30天趋势')

c7d = '{}'
if d7f is not None and not d7f.empty and len(tdc) > 1:
    d7t = d7f.tail(8)
    tr7 = [dict(x=d7t[tdc[0]].astype(str).tolist(), y=d7t[tdc[1]].fillna(0).round(0).tolist(),
        type='scatter', mode='lines+markers', name='GSV', line=dict(width=2, color='#667eea'), marker=dict(size=5))]
    if len(tdc) > 4:
        tr7.append(dict(x=d7t[tdc[0]].astype(str).tolist(), y=d7t[tdc[4]].fillna(0).round(0).tolist(),
            type='scatter', mode='lines+markers', name='毛利', line=dict(width=2, color='#38ef7d'), marker=dict(size=5)))
    c7d = json.dumps(dict(data=tr7, layout=dict(title='近7天销售额&毛利趋势', height=300,
        margin=dict(l=50, r=20, t=40, b=30), template='plotly_white', hovermode='x unified')))

cmth = '{}'
if not df_tm.empty and len(tdc) > 1:
    df_tm['_mth'] = df_tm[tdc[0]].apply(lambda x: x.strftime('%y/%m'))
    ms = df_tm.groupby('_mth')[tdc[1]].sum().tail(6)
    mm = df_tm.groupby('_mth')[tdc[4]].sum().tail(6) if len(tdc) > 4 else ms * 0.3
    cmth = json.dumps(dict(data=[
        dict(x=ms.index.tolist(), y=ms.values.round(0).tolist(), type='bar', name='GSV', marker=dict(color='#667eea')),
        dict(x=mm.index.tolist(), y=mm.values.round(0).tolist(), type='bar', name='毛利', marker=dict(color='#38ef7d'))],
        layout=dict(title='近6个月GSV与毛利对比', height=320, barmode='group',
        margin=dict(l=50, r=20, t=40, b=30), template='plotly_white', legend=dict(orientation='h', y=1.15))))

# ---- products ----
prs = ''; alr = ''
if not products.empty:
    pn = products.columns[0]; ps = products.columns[1]; pq = products.columns[2]
    pm = products.columns[3]; pc = products.columns[4]
    if not inventory.empty:
        ins = inventory.columns[0]; ist = inventory.columns[1]; idsl = inventory.columns[2]
        products['mk'] = products[pn].str.extract(r'(CK\d+)', expand=False)
        inventory['mk'] = inventory[ins].str.extract(r'(CK\d+)', expand=False)
        products = products.merge(inventory[['mk', ist, idsl]], on='mk', how='left')
        products['stk'] = products[ist].fillna(0); products['dsl'] = products[idsl].fillna(1)
    else:
        products['stk'] = 0; products['dsl'] = 1
    products['sd'] = (products['stk'] / products['dsl'].replace(0, 1)).round(0)
    products = products[products[ps] > 0]
    for _, r in products.iterrows():
        cs = 'warn' if r['sd'] < 7 else ('ok' if r['sd'] < 60 else 'over')
        st = '\u26a0\ufe0f\u7f3a\u8d27' if r['sd'] < 7 else ('\u2705\u6b63\u5e38' if r['sd'] < 60 else '\U0001f4e6\u6ede\u9500')
        prs += '<tr><td>{}</td><td class=num>{}</td><td class=num>{}</td><td class=num>{}%</td><td class=num>{}</td><td class=num>{}</td><td class=num>{}天</td><td class={}>{}</td></tr>'.format(
            r[pn], F(r[ps]), int(r[pq]), round(r[pm], 1), F(r[pc]), int(r['stk']), int(r['sd']), cs, st)
        if r['sd'] < 7:
            alr += '<div class=alert>\u26a0\ufe0f {} \u2014 库存仅剩{}件({}天)</div>'.format(r[pn], int(r['stk']), int(r['sd']))
if not alr:
    alr = '<p class=ok-text>\u2705 所有单品库存充足</p>'

print('Building HTML...')

# ---- store detail table ----
def SD(tag):
    i = pk.get(tag, {})
    return '<table><tr><th>指标</th><th>最新</th><th>本月累计</th></tr>' + \
        '<tr><td>销售额</td><td class=num>{}</td><td class=num>{}</td></tr>'.format(F(i.get('sales',0)), F(i.get('month',0))) + \
        '<tr><td>毛利</td><td class=num>--</td><td class=num>{}</td></tr>'.format(F(i.get('mg',0))) + \
        '<tr><td>推广费</td><td class=num>{}</td><td class=num>{}</td></tr>'.format(F(i.get('cost',0)), F(i.get('mcost',0))) + \
        '<tr><td>ROI</td><td class=num>{:.1f}</td><td class=num>--</td></tr></table>'.format(i.get('roi',0))

# ---- HTML ----
html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>南京建武数据看板</title>
<script src="https://cdn.plot.ly/plotly-3.1.0.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f6;color:#1a1a2e;display:flex;min-height:100vh}
.sidebar{width:220px;background:linear-gradient(180deg,#1a1a2e 0%,#16213e 100%);color:#fff;padding:20px 0;flex-shrink:0;display:flex;flex-direction:column}
.sidebar h2{padding:0 20px 16px;font-size:17px;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:8px}
.sidebar .tab{display:block;padding:12px 20px;color:rgba(255,255,255,.7);cursor:pointer;font-size:14px;border-left:3px solid transparent;transition:all .15s;text-decoration:none}
.sidebar .tab:hover{background:rgba(255,255,255,.05);color:#fff}
.sidebar .tab.active{background:rgba(255,255,255,.1);color:#fff;border-left-color:#667eea;font-weight:600}
.sidebar .info{margin-top:auto;padding:20px;font-size:11px;color:rgba(255,255,255,.4)}
.main{flex:1;overflow-y:auto;padding:24px;max-width:1200px}
.kpi-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.kpi-card{flex:1;min-width:180px;border-radius:12px;padding:18px;color:#fff}
.kpi-card.purple{background:linear-gradient(135deg,#667eea,#764ba2)}
.kpi-card.green{background:linear-gradient(135deg,#11998e,#38ef7d)}
.kpi-card.orange{background:linear-gradient(135deg,#f093fb,#f5576c)}
.kpi-card.blue{background:linear-gradient(135deg,#4facfe,#00f2fe)}
.kpi-label{font-size:12px;opacity:.85}
.kpi-value{font-size:24px;font-weight:700;margin:4px 0}
.kpi-chg{font-size:11px;opacity:.9;min-height:15px}
.up{color:#90ff90}.down{color:#ff9090}
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.chart-full{margin-bottom:16px}
@media(max-width:900px){.chart-row{grid-template-columns:1fr}.kpi-card{min-width:140px}body{flex-direction:column}.sidebar{width:100%;flex-direction:row;overflow-x:auto;padding:10px}.sidebar h2{display:none}}
.chart-box{background:#fff;border-radius:12px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.tab-content{display:none}
.tab-content.active{display:block}
.section-title{font-size:16px;font-weight:600;margin:24px 0 12px;padding-left:10px;border-left:4px solid #667eea}
.subtab{display:inline-block;padding:8px 20px;border:1px solid #ddd;background:#fff;border-radius:6px;cursor:pointer;font-size:13px;margin-right:8px;transition:all .15s}
.subtab.active{background:#667eea;color:#fff;border-color:#667eea}
.subtab:hover:not(.active){background:#f0f0f0}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px}
th{background:#f8f9fc;padding:12px 14px;text-align:left;font-size:13px;font-weight:600;color:#555;border-bottom:2px solid #eee}
td{padding:10px 14px;font-size:13px;border-bottom:1px solid #f0f0f0}
.num{text-align:right;font-variant-numeric:tabular-nums}
.warn{color:#e74c3c;font-weight:600}.ok{color:#27ae60}.over{color:#e67e22}
.ok-text{color:#27ae60;font-weight:600;padding:10px 0}
.alert{background:#fff3cd;padding:10px 16px;border-radius:8px;margin:8px 0;border-left:4px solid #ffc107;font-size:13px}
.kt{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px}
.kt .rl{font-weight:600;background:#f8f9fc;font-size:13px}
.sc{font-size:10px;opacity:.7}
</style>
</head>
<body>
<div class="sidebar">
    <h2>&#x1f4ca; 南京建武</h2>
    <a class="tab active" onclick="ST('company')">&#x1f3e2; 公司层</a>
    <a class="tab" onclick="ST('product')">&#x1f4e6; 单品层</a>
    <a class="tab" onclick="ST('tmall')">&#x1f6d2; 天猫</a>
    <a class="tab" onclick="ST('douyin')">&#x1f3b5; 抖音</a>
    <a class="tab" onclick="ST('pdd')">&#x1f4b0; 拼多多</a>
    <a class="tab" onclick="ST('jd')">&#x1f4e6; 京东</a>
    <div class="info">数据截止: ''' + str(ldate) + '<br>生成: ' + datetime.now().strftime('%m-%d %H:%M') + '''</div>
</div>
<div class="main">
    <div id="tab-company" class="tab-content active">
        <div class="section-title">&#x1f4c8; 公司总览</div>
        <div class="kpi-row">
            <div class="kpi-card purple"><div class="kpi-label">昨日总销售额</div><div class="kpi-value">''' + F(cy) + '''</div></div>
            <div class="kpi-card green"><div class="kpi-label">昨日总毛利</div><div class="kpi-value">''' + F(cy * 0.3) + '''</div></div>
            <div class="kpi-card blue"><div class="kpi-label">毛利率</div><div class="kpi-value">''' + f'{mr:.1f}%' + '''</div></div>
            <div class="kpi-card orange"><div class="kpi-label">本月累计</div><div class="kpi-value">''' + F(cm) + '''</div></div>
        </div>
        <div class="kpi-row">
            <div class="kpi-card purple"><div class="kpi-label">天猫</div><div class="kpi-value">''' + F(stores.get('天猫', 0)) + '''</div></div>
            <div class="kpi-card blue"><div class="kpi-label">抖音</div><div class="kpi-value">''' + F(stores.get('抖音', 0)) + '''</div></div>
            <div class="kpi-card orange"><div class="kpi-label">拼多多</div><div class="kpi-value">''' + F(stores.get('拼多多', 0)) + '''</div></div>
            <div class="kpi-card green"><div class="kpi-label">京东</div><div class="kpi-value">''' + F(stores.get('京东', 0)) + '''</div></div>
        </div>
        <div class="chart-row"><div class="chart-box"><div id="chart_company"></div></div><div class="chart-box"><div id="chart_multi"></div></div></div>
    </div>
    <div id="tab-product" class="tab-content">
        <div class="section-title">&#x1f4e6; 单品明细</div>
        <table><thead><tr><th>单品</th><th>销售额</th><th>销量</th><th>毛利率</th><th>推广费</th><th>库存</th><th>库存天数</th><th>状态</th></tr></thead><tbody>''' + prs + '''</tbody></table>
        <p style="margin:8px 0;color:#999;font-size:12px;">共 ''' + str(len(products)) + ''' 个在售单品</p>
        <div class="section-title">&#x26a0;&#xfe0f; 库存预警</div>''' + alr + '''
    </div>
    <div id="tab-tmall" class="tab-content">
        <div class="section-title">&#x1f6d2; 天猫平台 (002数据源)</div>
        <div style="margin-bottom:16px">
            <button class="subtab active" onclick="ST2('store')">&#x1f3ec; 店铺数据</button>
            <button class="subtab" onclick="ST2('product')">&#x1f4e6; 单品数据</button>
        </div>
        <div id="tmall-store">''' + tm_tbl + '''
        <div class="chart-row"><div class="chart-box"><div id="chart_7d"></div></div><div class="chart-box"><div id="chart_mth"></div></div></div>
        <div class="chart-row"><div class="chart-box"><div id="chart_tmall"></div></div><div class="chart-box">''' + SD('TM') + '''</div></div>
        </div>
        <div id="tmall-product" style="display:none"><p style="color:#999;">单品数据加载中...</p></div>
    </div>
    <div id="tab-douyin" class="tab-content">
        <div class="section-title">&#x1f3b5; 抖音平台 (三店合并)</div>
        <div class="kpi-row">
            <div class="kpi-card purple"><div class="kpi-label">销售额</div><div class="kpi-value">''' + F(pk.get('DY', {}).get('sales', 0)) + '''</div></div>
            <div class="kpi-card green"><div class="kpi-label">本月累计</div><div class="kpi-value">''' + F(pk.get('DY', {}).get('month', 0)) + '''</div></div>
            <div class="kpi-card blue"><div class="kpi-label">ROI</div><div class="kpi-value">''' + f'{pk.get("DY",{}).get("roi",0):.1f}' + '''</div></div>
            <div class="kpi-card orange"><div class="kpi-label">推广费</div><div class="kpi-value">''' + F(pk.get('DY', {}).get('cost', 0)) + '''</div></div>
        </div>
        <div class="chart-row"><div class="chart-box"><div id="chart_douyin"></div></div><div class="chart-box">''' + SD('DY') + '''</div></div>
    </div>
    <div id="tab-pdd" class="tab-content">
        <div class="section-title">&#x1f4b0; 拼多多平台</div>
        <div class="kpi-row">
            <div class="kpi-card purple"><div class="kpi-label">销售额</div><div class="kpi-value">''' + F(pk.get('PDD', {}).get('sales', 0)) + '''</div></div>
            <div class="kpi-card green"><div class="kpi-label">本月累计</div><div class="kpi-value">''' + F(pk.get('PDD', {}).get('month', 0)) + '''</div></div>
            <div class="kpi-card blue"><div class="kpi-label">ROI</div><div class="kpi-value">''' + f'{pk.get("PDD",{}).get("roi",0):.1f}' + '''</div></div>
            <div class="kpi-card orange"><div class="kpi-label">推广费</div><div class="kpi-value">''' + F(pk.get('PDD', {}).get('cost', 0)) + '''</div></div>
        </div>
        <div class="chart-row"><div class="chart-box"><div id="chart_pdd"></div></div><div class="chart-box">''' + SD('PDD') + '''</div></div>
    </div>
    <div id="tab-jd" class="tab-content">
        <div class="section-title">&#x1f4e6; 京东平台</div>
        <div class="kpi-row">
            <div class="kpi-card purple"><div class="kpi-label">销售额</div><div class="kpi-value">''' + F(pk.get('JD', {}).get('sales', 0)) + '''</div></div>
            <div class="kpi-card green"><div class="kpi-label">本月累计</div><div class="kpi-value">''' + F(pk.get('JD', {}).get('month', 0)) + '''</div></div>
            <div class="kpi-card blue"><div class="kpi-label">ROI</div><div class="kpi-value">''' + f'{pk.get("JD",{}).get("roi",0):.1f}' + '''</div></div>
            <div class="kpi-card orange"><div class="kpi-label">推广费</div><div class="kpi-value">''' + F(pk.get('JD', {}).get('cost', 0)) + '''</div></div>
        </div>
        <div class="chart-row"><div class="chart-box"><div id="chart_jd"></div></div><div class="chart-box">''' + SD('JD') + '''</div></div>
    </div>
</div>
<script>
function ST(n){
    document.querySelectorAll(".tab").forEach(function(t){t.classList.remove("active")});
    document.querySelectorAll(".tab-content").forEach(function(c){c.classList.remove("active")});
    document.getElementById("tab-"+n).classList.add("active");
    var tabs=document.querySelectorAll(".tab");
    tabs.forEach(function(t){if(t.textContent.includes(n))t.classList.add("active")});
    window.dispatchEvent(new Event("resize"));
}
function ST2(v){
    document.getElementById("tmall-store").style.display=v==="store"?"block":"none";
    document.getElementById("tmall-product").style.display=v==="product"?"block":"none";
    document.querySelectorAll(".subtab").forEach(function(b){b.classList.remove("active")});
    if(v==="store")document.querySelectorAll(".subtab")[0].classList.add("active");
    else document.querySelectorAll(".subtab")[1].classList.add("active");
    window.dispatchEvent(new Event("resize"));
}
var charts=[
    ["chart_company", ''' + cc + '''],["chart_multi", ''' + cmc + '''],["chart_7d", ''' + c7d + '''],["chart_mth", ''' + cmth + '''],["chart_tmall", ''' + ct + '''],["chart_douyin", ''' + cdy + '''],["chart_pdd", ''' + cp + '''],["chart_jd", ''' + cj + ''']
];
charts.forEach(function(c){
    if(c[1]&&c[1].data)Plotly.newPlot(c[0],c[1].data,c[1].layout,{responsive:true});
    else document.getElementById(c[0]).innerHTML='<p style="color:#999;text-align:center;padding:80px;">暂无数据</p>';
});
</script>
</body>
</html>'''

with open('report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Done! report.html ({os.path.getsize("report.html")/1024:.0f} KB)')
print(f'Latest data: {ldate}')
