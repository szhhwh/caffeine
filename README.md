# Caffeine

Windows 系统托盘应用，保持屏幕常亮。

## 功能

- **无限模式**：永久保持屏幕常亮，直到手动关闭
- **定时模式**：30 分钟 / 1 小时 / 2 小时倒计时，自动恢复
- **开机自启动**：通过注册表管理自启
- **系统托盘图标**：动态图标显示当前状态（彩色=激活，灰色=未激活）

## 开发

```bash
# 安装依赖
uv sync

# 运行（仅 Windows）
uv run python main.py
```

## 构建

```bash
# 安装构建依赖
uv sync --extra build

# 打包为 exe
uv run python build.py
```

## 制作安装包

1. 安装 [Inno Setup](https://jrsoftware.org/isinfo.php)
2. 运行 `build.py` 生成 `dist/Caffeine.exe`
3. 用 Inno Setup 编译 `installer.iss`
4. 输出的安装包位于 `installer_output/` 目录

## 系统要求

- Windows 10 / 11
- 无需安装 Python（打包后独立运行）
