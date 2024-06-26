# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Added
- Built-in implementation of an ASB for MongoDB
- Migration process now can be verbose, printing feedback messages as the
  migration process goes. The method `SVIP.migrate()` and the command `migrate`
  are non-verbose and verbose by default, respectively.
- Backups can now be performed outside of a migration context.
- Added support for SQLite.

### Changed
- Nicer default for `AppStateBackup` subclasses that do not override `info()`:
  it inspects attributes and print them
- ASBs that support backup are now required to support performing backup with
  `None` as the argument for the `migration_info` parameter.

### Fixed
- Using `from __future__ import annotations` in order to support latest
  features regarding annotations in different releases of Python 3.
- The version information was not restored after backup was restored. That was
  a bug. Fixed now! :-)
- Using `--no-save-backup` would cause a error when at some point of the
  program information about availability of backup is checked. This was a bug
  in the code because of a variable being undefined, which has been fixed now.

## 0.0.1 - 2021-07-26
- Very basic release: code documented but we are still missing documentation
  for the project.
