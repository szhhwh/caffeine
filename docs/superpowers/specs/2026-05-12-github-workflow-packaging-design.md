# GitHub Workflow Packaging Design

## Summary

Add Inno Setup installer and portable zip packaging to the existing GitHub Actions workflow, so that releases include both an installer (.exe) and a portable version (.zip) with `_x64` platform suffix.

## Context

Caffeine is a Windows-only system tray app (Python + pystray + Pillow), currently built with PyInstaller and released as a bare `.exe` on GitHub Releases. An `installer.iss` Inno Setup script already exists locally but is not used in CI. The README describes manual installer creation steps.

## Requirements

- On tag push (v*), build Caffeine.exe, then generate an Inno Setup installer and a portable zip
- Version number extracted from git tag (e.g. `v1.0.0` → `1.0.0`), injected into `installer.iss`
- Release artifacts named with `_x64` platform suffix:
  - `Caffeine_Setup_{VERSION}_x64.exe` (Inno Setup installer)
  - `Caffeine_Portable_{VERSION}_x64.zip` (portable zip of bare exe)
- PR/push-to-main builds still produce exe artifact for CI validation, but skip installer/zip/release

## Design

### Approach: Single-job pipeline (Option A)

All packaging happens in the existing `build` job on `windows-latest`, as sequential steps after PyInstaller. The `release` job downloads all artifacts and publishes them together.

### Workflow changes

#### build job — new steps after PyInstaller

1. **Extract version** (only on tag):
   ```yaml
   - name: Extract version
     if: startsWith(github.ref, 'refs/tags/v')
     run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_ENV
   ```

2. **Inject version into installer.iss** (only on tag):
   ```powershell
   (Get-Content installer.iss) -replace '#define MyAppVersion "1.0.0"', "#define MyAppVersion \"$env:VERSION\"" | Set-Content installer.iss
   ```

3. **Install Inno Setup** (only on tag):
   ```yaml
   - name: Install Inno Setup
     if: startsWith(github.ref, 'refs/tags/v')
     run: choco install innosetup --no-progress
   ```

4. **Compile installer** (only on tag):
   ```yaml
   - name: Compile installer
     if: startsWith(github.ref, 'refs/tags/v')
     run: iscc installer.iss
   ```
   Inno Setup reads `dist\Caffeine.exe` (from PyInstaller step) and outputs to `installer_output\Caffeine_Setup_{VERSION}_x64.exe` (platform suffix comes from the updated `OutputBaseFilename` in `installer.iss`).

5. **Create portable zip** (only on tag):
   ```powershell
   Compress-Archive -Path dist\Caffeine.exe -DestinationPath "dist\Caffeine_Portable_$env:VERSION_x64.zip"
   ```

6. **Upload artifacts** — split into two uploads:
   - exe artifact (always, for CI validation on PR/push-to-main)
   - installer + zip artifact (only on tag, for release)

#### release job

Download the installer+zip artifact, upload both files to GitHub Release alongside the bare exe.

### installer.iss changes

- `OutputBaseFilename` changes from `Caffeine_Setup_{#MyAppVersion}` to `Caffeine_Setup_{#MyAppVersion}_x64` so the Inno Setup output already has the platform suffix, eliminating the rename step.

### Artifact structure

| Trigger | Artifacts uploaded |
|---------|-------------------|
| PR / push-to-main | `Caffeine-windows` (bare exe) |
| Tag push | `Caffeine-windows` (bare exe) + `Caffeine-release` (installer + portable zip) |

### Release output

On tag push, the GitHub Release will contain:
- `Caffeine_Setup_1.0.0_x64.exe`
- `Caffeine_Portable_1.0.0_x64.zip`
- `Caffeine.exe` (bare exe, kept for backward compat)

## Files to modify

1. `.github/workflows/build.yml` — add packaging steps, update release job
2. `installer.iss` — update `OutputBaseFilename` to include `_x64`