# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased
### Added
- Built-in implementation of an ASB for MongoDB

### Changed
- Nicer default for `AppStateBackup` subclasses that do not override `info()`:
  it inspects attributes and print them

### Fixed
- Using `from __future__ import annotations` in order to support latest
  features regarding annotations in different releases of Python 3.

## 0.0.1 - 2021-07-26
- Very basic release: code documented but we are still missing documentation
  for the project.
