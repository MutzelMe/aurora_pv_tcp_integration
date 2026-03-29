# Semantic Versioning Guide

## 📋 Versioning Rules (semver.org)

### Version Format: `MAJOR.MINOR.PATCH`

### When to Update Each Part:

#### **PATCH** (0.x.PATCH) - Bug Fixes
- **When:** Backwards-compatible bug fixes
- **Examples:**
  - Fixing the "Invalid handler specified" error
  - Removing merge conflict markers
  - Cleaning up Python cache files

#### **MINOR** (0.MINOR.0) - New Features
- **When:** Backwards-compatible new functionality
- **Examples:**
  - Adding weekly/monthly/yearly energy sensors
  - Implementing sequential inverter processing
  - Enhancing config flow with real validation
  - Adding new error classes

#### **MAJOR** (MAJOR.0.0) - Breaking Changes
- **When:** Incompatible API changes
- **Examples:**
  - Changing sensor names (breaking for existing users)
  - Removing deprecated features
  - Major architecture changes

## 🎯 Our Version History

### Version 0.4.0 (Current)
- **MINOR update** for config flow enhancements
- Added real connection validation
- Improved error handling
- Translated all comments

### Version 0.3.0
- **MINOR update** for weekly/monthly/yearly sensors
- Sequential inverter processing
- English translation

### Version 0.2.2
- Initial HACS integration
- Basic sensor platform

### Version 0.1.0
- Initial project setup

## 🔄 When to Update Version

### Small Changes (PATCH)
- Bug fixes
- Documentation improvements
- Code cleanup
- **Example:** Fixing typos, removing unused code

### Medium Changes (MINOR)
- New features
- Functionality enhancements
- **Example:** Adding new sensors, improving config flow

### Large Changes (MAJOR)
- Breaking changes
- API changes
- **Example:** Renaming sensors, changing interfaces

## 📝 CHANGELOG Best Practices

### Format
```markdown
## [Unreleased]

### Added
- New features here

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes here

### Removed
- Deprecated features removed
```

### When to Update CHANGELOG
- **Before committing** new features
- **After fixing** bugs
- **Before releasing** new version
- Keep it **up-to-date** with all changes

## 🎯 Versioning Workflow

1. **Make changes** to code
2. **Update CHANGELOG.md** (before commit)
3. **Update manifest.json** version
4. **Commit** with clear message
5. **Push** to repository
6. **Tag release** (optional for major versions)

## 📋 Example Workflow

```bash
# Make changes
git add .

# Update version in manifest.json
# Update CHANGELOG.md

# Commit
git commit -m "Bump version to X.Y.Z

- Description of changes
- Follows semver rules"

# Push
git push origin main

# Optional: Tag release
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

## 🔍 Version Checklist

- [ ] Code changes complete
- [ ] Tests passing
- [ ] CHANGELOG.md updated
- [ ] manifest.json version updated
- [ ] Commit message follows conventions
- [ ] Ready to push

## 📚 Resources

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- [Home Assistant Versioning Guide](https://developers.home-assistant.io/docs/development_versioning)

---

**Current Version:** 0.4.0
**Next Version:** 0.4.1 (PATCH) or 0.5.0 (MINOR) or 1.0.0 (MAJOR)