# User-supplied proposal: not executed or validated

Received September 9, 2026. Preserved as source evidence, not setup instructions.
No outcome is claimed for the proposed Proxmox/Bliss/module/identity stack.
See EXPERIMENT_LOG.md for observed results and docs/DEBUGGING.md for prior review.

```text
1. Why Existing Emulators Fail for the Target Application
Issue	Why Standard AVD Fails	What We Need
No Google Play Services	Generic AVD doesn't include Play Store	Bliss OS with GApps
ARM Architecture	x86_64 AVD can't run ARM-native code	libhoudini/ARM translation
Device Not Certified	Google blocks sign-in on uncertified devices	Valid device fingerprint
No Root Access	Can't spoof device identity	Magisk systemless root
Play Integrity Failure	Emulator detected by Google	Play Integrity Fix module
Root Detection	App detects root/Magisk	Shamiko + MagiskHide
Emulator Detection	App detects it's running on an emulator	Device fingerprint + hardware spoofing
2. Complete Proxmox Setup (Required)
2.1 Hardware Requirements
Component	Minimum	Recommended
CPU	8 cores x86_64	64+ cores (AMD EPYC/Intel Xeon)
RAM	64GB	256GB+
Storage	1TB NVMe	4TB+ NVMe RAID10
Network	1Gbps	10Gbps+
2.2 Install Proxmox VE
bash
# On Debian/Ubuntu server
wget -qO - https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg | apt-key add -
echo "deb https://enterprise.proxmox.com/debian bookworm pve-enterprise" > /etc/apt/sources.list.d/pve-enterprise.list
apt update && apt install proxmox-ve postfix open-iscsi -y

# Install graphics libraries for Bliss OS
apt install libgl1 libegl1 -y

# Verify KVM acceleration
kvm-ok
3. Bliss OS Template Creation
3.1 Download Bliss OS with GApps
bash
# Download Bliss OS 16.9.7 with GApps (required for Play Store)
wget https://sourceforge.net/projects/blissos-x86/files/Official/BlissOS16/Gapps/Generic/Bliss-v16.9.7-x86_64-OFFICIAL-gapps-20241011.iso
⚠️ Critical: Must use the GApps version. FOSS version has no Play Store.

3.2 Upload ISO to Proxmox
bash
pvesm upload local /path/to/Bliss-v16.9.7-x86_64-OFFICIAL-gapps-20241011.iso
3.3 Create the VM
bash
qm create 9000 \
    --name "bliss-template" \
    --memory 8192 \
    --cores 4 \
    --cpu host \
    --machine q35 \
    --bios seabios \
    --sata0 local:64,format=qcow2 \
    --net0 virtio,bridge=vmbr0 \
    --vga std \
    --boot order=sata0 \
    --cdrom local:iso/Bliss-v16.9.7-x86_64-OFFICIAL-gapps-20241011.iso
3.4 Install Bliss OS
bash
qm start 9000
# Connect via VNC/console
# Follow installation:
# 1. Select "Installation" (not Live)
# 2. Create GPT partition table
# 3. Create partitions:
#    - EFI partition (200MB, type EFI)
#    - System partition (ext4, mount /system)
#    - Data partition (ext4, mount /data)
# 4. Install GRUB
# 5. Reboot, remove ISO
3.5 Initial Android Setup
Boot into Android

Complete setup wizard

Sign into Google Account (CRITICAL – provisions Play Store)

Let Play Store update Google Play Services

Enable Developer Options (tap Build Number 7 times)

Enable USB Debugging

3.6 Enable ADB Over TCP/IP
bash
# Get VM IP
qm guest cmd 9000 network-get-interfaces

# Connect via ADB
adb connect <VM_IP>:5555

# Set ADB to persist
adb shell setprop persist.adb.tcp.port 5555
adb shell setprop service.adb.tcp.port 5555
adb shell stop adbd
adb shell start adbd
4. Magisk Root Installation (Required)
4.1 Download Magisk
bash
wget https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk
4.2 Install Magisk APK
bash
adb install Magisk-v30.7.apk
4.3 Extract and Patch Boot Image
bash
# Extract boot image
adb shell su -c "dd if=/dev/block/by-name/boot of=/sdcard/boot.img"
adb pull /sdcard/boot.img

# Push for patching
adb push boot.img /sdcard/

# ON VM: Open Magisk → Install → Select and Patch a File → Choose boot.img
# Note output path (usually /sdcard/Download/magisk_patched_boot.img)

# Pull patched image
adb pull /sdcard/Download/magisk_patched_boot.img

# Flash
adb push magisk_patched_boot.img /sdcard/
adb shell su -c "dd if=/sdcard/magisk_patched_boot.img of=/dev/block/by-name/boot"

# Reboot
adb reboot
4.4 Verify Root
bash
adb wait-for-device
adb shell magisk -v
adb shell su -c "id"
5. Install Required Magisk Modules (Critical for Target App)
5.1 Download All Required Modules
bash
# Zygisk Next - Runtime hooking framework
wget https://github.com/Dr-TSNG/ZygiskNext/releases/latest/download/zygisk_next.zip

# Shamiko - Root detection evasion
wget https://github.com/LSPosed/LSPosed.github.io/releases/download/shamiko-1.0.1/shamiko-1.0.1-304-release.zip

# MagiskHide Props Config - Device fingerprint spoofing
wget https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf/releases/latest/download/MagiskHidePropsConf.zip

# Play Integrity Fix - Play Integrity API bypass (CRITICAL)
wget https://github.com/KOWX712/PlayIntegrityFix/releases/latest/download/PlayIntegrityFix.zip

# Universal SafetyNet Fix - SafetyNet bypass
wget https://github.com/kdrag0n/safetynet-fix/releases/latest/download/safetynet-fix.zip

# libhoudini - ARM Translation (CRITICAL for ARM-only apps)
wget https://github.com/geekspeed/magisk_libhoudini/releases/latest/download/magisk_libhoudini.zip

# LSPosed - Xposed framework for device spoofing
wget https://github.com/LSPosed/LSPosed/releases/latest/download/LSPosed-v1.9.2-7054-zygisk-release.zip

# Device Emulator - Hardware device spoofing
wget https://github.com/jianyu03/DeviceEmulator/releases/latest/download/device_emulator.zip
5.2 Push and Install Modules
bash
# Push all modules
adb push zygisk_next.zip /sdcard/
adb push shamiko.zip /sdcard/
adb push MagiskHidePropsConf.zip /sdcard/
adb push PlayIntegrityFix.zip /sdcard/
adb push safetynet-fix.zip /sdcard/
adb push magisk_libhoudini.zip /sdcard/
adb push LSPosed-v1.9.2-7054-zygisk-release.zip /sdcard/
adb push device_emulator.zip /sdcard/

# Install each module
adb shell su -c "magisk --install-module /sdcard/zygisk_next.zip"
adb shell su -c "magisk --install-module /sdcard/shamiko.zip"
adb shell su -c "magisk --install-module /sdcard/MagiskHidePropsConf.zip"
adb shell su -c "magisk --install-module /sdcard/PlayIntegrityFix.zip"
adb shell su -c "magisk --install-module /sdcard/safetynet-fix.zip"
adb shell su -c "magisk --install-module /sdcard/magisk_libhoudini.zip"
adb shell su -c "magisk --install-module /sdcard/LSPosed-v1.9.2-7054-zygisk-release.zip"
adb shell su -c "magisk --install-module /sdcard/device_emulator.zip"

# Reboot
adb reboot
5.3 Configure Magisk Settings
bash
adb wait-for-device

# Enable Zygisk
adb shell su -c "magisk --enable-zygisk"

# Enable DenyList
adb shell su -c "magisk --denylist enable"

# Add packages to hide from
adb shell su -c "magiskhide add com.google.android.gms"
adb shell su -c "magiskhide add com.google.android.gms.persistent"
adb shell su -c "magiskhide add com.google.android.gms.unstable"
adb shell su -c "magiskhide add com.google.android.gsf"
adb shell su -c "magiskhide add com.android.vending"

# Add target app to hide from
adb shell su -c "magiskhide add com.target.application"
6. ARM Translation Configuration (Critical for Target App)
6.1 Enable ARM Translation
bash
# Set native bridge properties
adb shell su -c "setprop persist.sys.nativebridge 1"
adb shell su -c "setprop ro.dalvik.vm.native.bridge houdini"
adb shell su -c "setprop ro.enable.native.bridge.exec 1"

# For 64-bit
adb shell su -c "setprop ro.dalvik.vm.native.bridge64 houdini64"

# Set CPU ABI (Android apps check this)
adb shell su -c "setprop ro.product.cpu.abilist arm64-v8a,armeabi-v7a,armeabi,x86_64,x86"
adb shell su -c "setprop ro.product.cpu.abilist32 armeabi-v7a,armeabi,x86"
adb shell su -c "setprop ro.product.cpu.abilist64 arm64-v8a,x86_64"

# Reboot
adb reboot
6.2 Verify ARM Translation
bash
adb shell "cat /proc/cpuinfo | grep -i arm"
# Should show ARMv7 or similar

adb shell "getprop ro.product.cpu.abilist"
# Should show arm64-v8a first
7. Device Fingerprint Configuration (Critical for Play Store)
7.1 Apply Pixel 4 Fingerprint
bash
# Via MagiskHide Props Config (recommended)
adb shell su -c "props"
# Menu: 1 → 2 → 3 (Google → Pixel 4)
# Confirm, reboot
7.2 Manual Fingerprint (If props doesn't work)
bash
adb shell su -c "setprop ro.product.model 'Pixel 4'"
adb shell su -c "setprop ro.product.manufacturer 'Google'"
adb shell su -c "setprop ro.build.fingerprint 'google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys'"
adb shell su -c "setprop ro.build.description 'flame-user 12 SP1A.210812.016.C2 1234567 release-keys'"
adb shell su -c "setprop ro.product.name flame"
adb shell su -c "setprop ro.product.device flame"
adb shell su -c "setprop ro.build.version.sdk 31"
adb shell su -c "setprop ro.build.version.release 12"

# Make permanent
adb shell su -c "mount -o rw,remount /system"
adb shell su -c "cp /system/build.prop /system/build.prop.bak"
adb shell su -c "echo 'ro.product.model=Pixel 4' >> /system/build.prop"
adb shell su -c "echo 'ro.product.manufacturer=Google' >> /system/build.prop"
adb shell su -c "echo 'ro.build.fingerprint=google/flame/flame:12/SP1A.210812.016.C2/1234567:user/release-keys' >> /system/build.prop"
adb shell su -c "echo 'ro.build.description=flame-user 12 SP1A.210812.016.C2 1234567 release-keys' >> /system/build.prop"
adb shell su -c "echo 'ro.product.name=flame' >> /system/build.prop"
adb shell su -c "echo 'ro.product.device=flame' >> /system/build.prop"
adb shell su -c "echo 'ro.build.version.sdk=31' >> /system/build.prop"
adb shell su -c "echo 'ro.build.version.release=12' >> /system/build.prop"
adb reboot
7.3 Alternative Fingerprints (If Pixel 4 gets flagged)
bash
# Pixel 5
google/barbet/barbet:12/SP1A.210812.016.C2/1234567:user/release-keys

# Pixel 6
google/oriole/oriole:13/TP1A.221005.002/1234567:user/release-keys

# Samsung Galaxy S21
samsung/r0qxxx/r0q:12/SP1A.210812.016.C2/1234567:user/release-keys
8. Device Identity Spoofing (Unique Device Per Instance)
8.1 LSPosed Configuration
bash
# Open LSPosed app on VM
# 1. Enable "Device Emulator" module
# 2. Reboot
8.2 Identity Generation Script
bash
#!/bin/bash
# generate_identity.sh

# Android ID (16-char hex)
ANDROID_ID=$(openssl rand -hex 8)

# IMEI (15 digits)
TAC=$(printf "%06d" $((RANDOM % 1000000)))
FAC=$(printf "%02d" $((RANDOM % 100)))
SNR=$(printf "%06d" $((RANDOM % 1000000)))
IMEI="${TAC}${FAC}${SNR}"

# MAC Address
MAC="00:16:3E:$(openssl rand -hex 3 | sed 's/\(..\)/\1:/g' | sed 's/:$//')"

# Serial
SERIAL=$(openssl rand -hex 8 | tr 'a-z' 'A-Z')

cat << EOF
{
  "android_id": "$ANDROID_ID",
  "imei": "$IMEI",
  "mac_address": "$MAC",
  "serial": "$SERIAL",
  "model": "Pixel 4",
  "manufacturer": "Google"
}
EOF
8.3 Apply Identity via ADB
bash
# Apply identity to VM
VM_IP=$1
ANDROID_ID=$2
IMEI=$3
SERIAL=$4

adb connect $VM_IP:5555

# Apply via build.prop
adb shell su -c "setprop ro.serialno $SERIAL"
adb shell su -c "setprop ro.ril.imei $IMEI"
adb shell su -c "setprop ro.product.model 'Pixel 4'"
adb shell su -c "setprop ro.product.manufacturer 'Google'"

# Apply via Device Emulator config
cat > /tmp/device_config.json << EOF
{
  "android_id": "$ANDROID_ID",
  "imei": "$IMEI",
  "serial": "$SERIAL",
  "model": "Pixel 4",
  "manufacturer": "Google"
}
EOF

adb push /tmp/device_config.json /sdcard/
adb shell su -c "cp /sdcard/device_config.json /data/data/com.device.emulator/config.json"

# Clear Google Services (forces re-registration)
adb shell pm clear com.google.android.gms
adb shell pm clear com.google.android.gsf
adb shell pm clear com.android.vending

adb reboot
9. Fix Play Store Compatibility
9.1 Clear Google Services Data
bash
adb shell pm clear com.google.android.gms
adb shell pm clear com.google.android.gsf
adb shell pm clear com.android.vending
adb shell su -c "rm -rf /data/data/com.google.android.gms/cache/*"
adb shell su -c "rm -rf /data/data/com.google.android.gsf/cache/*"
adb shell su -c "rm -rf /data/data/com.android.vending/cache/*"
adb reboot
9.2 Wait for Device Certification
bash
# Wait 5-15 minutes
adb shell "dumpsys package com.android.vending | grep -A 5 'lastUpdateTimestamp'"
# If timestamp appears, device is certified
9.3 Verify Play Store Shows "Install"
bash
adb shell am start -n com.android.vending/.AssetBrowserActivity
# Search for the target application
# Should show "Install" button (not "No eligible devices")
10. Convert to Template
bash
qm stop 9000
qm template 9000

# Verify
qm list
# Should show template with (template) flag
11. Clone Instances for Multiple Devices
11.1 Clone and Configure
bash
#!/bin/bash
# deploy_instance.sh

TEMPLATE_ID=9000
BASE_VM_ID=10000
VM_NAME=$1
IDENTITY=$(./generate_identity.sh)

# Clone from template
qm clone $TEMPLATE_ID $BASE_VM_ID --name $VM_NAME --full

# Set unique MAC
MAC=$(echo $IDENTITY | jq -r '.mac_address')
qm set $BASE_VM_ID --net0 virtio,macaddr=$MAC,bridge=vmbr0

# Start VM
qm start $BASE_VM_ID

# Wait for boot
sleep 30

# Apply identity
VM_IP=$(qm guest cmd $BASE_VM_ID network-get-interfaces | jq -r '.[0].ip-addresses[0].ip-address')
adb connect $VM_IP:5555
./apply_identity.sh $VM_IP $(echo $IDENTITY | jq -r '.android_id') $(echo $IDENTITY | jq -r '.imei') $(echo $IDENTITY | jq -r '.serial')

echo "Instance $VM_NAME deployed with identity: $IDENTITY"
12. Complete Verification Script
bash
#!/bin/bash
# verify_setup.sh

echo "=== VERIFYING ANDROID VM SETUP ==="

# 1. Check ADB
echo "Checking ADB..."
adb devices | grep emulator
if [ $? -eq 0 ]; then
    echo "✅ ADB connected"
else
    echo "❌ ADB not connected"
    exit 1
fi

# 2. Check Magisk
echo "Checking Magisk..."
MAGISK_VER=$(adb shell magisk -v 2>/dev/null)
if [ ! -z "$MAGISK_VER" ]; then
    echo "✅ Magisk installed: $MAGISK_VER"
else
    echo "❌ Magisk not installed"
fi

# 3. Check Root
echo "Checking root..."
ROOT=$(adb shell su -c "id" 2>/dev/null | grep uid=0)
if [ ! -z "$ROOT" ]; then
    echo "✅ Root access available"
else
    echo "❌ Root not available"
fi

# 4. Check Modules
echo "Checking Magisk modules..."
adb shell su -c "ls /data/adb/modules" | while read module; do
    echo "  📦 $module"
done

# 5. Check Zygisk
echo "Checking Zygisk..."
ZYGISK=$(adb shell getprop persist.zygisk.enabled 2>/dev/null)
if [ "$ZYGISK" = "1" ]; then
    echo "✅ Zygisk enabled"
else
    echo "❌ Zygisk not enabled"
fi

# 6. Check ARM Translation
echo "Checking ARM translation..."
ARM=$(adb shell "cat /proc/cpuinfo | grep -i arm" 2>/dev/null)
if [ ! -z "$ARM" ]; then
    echo "✅ ARM translation working"
else
    echo "❌ ARM translation not working"
fi

# 7. Check Device Fingerprint
echo "Checking device fingerprint..."
MODEL=$(adb shell getprop ro.product.model 2>/dev/null)
FINGERPRINT=$(adb shell getprop ro.build.fingerprint 2>/dev/null)
echo "  Model: $MODEL"
echo "  Fingerprint: $FINGERPRINT"

# 8. Check Google Play Services
echo "Checking Google Play Services..."
GMS=$(adb shell pm path com.google.android.gms 2>/dev/null)
if [[ "$GMS" =~ "package:" ]]; then
    echo "✅ Google Play Services installed"
else
    echo "❌ Google Play Services missing"
fi

# 9. Check Play Store
echo "Checking Play Store..."
STORE=$(adb shell pm path com.android.vending 2>/dev/null)
if [[ "$STORE" =~ "package:" ]]; then
    echo "✅ Play Store installed"
else
    echo "❌ Play Store missing"
fi

# 10. Check Play Integrity
echo "Checking Play Integrity..."
INTEGRITY=$(adb shell "dumpsys package com.google.android.gms | grep -A 10 'Play Integrity'" 2>/dev/null)
if [[ "$INTEGRITY" =~ "MEETS_DEVICE_INTEGRITY" ]]; then
    echo "✅ Play Integrity passing"
else
    echo "⚠️ Play Integrity status unknown"
fi

echo "=== VERIFICATION COMPLETE ==="

```
