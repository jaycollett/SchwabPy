# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2025-11-28

### Changed
- Updated README with comprehensive PyPI installation instructions
- Added PyPI badges for version, downloads, and license visibility
- Improved documentation formatting and clarity
- Added link to QUICKSTART guide in README

### Fixed
- Package metadata consistency across setup.py, pyproject.toml, and __init__.py

## [2.0.0] - 2024-11-28

### Added
- Complete PyPI packaging configuration
- Secure token storage with automatic file permissions (0600)
- Built-in rate limiting (120 requests/min, configurable)
- Automatic retry logic with exponential backoff for transient errors
- Comprehensive input validation for all API parameters
- 47+ unit tests for reliability
- Context manager support for automatic resource cleanup
- Type hints throughout the library
- Custom exceptions for better error handling
- Data models: Account, Position, Balance, Quote, Instrument, Order, OptionChain

### Changed
- Major refactoring for production readiness
- Improved security with proper token file permissions
- Enhanced error messages and logging
- Better documentation with examples

### Security
- Token files now created with secure permissions (0600)
- Added validation to prevent common security issues
- Improved OAuth 2.0 flow with better error handling

## [0.2.0] - 2024-11-28

### Added
- Initial market data API implementation
- Account management functionality
- Order placement capabilities
- OAuth 2.0 authentication with automatic token refresh
- Basic documentation and examples

### Changed
- Reduced verbose logging to debug level

## [0.1.0] - 2024-11-27

### Added
- Initial project structure
- Basic Schwab API client
- Authentication framework
