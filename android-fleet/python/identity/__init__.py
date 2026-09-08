"""
Identity Manager - Generate unique device identities for Android VM instances.
"""
import secrets
import random


def generate_android_id() -> str:
    """Generate a 16-character hex Android ID."""
    return secrets.token_hex(8)


def generate_imei() -> str:
    """Generate a valid 15-digit IMEI using Luhn algorithm."""
    # Generate first 14 digits randomly
    imei_part = ''.join([str(random.randint(0, 9)) for _ in range(14)])
    
    # Calculate check digit using Luhn algorithm
    check_digit = calculate_luhn_check_digit(imei_part)
    
    return imei_part + str(check_digit)


def calculate_luhn_check_digit(number: str) -> int:
    """Calculate Luhn check digit for IMEI (14 digits input, returns 1 digit)."""
    # Reverse for processing - position 0 is rightmost
    rev = number[::-1]
    
    total = 0
    for i, ch in enumerate(rev):
        d = int(ch)
        # Double digits at even indices in reversed (odd positions from right in original)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    return (10 - (total % 10)) % 10


def generate_mac_address() -> str:
    """Generate a unique MAC address with OUI for virtual machines."""
    # Use Proxmox OUI: 00:16:3E
    oui = "00:16:3E"
    random_part = ':'.join([
        f"{secrets.randbits(8):02x}"
        for _ in range(3)
    ])
    return f"{oui}:{random_part}"


def generate_serial() -> str:
    """Generate a 16-character alphanumeric serial number."""
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(chars) for _ in range(16))


def generate_fingerprint() -> dict:
    """Generate device fingerprint for Pixel 4 (Android 12)."""
    return {
        "model": "Pixel 4",
        "manufacturer": "Google",
        "product": "flame",
        "device": "flame",
        "name": "flame",
        "fingerprint": "google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys",
        "description": "flame-user 12 SP1A.210812.016.C2 1234567 release-keys",
        "sdk": "31",
        "release": "12"
    }


def generate_identity() -> dict:
    """Generate complete unique identity for an Android instance."""
    fingerprint = generate_fingerprint()
    
    return {
        "android_id": generate_android_id(),
        "imei": generate_imei(),
        "mac_address": generate_mac_address(),
        "serial": generate_serial(),
        "model": fingerprint["model"],
        "manufacturer": fingerprint["manufacturer"],
        "fingerprint": fingerprint["fingerprint"],
        "description": fingerprint["description"],
        "product": fingerprint["product"],
        "device": fingerprint["device"],
        "name": fingerprint["name"],
        "sdk": fingerprint["sdk"],
        "release": fingerprint["release"]
    }


if __name__ == "__main__":
    import json
    identity = generate_identity()
    print(json.dumps(identity, indent=2))