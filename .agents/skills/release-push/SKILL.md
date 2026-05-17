---
name: release-push
description: 发布新版本：更新版本号、提交、打 tag 并推送
---

# Release & Push

发布 Caffeine 新版本的标准化流程。

## When to Use

当用户要求发布新版本、打 tag、或推送版本更新时使用。

## Workflow

### 1. 检查现有版本号

```bash
grep '^version = ' pyproject.toml
grep 'MyAppVersion' installer.iss
git tag --sort=-v:refname | head -3
```

### 2. 更新版本号

修改 `pyproject.toml` 中的 `version` 字段和 `installer.iss` 中的 `MyAppVersion`。

### 3. 提交并打 tag

```bash
git add pyproject.toml installer.iss
git commit -m "chore: bump version to <VERSION>"
git tag <VERSION>
```

### 4. 推送

```bash
git push
git push origin <VERSION>
```

如果 tag 已存在，需要先删除再重新创建：

```bash
git tag -d <VERSION>
git tag <VERSION>
git push origin <VERSION> --force
```
