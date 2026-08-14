# Constitutional Pre-Flight — Golden Hour shell theme

**Date:** 2026-08-13  
**Branch:** `cursor/vendor-cursor-skills-d598`  
**Change class:** UI design-system tokens only. No EventBus, services, repositories, or layout redesign.

---

## Authority read

| Layer | Document | Status |
|-------|----------|--------|
| L1 | `PROJECT_CONSTITUTION_V4.md` | Read — UI is a renderer; tokens live in design system |
| Peer | `docs/UI_CONSTITUTION.md` | Article 4 lists three official themes; code already has additional named palettes (`Midnight`, `Forest`, …). Golden Hour is another **named palette**, not a fourth constitutional theme replacing Mission Control / Executive / Tactical. Article 5 subsystem colors (`GOAL_AMBER`, etc.) are **not** remapped. |
| L2 | `AGENTS.md` | UI isolation preserved; no service calls |
| L3 | `theme_v2.py`, `theme_manager.py`, `settings_view.py` | Theme swatches iterate `T.THEMES` |

---

## Intent

Operator asked Theme Factory to apply **Golden Hour** to the ACC CustomTkinter shell as well as slide/HTML/doc artifacts.

1. Add `THEMES["Golden Hour"]` using mustard / terracotta / beige / chocolate from `themes/golden-hour.md`.  
2. Normalize aliases (`golden hour`, `golden_hour`).  
3. Apply via existing `theme_manager.apply` + Settings appearance swatches.  
4. Do not change layout, navigation, or default `SettingsSnapshot.theme` (`dark` → VS Dark). Operators select Golden Hour in Settings.

Typography: Theme Factory specifies FreeSans; ACC shell on Windows-ARM64 uses **Segoe UI** (existing `FONT_FAMILY`). Weight hierarchy (bold headers / regular body) is unchanged.

---

## Out of scope

- Restyling Article 5 semantic subsystem tokens  
- Changing default theme for existing installs  
- Layout / widget structure  
- Amending UI Constitution Article 4 to add an official fourth theme  

---

## Verification

- Unit: `theme_manager.apply(..., theme_name="Golden Hour")` sets chocolate/beige/mustard tokens  
- `python3 -m pytest tests/ui/test_mission_control_p7p8.py -q`  
- Desktop GUI cannot run on this Linux Cloud host  

---

## Verdict

**Pre-flight COMPLETE.** Token addition may proceed.
