"""
Machine ID Generator
Generates unique machine identifier for license binding
"""
import platform
import hashlib
import json
import uuid
from typing import Optional


def get_machine_id() -> str:
    """
    Generate unique machine ID based on hardware characteristics.
    
    Returns:
        16-character hexadecimal machine ID
    """
    try:
        # Collect machine-specific information
        machine_info = {
            "hostname": platform.node(),
            "processor": platform.processor(),
            "system": platform.system(),
            "platform": platform.platform(),
        }
        
        # Get MAC address (network interface)
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                           for i in range(0, 8*6, 8)][::-1])
            machine_info["mac_address"] = mac
        except Exception:
            machine_info["mac_address"] = "unknown"
        
        # Create deterministic hash
        machine_string = json.dumps(machine_info, sort_keys=True)
        machine_hash = hashlib.sha256(machine_string.encode()).hexdigest()
        
        # Return first 16 characters (64-bit identifier)
        return machine_hash[:16]
    
    except Exception:
        # Fallback: use hostname hash
        try:
            hostname = platform.node()
            return hashlib.sha256(hostname.encode()).hexdigest()[:16]
        except Exception:
            # Last resort: random (not ideal, but works)
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16]


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

