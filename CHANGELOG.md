# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 0.3.0
### Added
- Initial notebook support for sweeper functionality
- Logfile capability from launch control GUI
- Driver for Thorlabs PM320E
- GUI for fiber coupling

### Changed
- Servers are now, by default, secure. This means that you should have a common `pylabnet.pem` file in your `Windows/System32` directory to use the client-server interface.
- Updated README.md

## 0.2.6
### Changed
- Fixed bugs with developer mode installation and jupyter notebook support
- Updated README.md

## 0.2.7
### Added
- Driver support for Smaract MCS2 nanopositioners
- GUI control for 9-axis Smaract MCS2 stepper
- GUI functionality for using button "press" and "release" events
- Support for scope plotting and checking via pulseblock

### Removed
- Explicit support for dedicated conda environment

## 0.2.6
### Changed
- Fixed bugs with developer mode installation and jupyter notebook support
- Updated README.md

### Removed
- Depreciated `.cmd` launching in favor of `.exe` launching even in developer mode

## 0.2.5
### Added
- Automatic generation of .cmd launching script
- Automatic activation of virtual environment in launching

### Changed
- Documentation in root `README.md` to include command for development in virtual environment

### Removed
- Explicit tracking of .cmd files in repository, since they are now generated when manually built

## 0.2.4
### Added
- Support for virtual environments

### Changed
- Documentation in root `README.md` to explain use of virtual environments

### Removed
- Conda environment support
## 0.2.3
### Added
- Basic pip install capability from pypi.org
### Changed
- Documentation to reflect new pip installable package

## 0.2.2
### Added
- Basic test pypi functionality