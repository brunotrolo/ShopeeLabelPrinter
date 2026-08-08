# 📋 Repository Rename Guide: Shopee_Printer → Shopee Label Print

This guide walks you through renaming the repository from `Shopee_Printer` to a URL-friendly name while maintaining all functionality and references.

## ⚠️ Important Notes

- **GitHub Repository URL will change** — you may want to set up a redirect
- **GitHub Pages URL will remain the same** — `brunotrolo.github.io/Shopee_Printer/` (GitHub doesn't auto-redirect custom domain paths)
- **Breaking change:** Anyone with bookmarks/links will need to update them
- **All code and functionality remains the same** — only documentation and URLs change

---

## 🎯 Step 1: Update Local References (Before Renaming on GitHub)

These updates prepare your code for the rename. Do these NOW:

### 1.1 Update `src/shopee_label_printer/__init__.py`

Find this line:
```python
__url__ = "https://github.com/brunotrolo/Shopee_Printer"
```

Change it to:
```python
__url__ = "https://github.com/brunotrolo/ShopeeLabelPrinter"
```

### 1.2 Update `README.md`

Replace all GitHub URLs from:
```
https://github.com/brunotrolo/Shopee_Printer
```

To:
```
https://github.com/brunotrolo/ShopeeLabelPrinter
```

Also update GitHub Pages URLs from:
```
brunotrolo.github.io/Shopee_Printer/
```

To:
```
brunotrolo.github.io/ShopeeLabelPrinter/
```

Check these specific sections:
- Quick Start → Web Version link
- Desktop Version (.exe) → Releases link
- GitHub Actions → Actions link
- Contributing → GitHub link
- Badge (GitHub release link)

### 1.3 Update `LEIA-ME.md`

Same changes as README.md, but in Portuguese documentation:
- Replace GitHub URLs
- Replace GitHub Pages URLs
- Keep Portuguese text intact

### 1.4 Check `docs/index.html`

Verify that links in the HTML header point to the new repository:

Look for:
```html
<a class="btn" href="https://github.com/brunotrolo/Shopee_Printer" target="_blank" rel="noopener">
<a class="btn primary" href="https://github.com/brunotrolo/Shopee_Printer/releases/latest/download/ShopeeLabelPrinter.exe">
```

Update to:
```html
<a class="btn" href="https://github.com/brunotrolo/ShopeeLabelPrinter" target="_blank" rel="noopener">
<a class="btn primary" href="https://github.com/brunotrolo/ShopeeLabelPrinter/releases/latest/download/ShopeeLabelPrinter.exe">
```

### 1.5 Check GitHub Workflows (`.github/workflows/`)

Search for any references to the repository name in workflow files:
```bash
grep -r "Shopee_Printer" .github/workflows/
```

Update any hardcoded repository names in workflow files if found.

### 1.6 Commit These Changes

```bash
git add README.md LEIA-ME.md src/shopee_label_printer/__init__.py docs/index.html
git commit -m "Prepare for repository rename: update internal references"
git push origin main
```

---

## 🚀 Step 2: Rename Repository on GitHub

You must do this through GitHub's web interface (not command-line):

1. Go to https://github.com/brunotrolo/Shopee_Printer
2. Click **Settings** (top-right menu)
3. Under **Repository name**, change from `Shopee_Printer` to `ShopeeLabelPrinter`
4. Click **Rename**

GitHub will:
- ✅ Automatically redirect old URLs for ~1 year
- ✅ Update all internal references
- ❌ NOT redirect GitHub Pages paths (see note below)

---

## 📍 Step 3: Handle GitHub Pages Redirect (Optional but Recommended)

Your GitHub Pages currently live at:
```
https://brunotrolo.github.io/Shopee_Printer/
```

After rename, they'll be at:
```
https://brunotrolo.github.io/ShopeeLabelPrinter/
```

### Option A: Simple Redirect (Easiest)

Create `docs/index-old-redirect.html` at the root of the Shopee_Printer GitHub Pages:

Actually, **GitHub won't serve this** because the old path won't exist after rename.

### Option B: Set Up a 301 Redirect (Best)

This requires more manual work outside this environment. After rename, you'll need to:

1. Keep the old `Shopee_Printer` repository as a stub (or create a new empty one)
2. Enable GitHub Pages on it
3. Add an `index.html` that redirects to the new URL:

```html
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0;url=https://brunotrolo.github.io/ShopeeLabelPrinter/">
</head>
<body>
    <p>Redirecting to <a href="https://brunotrolo.github.io/ShopeeLabelPrinter/">https://brunotrolo.github.io/ShopeeLabelPrinter/</a></p>
</body>
</html>
```

### Option C: Update Documentation & Accept URL Change

Simply update all documentation to point to the new URL and accept that old bookmarks will break. This is the simplest approach.

---

## 🔍 Step 4: Update Package References (if published to PyPI)

If `ShopeeLabelPrinterer` is published to PyPI, you may need to:
- Verify the PyPI project settings
- Update any mentions of installation commands
- Document the old vs. new package names

Currently, the package is installed via GitHub releases, so this may not apply.

---

## ✅ Step 5: Verify Everything Works

After rename and updating all references:

### Test Web Version
1. Visit: https://brunotrolo.github.io/ShopeeLabelPrinter/
2. Verify it loads correctly
3. Test all functionality

### Test GitHub Links
1. Go to the new repository: https://github.com/brunotrolo/ShopeeLabelPrinter
2. Check that releases still exist
3. Verify GitHub Pages is enabled
4. Check GitHub Actions workflows run correctly

### Test Desktop Version
1. Verify `.exe` can still be downloaded from new Releases page
2. Test that the desktop app works

### Test Old URLs
1. Visit old URL: https://github.com/brunotrolo/Shopee_Printer
2. Should redirect to new URL

---

## 📝 URL Reference Sheet

### Before Rename
```
Repository:      https://github.com/brunotrolo/Shopee_Printer
Releases:        https://github.com/brunotrolo/Shopee_Printer/releases
Actions:         https://github.com/brunotrolo/Shopee_Printer/actions
.exe Download:   https://github.com/brunotrolo/Shopee_Printer/releases/latest/download/ShopeeLabelPrinter.exe
GitHub Pages:    https://brunotrolo.github.io/Shopee_Printer/
Issues:          https://github.com/brunotrolo/Shopee_Printer/issues
```

### After Rename
```
Repository:      https://github.com/brunotrolo/ShopeeLabelPrinter
Releases:        https://github.com/brunotrolo/ShopeeLabelPrinter/releases
Actions:         https://github.com/brunotrolo/ShopeeLabelPrinter/actions
.exe Download:   https://github.com/brunotrolo/ShopeeLabelPrinter/releases/latest/download/ShopeeLabelPrinter.exe
GitHub Pages:    https://brunotrolo.github.io/ShopeeLabelPrinter/
Issues:          https://github.com/brunotrolo/ShopeeLabelPrinter/issues
```

---

## 🐛 Known Issues After Rename

### Issue 1: Old GitHub Pages URL Still Works (Temporarily)
- GitHub URLs auto-redirect for ~1 year
- GitHub Pages paths **DO NOT** auto-redirect
- Users visiting `brunotrolo.github.io/Shopee_Printer/` will get 404
- **Solution:** Set up redirect mentioned in Step 3

### Issue 2: Bookmarks & Shared Links Break
- Anyone with bookmarked old URL will get 404 for GitHub Pages
- **Solution:** Communicate the change, update README, add redirect

### Issue 3: Cached URLs in Wayback Machine
- Archive.org caches old URLs
- Not critical, but URLs will point to old path
- No action needed (it's a public service)

---

## 📋 Checklist for Rename

- [ ] Update `src/shopee_label_printer/__init__.py` — change __url__
- [ ] Update `README.md` — all GitHub links and GitHub Pages URLs
- [ ] Update `LEIA-ME.md` — all GitHub links and GitHub Pages URLs
- [ ] Update `docs/index.html` — header links to repository and releases
- [ ] Check `.github/workflows/` — verify no hardcoded repo references
- [ ] Commit and push all changes to main branch
- [ ] Rename repository on GitHub to `ShopeeLabelPrinter`
- [ ] Verify GitHub Pages works at new URL
- [ ] Test downloads from new Releases page
- [ ] Verify GitHub Actions workflows run correctly
- [ ] (Optional) Set up GitHub Pages redirect for old URL
- [ ] Update any external documentation/websites linking to this repo
- [ ] Close any open issues/PRs related to rename (if any)

---

## 🔗 Additional Resources

- [GitHub Repository Rename Docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository)
- [GitHub Pages Custom Domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-site)
- [SEO Impact of URL Changes](https://developers.google.com/search/docs/advanced/crawling/manage-urls)

---

## 📞 Support

If you encounter issues during the rename:

1. **Repository not renaming?** Make sure you have admin permissions
2. **Workflows failing?** Check `.github/workflows/` for hardcoded repo references
3. **GitHub Pages broken?** Verify repository is public and Pages is enabled
4. **Old links broken?** Add a redirect as described in Step 3

---

**Last updated:** August 8, 2026
