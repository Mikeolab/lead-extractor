"""
Machine ID Generator
Generates unique machine identifier for license binding.
Uses stable hardware IDs that persist across reboots and app restarts.
"""
import platform
import hashlib
import json
import uuid
import subprocess
from typing import Optional, List


def _get_windows_stable_ids() -> List[str]:
    """Get stable hardware IDs on Windows (survive reboots, exe restarts)."""
    ids = []
    # 1. System UUID (motherboard/BIOS) - most stable on Windows
    # Try wmic first (older Windows), then PowerShell (Windows 11+ - wmic deprecated)
    for cmd, get_uuid in [
        (["wmic", "csproduct", "get", "uuid"], lambda out: _parse_wmic_uuid(out)),
        (["powershell", "-NoProfile", "-Command",
          "(Get-WmiObject Win32_ComputerSystemProduct).UUID"], lambda out: out.strip() if out.strip() else None),
    ]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000 if platform.system() == "Windows" else 0
            )
            if result.returncode == 0 and result.stdout:
                uuid_val = get_uuid(result.stdout) if cmd[0] == "wmic" else result.stdout.strip()
                if uuid_val and len(uuid_val) > 10:
                    ids.append(uuid_val.upper())
                    break
        except Exception:
            pass
        if ids:
            break
    # 2. Disk drive serial - stable unless disk replaced
    try:
        result = subprocess.run(
            ["wmic", "diskdrive", "get", "serialnumber"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000 if platform.system() == "Windows" else 0
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line and line.upper() != "SERIALNUMBER" and len(line) > 4:
                    ids.append(line)
                    break
    except Exception:
        pass
    return ids


def _parse_wmic_uuid(stdout: str) -> Optional[str]:
    """Parse UUID from wmic output."""
    for line in stdout.strip().splitlines():
        line = line.strip().upper()
        if line and line != "UUID" and len(line) > 10:
            return line
    return None


def _get_darwin_stable_ids() -> List[str]:
    """Get stable hardware IDs on macOS."""
    ids = []
    try:
        result = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "IOPlatformUUID" in result.stdout:
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    idx = line.find('"', line.find("IOPlatformUUID"))
                    if idx >= 0:
                        end = line.find('"', idx + 1)
                        if end > idx:
                            ids.append(line[idx + 1:end])
                            break
    except Exception:
        pass
    return ids


def _get_linux_stable_ids() -> List[str]:
    """Get stable hardware IDs on Linux."""
    ids = []
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        try:
            with open(path) as f:
                mid = f.read().strip()
                if mid:
                    ids.append(mid)
                    break
        except Exception:
            pass
    return ids


def get_machine_id() -> str:
    """
    Generate unique machine ID based on STABLE hardware characteristics.
    Prioritizes IDs that persist across reboots and app restarts.

    Returns:
        16-character hexadecimal machine ID
    """
    stable_ids = []
    system = platform.system()

    if system == "Windows":
        stable_ids = _get_windows_stable_ids()
    elif system == "Darwin":
        stable_ids = _get_darwin_stable_ids()
    elif system == "Linux":
        stable_ids = _get_linux_stable_ids()

    # Use ONLY stable IDs when available - don't mix with hostname/MAC (those change on reboot)
    if stable_ids:
        parts = json.dumps(stable_ids, sort_keys=True)
    else:
        # Fallback when no stable IDs (e.g. VM, sandbox) - less reliable
        fallback_info = {}
        try:
            fallback_info = {
                "processor": platform.processor(),
                "system": system,
                "platform": platform.platform(),
            }
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                               for i in range(0, 8 * 6, 8)][::-1])
                fallback_info["mac"] = mac
            except Exception:
                fallback_info["mac"] = "unknown"
            fallback_info["hostname"] = platform.node()
        except Exception:
            pass
        parts = json.dumps(fallback_info, sort_keys=True)
    machine_hash = hashlib.sha256(parts.encode()).hexdigest()
    return machine_hash[:16]


def validate_machine_id(license_machine_id: str, current_machine_id: Optional[str] = None) -> bool:
    """
    Validate that license machine ID matches current machine.
    
    Args:
        license_machine_id: Machine ID from license
        current_machine_id: Current machine ID (if None, will generate)
    
    Returns:
        True if machine IDs match
    """
    if not license_machine_id:
        return False
    
    if current_machine_id is None:
        current_machine_id = get_machine_id()
    
    return license_machine_id.lower() == current_machine_id.lower()


if __name__ == "__main__":
    # Test machine ID generation
    mid = get_machine_id()
    print(f"Machine ID: {mid}")
    print(f"Length: {len(mid)}")
    print(f"Validation test: {validate_machine_id(mid, mid)}")

