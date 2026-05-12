# GitHub Workflow Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Inno Setup installer and portable zip packaging to the GitHub Actions workflow so that releases include `Caffeine_Setup_{VERSION}_x64.exe` and `Caffeine_Portable_{VERSION}_x64.zip`.

**Architecture:** Single-job pipeline — all packaging steps run in the existing `build` job on `windows-latest` after PyInstaller, conditionally on tag push. Version extracted from git tag and injected into `installer.iss`. The `release` job downloads all artifacts and publishes them together.

**Tech Stack:** GitHub Actions, Inno Setup (iscc), PyInstaller, PowerShell (Compress-Archive)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `installer.iss` | Update `OutputBaseFilename` to include `_x64` suffix |
| `.github/workflows/build.yml` | Add version extraction, Inno Setup install/compile, portable zip creation, split artifact uploads, update release job |

---

### Task 1: Update installer.iss OutputBaseFilename

**Files:**
- Modify: `installer.iss:15`

- [ ] **Step 1: Update OutputBaseFilename to include `_x64` suffix**

Change line 15 of `installer.iss` from:
```
OutputBaseFilename=Caffeine_Setup_{#MyAppVersion}
```
to:
```
OutputBaseFilename=Caffeine_Setup_{#MyAppVersion}_x64
```

- [ ] **Step 2: Commit**

```bash
git add installer.iss
git commit -m "feat: add _x64 platform suffix to installer output filename"
```

---

### Task 2: Update build.yml — add packaging steps to build job

**Files:**
- Modify: `.github/workflows/build.yml:28-36`

- [ ] **Step 1: Add version extraction step after PyInstaller build**

Insert after the "Build with PyInstaller" step:

```yaml
      - name: Extract version
        if: startsWith(github.ref, 'refs/tags/v')
        shell: bash
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
```

- [ ] **Step 2: Add version injection step into installer.iss**

```yaml
      - name: Inject version into installer.iss
        if: startsWith(github.ref, 'refs/tags/v')
        shell: pwsh
        run: |
          (Get-Content installer.iss) -replace '#define MyAppVersion "1.0.0"', "#define MyAppVersion \"$env:VERSION\"" | Set-Content installer.iss
```

- [ ] **Step 3: Add Inno Setup install step**

```yaml
      - name: Install Inno Setup
        if: startsWith(github.ref, 'refs/tags/v')
        shell: pwsh
        run: choco install innosetup --no-progress
```

- [ ] **Step 4: Add Inno Setup compile step**

```yaml
      - name: Compile installer
        if: startsWith(github.ref, 'refs/tags/v')
        shell: pwsh
        run: iscc installer.iss
```

- [ ] **Step 5: Add portable zip creation step**

```yaml
      - name: Create portable zip
        if: startsWith(github.ref, 'refs/tags/v')
        shell: pwsh
        run: Compress-Archive -Path dist\Caffeine.exe -DestinationPath "dist\Caffeine_Portable_$env:VERSION_x64.zip"
```

- [ ] **Step 6: Split artifact uploads — keep exe upload, add release artifact upload**

Replace the existing "Upload artifact" step with two uploads:

```yaml
      - name: Upload exe artifact
        uses: actions/upload-artifact@v4
        with:
          name: Caffeine-windows
          path: dist/Caffeine.exe

      - name: Upload release artifacts
        if: startsWith(github.ref, 'refs/tags/v')
        uses: actions/upload-artifact@v4
        with:
          name: Caffeine-release
          path: |
            installer_output/Caffeine_Setup_${{ env.VERSION }}_x64.exe
            dist/Caffeine_Portable_${{ env.VERSION }}_x64.zip
```

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "feat: add Inno Setup installer and portable zip packaging to build job"
```

---

### Task 3: Update build.yml — update release job

**Files:**
- Modify: `.github/workflows/build.yml:37-56`

- [ ] **Step 1: Add download of release artifacts to release job**

In the release job, add a second download-artifact step after the existing one:

```yaml
      - name: Download release artifacts
        uses: actions/download-artifact@v4
        with:
          name: Caffeine-release
          path: release
```

- [ ] **Step 2: Update the Create release step to include all three files**

Replace the existing "Create release" step with:

```yaml
      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/Caffeine.exe
            release/Caffeine_Setup_*_x64.exe
            release/Caffeine_Portable_*_x64.zip
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "feat: update release job to publish installer and portable zip"
```

---

### Task 4: Verify workflow YAML is valid

- [ ] **Step 1: Validate YAML syntax**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('YAML is valid')"
```
Expected: `YAML is valid`

- [ ] **Step 2: Review final workflow file for correctness**

Read `.github/workflows/build.yml` and verify:
- `env.VERSION` is set before it's referenced in artifact paths
- All conditional steps have `if: startsWith(github.ref, 'refs/tags/v')`
- Inno Setup `iscc` command references `installer.iss` correctly
- `Compress-Archive` path uses `dist\Caffeine.exe` (which PyInstaller produces)
- Release job downloads both `Caffeine-windows` and `Caffeine-release` artifacts
- Release files glob patterns match actual filenames

- [ ] **Step 3: Commit any fixes if needed**