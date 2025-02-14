#!/bin/bash

# Prompt user for domain
read -p "Enter the domain name (e.g., sub.example.com): " DOMAIN

# Prompt user to select a DNS record type
VALID_RECORDS=("A" "CNAME" "MX" "TXT" "NS" "AAAA")
while true; do
    read -p "Enter the DNS record type to monitor (${VALID_RECORDS[*]}): " RECORD_TYPE
    if [[ " ${VALID_RECORDS[@]} " =~ " $RECORD_TYPE " ]]; then
        break
    else
        echo "❌ Invalid record type! Please enter one of: ${VALID_RECORDS[*]}"
    fi
done

# Prompt user for DNS resolver
read -p "Enter the DNS resolver to use (default: 8.8.8.8): " DNS_RESOLVER
DNS_RESOLVER=${DNS_RESOLVER:-8.8.8.8}  # Default to 8.8.8.8 if nothing is entered

# Log file setup
LOGFILE="dns_ttl_log.txt"
echo "Starting DNS TTL Monitor for $DOMAIN ($RECORD_TYPE record) using $DNS_RESOLVER..." | tee -a "$LOGFILE"

# Get initial value and TTL
INITIAL_OUTPUT=$(dig @$DNS_RESOLVER $DOMAIN $RECORD_TYPE +noall +answer | head -n 1)
INITIAL_TTL=$(echo "$INITIAL_OUTPUT" | awk '{print $2}')
INITIAL_VALUE=$(echo "$INITIAL_OUTPUT" | awk '{$1=$2=$3=""; print $0}' | sed 's/^ *//')

if [[ -z "$INITIAL_VALUE" ]]; then
    echo "⚠️  Unable to resolve initial $RECORD_TYPE record. Please verify that the record exists."
    exit 1
fi

echo "✅ Initial $RECORD_TYPE Record: $INITIAL_VALUE (TTL: $INITIAL_TTL)" | tee -a "$LOGFILE"

while true; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$TIMESTAMP] Checking DNS records..." | tee -a "$LOGFILE"

    OUTPUT=$(dig @$DNS_RESOLVER $DOMAIN $RECORD_TYPE +noall +answer | head -n 1)
    TTL=$(echo "$OUTPUT" | awk '{print $2}')
    RESPONSE=$(echo "$OUTPUT" | awk '{$1=$2=$3=""; print $0}' | sed 's/^ *//')

    if [[ -z "$RESPONSE" ]]; then
        echo "Resolver: $DNS_RESOLVER -> No $RECORD_TYPE record found." | tee -a "$LOGFILE"
    else
        echo "Resolver: $DNS_RESOLVER -> $RESPONSE (TTL: $TTL)" | tee -a "$LOGFILE"
    fi

    # Check if the record has changed
    if [[ "$RESPONSE" != "$INITIAL_VALUE" && -n "$RESPONSE" ]]; then
        echo -e "\n🚨 DNS CHANGE DETECTED! 🚨"
        echo "Old Value: $INITIAL_VALUE"
        echo "New Value: $RESPONSE"
        echo "TTL: $TTL"
        echo "Timestamp: $TIMESTAMP"
        echo "---------------------------------\n"

        echo "[$TIMESTAMP] 🚨 CHANGE DETECTED! Old: $INITIAL_VALUE -> New: $RESPONSE (TTL: $TTL)" >> "$LOGFILE"

        # Update initial value for further monitoring
        INITIAL_VALUE="$RESPONSE"
    fi

    echo "---------------------------------" | tee -a "$LOGFILE"

    # Wait for TTL before checking again (default to 60s if TTL is missing)
    # THIS SCRIPT CREATED BY ARLEN KIRKALDIE 02/13/2025
    TTL=${TTL:-60}
    sleep $TTL
done
