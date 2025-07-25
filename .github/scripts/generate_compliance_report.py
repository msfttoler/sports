#!/usr/bin/env python3
import json
import os
from datetime import datetime

def load_json_safe(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return {}

def count_issues(data, key_path):
    try:
        current = data
        for key in key_path:
            current = current.get(key, [])
        return len(current) if isinstance(current, list) else 0
    except:
        return 0

# Generate compliance report
report = {
    "scan_date": datetime.now().isoformat(),
    "compliance_status": "PASS",
    "summary": {
        "critical_issues": 0,
        "high_issues": 0,
        "medium_issues": 0,
        "low_issues": 0
    },
    "details": {}
}

# Check all security scan results
for root, dirs, files in os.walk("security-results"):
    for file in files:
        if file.endswith('.json'):
            filepath = os.path.join(root, file)
            data = load_json_safe(filepath)
            
            if 'safety-results' in file:
                vulns = count_issues(data, ['vulnerabilities'])
                report["details"]["python_vulnerabilities"] = vulns
                if vulns > 0:
                    report["summary"]["high_issues"] += vulns
                    
            elif 'bandit-results' in file:
                issues = count_issues(data, ['results'])
                report["details"]["security_issues"] = issues
                if issues > 0:
                    report["summary"]["medium_issues"] += issues
                    
            elif 'checkov-results' in file:
                failed = count_issues(data, ['results', 'failed_checks'])
                report["details"]["infrastructure_issues"] = failed
                if failed > 0:
                    report["summary"]["medium_issues"] += failed

# Determine overall compliance status
total_critical = report["summary"]["critical_issues"]
total_high = report["summary"]["high_issues"]

if total_critical > 0:
    report["compliance_status"] = "FAIL - Critical issues found"
elif total_high > 5:
    report["compliance_status"] = "FAIL - Too many high-severity issues"
elif total_high > 0:
    report["compliance_status"] = "WARN - High-severity issues found"

# Save report
with open('compliance-report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"Compliance Status: {report['compliance_status']}")
print(f"Critical: {total_critical}, High: {total_high}")
