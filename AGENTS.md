# AGENTS.md

## 项目背景

**南京建武** 企业数据看板项目。WPS 云盘（企业 ID: 615998532，群组 ID: 3055417161）存储所有源数据文件。

## 项目架构

```
jianwu-aboard/
├── app.py              # Streamlit 主程序（6 页面看板）
├── build_report.py     # 静态 HTML 报表生成器（离线可用）
├── report.html         # 生成的静态看板（373KB，双击浏览器打开）
├── wps_client.py       # WPS 云盘 API 客户端（认证/文件列表/下载）
├── data_loader.py      # 数据加载层（从云盘提取各平台指标，含 24h 缓存）
├── scan_all.py         # 云盘全量文件扫描工具
├── cookies.xlsx        # 认证凭据（Sheet2），不提交 git（.gitignore）
├── requirements.txt    # streamlit, plotly, openpyxl, pandas, numpy
└── .gitignore          # cookies.xlsx + __pycache__
```

## 快速启动

```bash
pip install -r requirements.txt

# 方式一：静态 HTML（双击浏览器打开，无需服务端）
python build_report.py
# → 双击 report.html

# 方式二：Streamlit 本地服务
streamlit run app.py
# → http://localhost:8501
```

## 每日更新数据

```bash
cd C:\Users\91756\opencode\jianwu-aboard
python build_report.py
# 刷新 report.html 页面即可查看最新数据
```

## 项目迁移（换机器）

```bash
# 方式一：从旧机器直接拷贝整个 jianwu-aboard/ 文件夹
# 方式二：git clone + 手动复制 cookies.xlsx
git clone https://github.com/cakalyenofficial/jianwu-aboard.git
# 然后把 cookies.xlsx 复制进去（.gitignore，不会提交）

pip install -r requirements.txt
python build_report.py          # 生成静态看板
# 或 streamlit run app.py       # 启动 Streamlit 服务
```

## 看板结构（6 标签分层）

| 页面 | 数据来源 | 指标 |
|------|---------|------|
| 🏢 公司层 | `001/每日汇报看板` + 四平台日数据汇总 | 昨日销售额/毛利、分店铺KPI、毛利率、本月累计、趋势图 |
| 📦 单品层 | `001/单品数据统计表` + `009/进销存` | 单品明细表、毛利率、库存天数、库存预警 |
| 🛒 天猫 | `001/天猫每日数据`(日趋势) + `002/店铺销售数据源`(月度) | **三层KPI**（当月/近7天/昨日各5项）、7天折线图、6月柱状图、30天趋势 |
| 🎵 抖音 | `003` 三店合并（CK旗舰+折叠车+微瑕） | 销售额/ROI/推广费、30天趋势、月度汇总 |
| 💰 拼多多 | `006/拼多多销售总和` | 同上 |
| 📦 京东 | `005/每天店铺数据下载明细` → 按日聚合 | 同上 |

## 天猫专属看板（v3 新增）

天猫页有两层子标签：

### 店铺数据
- 三层 KPI 表（当月 / 近7天 / 昨日）× 五列（GSV、利润额、利润率、推广总额、推广占比）
- 7 天销售额 & 毛利双轴折线图
- 近 6 个月 GSV vs 毛利柱状对比图
- 30 天趋势 + 月度汇总表
- 数据源：月度数据来自 `002-天猫销售数据/店铺销售数据源`，日数据来自 `001/天猫每日数据`

### 单品数据（待开发）
- 数据源：`002/单品数据明细`（567列 × 1297行）
- 产品：CK09(3链接) CK08(3链接) CK06 L1 K01 L2 K7

## 抖音三店合并（v3 修复）

`003-2026年抖音CK店铺数据表.xlsx` 三个 sheet：
| Sheet | 店铺名 | skip_rows | cost列 |
|-------|--------|-----------|--------|
| 销售额-抖音CK | 抖音CK旗舰店 | 11 | col2 |
| 销售额-抖音折叠车 | 抖音折叠自行车旗舰店 | 4 | col4 |
| 销售额-抖音CK微瑕 | 抖音CK微瑕店 | 9 | col2 |

三店每日数据按日期 `groupby sum` 合并。

## 缓存策略

| 机制 | 位置 | 说明 |
|------|------|------|
| `@st.cache_data(ttl=86400)` | data_loader.py | 文件映射和 workbook 缓存 24h |
| 每日 10:00 自动刷新 | app.py sidebar | 首次访问 ≥10:00 自动 `st.cache_data.clear()` |
| 🔄 手动刷新按钮 | app.py sidebar | 即时清缓存重载 |
| `build_report.py` | 独立脚本 | 每次运行重新拉取全量数据 |

## 数据加载关键修复（2026-06-18）

