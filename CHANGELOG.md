# Changelog

## [0.2.0] - 2026-02-05

### Added
- **Thermostat schedule commands** (`ccu schedule`)
  - `schedule get` - View heating profiles (Wochenprogramme)
  - `schedule set-simple` - Set single heating period per day
  - `schedule set-constant` - Set constant temperature (no night setback)
  - `schedule activate` - Switch between profiles P1/P2/P3
- `set_link_info` in XMLRPCClient for renaming device links
- Human-readable channel names in `link list` output
- JSON output option for `link list`
- Room description support (`room describe`)

### Fixed
- Inbox device listing with async fetch
- Removed non-functional `room create` command

### Changed
- Improved device rename with channel types display

## [0.1.0] - 2026-01-04

### Added
- Initial release
- kubectl-style CLI pattern (`resource action`)
- Device management (`device list`, `device get`, `device rename`, `device config`)
- Datapoint read/write (`datapoint get`, `datapoint set`)
- System variables (`sysvar list`)
- Program management (`program list`, `program get`, `program run`, `program enable/disable`, `program delete`)
- Room management (`room list`, `room get`, `room rename`, `room delete`, `room add-device`, `room remove-device`)
- Device links (`link list`, `link get`, `link create`, `link delete`, `link config get/set`)
- Device pairing (`device pair on/off/status`, `device inbox list/accept`)
- XDG config support (`~/.config/ccu-cli/config.toml`)
- Environment variable configuration
