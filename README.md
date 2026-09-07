# Caffeine

<p align="center">
  <strong>Windows 系统托盘应用 — 一键保持屏幕常亮</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" alt="Platform" />
  <img src="https://img.shields.io/badge/python-3.13-blue" alt="Python" />
</p>

---

## 功能

- **单击切换** — 左键单击托盘图标即可开启/关闭，自动恢复上一次使用的模式（跨重启记忆，定时模式继续剩余倒计时）
- **无限模式** — 永久保持屏幕常亮，直到手动关闭
- **定时模式** — 30 分钟 / 1 小时 / 2 小时倒计时，自动恢复
- **开机自启动** — 通过注册表管理，安装包可自动配置
- **系统托盘图标** — 动态咖啡杯图标显示当前状态（彩色 = 激活，灰色 = 未激活）
- **多语言安装包** — 支持中文 / 英文安装界面

## 下载安装

前往 [Releases](../../releases) 页面下载最新版本：

| 文件 | 说明 |
|------|------|
| `Caffeine_Setup_*_x64.exe` | 安装包，推荐使用 |
| `Caffeine_Portable_*_x64.zip` | 免安装版，解压即用 |

## 使用

运行后程序驻留系统托盘：

- **左键单击**咖啡杯图标：快速开启 / 关闭，自动恢复上一次使用的模式（定时模式会继续剩余倒计时，配置保存在 `%APPDATA%\Caffeine\config.json`）
- **右键点击**咖啡杯图标：

  1. 选择 **∞ 无限模式** 永久保持常亮
  2. 选择 **▶ 定时模式** 设置倒计时
  3. 勾选 **开机自启动** 随系统启动

## 开发

```bash
# 安装依赖（需要 uv）
uv sync

# 运行测试与检查
uv run pytest
uv run ruff check .

# 运行（仅 Windows）
uv run python main.py
```

## 构建

```bash
# 安装构建依赖
uv sync --extra build

# 打包为 exe（自动生成 ICO 图标）
uv run python build.py
```

## 系统要求

- Windows 10 / 11
- 打包后无需安装 Python

## 致谢

- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘图标
- [Pillow](https://python-pillow.org) — 图像处理
- [PyInstaller](https://pyinstaller.org) — Python 打包
- [Inno Setup](https://jrsoftware.org/isinfo.php) — Windows 安装包
