#!/usr/bin/env python3
"""
Identity Generation Script for Android Fleet
Generates unique device identities for Android VM instances.
"""

import secrets
import json
import argparse
from datetime import datetime, timezone


def generate_android_id() -> str:
    """Generate 16-character hex Android ID."""
    return secrets.token_hex(8)


def generate_imei() -> str:
    """Generate valid 15-digit IMEI with Luhn checksum."""
    # TAC (Type Allocation Code) - 6 digits
    tac = secrets.randbelow(1000000)
    # FAC (Final Assembly Code) - 2 digits  
    fac = secrets.randbelow(100)
    # SNR (Serial Number) - 6 digits
    snr = secrets.randbelow(1000000)
    
    # Combine first 14 digits
    imei_base = f"{tac:06d}{fac:02d}{snr:06d}"
    
    # Calculate Luhn checksum digit
    total = 0
    for i, digit in enumerate(reversed(imei_base)):
        d = int(digit)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    checksum = (10 - (total % 10)) % 10
    return f"{imei_base}{checksum}"


def generate_mac_address() -> str:
    """Generate unique MAC address with OUI for virtual devices."""
    # Use 00:16:3E OUI (Xensource/Xen VMs) or random local MAC
    oui = "00:16:3E"
    random_part = ":".join([f"{secrets.randbelow(256):02x}" for _ in range(3)])
    return f"{oui}:{random_part}"


def generate_serial() -> str:
    """Generate 16-character alphanumeric serial number."""
    return secrets.token_hex(8).upper()


def select_fingerprint() -> dict:
    """Select random certified device fingerprint."""
    fingerprints = [
        {
            "model": "Pixel 4",
            "manufacturer": "Google",
            "device": "flame",
            "name": "flame",
            "fingerprint": "google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys",
            "description": "flame-user 12 SP1A.210812.016.C2 1234567 release-keys",
            "sdk": "31",
            "release": "12"
        },
        {
            "model": "Pixel 5",
            "manufacturer": "Google",
            "device": "redfin",
            "name": "redfin",
            "fingerprint": "google/redfin/redfin:13/TP1A.220905.001/1234567:user/release-keys",
            "description": "redfin-user 13 TP1A.220905.001 1234567 release-keys",
            "sdk": "33",
            "release": "13"
        },
        {
            "model": "Pixel 6",
            "manufacturer": "Google",
            "device": "oriole",
            "name": "oriole",
            "fingerprint": "google/oriole/oriole:14/UP1A.231005.007/1234567:user/release-keys",
            "description": "oriole-user 14 UP1A.231005.007 1234567 release-keys",
            "sdk": "34",
            "release": "14"
        }
    ]
    return secrets.choice(fingerprints)


def generate_identity(instance_name: str = None) -> dict:
    """Generate complete device identity."""
    fingerprint = select_fingerprint()
    
    identity = {
        "android_id": generate_android_id(),
        "imei": generate_imei(),
        "mac_address": generate_mac_address(),
        "serial": generate_serial(),
        "model": fingerprint["model"],
        "manufacturer": fingerprint["manufacturer"],
        "device": fingerprint["device"],
        "name": fingerprint["name"],
        "fingerprint": fingerprint["fingerprint"],
        "description": fingerprint["description"],
        "sdk": fingerprint["sdk"],
        "release": fingerprint["release"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instance_name": instance_name or f"android-{secrets.token_hex(4)}"
    }
    
    return identity


def validate_identity(identity: dict) -> bool:
    """Validate generated identity format."""
    # Validate Android ID (16 hex chars)
    if len(identity["android_id"]) != 16:
        return False
    try:
        int(identity["android_id"], 16)
    except ValueError:
        return False
    
    # Validate IMEI (15 digits)
    if len(identity["imei"]) != 15 or not identity["imei"].isdigit():
        return False
    
    # Validate MAC address format
    mac_parts = identity["mac_address"].split(":")
    if len(mac_parts) != 6:
        return False
    for part in mac_parts:
        try:
            int(part, 16)
        except ValueError:
            return False
    
    # Validate serial (16 hex chars)
    if len(identity["serial"]) != 16:
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate Android device identity")
    parser.add_argument("--name", type=str, help="Instance name")
    parser.add_argument("--count", type=int, default=1, help="Number of identities to generate")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()
    
    identities = []
    for i in range(args.count):
        identity = generate_identity(f"{args.name}-{i}" if args.name else None)
        if validate_identity(identity):
            identities.append(identity)
        else:
            print(f"Error: Generated invalid identity, retrying...")
            identity = generate_identity(f"{args.name}-{i}" if args.name else None)
            identities.append(identity)
    
    output = json.dumps(identities if args.count > 1 else identities[0], indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Identities written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
