
import requests
import json
import time

def test_nl2sql_regression():
    # 1. LOGIN
    login_url = "http://localhost:8000/api/auth/login"
    login_payload = {"identifier": "demo", "password": "Demo1234"}
    auth_res = requests.post(login_url, json=login_payload)
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "text/event-stream"}

    # 2. CALL CHAT API with Data query
    chat_url = "http://localhost:8000/api/chat"
    chat_payload = {"message": "IMOR de INVEX últimos 3 meses", "stream": True}
    
    print("\n📡 [Test] Sending data query for IMOR...")
    response = requests.post(chat_url, json=chat_payload, headers=headers, stream=True)
    
    full_content = ""
    event_types = []
    has_sql_in_content = False
    
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith("event:"):
                event_types.append(decoded_line.replace("event:", "").strip())
            if decoded_line.startswith("data:"):
                data_str = decoded_line.replace("data:", "").strip()
                if data_str != "[DONE]":
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            full_content += data["content"]
                            if "SELECT" in data["content"] and "FROM" in data["content"]:
                                has_sql_in_content = True
                    except:
                        pass

    # 3. ASSERTIONS
    errors = []
    
    # Check 1: Intent Detection
    if "bank_chart" not in event_types:
        errors.append("FAILURE: 'bank_chart' event NOT detected. Query missed the SQL pipeline.")
    
    # Check 2: SQL Injection in content
    if not has_sql_in_content:
        errors.append("FAILURE: SQL query NOT found in the assistant response text.")
    
    # Check 3: Interpretation (LLM analysis)
    if "INVEX" not in full_content or "%" not in full_content:
        errors.append("FAILURE: Assistant response seems generic or missing data interpretation.")

    if not errors:
        print("\n✅ [RESULT] NL2SQL is BACK and FUNCTIONAL.")
    else:
        print("\n❌ [RESULT] NL2SQL REGRESSION TEST FAILED:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n[Debug] Full response preview:\n{full_content[:500]}...")

if __name__ == "__main__":
    test_nl2sql_regression()
