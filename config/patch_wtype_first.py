#!/usr/bin/env python3
"""Patch hyprwhspr text_injector.py: prefer wtype over Hyprland sendshortcut.

Hyprland >= 0.55's sendshortcut dispatcher can silently no-op for some apps
(observed with Ghostty) while hyprctl still exits 0, so hyprwhspr believes
the paste succeeded and never falls back. This swaps the order: wtype's
virtual-keyboard path first, sendshortcut as the fallback.

Run with: sudo python3 ~/.config/hyprwhspr/patch_wtype_first.py
Reapply after any hyprwhspr package upgrade (like the realtime_base.py patch).
"""
import shutil
import sys

TARGET = "/usr/lib/hyprwhspr/lib/src/text_injector.py"

OLD = """            elif self._is_hyprland_session():
                pasted = self._send_shortcut_hyprland(paste_chord)
                if not pasted and self.wtype_available:
                    pasted = self._send_paste_keys_wtype(paste_chord)
                    if pasted:
                        self._clear_stuck_modifiers()
"""

NEW = """            elif self._is_hyprland_session():
                # Local patch (2026-08-12): Hyprland >= 0.55 sendshortcut can
                # silently no-op for some apps (e.g. Ghostty) while hyprctl
                # still exits 0, so prefer wtype's virtual-keyboard path and
                # keep sendshortcut as the fallback.
                if self.wtype_available:
                    pasted = self._send_paste_keys_wtype(paste_chord)
                    if pasted:
                        self._clear_stuck_modifiers()
                if not pasted:
                    pasted = self._send_shortcut_hyprland(paste_chord)
"""

src = open(TARGET).read()
if NEW in src:
    print("Already patched - nothing to do.")
    sys.exit(0)
if OLD not in src:
    print("ERROR: expected code block not found (package changed?); aborting, file untouched.")
    sys.exit(1)
shutil.copy2(TARGET, TARGET + ".bak-wtype-first")
open(TARGET, "w").write(src.replace(OLD, NEW, 1))
print(f"Patched {TARGET} (backup at {TARGET}.bak-wtype-first)")
print("Now run: systemctl --user restart hyprwhspr")
