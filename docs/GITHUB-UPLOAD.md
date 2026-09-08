# Upload this project to GitHub

This `github` folder is a standalone source snapshot. Upload **its contents** at your repository root, so GitHub shows `README.md`, `ClearMirror.sln`, `src/` and `.github/` directly. The outer folder name is only a delivery container.

The folder contains source, documentation, icons, tests, a workflow, and a sanitized example profile. Recordings, downloaded engines, local profiles, build output, backups, and personal phone identifiers are excluded. There is no Git history or remote configured in this snapshot.

## Option A: Git commands

Create a new empty repository on GitHub, for example `ClearMirror`. Leave automatic README, license and `.gitignore` creation unchecked because this folder already contains the prepared files.

Open PowerShell **inside this `github` folder**, replace `YOUR_USERNAME` and the repository name as needed, then run:

```powershell
git init
git add .
git status --short
git commit -m "Initial ClearMirror source release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ClearMirror.git
git push -u origin main
```

Sign in using Git's normal authentication when prompted. These commands are for a new empty repository; for an existing repository, work in its clone and review the copied files before committing. Do not run this from the original project parent, which also contains personal runtime data.

## Option B: GitHub website

Create the repository, use **Add file → Upload files** (or the empty repository's upload link), drag the contents of this folder into the upload area, and commit. Include `.gitignore`, `.gitattributes` and the entire `.github` folder. If your picker hides dotfiles, use Git so they are included reliably.

Upload extracted source files rather than a ZIP as the repository's only file. GitHub's web uploader allows files up to 25 MiB and up to 100 files per upload; this source snapshot is small enough for that method. See [GitHub's upload instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## After uploading

- Open the README and check the documentation links.
- Open the **Actions** tab to see the Windows build and smoke tests. The workflow is included, but a GitHub run can only be verified after you upload it.
- Suggested repository description: `Windows Android mirroring controller with USB/Wi-Fi pairing, audio, recording, gaming controls, and PC microphone hardware routing.`
- Optional topics: `android`, `scrcpy`, `screen-mirroring`, `wpf`, `dotnet`, `windows`, `adb`.

## Sharing the runnable app

Build using [BUILD.md](BUILD.md), then ZIP the complete `dist/ClearMirror` folder. If you want a downloadable app on GitHub, attach that ZIP to a Release (for example version `v1.1.1`). Source remains in the repository; the portable build is a separate release attachment. Check the ZIP contains no personal recordings or saved device-specific profiles before sharing.

The source snapshot has no selected project-wide license. Choose your intended license before presenting it as a licensed open-source release. Existing dependency notices are retained in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## বাংলা সংক্ষিপ্ত নির্দেশনা

এই `github` folder-এর **ভেতরের সব file/folder** নতুন GitHub repository-তে upload করুন। বাইরের পুরো project folder upload করবেন না। Repository খুললেই যেন `README.md`, `src`, `tests` ও `.github` দেখা যায়। `.gitignore` এবং `.github`-ও রাখতে হবে। চালানোর EXE চাইলে build guide অনুসরণ করে আলাদা Release ZIP তৈরি করুন।
