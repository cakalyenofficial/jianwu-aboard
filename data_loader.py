# -*- coding: utf-8 -*-
"""数据加载器 — 从 WPS 云盘拉取数据，提取结构化指标"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from wps_client import download_file, read_xlsx, list_files

# ============================================================
# 文件 ID 映射（一次加载，缓存全文件）
# ============================================================
@st.cache_data(ttl=3600)
def _get_file_id_map():
    """递归遍历云盘，返回 {文件名: file_id} 映射"""
    id_map = {}
    def walk(parentid=0):
        for f in list_files(parentid):
            id_map[f['fname']] = f['id']
            if f['ftype'] == 'folder':
                walk(f['id'])
    walk()
    return id_map

@st.cache_data(ttl=3600)
def _load_workbook(fname):
    """按文件名加载一个 xlsx workbook"""
    fmap = _get_file_id_map()
    if fname not in fmap:
        raise FileNotFoundError(f'云盘中未找到: {fname}')
    return read_xlsx(fmap[fname])

# ============================================================
# 公司层
# ============================================================
def load_company_daily():
    """从 001/每日汇报看板 提取公司每日汇总"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['每日汇报看板']
    data = list(ws.iter_rows(values_only=True))

    # 找到数据起始行 (pre_row>6 + total 关键词)
    start = 0
    for i, row in enumerate(data):
        if row[0] and '昨日' in str(row[0]).lower():
            start = i
            break

    result = {}
    for row in data[start:start+20]:
        key = str(row[0] or '').strip()
        val = row[2] if row[2] else row[1]  # 数值可能在 B 或 C 列
        if isinstance(val, str):
            continue
        if isinstance(val, (int, float)) and not np.isnan(val):
            # 清理 key 名
            key = key.replace('\n', ' ').strip()
            result[key] = float(val)

    return result

def load_company_store_breakdown():
    """从 001/每日汇报看板 提取分店铺昨日数据"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['每日汇报看板']
    data = list(ws.iter_rows(values_only=True))

    stores = {}
    store_keywords = ['天猫', '抖音', '拼多多', '京东']
    for row in data:
        key = str(row[0] or '')
        val = row[2] if isinstance(row[2], (int, float)) else row[1]
        if isinstance(val, (int, float)) and not np.isnan(val):
            for sk in store_keywords:
                if sk in key and '销售' in key:
                    if sk not in stores:
                        stores[sk] = float(val)
    return stores

def load_company_store_daily(store_name):
    """从 001 的各店铺 sheet 提取每日数据"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    sheet_map = {
        '天猫': '天猫每日数据',
        '抖音': '抖音CK旗舰店',
        '拼多多': '拼多多CK旗舰店',
        '京东': '京东CK母婴自营每日数据',
    }
    sn = sheet_map.get(store_name, '')
    if sn not in wb.sheetnames:
        return pd.DataFrame()

    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    df = _parse_daily_sheet(rows, store_name)
    return df

# ============================================================
# 单品层
# ============================================================
def load_product_stats():
    """从 001/单品数据统计表 提取单品销售数据"""
    wb = _load_workbook('001-2026公司经营销售数据.xlsx')
    ws = wb['单品数据统计表']
    rows = list(ws.iter_rows(values_only=True))

    # 找表头行
    header_row = -1
    for i, row in enumerate(rows):
        if row[0] and '单品' in str(row[0]):
            header_row = i
            break
    if header_row < 0:
        return pd.DataFrame()

    # 读数据
    records = []
    for row in rows[header_row+1:]:
        if not row[0]: continue
        name = str(row[0]).strip()
        records.append({
            '单品': name,
            '销售额': _num(row[3]),
            '销量': _num(row[4]),
            '毛利率': _num(row[5]),
            '推广费': _num(row[6]),
        })
    return pd.DataFrame(records)

def load_inventory():
    """从 009 加载库存数据"""
    wb = _load_workbook('009-进销存新系统 .xlsx')
    ws = wb['当前库存']
    rows = list(ws.iter_rows(values_only=True))

    records = []
    for row in rows[3:]:
        if not row[1]: continue
        records.append({
            '型号': str(row[1]).strip(),
            '当前库存': _num(row[2]),
            '日均销量': _num(row[3]),
        })
    return pd.DataFrame(records)

# ============================================================
# 四平台
# ============================================================
def load_tmall_daily():
    """天猫每日数据"""
    return load_company_store_daily('天猫')

def load_douyin_daily():
    """抖音 CK 每日数据: 003/销售额-抖音CK"""
    df_ck = _parse_file_simple('003-2026年抖音CK店铺数据表.xlsx', '销售额-抖音CK')
    df_mc = _parse_file_simple('004-2026年抖音名创贝适宝专卖店数据.xlsx', '每日数据')
    if not df_ck.empty and not df_mc.empty:
        df_ck = df_ck.add_suffix('_CK')
        df_mc = df_mc.add_suffix('_MC')
    return df_ck if not df_ck.empty else df_mc

def load_pdd_daily():
    """拼多多每日数据"""
    df = _parse_file_simple('006-拼多多平台数据.xlsx', '拼多多销售总和')
    if df.empty:
        df = _parse_file_simple('006-拼多多平台数据.xlsx', '拼多多黑标店')
    return df

def load_jd_daily():
    """京东每日数据: 005/平台汇总"""
    wb = _load_workbook('005-京东数据表格.xlsx')
    if '每天店铺数据下载明细' in wb.sheetnames:
        ws = wb['每天店铺数据下载明细']
        rows = list(ws.iter_rows(values_only=True))
        return _parse_daily_sheet(rows, '京东')
    return pd.DataFrame()

# ============================================================
# 辅助函数
# ============================================================
def _num(v):
    if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
        return float(v)
    return 0.0

def _parse_daily_sheet(rows, store_name):
    """通用每日数据解析：日期列 + 销售额/推广费/毛利"""
    records = []
    for row in rows:
        if not row: continue
        # 尝试检测日期（第一列）
        date_val = row[0]
        if isinstance(date_val, datetime):
            d = date_val.date()
        elif isinstance(date_val, str):
            # 跳过非日期行
            if not any(c.isdigit() for c in date_val[:10]):
                continue
            try:
                d = pd.to_datetime(date_val).date()
            except:
                continue
        else:
            continue

        # 尝试取多个数值列
        sales = _num(row[1]) if len(row) > 1 else 0
        cost = _num(row[2]) if len(row) > 2 else 0
        orders = _num(row[3]) if len(row) > 3 else 0
        margin = _num(row[4]) if len(row) > 4 else 0

        # 尝试不同列映射
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

def _parse_file_simple(fname, sheet_name):
    """从指定文件/sheet 获取每日数据"""
    try:
        wb = _load_workbook(fname)
    except:
        return pd.DataFrame()
    if sheet_name not in wb.sheetnames:
        return pd.DataFrame()
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    return _parse_daily_sheet(rows, sheet_name)
