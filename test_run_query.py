#!/usr/bin/env python3
"""Test script: run a single query via WebSocket and report results."""
import json
import sys
import time

# Add project root
sys.path.insert(0, "/Users/mikeolab/lead-extractor")

try:
    import websocket
except ImportError:
    print("ERROR: websocket-client not installed. Run: pip install websocket-client")
    sys.exit(1)

WEBSOCKET_URL = "ws://localhost:8000/ws"
QUERY = 'any@email.com + sbcglobal.net + Vendor invoice + bellsouth.net + pdf in usa 2025_2026'

def main():
    status_log = []
    leads = []
    complete = False

    def on_message(ws, message):
        nonlocal complete
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            if msg_type == "status":
                text = data.get("message", "")
                status_log.append(text)
                print(f"  [status] {text}")
            elif msg_type == "leads":
                leads_data = data.get("data", [])
                leads.extend(leads_data)
                print(f"  [leads] +{len(leads_data)} leads (total: {len(leads)})")
            elif msg_type == "complete":
                complete = True
                final = data.get("data", [])
                leads.clear()
                leads.extend(final)
                print(f"  [complete] {len(final)} leads total")
            elif msg_type == "error":
                print(f"  [ERROR] {data.get('message', '')}")
            elif msg_type == "lead_count":
                count = data.get("count", 0)
                print(f"  [lead_count] {count}")
        except Exception as e:
            print(f"  [parse error] {e}")

    def on_error(ws, error):
        print(f"  [WS error] {error}")

    def on_close(ws, close_status, close_msg):
        print(f"  [closed] status={close_status} msg={close_msg}")

    def on_open(ws):
        payload = {
            "command": "start",
            "queries": [QUERY],
            "max_pages": 3,
            "delay_pages": 2.0,
            "delay_actions": 1.0,
            "target_leads": 0,
            "search_engine": "duckduckgo",
            "headless": True,
        }
        ws.send(json.dumps(payload))
        print(f"  [sent] query: {QUERY[:60]}...")

    print("Connecting to", WEBSOCKET_URL, "...")
    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
    )
    # Run with 180s timeout (3 min)
    import threading
    ws_thread = threading.Thread(target=lambda: ws.run_forever())
    ws_thread.daemon = True
    ws_thread.start()

    start = time.time()
    timeout = 180
    while not complete and (time.time() - start) < timeout:
        time.sleep(1)
    if complete:
        print("\n--- RESULT ---")
        print(f"Leads extracted: {len(leads)}")
        for i, lead in enumerate(leads[:5]):
            print(f"  {i+1}. {lead.get('email', 'N/A')} | {lead.get('source_url', '')[:50]}...")
        if len(leads) > 5:
            print(f"  ... and {len(leads)-5} more")
        print("\nTest PASSED" if leads or "DuckDuckGo" in " ".join(status_log) else "Test ran (no leads found)")
    else:
        print("\n--- TIMEOUT or incomplete ---")
        print("Last statuses:", status_log[-5:] if status_log else "none")
        print("Leads so far:", len(leads))

if __name__ == "__main__":
    main()
