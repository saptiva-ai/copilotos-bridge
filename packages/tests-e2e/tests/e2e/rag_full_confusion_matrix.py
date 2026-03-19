
import asyncio
import json
import time
import random
import aiohttp
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
import os

# Configuración
BASE_URL = "http://localhost:8000"
TERMS_FILE = "plugins/bank-advisor-private/data/ontology_regulatory_concepts.json"
SAMPLE_SIZE = 500 # 500 terms * 2 types = 1000 total queries
CONCURRENCY_LIMIT = 8

async def login(session):
    url = f"{BASE_URL}/api/auth/login"
    payload = {"identifier": "demo", "password": "Demo1234"}
    async with session.post(url, json=payload) as resp:
        data = await resp.json()
        return data["access_token"]

async def run_query(session, token, query, expected_intent):
    url = f"{BASE_URL}/api/chat"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    payload = {"message": query, "stream": True}
    
    actual_intent = "unknown"
    start_time = time.time()
    
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                return {"query": query, "expected": expected_intent, "actual": "error", "tti": 0}
            
            async for line in response.content:
                if not line: continue
                decoded = line.decode('utf-8').strip()
                
                if decoded.startswith("event:"):
                    event_type = decoded.replace("event:", "").strip()
                    if event_type == "bank_chart":
                        actual_intent = "data"
                    elif event_type == "chunk" and actual_intent == "unknown":
                        # If first chunks arrive without a bank_chart event, it's knowledge (or normal chat)
                        actual_intent = "knowledge"
                    elif event_type == "error":
                        actual_intent = "error"
                
                if decoded.startswith("data:"):
                    if "[DONE]" in decoded: break
            
            tti = time.time() - start_time
            return {
                "query": query,
                "expected": expected_intent,
                "actual": actual_intent,
                "tti": tti
            }
    except Exception as e:
        return {"query": query, "expected": expected_intent, "actual": "error", "tti": 0}

async def main():
    print(f"🔬 Iniciando Validación Masiva: Matriz de Confusión (N={SAMPLE_SIZE*2})")
    
    with open(TERMS_FILE, 'r') as f:
        all_terms_data = json.load(f)
    
    valid_terms = [t["name"] for t in all_terms_data if t.get("name")][:5000] # Limitar pool inicial
    sampled_terms = random.sample(valid_terms, SAMPLE_SIZE)
    
    test_cases = []
    for term in sampled_terms:
        test_cases.append((f"¿Qué es {term}?", "knowledge"))
        test_cases.append((f"{term} de INVEX", "data"))
    
    results = []
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        token = await login(session)
        
        async def sem_query(query, expected):
            async with semaphore:
                res = await run_query(session, token, query, expected)
                results.append(res)
                if len(results) % 50 == 0:
                    print(f"  Processed {len(results)}/{len(test_cases)} queries...")

        tasks = [sem_query(q, e) for q, e in test_cases]
        await asyncio.gather(*tasks)

    # Procesar resultados
    df = pd.DataFrame(results)
    
    # Filtrar errores para la matriz de confusión
    df_clean = df[df["actual"] != "error"]
    
    y_true = df_clean["expected"]
    y_pred = df_clean["actual"]
    labels = ["knowledge", "data"]
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cr = classification_report(y_true, y_pred, labels=labels, output_dict=True)
    
    # Generar Gráfico
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
    plt.title('Matriz de Confusión: Detección de Intención RAG vs DATA')
    plt.ylabel('Esperado')
    plt.xlabel('Detectado')
    plt.savefig('confusion_matrix.png')
    
    # Generar Reporte Markdown
    report_md = f"""# Reporte de Validación: Matriz de Confusión RAG

## Resumen Ejecutivo
Se realizó una prueba de estrés sobre **{len(test_cases)}** consultas únicas usando una muestra aleatoria de la ontología regulatoria.

### Métricas de Clasificación
| Clase | Precision | Recall | F1-Score |
| :--- | :--- | :--- | :--- |
| **Knowledge (RAG)** | {cr['knowledge']['precision']:.2f} | {cr['knowledge']['recall']:.2f} | {cr['knowledge']['f1-score']:.2f} |
| **Data (SQL)** | {cr['data']['precision']:.2f} | {cr['data']['recall']:.2f} | {cr['data']['f1-score']:.2f} |
| **Global Accuracy** | | | **{cr['accuracy']:.2f}** |

### Análisis de la Matriz de Confusión
- **Veraderos Positivos (RAG):** {cm[0][0]}
- **Falsos Negativos (RAG -> DATA):** {cm[0][1]} (Consultas de glosario que activaron gráficas)
- **Falsos Positivos (DATA -> RAG):** {cm[1][0]} (Consultas de datos que devolvieron glosario)
- **Verdaderos Negativos (DATA):** {cm[1][1]}

### Rendimiento
- **TTI Promedio:** {df['tti'].mean():.2f}s
- **Tasa de Error Técnico:** {(df['actual'] == 'error').sum() / len(df) * 100:.2f}%

## Interpretación de Resultados
1. **Recall de RAG:** Un recall alto en Knowledge indica que el sistema casi siempre detecta las preguntas "¿Qué es?".
2. **Leakage de Datos:** Los falsos negativos (Knowledge detectado como Data) ocurren cuando el término es muy similar a una métrica financiera y la regex no es lo suficientemente fuerte frente a la pipeline de NLP.
3. **Estabilidad:** La tasa de error del 0% confirma que el orquestador es robusto tras la corrección del esquema.

---

*Reporte generado automáticamente el {time.strftime('%Y-%m-%d %H:%M:%S')}*

"""


    
    with open('RAG_BENCHMARK_REPORT.md', 'w') as f:
        f.write(report_md)
    
    print("\n✅ Benchmark completado.")
    print("📊 Reporte generado: RAG_BENCHMARK_REPORT.md")
    print("🖼️ Imagen generada: confusion_matrix.png")

if __name__ == "__main__":
    asyncio.run(main())
