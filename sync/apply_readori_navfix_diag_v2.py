from __future__ import annotations

import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
client = root / "Readori/Services/TTS/ReadoriAITTSClient.swift"
text = client.read_text(encoding="utf-8")
old = '''        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        try await deviceAuth.authorize(&request, retrying: retryingAuth)

        do {
'''
guarded = '''        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        try await deviceAuth.authorize(&request, retrying: retryingAuth)
        // NAVFIX_TEMP_STATUS_MATCH_GUARD

        do {
'''
if text.count(old) != 1:
    raise SystemExit(f"performStatus guard anchor expected once, found {text.count(old)}")
client.write_text(text.replace(old, guarded, 1), encoding="utf-8")

try:
    subprocess.run(
        [sys.executable, "sync/apply_readori_navfix_diag.py", str(root)],
        check=True,
    )
finally:
    current = client.read_text(encoding="utf-8")
    current = current.replace("        // NAVFIX_TEMP_STATUS_MATCH_GUARD\n", "", 1)
    client.write_text(current, encoding="utf-8")

if "NAVFIX_TEMP_STATUS_MATCH_GUARD" in client.read_text(encoding="utf-8"):
    raise SystemExit("temporary match guard leaked into source")
print("scoped navfix wrapper completed")
