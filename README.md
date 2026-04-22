# 途强GPS转Traccar - Home Assistant 集成

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/lambilly/ha_tuqiang_traccar)](https://github.com/lambilly/ha_tuqiang_traccar/releases)
[![License](https://img.shields.io/github/license/lambilly/ha_tuqiang_traccar)](LICENSE)

将途强物联（[www.tuqiang.net](https://www.tuqiang.net)）或途强在线（[www.tuqiang123.com](https://www.tuqiang123.com)）GPS定位设备的位置数据实时转发至您自建的 **Traccar** 服务器。

本集成以轻量级后台服务形式运行，**不会在 Home Assistant 中创建任何实体**，仅负责定时获取途强平台设备位置并通过 Traccar 的 OsmAnd 协议上报。

---

## ✨ 功能特点

- ✅ 支持途强物联（tuqiang.net）和途强在线（tuqiang123.com）双平台
- ✅ 配置时可选择平台，支持添加多个不同平台账号
- ✅ 自动获取账号下所有设备列表，可自由勾选需要转发的设备
- ✅ 自定义 Traccar 服务器地址（支持 HTTP/HTTPS）
- ✅ 可选设备标识前缀，便于多车管理
- ✅ 可配置上报间隔（10～3600 秒）
- ✅ 纯后台运行，零实体占用

---

## 📦 安装

### 方式一：通过 HACS 自定义仓库（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在 HACS 中点击「集成」→ 右上角菜单 →「自定义存储库」
3. 填写仓库地址：`https://github.com/lambilly/ha_tuqiang_traccar`，类别选择「集成」
4. 点击添加，然后在 HACS 中搜索「途强GPS转Traccar」并安装
5. 重启 Home Assistant

### 方式二：手动安装

1. 下载本仓库最新 Release 中的 `tuqiang_traccar.zip` 并解压
2. 将 `custom_components/tuqiang_traccar` 文件夹复制到您 Home Assistant 配置目录下的 `custom_components` 目录中
3. 重启 Home Assistant

---

## ⚙️ 配置

### 第一步：添加集成

1. 在 Home Assistant 中，前往「设置」→「设备与服务」→「添加集成」
2. 搜索「途强GPS转Traccar」并点击

### 第二步：选择平台

- 途强物联（tuqiang.net）
- 途强在线（tuqiang123.com）

### 第三步：输入账号信息

根据所选平台输入对应的用户名和密码。

### 第四步：选择设备

系统会列出账号下所有设备，勾选需要转发到 Traccar 的设备。

### 第五步：配置 Traccar 服务器

| 字段 | 说明 |
|------|------|
| Traccar 服务器地址 | **必填**，格式如 `http://192.168.1.110:5055`<br/>⚠️ 注意：端口应为 **Traccar 客户端接入端口**（默认 5055），**而非 Web 管理端口**（默认 8082） |
| 设备标识前缀（可选） | 可在此填写一个字符串，最终上报的设备标识将为 `前缀+IMEI` |
| 上报间隔（秒） | 数据获取与上报的时间间隔，建议 30～60 秒 |

点击提交后，集成即开始运行。您可以为多个平台账号分别添加配置，每个配置独立运行。

---

## 🚗 在 Traccar 中添加设备

在 Traccar 网页管理后台中：

1. 进入设备管理页面
2. 点击「添加设备」
3. 填写设备名称（任意）
4. **标识符**一栏填写与集成配置一致的 ID：
   - 若未设置前缀：直接填写途强设备的 **IMEI**
   - 若设置了前缀：填写 `前缀 + IMEI`
5. 保存即可。

---

## ❓ 常见问题

### 1. 为什么集成中没有生成任何实体？
本集成设计为纯数据转发工具，不会在 Home Assistant 中产生 `device_tracker` 或 `sensor` 实体。若您需要在 HA 中查看设备位置，建议使用 [Traccar 官方集成](https://www.home-assistant.io/integrations/traccar/)。

### 2. 设备位置长时间不更新？
- 检查途强平台中设备是否在线
- 检查 Traccar 服务器地址及端口是否可达
- 查看 Home Assistant 日志，搜索 `tuqiang_traccar` 查看详细错误

### 3. 登录失败，提示“invalid_auth”？
- 确认用户名密码无误
- 部分途强在线账号密码可能需要特殊编码，已内置处理

---

## 📄 许可

本项目基于 MIT 协议开源。

---

## 👨‍💻 作者

**lambilly**

- GitHub: [@lambilly](https://github.com/lambilly)

---

## ⭐ 致谢

- [Home Assistant](https://www.home-assistant.io/)
- [Traccar](https://www.traccar.org/)
- [途强物联](https://www.tuqiang.net/)
- [途强在线](https://www.tuqiang123.com/)
