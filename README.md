# 盈时宝计时计费系统 · YingShiBao

> 通用计时计费系统 — 电玩店 · 网吧 · 自习室 · 棋牌室 · 台球室 · 私人影院 · 茶馆 · 任何按时间收费的场所
> A universal timing & billing system for any venue that charges by time — built by a shop owner, for shop owners.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![pywebview](img.shields.io/badge/pywebview-4.x-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 概述 · Overview

盈时宝是一套**通用的计时收银系统**。它不是为某个特定行业写的——只要你的生意是按时间收费的（开个房→计时→收钱），它就能用。

它运行在店里的电脑上，店员在电脑上操作，老板用手机在同 WiFi 下也能查看营收。

- **电脑端**：原生桌面窗口（pywebview）
- **手机端**：同 WiFi 下浏览器访问电脑 IP 即可
- **数据**：存在电脑本机 SQLite，无需云端账号

Built with Flask + pywebview + SQLite. No cloud dependency — your data stays on your machine.

---

## 功能 · Features

| 功能 | 说明 |
|------|------|
| 🏠 **包间管理** | 添加/编辑/删除房间，10种分类（主机/游戏/桌游/拼豆/台球/茶馆/麻将/私人影院/自习室/其他） |
| ⏱ **计时模式** | 倒计时（30/60/120/180分钟+自定义） / 正计时 |
| 🔄 **续时** | 一键续时，自动扣除超时时间 |
| 📊 **首页看板** | 今日收入、单数、活跃计时、总收入、收入来源分布 |
| 💰 **手动记账** | 方便记录非计时收入（商品销售等） |
| 📎 **XLSX 导出** | 导出到桌面，含汇总行+分类统计 |
| 🔔 **声音提醒** | macOS 原生通知 + afplay / Windows toast + winsound |
| 📱 **手机访问** | 同 WiFi 开浏览器就能用，无需装 App |

---

## 快速开始 · Quick Start

### 开发运行

```bash
# 1. 克隆
git clone https://github.com/henson957/yingshibao.git
cd yingshibao

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python app.py
# → 浏览器打开 http://127.0.0.1:5050
```

### 桌面打包

**macOS：**
```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包（参考 盈时宝.spec）
pyinstaller 盈时宝.spec
# → dist/盈时宝.app
```

**Windows：**
```bash
# 直接双击运行
build_win.bat
# → dist/盈时宝计时计费系统/
```

---

## 目录结构 · Project Structure

```
├── app.py              # Flask 后端（核心 API + SQLite）
├── main.py             # pywebview 桌面入口 + 跨平台通知
├── templates/
│   └── index.html      # 前端 SPA（单页应用）
├── requirements.txt    # Python 依赖
├── build_win.bat       # Windows 打包脚本
├── README_WIN.txt      # Windows 打包说明
├── 盈时宝.ico           # 应用图标
└── 盈时宝.spec          # macOS PyInstaller 配置
```

---

## 技术栈 · Tech Stack

| 层 | 技术 |
|----|------|
| 后端 | Flask 3.x + SQLite |
| 桌面壳 | pywebview 4.x |
| 前端 | HTML + Vanilla JS（SPA） |
| 导出 | xlsxwriter |
| 打包 | PyInstaller |

---

## 设计理念 · Philosophy

1. **本地优先** — 数据存自己电脑，不依赖任何云服务
2. **双端覆盖** — 电脑操作 + 手机查看，同 WiFi 就行
3. **老板视角** — 看板直给营收关键指标，不绕弯
4. **开箱即用** — 装好依赖跑起来就能用，零配置

---

## License

MIT © [henson957](https://github.com/henson957)
