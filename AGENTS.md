# AGENTS.md

## 项目背景

**南京建武** 企业数据看板项目。WPS 云盘（企业 ID: 615998532，群组 ID: 3055417161）存储所有源数据文件。

## 项目架构

```
jianwu-aboard/
├── app.py              # Streamlit 主程序（6 页面看板）
├── wps_client.py       # WPS 云盘 API 客户端（认证/文件列表/下载）
├── data_loader.py      # 数据加载层（从云盘提取各平台指标，含 1h 缓存）
├── cookies.xlsx        # 认证凭据（Sheet2），不提交 git（.gitignore）
├── 看板设计.xmind       # 看板设计文档
├── requirements.txt    # streamlit, plotly, openpyxl, pandas, numpy
└── .gitignore          # cookies.xlsx + __pycache__
```

## 快速启动

```bash
pip install -r requirements.txt
streamlit run app.py
# → http://localhost:8501
```

## 项目迁移（换机器）

整个文件夹复制到新机器即可，项目完全自包含。步骤：

```bash
# 方式一：从旧机器直接拷贝整个 jianwu-aboard/ 文件夹
# 方式二：git clone + 手动复制 cookies.xlsx
git clone https://github.com/cakalyenofficial/jianwu-aboard.git
# 然后把 cookies.xlsx 复制进去（.gitignore，不会提交）

pip install -r requirements.txt
streamlit run app.py
```

⚠️ **`cookies.xlsx` 必须随文件夹一起复制**，内含 WPS 云盘认证凭据，GitHub 上无此文件。

## Streamlit Cloud 部署

代码推送 GitHub 后自动部署。需在 Streamlit Cloud 的 Secrets 中配置：

```
WPS_SID, KSO_SID, WPS_CSRF, WPS_UID, WPS_CV, WPS_ENV
```

本地运行时从 `cookies.xlsx` 读取，云端从 `st.secrets` 读取。

## 看板结构（6 页面平铺侧边栏）

| 页面 | 数据来源 | 指标 |
|------|---------|------|
| 🏢 公司层 | `001/每日汇报看板` | 昨日销售额/毛利、分店铺KPI、趋势图、月度汇总 |
| 📦 单品层 | `001/单品数据统计表` + `009/库存` | 单品明细表、毛利率、库存预警（缺货/滞销标注） |
| 🛒 天猫 | `001/天猫每日数据` | 销售额/毛利/ROI/订单数、30天趋势、月度环比 |
| 🎵 抖音 | `003/销售额-抖音CK` + `004/每日数据` | 同上 |
| 💰 拼多多 | `006/拼多多销售总和` | 同上 |
| 📦 京东 | `005/每天店铺数据下载明细` | 同上 |

## WPS 云盘 API

### 认证

从浏览器提取 `www.kdocs.cn` 域名 cookies 存入 `cookies.xlsx`（Sheet2），字段包括 `wps_sid`、`kso_sid`、`csrf`、`uid`、`cv`、`env`。

### 核心接口

```bash
# 文件列表（递归遍历逐级传 parentid）
GET https://drive.wps.cn/api/v5/groups/3055417161/files?count=200&offset=0&order=asc&orderby=fname&parentid=0&with_link=true

# 获取下载链接
GET https://drive.wps.cn/api/v5/groups/3055417161/files/{file_id}/download?isblocks=0&support_checksums=md5,sha1

# 下载（预签名URL无需cookie）
GET {presigned_url}
```

请求头必须带 `Cookie` 和 `x-csrf-rand`。

### 文件读取

- **xlsx**：`openpyxl` (v3.1.5)，WPS 文件需 monkey-patch `DataValidation.__init__`，过滤 `id`/`uid`/`sqref`/`extLst` 等未知 kwarg
- **xmind**：解压 zip → 解析 `content.xml`，namespace `urn:xmind:xmap:xmlns:content:2.0`
- **ksheet/dbt/form**：WPS 专有格式，openpyxl 不支持
- **在线读取**：`io.BytesIO(downloaded_bytes)` + `data_only=True`，不落盘

### 数据缓存

`data_loader.py` 使用 `@st.cache_data(ttl=3600)`，同一小时内重复访问不重新下载。部署 Streamlit Cloud 后重启应用可强制刷新。

## 环境

```bash
python --version  # 3.12.10
pip install streamlit plotly openpyxl pandas numpy
```
