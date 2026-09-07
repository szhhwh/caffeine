---
name: release-push
description: 发布新版本：更新版本号、提交、打 tag 并推送
---

# Release & Push

发布 Caffeine 新版本的标准化流程。

## When to Use

当用户要求发布新版本、bump 版本号、打 tag、或推送版本更新时使用。

## Workflow

### 1. 检查当前版本号

```bash
uv version --short
git tag --sort=-v:refname | head -5
```

向用户展示当前版本和最近的 tag 列表。

### 2. 确认新版本号

询问用户目标版本号，提供以下选项：
- **patch** (默认): 当前版本号 patch 位 +1
- **minor**: 当前版本号 minor 位 +1，patch 归零
- **major**: 当前版本号 major 位 +1，minor 和 patch 归零

### 3. 更新版本号

版本号唯一维护在 `pyproject.toml`，用一条命令同时更新它和 `uv.lock`：

```bash
uv version <VERSION>
```

不要手动修改 `installer.iss` 的版本号：CI 发布时会通过 `scripts/inject_version.py` 从 tag 注入真实版本。

### 4. 提交并打 tag

```bash
git add pyproject.toml uv.lock
git commit -m "chore: bump version to <VERSION>"
git tag v<VERSION>
```

tag 格式为 `v` + 版本号，如 `v1.2.0`。CI 的构建发布流程仅在 `v*` tag 上触发，缺少 `v` 前缀会导致发布产物缺失。

### 5. 推送

询问用户是否推送，提供选项：
- 推送 commit + tag（推荐）
- 仅推送 commit
- 不推送

推送命令：

```bash
git push
git push origin v<VERSION>
```

如果 tag 已存在，需先删除再重新创建：

```bash
git tag -d v<VERSION>
git tag v<VERSION>
git push origin v<VERSION> --force
```

## 注意事项

- 版本号格式遵循 semver：`MAJOR.MINOR.PATCH`
- 版本号单一来源为 `pyproject.toml`；`uv.lock` 由 `uv version` 自动同步，`installer.iss` 由 CI 注入，均不手动维护
- 提交信息格式：`chore: bump version to <VERSION>`
- 推送前检查 `git status` 确保工作区干净
