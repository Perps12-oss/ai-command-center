# Phase 9: Cross-Platform Expansion

**Status:** NOT_COMPLETE (code-verified 2026-07-20 — hotkey/tray stubs remain)  
**Priority:** LOW  
**Estimated Effort:** 8-12 weeks  
**Dependencies:** Phase 5 (Async EventBus)  
**Authority:** `PLATFORM_STRATEGY.md`, `PROJECT_CONSTITUTION_V4.md`  
**Verification:** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md` — do not confuse with frontend Phase 11

---

## Executive Summary

Expand AI Command Center beyond Windows to macOS and Linux. Maintain feature parity across platforms while adapting to platform-specific constraints (hotkeys, system tray, file paths).

---

## Current State

**Windows:** Primary platform, all features working

**macOS:** Hotkey provider scaffold (`platform/hotkey_provider.py` abstract base)

**Linux:** No implementation

---

## Platform Comparison

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| Global hotkey | ✅ `win32` | ⏳ CGEvent | ❌ X11/Wayland |
| System tray | ✅ | ⏳ NSStatusItem | ⏳ libappindicator |
| Path handling | ✅ | ⏳ POSIX | ⏳ POSIX + home |
| Notifications | ✅ | ⏳ NSUserNotification | ⏳ libnotify |
| Startup | ✅ Registry | ⏳ LSSharedFileList | ⏳ .desktop |

---

## Architecture

### Platform Abstraction

```text
┌─────────────────────────────────────────────────────────────────┐
│                      PlatformService (ABC)                        │
├─────────────────────────────────────────────────────────────────┤
│  hotkey_provider: HotkeyProvider                                │
│  tray_provider: TrayProvider                                    │
│  notification_provider: NotificationProvider                     │
│  path_provider: PathProvider                                    │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ WindowsPlatform │  │ macOSPlatform   │  │ LinuxPlatform   │
│   Service       │  │    Service      │  │    Service      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Hotkey Provider Strategy

| Platform | Technology | Permissions |
|----------|------------|-------------|
| Windows | `win32` `RegisterHotKey` | None |
| macOS | `CGEvent` tap | Accessibility (System Preferences) |
| Linux X11 | `XGrabKey` | None |
| Linux Wayland | `ZWaylandKeyboardShortcuts` | none (limited) |

---

## Implementation

### 9.1 Platform Abstraction

**File:** `ai_command_center/platform/platform_service.py`

```python
class PlatformService(ABC):
    @abstractmethod
    def get_platform_id(self) -> PlatformID: ...
    
    @abstractmethod
    def get_hotkey_provider(self) -> HotkeyProvider: ...
    
    @abstractmethod
    def get_tray_provider(self) -> TrayProvider: ...
    
    @abstractmethod
    def get_notification_provider(self) -> NotificationProvider: ...
```

### 9.2 macOS Implementation

**File:** `ai_command_center/platform/hotkey_provider_macos.py`

**Deliverables:**
- CGEvent tap registration
- Accessibility permissions check
- User prompt for permissions
- Key code translation

**File:** `ai_command_center/platform/tray_provider_macos.py`

**Deliverables:**
- NSStatusItem integration
- Menu construction
- Click handling

### 9.3 Linux Implementation

**File:** `ai_command_center/platform/hotkey_provider_linux.py`

**Deliverables:**
- X11 `XGrabKey` implementation
- Wayland detection and fallback
- Key code translation

**File:** `ai_command_center/platform/tray_provider_linux.py`

**Deliverables:**
- AppIndicator integration
- Menu construction
- Click handling

### 9.4 Path Provider

**File:** `ai_command_center/platform/path_provider.py`

**Standardize:**
- Config directory
- Data directory
- Cache directory
- Temp directory

---

## Files

### Create

```
ai_command_center/platform/platform_service.py
ai_command_center/platform/hotkey_provider_macos.py
ai_command_center/platform/tray_provider_macos.py
ai_command_center/platform/hotkey_provider_linux.py
ai_command_center/platform/tray_provider_linux.py
ai_command_center/platform/path_provider.py
tests/test_platform_abstraction.py
tests/test_macos_hotkey.py
tests/test_linux_hotkey.py
```

### Modify

```
ai_command_center/main.py (platform detection)
ai_command_center/application.py (platform service injection)
```

---

## Testing

### Unit Tests

- [ ] `test_platform_detection`
- [ ] `test_hotkey_provider_interface`
- [ ] `test_path_provider_consistency`

### Platform-Specific Tests

**macOS:**
- [ ] `test_cgevent_tap_registration`
- [ ] `test_accessibility_permission_check`
- [ ] `test_tray_menu`

**Linux:**
- [ ] `test_x11_hotkey_grab`
- [ ] `test_wayland_fallback`
- [ ] `test_appindicator_tray`

---

## Exit Criteria

- [ ] macOS hotkey working with accessibility permissions
- [ ] macOS system tray functional
- [ ] Linux hotkey working (X11 primary)
- [ ] Linux system tray functional
- [ ] Path provider consistent across platforms
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Real-time collaboration across platforms
- Native look adaptation
- Platform-specific feature divergence

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
