# AGENTS.md

## 项目背景

**南京建武** 企业数据看板项目。WPS 云盘（企业 ID: 615998532，群组 ID: 3055417161）存储所有源数据文件。

## WPS 云盘 API

### 认证

需要从浏览器提取 `www.kdocs.cn` 域名下的 cookies，存入 `cookies.xlsx`（Sheet2）：

| Cookie | 示例值 |
|--------|--------|
| `wps_sid` | V02SsGad7EF... |
| `kso_sid` | TKS-f0Ttzdz... |
| `csrf` | r2cXj8tpCa... |
| `uid` | 1807424518 |
| `cv` | 0kW5vyuZq... |
| `env` | prod-0 |

### 核心接口

```bash
# 文件列表（递归遍历需逐级传 parentid）
GET https://drive.wps.cn/api/v5/groups/3055417161/files?count=200&offset=0&order=asc&orderby=fname&parentid=0&with_link=true

# 获取下载链接
GET https://drive.wps.cn/api/v5/groups/3055417161/files/{file_id}/download?isblocks=0&support_checksums=md5,sha1

# 下载文件（用上一步返回的预签名URL，cookie 非必须）
GET {presigned_url}
```

请求头必须带 `Cookie` 和 `x-csrf-rand`。

### 文件读取

- **xlsx**：`openpyxl` (v3.1.5)，对 WPS 生成的文件需 monkey-patch `DataValidation.__init__`，过滤 `id`/`uid`/`sqref`/`extLst` 等未知 kwarg
- **xmind**：解压 zip → 解析 `content.xml`，namespace 为 `urn:xmind:xmap:xmlns:content:2.0`
- **ksheet/dbt/form**：WPS 专有格式，openpyxl 不支持，需在线查看或手动导出

### 在线读取（不落盘）

```python
# 流式读取，不保存本地
import io, openpyxl
wb = openpyxl.load_workbook(io.BytesIO(downloaded_bytes), data_only=True)
```

## 环境

```bash
python --version  # 3.12.10
node --version    # v24.16.0
pip install openpyxl xmindparser
```

## 文件索引

看板设计文档：`看板设计.xmind` — 三层看板架构（公司层/单品层/四平台店铺层），各层指标包括昨日汇总、销售额/毛利/趋势、环比对比、库存预警。

所有云盘文件已遍历完毕，详见项目内各 xlsx 文件的 sheet 结构。
