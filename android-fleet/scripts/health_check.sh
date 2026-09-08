#!/bin/bash
# Health Check Script for Android Fleet
# Verifies instance health, ADB connectivity, and Google Services

set -e

HEALTHY=0
UNHEALTHY=0
TOTAL=0

check_instance() {
    local ip=$1
    local port=${2:-5555}
    TOTAL=$((TOTAL + 1))
    
    echo -n "Checking $ip:$port... "
    
    # Check ADB connectivity
    if ! adb connect "$ip:$port" >/dev/null 2>&1; then
        echo "❌ ADB connection failed"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
    
    # Wait for connection
    sleep 1
    
    # Check if device is recognized
    if ! adb devices | grep -q "$ip:$port.*device"; then
        echo "❌ Device not recognized"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
    
    # Check system properties
    MODEL=$(adb shell getprop ro.product.model 2>/dev/null | tr -d '\r\n')
    if [ -z "$MODEL" ] || [ "$MODEL" = "" ]; then
        echo "❌ Cannot read device model"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
    
    # Check Google Play Services
    GMS=$(adb shell pm path com.google.android.gms 2>/dev/null)
    if [[ ! "$GMS" =~ "package:" ]]; then
        echo "❌ Google Play Services missing"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
    
    # Check Play Store
    VENDING=$(adb shell pm path com.android.vending 2>/dev/null)
    if [[ ! "$VENDING" =~ "package:" ]]; then
        echo "❌ Google Play Store missing"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
    
    # Check memory (optional)
    MEM_INFO=$(adb shell cat /proc/meminfo 2>/dev/null | grep MemAvailable)
    if [ -z "$MEM_INFO" ]; then
        echo "⚠️  Cannot read memory info (non-critical)"
    fi
    
    echo "✅ OK ($MODEL)"
    HEALTHY=$((HEALTHY + 1))
    return 0
}

echo "=========================================="
echo "Android Fleet Health Check"
echo "=========================================="
echo ""

# Check instances from file if provided
if [ -n "$1" ] && [ -f "$1" ]; then
    echo "Reading instances from $1..."
    while IFS=, read -r ip port name; do
        [[ "$ip" =~ ^#.*$ ]] && continue
        [[ -z "$ip" ]] && continue
        check_instance "$ip" "${port:-5555}"
    done < "$1"
elif [ -n "$ANDROID_FLEET_HOSTS" ]; then
    echo "Reading instances from ANDROID_FLEET_HOSTS..."
    IFS=',' read -ra HOSTS <<< "$ANDROID_FLEET_HOSTS"
    for host in "${HOSTS[@]}"; do
        check_instance "$host"
    done
else
    # Default: check common Android VM IP ranges
    echo "Scanning common IP ranges..."
    for i in {100..120}; do
        ip="192.168.100.$i"
        check_instance "$ip" 2>/dev/null || true
    done
fi

echo ""
echo "=========================================="
echo "Health Check Summary"
echo "=========================================="
echo "Total Instances: $TOTAL"
echo "Healthy:         $HEALTHY"
echo "Unhealthy:       $UNHEALTHY"
echo "Health Rate:     $(( (HEALTHY * 100) / (TOTAL > 0 ? TOTAL : 1) ))%"
echo "=========================================="

if [ $UNHEALTHY -gt 0 ]; then
    exit 1
fi
exit 0
