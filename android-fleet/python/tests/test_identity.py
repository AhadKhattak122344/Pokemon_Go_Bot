"""Unit tests for identity generation."""
import sys
sys.path.insert(0, '/workspace/android-fleet/python')

from identity import generate_identity, generate_imei, calculate_luhn_check_digit


def test_android_id_format():
    """Test Android ID is 16 hex characters."""
    identity = generate_identity()
    assert len(identity['android_id']) == 16
    assert all(c in '0123456789abcdef' for c in identity['android_id'])
    print("✓ Android ID format valid")


def test_imei_format():
    """Test IMEI is 15 digits."""
    identity = generate_identity()
    assert len(identity['imei']) == 15
    assert identity['imei'].isdigit()
    print("✓ IMEI format valid")


def test_imei_luhn():
    """Test IMEI passes Luhn check."""
    from identity import calculate_luhn_check_digit
    
    for _ in range(10):
        imei = generate_imei()
        # Verify using same algorithm as generation
        imei_14 = imei[:14]
        check = int(imei[14])
        
        # Recalculate check digit
        rev = imei_14[::-1]
        total = 0
        for i, ch in enumerate(rev):
            d = int(ch)
            if i % 2 == 0:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        
        expected_check = (10 - (total % 10)) % 10
        assert check == expected_check, f"IMEI {imei} check digit mismatch: {check} != {expected_check}"
        
        # Verify full IMEI sum is divisible by 10
        rev_full = imei[::-1]
        total_full = 0
        for i, ch in enumerate(rev_full):
            d = int(ch)
            if i % 2 == 1:  # Skip check digit at position 0
                d *= 2
                if d > 9:
                    d -= 9
            total_full += d
        
        assert total_full % 10 == 0, f"IMEI {imei} failed Luhn validation (sum={total_full})"
    
    print("✓ IMEI Luhn validation passed")


def test_mac_address_format():
    """Test MAC address format."""
    identity = generate_identity()
    mac = identity['mac_address']
    assert mac.startswith('00:16:3E')
    parts = mac.split(':')
    assert len(parts) == 6
    print("✓ MAC address format valid")


def test_serial_format():
    """Test serial number is 16 alphanumeric chars."""
    identity = generate_identity()
    assert len(identity['serial']) == 16
    assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in identity['serial'])
    print("✓ Serial number format valid")


def test_fingerprint():
    """Test fingerprint contains Pixel 4 data."""
    identity = generate_identity()
    assert identity['model'] == 'Pixel 4'
    assert identity['manufacturer'] == 'Google'
    assert 'google/flame/flame' in identity['fingerprint']
    print("✓ Fingerprint valid")


def test_uniqueness():
    """Test identities are unique."""
    identities = [generate_identity() for _ in range(100)]
    android_ids = [i['android_id'] for i in identities]
    imeis = [i['imei'] for i in identities]
    macs = [i['mac_address'] for i in identities]
    
    assert len(set(android_ids)) == 100
    assert len(set(imeis)) == 100
    assert len(set(macs)) == 100
    print("✓ All identities unique")


if __name__ == '__main__':
    test_android_id_format()
    test_imei_format()
    test_imei_luhn()
    test_mac_address_format()
    test_serial_format()
    test_fingerprint()
    test_uniqueness()
    print("\n✅ All tests passed!")
