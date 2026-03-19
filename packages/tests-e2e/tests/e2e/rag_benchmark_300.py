
import asyncio
import json
import time
import random
import aiohttp
import pandas as pd
from typing import List, Dict
import os

# Configuración
BASE_URL = "http://localhost:8000"
TERMS_FILE = "plugins/bank-advisor-private/data/ontology_regulatory_concepts.json"
BENCHMARK_SIZE = 300
CONCURRENCY_LIMIT = 5  # Consultas simultáneas para no saturar el LLM

async def login(session):
    url = f"{BASE_URL}/api/auth/login"
    payload = {"identifier": "demo", "password": "Demo1234"}
    async with session.post(url, json=payload) as resp:
        data = await resp.json()
        return data["access_token"]

async def run_query(session, token, term):
    url = f"{BASE_URL}/api/chat"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    payload = {"message": f"¿Qué es {term}?", "stream": True}
    
    metrics = {
        "term": term,
        "tti": 0,
        "total_time": 0,
        "rag_hit": False,
        "has_chart_event": False,
        "event_types": [],
        "content_length": 0,
        "has_sources": False,
        "error": None
    }
    
    start_time = time.time()
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                metrics["error"] = f"HTTP {response.status}"
                return metrics
            
            full_content = ""
            async for line in response.content:
                if not line: continue
                decoded = line.decode('utf-8').strip()
                
                if decoded.startswith("event:"):
                    event_type = decoded.replace("event:", "").strip()
                    metrics["event_types"].append(event_type)
                    if event_type == "bank_chart":
                        metrics["has_chart_event"] = True
                
                if decoded.startswith("data:"):
                    data_str = decoded.replace("data:", "").strip()
                    if data_str == "[DONE]": break
                    
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            if metrics["tti"] == 0:
                                metrics["tti"] = time.time() - start_time
                            full_content += data["content"]
                    except:
                        pass
            
            metrics["total_time"] = time.time() - start_time
            metrics["content_length"] = len(full_content)
            metrics["rag_hit"] = "bank_chart" not in metrics["event_types"]
            metrics["has_sources"] = "Fuentes:" in full_content or "Source:" in full_content or "**Fuentes:**" in full_content
            
    except Exception as e:
        metrics["error"] = str(e)
    
    return metrics

async def main():
    print(f"🚀 Iniciando Benchmark de RAG (N={BENCHMARK_SIZE})")
    
    # 1. Cargar términos
    with open(TERMS_FILE, 'r') as f:
        all_terms_data = json.load(f)
    
    # Filtrar términos con nombre válido y elegir muestra
    valid_terms = [t["name"] for t in all_terms_data if t.get("name")]
    sampled_terms = random.sample(valid_terms, BENCHMARK_SIZE)
    
    print(f"📦 Cargados {len(valid_terms)} términos. Seleccionados {BENCHMARK_SIZE} para la prueba.")

    # 2. Ejecutar benchmark
    results = []
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        
        async def sem_query(term):
            async with semaphore:
                res = await run_query(session, token, term)
                print(f"  [{len(results)+1}/{BENCHMARK_SIZE}] Term: {term[:20]}... | TTI: {res['tti']:.2f}s | RAG: {res['rag_hit']}")
                results.append(res)

        tasks = [sem_query(term) for term in sampled_terms]
        await asyncio.gather(*tasks)

    # 3. Procesar resultados
    df = pd.DataFrame(results)
    
    # Métricas agregadas
    summary = {
        "Total Queries": len(df),
        "RAG Hit Rate (%)": (df["rag_hit"].sum() / len(df)) * 100,
        "Avg TTI (s)": df[df["tti"] > 0]["tti"].mean(),
        "Avg Total Time (s)": df["total_time"].mean(),
        "Source Citation Rate (%)": (df["has_sources"].sum() / len(df)) * 100,
        "Error Rate (%)": (df["error"].notnull().sum() / len(df)) * 100,
        "Chart Event Leak Rate (%)": (df["has_chart_event"].sum() / len(df)) * 100
    }

    print("\n" + "="*50)
    print("📊 RESUMEN DEL BENCHMARK")
    print("="*50)
    for k, v in summary.items():
        print(f"{k:.<30} {v:>10.2f}" if isinstance(v, float) else f"{k:.<30} {v:>10}")
    
    # Guardar reporte
    report_file = "rag_benchmark_results.csv"
    df.to_csv(report_file, index=False)
    print(f"\n✅ Reporte detallado guardado en: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())
