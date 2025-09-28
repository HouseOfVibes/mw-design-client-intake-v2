#!/usr/bin/env python3
"""
MW Design Studio - Security Monitor
Simple security monitoring and alerting for client intake form
"""

import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_security_log(log_file='security.log', hours_back=24):
    """Analyze security log for suspicious patterns"""

    if not os.path.exists(log_file):
        print(f"⚠️  Security log not found: {log_file}")
        return

    # Track events by IP and type
    ip_events = defaultdict(list)
    event_counts = defaultdict(int)
    suspicious_ips = set()

    cutoff_time = datetime.now() - timedelta(hours=hours_back)

    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Parse log line: TIMESTAMP - EVENT_TYPE - User: USER - IP: IP - DETAILS
                if ' - IP: ' in line:
                    parts = line.split(' - ')
                    if len(parts) >= 4:
                        timestamp_str = parts[0]
                        event_type = parts[1].strip()
                        ip_part = parts[3].split(' - ')[0].replace('IP: ', '').strip()

                        try:
                            # Parse timestamp (you may need to adjust format)
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')

                            if log_time >= cutoff_time:
                                ip_events[ip_part].append((log_time, event_type))
                                event_counts[event_type] += 1

                                # Flag suspicious patterns
                                if 'Failed' in event_type or 'Invalid' in event_type:
                                    suspicious_ips.add(ip_part)

                        except ValueError:
                            continue

    except Exception as e:
        print(f"❌ Error reading security log: {e}")
        return

    # Generate report
    print(f"🔍 Security Analysis - Last {hours_back} hours")
    print("=" * 50)

    print(f"\n📊 Event Summary:")
    for event_type, count in sorted(event_counts.items()):
        if count > 0:
            icon = "⚠️" if any(word in event_type for word in ['Failed', 'Invalid', 'Exceeded']) else "✅"
            print(f"  {icon} {event_type}: {count}")

    # Check for rate limiting triggers
    rate_limited_ips = []
    for ip, events in ip_events.items():
        submission_events = [e for e in events if 'Form Submission' in e[1]]
        if len(submission_events) > 10:  # More than 10 submissions
            rate_limited_ips.append((ip, len(submission_events)))

    if rate_limited_ips:
        print(f"\n⚠️  High Activity IPs:")
        for ip, count in sorted(rate_limited_ips, key=lambda x: x[1], reverse=True):
            print(f"  📍 {ip}: {count} form submissions")

    if suspicious_ips:
        print(f"\n🚨 Suspicious Activity:")
        for ip in suspicious_ips:
            events = ip_events[ip]
            print(f"  📍 {ip}: {len(events)} events")
            for timestamp, event_type in events[-3:]:  # Show last 3 events
                print(f"    └─ {timestamp.strftime('%H:%M:%S')} - {event_type}")

    if not suspicious_ips and not rate_limited_ips:
        print(f"\n✅ No suspicious activity detected")

    print(f"\n📋 Total unique IPs: {len(ip_events)}")
    print(f"📋 Total events: {sum(event_counts.values())}")

def check_environment_security():
    """Check for common security misconfigurations"""
    print(f"\n🔒 Environment Security Check")
    print("=" * 35)

    checks = [
        ("NOTION_TOKEN", "Notion API token"),
        ("NOTION_DATABASE_ID", "Notion database ID"),
        ("GOOGLE_CHAT_WEBHOOK_URL", "Google Chat webhook"),
        ("SECRET_KEY", "Flask secret key")
    ]

    for var_name, description in checks:
        value = os.getenv(var_name)
        if value:
            # Don't log actual values, just check if they exist
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"  ✅ {description}: {masked_value}")
        else:
            print(f"  ⚠️  {description}: Not set")

    # Check if running in debug mode
    flask_env = os.getenv('FLASK_ENV', 'development')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    if flask_env == 'production' and not debug:
        print(f"  ✅ Production mode: Properly configured")
    else:
        print(f"  ⚠️  Development mode: Set FLASK_ENV=production for production")

if __name__ == "__main__":
    print("🛡️  MW Design Studio - Security Monitor")
    print("=" * 45)

    analyze_security_log()
    check_environment_security()

    print(f"\n💡 Security Recommendations:")
    print("  • Monitor security.log regularly")
    print("  • Set up log rotation to prevent large files")
    print("  • Consider IP blocking for repeated suspicious activity")
    print("  • Ensure HTTPS is enabled in production")
    print("  • Review and rotate API tokens periodically")