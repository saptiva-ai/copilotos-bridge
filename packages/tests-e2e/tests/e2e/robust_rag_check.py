import requests
import json
import time

def test_rag_robustness():
    # 1. LOGIN to get token
    login_url = "http://localhost:8000/api/auth/login"
    login_payload = {"identifier": "demo", "password": "Demo1234"}
    auth_res = requests.post(login_url, json=login_payload)
    token = auth_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. CALL CHAT API with Definition query
    chat_url = "http://localhost:8000/api/chat"
    chat_payload = {"message": "¿Qué es ICOR?", "stream": True}
    
    # Add Accept header for SSE
    headers["Accept"] = "text/event-stream"
    
    print("\n📡 [Test] Sending definition query for ICOR...")
    start_time = time.time()
    response = requests.post(chat_url, json=chat_payload, headers=headers, stream=True)
    
    full_content = ""
    event_types = []
    
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
                        if "error" in data:
                            print(f"❌ [Error Event] {data.get('error')}: {data.get('message')}")
                            if data.get("details"):
                                print(f"   Details: {data.get('details')}")
                    except:
                        pass

    tti = time.time() - start_time
    print(f"⏱️ [Metric] TTI: {tti:.2f}s")
    print(f"📊 [Metric] Events detected: {event_types}")
    
    # 3. ROBUST ASSERTIONS
    errors = []
    
    # Check 1: Intent Priority
    if "bank_chart" in event_types:
        errors.append("FAILURE: 'bank_chart' event detected. Query fell into SQL pipeline instead of RAG.")
    
    # Check 2: Hallucination check
    if "Impuestos sobre la Renta" in full_content:
        errors.append("FAILURE: Hallucination detected. ICOR defined as taxes instead of Reserves.")
    
    # Check 3: Definition accuracy
    if "Porcentaje de reservas sobre cartera vencida" not in full_content:
        errors.append("FAILURE: Correct definition not found in response text.")
    
    # Check 4: SLA Compliance
    if tti > 5.0:
        errors.append(f"FAILURE: SLA Violated. TTI was {tti:.2f}s (Target < 5s).")

    if not errors:
        print("\n✅ [RESULT] RAG is ROBUST and ACCURATE. Priority fix verified.")
    else:
        print("\n❌ [RESULT] RAG TEST FAILED:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n[Debug] Full response received:\n{full_content}")

if __name__ == "__main__":
    test_rag_robustness()
