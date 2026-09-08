#!/bin/bash
# Play Store Compatibility Fix Script
# Applies certified device fingerprint and clears Google services

set -e

echo "=========================================="
echo "Play Store Compatibility Fix"
echo "=========================================="

# Check if ADB is connected
if ! adb devices | grep -q "device$"; then
    echo "ERROR: No ADB device connected"
    echo "Connect with: adb connect <ip>:5555"
    exit 1
fi

echo "✓ ADB connection verified"

# Apply Pixel 4 fingerprint (Android 12)
echo ""
echo "Applying certified device fingerprint..."
adb shell su -c "setprop ro.product.model 'Pixel 4'"
adb shell su -c "setprop ro.product.manufacturer 'Google'"
adb shell su -c "setprop ro.build.fingerprint 'google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys'"
adb shell su -c "setprop ro.build.description 'flame-user 12 SP1A.210812.016.C2 1234567 release-keys'"
adb shell su -c "setprop ro.product.name 'flame'"
adb shell su -c "setprop ro.product.device 'flame'"
adb shell su -c "setprop ro.build.version.sdk '31'"
adb shell su -c "setprop ro.build.version.release '12'"

echo "✓ Fingerprint applied"

# Clear Google services data
echo ""
echo "Clearing Google services cache..."
adb shell pm clear com.google.android.gms
adb shell pm clear com.google.android.gsf
adb shell pm clear com.android.vending

echo "✓ Google services cleared"

# Clear cache directories
adb shell su -c "rm -rf /data/data/com.google.android.gms/cache/*" 2>/dev/null || true
adb shell su -c "rm -rf /data/data/com.google.android.gsf/cache/*" 2>/dev/null || true

# Reboot device
echo ""
echo "Rebooting device..."
adb reboot

echo ""
echo "Waiting for reboot (30 seconds)..."
sleep 30

# Wait for device to be ready
adb wait-for-device
sleep 10

# Verify fingerprint
echo ""
echo "Verifying configuration..."
MODEL=$(adb shell getprop ro.product.model | tr -d '\r\n')
FINGERPRINT=$(adb shell getprop ro.build.fingerprint | tr -d '\r\n')

echo "Device Model: $MODEL"
echo "Fingerprint: $FINGERPRINT"

if [ "$MODEL" = "Pixel 4" ]; then
    echo ""
    echo "=========================================="
    echo "✓ Device compatibility fixes applied!"
    echo "✓ Wait 5-15 minutes for Play Store certification"
    echo "=========================================="
else
    echo ""
    echo "WARNING: Fingerprint may not have been applied correctly"
    exit 1
fi