### WPS 序列号日期转换
WPS Excel 日期以整数序列号存储（如 45901），需转换为 Python date：
```python
_WPS_EPOCH = datetime(1899, 12, 30)
d = _WPS_EPOCH + timedelta(days=int(serial))
```
`_safe_date()` 兼容序列号/datetime/字符串三种格式。

### 各平台列映射

| 平台 | 文件/Sheet | 日期列 | 销售额列 | 推广费列 | 特殊处理 |
|------|-----------|--------|---------|---------|---------|
| 天猫 | 001/天猫每日数据 | col0(序列号) | col6 | 无(填0) | 跳过前6行 |
| 抖音CK | 003/销售额-抖音CK | col0(序列号) | col1(GMV) | col2 | 跳过前11行(月度汇总) |
| 抖音折叠车 | 003/销售额-抖音折叠车 | col0(序列号) | col1 | col4 | 跳过前4行 |
| 抖音微瑕 | 003/销售额-抖音CK微瑕 | col0(序列号) | col1 | col2 | 跳过前9行 |
| 拼多多 | 006/拼多多销售总和 | col0(datetime) | col1(gmv) | col3 | 跳过前7行(月度+表头) |
| 京东 | 005/每天店铺数据下载明细 | col0(datetime) | col3(成交金额) | 无 | SKU明细→按日groupby sum聚合 |

### 日期过滤
`_trim_future()` 剔除 > 昨日的未来日期；`daily_kpis()` 按机器日期昨日精确匹配，数据未更新时回填0。

### 每日汇报看板解析
- `load_company_daily()`：扫描「公司合计」block 全列（公司合计在 col 0-4），支持值在 col+1 或 col+2
- `load_company_store_breakdown()`：预扫描店铺 header 位置，按 column block 精确匹配（避免错配到「抖音投流花费」等非店铺名单元格）

### 单品统计表
- `load_product_stats()`：解析「综合」汇总行，新列映射：col1=单品, col2=销售金额, col6=销量, col9=推广费, col12=利润率

## WPS 云盘 API

### 认证与文件结构
从浏览器提取 `www.kdocs.cn` 域名 cookies 存入 `cookies.xlsx`（Sheet2）。

根目录共 26 项（8 文件夹 + 18 文件），核心数据文件：
001~014 系列 xlsx + 看板.ksheet + 建武官方号.xlsx 等。

### 核心接口
```bash
GET https://drive.wps.cn/api/v5/groups/3055417161/files?count=200&offset=0&order=asc&orderby=fname&parentid=0&with_link=true
GET https://drive.wps.cn/api/v5/groups/3055417161/files/{file_id}/download?isblocks=0&support_checksums=md5,sha1
GET {presigned_url}
```

### 文件读取
- **xlsx**：`openpyxl` (v3.1.5)，monkey-patch `DataValidation.__init__` 过滤未知 kwarg
- **ksheet/dbt/form**：WPS 专有格式，openpyxl 不支持
- **在线读取**：`io.BytesIO(downloaded_bytes)` + `data_only=True`，不落盘

## Streamlit Cloud 部署

代码推送 GitHub 后自动部署。Secrets 配置：
```
WPS_SID = V02SsGad7EFyvNVNe-nyHlOEQIoZcWc00ae9f21e006bbb1c06
KSO_SID = TKS-f0Ttzdz_Kp7rhG9M0poTTKS7fKoAKQKSylmLgwfDKyoaTI_DiNB8SR2Ie_UTIrbesWNoYXQFR7NFIQoUZ8_biS6yvNaN3EnyHuOSQIos1W1-T2KwYWU5s9IxsUf9v4FHTSrfWrIIKQ...
WPS_CSRF = r2cXj8tpCahy3CAJP4r3Z23EnbARZeFe
WPS_UID = 1807424518
WPS_CV = 0kW5vyuZq0Mr9j2EUcuMG1zcAtq0Z9gXxiv6kCXmO4u...
WPS_ENV = prod-0
```

部署地址：`https://jianwu-aboard-fuswnseqms3jueozhfwd7q.streamlit.app`

注意：`wps_client.py` 优先读 `st.secrets`，缺失时回退本地 `cookies.xlsx`。Secrets 配置不对会报 `FileNotFoundError: cookies.xlsx` 因为该文件已 gitignore。

## 环境

```bash
python --version  # 3.12.10
pip install streamlit plotly openpyxl pandas numpy
```

## 已知限制

1. **GitHub 推送不稳定**：当前机器到 GitHub HTTPS 443 端口偶发 `Connection reset`，SSH key 未配置
2. **静态 HTML 源文件编码**：`build_report.py` 中文字符需用 `\uXXXX` 转义，直接写中文可能被某些工具损坏
3. **单品数据明细**（002/单品数据明细，567列 × 1297行）：天猫单品子页待开发
4. **拼多多/京东**：店铺级看板仍用原始布局，未做天猫式的三层 KPI 增强
