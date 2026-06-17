# -*- coding: utf-8 -*-
"""数据加载器 — 从 WPS 云盘拉取数据，提取结构化指标"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from wps_client import download_file, read_xlsx, list_files

_WPS_EPOCH = datetime(1899, 12, 30)

# ============================================================
# 缓存
# ============================================================
@st.cache_data(ttl=86400)
def _get_file_id_map():
    id_map = {}
    def walk(parentid=0):
        for f in list_files(parentid):
            id_map[f['fname']] = f['id']
            if f['ftype'] == 'folder':
                walk(f['id'])
    walk()
    return id_map

@st.cache_data(ttl=86400)
def _load_workbook(fname):
    fmap = _get_file_id_map()
    if fname not in fmap:
        raise FileNotFoundError(f'云盘中未找到: {fname}')
    return read_xlsx(fmap[fname])

# ============================================================
# 辅助函数
# ============================================================
def _num(v):
    if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
        return float(v)
    return 0.0

def _safe_date(val):
    """兼容 WPS 序列号 / datetime / 字符串 三种日期格式"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, (int, float)):
        if 40000 < val < 100000:  # WPS 序列号范围
            return (_WPS_EPOCH + timedelta(days=int(val))).date()
        return None
    if isinstance(val, str):
        try:
            return pd.to_datetime(val).date()
        except Exception:
            return None
    return None

def _trim_future(df):
    """剔除未来日期（>昨天），保持数据截止到昨日"""
    if df.empty or '日期' not in df.columns:
        return df
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    df = df[df['日期'] <= yesterday].copy()
    return df.reset_index(drop=True)

def _parse_daily_sheet(rows, date_col=0, sales_col=1, cost_col=None,
                       orders_col=None, margin_col=None, skip_rows=0):
    """通用每日数据解析器

    参数:
        rows:     sheet.iter_rows(values_only=True) 返回的全部行
        date_col: 日期列索引（自动检测 WPS 序列号/datetime/字符串）
        sales_col: 销售额列索引
        cost_col: 推广费列索引（可选）
        orders_col: 订单数列索引（可选）
        margin_col: 毛利列索引（可选，无则按 销售额*30% 估算）
        skip_rows: 跳过前 N 行（月度汇总等）
    """
    records = []
    for row in rows[skip_rows:]:
        if not row or len(row) <= max(date_col, sales_col):
            continue
        d = _safe_date(row[date_col])
        if d is None:
            continue

        sales = _num(row[sales_col]) if sales_col is not None and len(row) > sales_col else 0
        cost = _num(row[cost_col]) if cost_col is not None and len(row) > cost_col else 0
        orders = _num(row[orders_col]) if orders_col is not None and len(row) > orders_col else 0
        margin = _num(row[margin_col]) if margin_col is not None and len(row) > margin_col else 0

        records.append({
            '日期': d,
            '销售额': sales,
            '推广费': cost,
            '订单数': orders,
            '毛利': margin if margin else sales * 0.3,
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values('日期').reset_index(drop=True)
    return df

def _finalize_daily(df):
    if df.empty:
        return df
    df = df.sort_values('日期').reset_index(drop=True)
    return _trim_future(df)

# ============================================================
# 公司层 — 每日汇报看板
# ============================================================
def load_company_daily():
    """从 001/每日汇报看板 提取公司合计 KPI"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['每日汇报看板']
    data = list(ws.iter_rows(values_only=True))

    result = {}
    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            if cell and '公司合计' in str(cell) and j == 0:
                # 读取公司合计下方 5 行指标
                for k in range(1, 6):
                    if i + k >= len(data):
                        break
                    mr = data[i + k]
                    for m in range(j, min(j + 4, len(mr) - 2)):
                        if not mr[m] or not isinstance(mr[m], str):
                            continue
                        key = str(mr[m]).strip().replace('\n', ' ')
                        # 值可能在 m+1 或 m+2（如 本月达成 的值在 col2 而非 col1）
                        val = None
                        if m + 1 < len(mr) and isinstance(mr[m + 1], (int, float)):
                            val = mr[m + 1]
                        elif m + 2 < len(mr) and isinstance(mr[m + 2], (int, float)):
                            val = mr[m + 2]
                        if val is not None and not (isinstance(val, float) and np.isnan(val)):
                            result[key] = float(val)
                return result
    return result

def load_company_store_breakdown():
    """从 001/每日汇报看板 提取分店铺昨日销售额"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['每日汇报看板']
    data = list(ws.iter_rows(values_only=True))

    platform_keywords = ['天猫', '抖音', '拼多多', '京东']

    # 第一步：预扫描所有店铺 header 位置 (row, block_start_col) -> platform
    store_positions = {}  # {(row, block_start): platform}
    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            if cell and isinstance(cell, str):
                for pk in platform_keywords:
                    if pk in str(cell):
                        # 店铺名出现在某行的头几个列之一 → 标记该 block
                        block_start = j - (j % 5)
                        # 只记录每个 block 第一次出现的店铺（最近 header）
                        if (i, block_start) not in store_positions:
                            store_positions[(i, block_start)] = pk

    # 第二步：遍历所有"昨日销售"单元格，向上找同 column block 的店铺
    stores = {}
    for row_idx, row in enumerate(data):
        for col_idx, cell in enumerate(row):
            if not cell or '昨日销售' not in str(cell):
                continue
            if col_idx + 1 >= len(row):
                continue
            val = row[col_idx + 1]
            if not isinstance(val, (int, float)) or (isinstance(val, float) and np.isnan(val)):
                continue

            block_start = col_idx - (col_idx % 5)
            # 向上查找同 block 最近的店铺 header
            for look_up in range(row_idx, -1, -1):
                if (look_up, block_start) in store_positions:
                    pk = store_positions[(look_up, block_start)]
                    stores[pk] = stores.get(pk, 0) + float(val)
                    break

    for pk in platform_keywords:
        if pk not in stores:
            stores[pk] = 0.0
    return stores

# ============================================================
# 单品层
# ============================================================
def load_product_stats():
    """从 001/单品数据统计表 提取单品汇总数据（全平台 block: col1=单品, col2=销售金额, col6=销量, col9=推广费, col12=利润率）"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['单品数据统计表']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    for row in rows:
        # 只取汇总行（col 0 == '综合' 且 col 1 有产品代码）
        if not row[0] or '综合' not in str(row[0]):
            continue
        if not row[1]:
            continue  # 跳过总计行
        name = str(row[1]).strip()
        records.append({
            '单品': name,
            '销售额': _num(row[2]) if len(row) > 2 else 0,
            '销量': _num(row[6]) if len(row) > 6 else 0,
            '毛利率': _num(row[12]) if len(row) > 12 else 0,
            '推广费': _num(row[9]) if len(row) > 9 else 0,
        })
    return pd.DataFrame(records)

def load_inventory():
    wb = _load_workbook('009-进销存新系统 .xlsx')
    ws = wb['当前库存']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    for row in rows[3:]:
        if not row[1]:
            continue
        records.append({
            '型号': str(row[1]).strip(),
            '当前库存': _num(row[2]),
            '日均销量': _num(row[3]),
        })
    return pd.DataFrame(records)

# ============================================================
# 天猫
# ============================================================
def load_tmall_daily():
    """001/天猫每日数据: col0=WPS序列号日期, col6=店铺销售额, col4=支付人数"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    if '天猫每日数据' not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb['天猫每日数据']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    for row in rows[6:]:  # 跳过前 6 行（空行 + 表头）
        if not row:
            continue
        d = _safe_date(row[0])
        if d is None:
            continue
        sales = _num(row[6]) if len(row) > 6 else 0
        orders = _num(row[4]) if len(row) > 4 else 0
        records.append({
            '日期': d,
            '销售额': sales,
            '推广费': 0,   # 天猫 sheet 无推广费列，后续可从其他来源补充
            '订单数': int(orders),
            '毛利': sales * 0.3,
        })

    df = pd.DataFrame(records)
    return _finalize_daily(df)

# ============================================================
# 抖音
# ============================================================
def load_douyin_daily():
    """003/销售额-抖音CK: col0=WPS序列号, col1=GMV, col2=广告消耗, col3=退款金额"""
    try:
        wb = _load_workbook('003-2026年抖音CK店铺数据表.xlsx')
    except Exception:
        return pd.DataFrame()

    if '销售额-抖音CK' not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb['销售额-抖音CK']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    # 跳过行0-10（月度汇总），从行11开始才是每日数据
    for row in rows[11:]:
        if not row or row[0] is None:
            continue
        d = _safe_date(row[0])
        if d is None:
            continue
        gmv = _num(row[1]) if len(row) > 1 else 0
        cost = _num(row[2]) if len(row) > 2 else 0
        refund = _num(row[3]) if len(row) > 3 else 0
        sales = gmv  # GMV 即销售额
        records.append({
            '日期': d,
            '销售额': sales,
            '推广费': cost,
            '订单数': 0,
            '毛利': max(sales - refund, 0) * 0.3,  # 用 GSV 估算毛利
        })

    df = pd.DataFrame(records)
    return _finalize_daily(df)

# ============================================================
# 拼多多
# ============================================================
def load_pdd_daily():
    """006/拼多多销售总和: col0=datetime, col1=gmv, col3=推广费, col4=利润"""
    try:
        wb = _load_workbook('006-拼多多平台数据.xlsx')
    except Exception:
        return pd.DataFrame()

    if '拼多多销售总和' not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb['拼多多销售总和']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    # 跳过行0-6（月度汇总 + 表头），行7起为每日数据
    for row in rows[7:]:
        if not row:
            continue
        d = _safe_date(row[0])
        if d is None:
            continue
        sales = _num(row[1]) if len(row) > 1 else 0
        cost = _num(row[3]) if len(row) > 3 else 0
        margin = _num(row[4]) if len(row) > 4 else 0
        records.append({
            '日期': d,
            '销售额': sales,
            '推广费': cost,
            '订单数': 0,
            '毛利': margin if margin else sales * 0.3,
        })

    df = pd.DataFrame(records)
    return _finalize_daily(df)

# ============================================================
# 京东
# ============================================================
def load_jd_daily():
    """005/每天店铺数据下载明细: SKU 级明细 → 按日汇总"""
    try:
        wb = _load_workbook('005-京东数据表格.xlsx')
    except Exception:
        return pd.DataFrame()

    if '每天店铺数据下载明细' not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb['每天店铺数据下载明细']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    for row in rows[1:]:  # 跳过表头行
        if not row or row[0] is None:
            continue
        d = _safe_date(row[0])
        if d is None:
            continue
        sales = _num(row[3]) if len(row) > 3 else 0     # col 3: 成交金额
        orders = _num(row[4]) if len(row) > 4 else 0     # col 4: 成交商品件数
        records.append({
            '日期': d,
            '销售额': sales,
            '订单数': int(orders),
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # 按日聚合（同一日期多 SKU）
    daily = df.groupby('日期', as_index=False).agg({
        '销售额': 'sum',
        '订单数': 'sum',
    })
    daily['推广费'] = 0
    daily['毛利'] = daily['销售额'] * 0.3
    daily = daily[['日期', '销售额', '推广费', '订单数', '毛利']]
    daily = daily.sort_values('日期').reset_index(drop=True)
    return _trim_future(daily)

# ============================================================
# 兜底：从 001 各子 sheet 提取每日数据（仅在主力加载器失效时使用）
# ============================================================
def load_company_store_daily(store_name):
    sheet_map = {
        '天猫': '天猫每日数据',
        '抖音': '抖音CK旗舰店',
        '拼多多': '拼多多CK旗舰店',
        '京东': '京东CK母婴自营每日数据',
    }
    sn = sheet_map.get(store_name, '')
    if not sn:
        return pd.DataFrame()
    try:
        wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    except Exception:
        return pd.DataFrame()
    if sn not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    return _finalize_daily(_parse_daily_sheet(rows, date_col=0, sales_col=6 if store_name == '天猫' else 3,
                               orders_col=4, skip_rows=6))
