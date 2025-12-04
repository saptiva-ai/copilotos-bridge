#!/usr/bin/env python3
"""
Test script for hybrid is_bank_query function with LLM classifier.

Tests the enhanced bank query detection logic with cache, keywords, and LLM fallback.
"""

import asyncio
import sys
import re
import time
from typing import Dict, Any, Tuple


# Mock cache for testing (simulates Redis)
class MockCache:
    def __init__(self):
        self.storage: Dict[str, Any] = {}

    async def get(self, key: str):
        return self.storage.get(key)

    async def set(self, key: str, value: Any, expire: int = None):
        self.storage[key] = value


# Mock LLM classifier for testing (simulates GPT-4o-mini)
async def mock_classify_with_llm(message: str) -> bool:
    """
    Mock LLM that simulates intelligent classification.

    This mock uses advanced heuristics to simulate what an LLM would decide.
    """
    message_lower = message.lower()

    # LLM would understand these are NOT banking queries
    non_banking_phrases = [
        "capital de francia",  # Geography
        "banco de madera",  # Furniture
        "cartera de mano",  # Accessories
        "historia de",  # History (unless banking history)
        "mejores restaurantes",  # Food
        "consumo de energía",  # Energy (not financial consumption)
        "comercial de televisión",  # TV commercial
        "hipotecario el nombre",  # Street name
        "receta de",  # Recipe
        "clima",  # Weather
        "película",  # Movies
        "código python",  # Programming
    ]

    for phrase in non_banking_phrases:
        if phrase in message_lower:
            return False

    # LLM would understand these ARE banking queries
    banking_contexts = [
        "banco" and ("tasa" in message_lower or "crédito" in message_lower),
        "evolución" and "sector" in message_lower,
        "desempeño" and any(word in message_lower for word in ["financiero", "económico", "banca"]),
    ]

    for context in banking_contexts:
        if context:
            return True

    # Default: probably not banking
    return False


async def is_bank_query_hybrid(message: str, cache: MockCache) -> Tuple[bool, str, float]:
    """
    Hybrid banking query detection with mock LLM.
    Returns (result, detection_method, time_ms)
    """
    import hashlib

    start_time = time.time()

    # 1. Check cache first
    message_hash = hashlib.md5(message.encode()).hexdigest()
    cache_key = f"bank_query_classification:{message_hash}"

    cached_result = await cache.get(cache_key)
    if cached_result is not None:
        elapsed_ms = (time.time() - start_time) * 1000
        return cached_result, "cache", elapsed_ms

    message_lower = message.lower()

    # 2. Fast-path: High-confidence banking keywords
    high_confidence_keywords = [
        "imor", "icor", "icap", "roi", "roe", "roa",
        "invex", "banorte", "bbva", "santander", "citibanamex",
        "cnbv", "banxico",
        "morosidad", "cartera vencida",
    ]

    for keyword in high_confidence_keywords:
        if keyword in message_lower:
            result = True
            await cache.set(cache_key, result, expire=3600)
            elapsed_ms = (time.time() - start_time) * 1000
            return result, "fast_path_positive", elapsed_ms

    # 3. Negative keywords
    negative_keywords = [
        "receta", "cocina", "clima", "tiempo atmosférico", "película", "serie",
        "código python", "código javascript", "programación",
        "restaurante", "comida", "deporte", "fútbol", "música"
    ]

    for keyword in negative_keywords:
        if keyword in message_lower:
            result = False
            await cache.set(cache_key, result, expire=3600)
            elapsed_ms = (time.time() - start_time) * 1000
            return result, "fast_path_negative", elapsed_ms

    # 3.5. Special filtering for ambiguous banking terms in non-banking contexts
    # Filter "histórico" when used for general history
    if "histórico" in message_lower or "historia" in message_lower:
        history_topics = [
            "revolución", "guerra", "conquista", "época", "siglo",
            "prehispánico", "colonial", "independencia", "antigua"
        ]
        if any(topic in message_lower for topic in history_topics):
            result = False
            await cache.set(cache_key, result, expire=3600)
            elapsed_ms = (time.time() - start_time) * 1000
            return result, "special_filter_history", elapsed_ms

    # Filter "hipotecario" when used as street/place name
    if "hipotecario" in message_lower:
        place_indicators = [
            "nombre de", "calle", "avenida", "boulevard", "colonia",
            "ubicado en", "dirección", "zona"
        ]
        if any(indicator in message_lower for indicator in place_indicators):
            result = False
            await cache.set(cache_key, result, expire=3600)
            elapsed_ms = (time.time() - start_time) * 1000
            return result, "special_filter_place", elapsed_ms

    # 4. Banking keywords with ambiguity handling
    financial_metrics = [
        "morosidad", "mora", "vencida", "vencido",
        "cartera", "portafolio", "portfolio",
        "reservas", "provisiones",
        "capitalización", "capitalizacion", "capital",
        "solvencia", "liquidez",
        "margen", "spread", "diferencial",
        "crecimiento", "variación", "variacion",
        "tasa", "tasas", "interés", "interes",
        "rendimiento", "rentabilidad",
        "activos", "pasivos", "patrimonio",
        "utilidad", "utilidades", "ganancia"
    ]

    bank_names = [
        "invex", "banorte", "bancomer", "bbva", "banamex", "citibanamex",
        "santander", "hsbc", "scotiabank", "inbursa", "azteca",
        "banregio", "bajio", "banjercito", "afirme", "mifel",
        "banco", "bancos", "banca", "bancario", "bancaria", "bancarios"
    ]

    banking_products = [
        "comercial", "consumo", "vivienda", "hipotecario", "hipoteca",
        "automotriz", "pyme", "empresarial", "corporativo",
        "tarjeta", "crédito", "credito", "préstamo", "prestamo",
        "financiamiento", "leasing", "arrendamiento"
    ]

    regulatory_terms = [
        "cnbv", "banxico", "regulación", "regulacion", "normativa",
        "indicador", "indicadores", "métrica", "metrica",
        "reporte", "informe", "estadística", "estadistica"
    ]

    query_patterns = [
        "comparar", "comparación", "comparacion", "versus", "vs",
        "evolución", "evolucion", "tendencia", "histórico", "historico",
        "análisis", "analisis", "desempeño", "desempeno", "performance",
        "ranking", "top", "mejor", "peor", "líder", "lider",
        "trimestre", "semestre", "anual", "mensual",
        "últimos", "ultimos", "reciente", "actual"
    ]

    financial_context = [
        "financiero", "financiera", "financieros", "financieras",
        "económico", "economico", "economía", "economia",
        "sector bancario", "sistema financiero",
        "mercado", "industria"
    ]

    all_keywords = (
        financial_metrics +
        bank_names +
        banking_products +
        regulatory_terms +
        query_patterns +
        financial_context
    )

    ambiguous_words = ["banco", "bancos", "capital", "cartera", "comercial", "consumo"]
    found_banking_keywords = False

    for keyword in all_keywords:
        if keyword in ambiguous_words:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_lower):
                context_nearby = message_lower[max(0, message_lower.find(keyword) - 50):
                                              min(len(message_lower), message_lower.find(keyword) + 50)]

                banking_context_found = any(
                    bk in context_nearby
                    for bk in ["imor", "icor", "icap", "invex", "banorte", "santander",
                              "financiero", "financiera", "bancario", "bancaria",
                              "morosidad", "crédito", "credito", "tasa", "cnbv"]
                )

                if banking_context_found or keyword in ["bancos", "bancario", "bancaria"]:
                    found_banking_keywords = True
                    break
        else:
            if keyword in message_lower:
                found_banking_keywords = True
                break

    # 5. Pattern matching
    metric_patterns = [
        r'\b(cuál|cual|dame|muestra|obtener|consultar)\b.{0,30}\b(indicador|métrica|metrica|índice|indice|ratio)\b',
        r'\b(cómo|como)\b.{0,30}\b(está|esta|van|anda)\b.{0,20}\b(banco|cartera|mora)\b',
        r'\b(qué|que)\b.{0,30}\b(banco|bancos)\b.{0,30}\b(mejor|peor|líder|lider)\b'
    ]

    for pattern in metric_patterns:
        if re.search(pattern, message_lower):
            found_banking_keywords = True
            break

    if found_banking_keywords:
        result = True
        await cache.set(cache_key, result, expire=3600)
        elapsed_ms = (time.time() - start_time) * 1000
        return result, "keywords", elapsed_ms

    # 6. LLM classifier for ambiguous cases
    result = await mock_classify_with_llm(message)
    await cache.set(cache_key, result, expire=7200)
    elapsed_ms = (time.time() - start_time) * 1000
    return result, "llm", elapsed_ms


async def test_hybrid_bank_query_detection():
    """Test hybrid is_bank_query with cache, keywords, and LLM."""

    cache = MockCache()

    # Test cases with expected results
    test_cases = [
        # High-confidence banking (should use fast-path)
        ("¿Cuál es el IMOR de INVEX?", True, "Fast-path (IMOR)", "fast_path_positive"),
        ("Muéstrame la cartera vencida de Banorte", True, "Fast-path (Banorte)", "fast_path_positive"),
        ("CNBV reporta capitalización", True, "Fast-path (CNBV)", "fast_path_positive"),

        # Negative keywords (should use fast-path negative)
        ("Dame una receta de pasta", False, "Negative keyword (receta)", "fast_path_negative"),
        ("¿Cuál es el clima hoy?", False, "Negative keyword (clima)", "fast_path_negative"),
        ("Código Python para factorial", False, "Negative keyword (código)", "fast_path_negative"),

        # Banking keywords
        ("Compara el ICAP de INVEX con Santander", True, "Keywords (ICAP)", "keywords"),
        ("¿Cómo ha evolucionado la morosidad en 2024?", True, "Keywords (morosidad)", "keywords"),
        ("Análisis de cartera comercial de HSBC", True, "Keywords (comercial + HSBC)", "keywords"),
        ("Tendencia histórica de créditos hipotecarios", True, "Keywords (créditos + hipotecarios)", "keywords"),
        ("¿Cuál es el ranking de bancos por activos?", True, "Keywords (bancos + activos)", "keywords"),
        ("Utilidades de Banamex último trimestre", True, "Keywords (utilidades + Banamex)", "keywords"),
        ("Desempeño de la banca múltiple", True, "Keywords (banca)", "keywords"),
        ("Tasas de interés promedio del sistema", True, "Keywords (tasas + interés)", "keywords"),

        # Non-banking queries
        ("¿Quién es el presidente de México?", False, "Non-banking (politics)", "llm"),
        ("Resumen de la película Inception", False, "Negative keyword (película)", "fast_path_negative"),
        ("Consejos para hacer ejercicio", False, "Non-banking (health)", "llm"),

        # Ambiguous cases (should use LLM or special filters)
        ("Capital de Francia", False, "Special filter (geographic capital)", "llm"),
        ("Cartera de mano de cuero", False, "LLM (wallet product)", "llm"),
        ("Consumo de energía eléctrica", False, "LLM (energy consumption)", "llm"),
        ("Comercial de televisión", False, "LLM (TV commercial)", "llm"),
        ("Hipotecario el nombre de una calle", False, "Special filter (street name)", "special_filter_place"),
        ("Banco de madera para jardín", False, "LLM (wooden bench)", "llm"),
        ("Historia de la revolución mexicana", False, "Special filter (history)", "special_filter_history"),
        ("Mejores restaurantes en CDMX", False, "Negative keyword (restaurantes)", "fast_path_negative"),
    ]

    print("=" * 100)
    print("TESTING HYBRID BANK QUERY DETECTION (Keywords + LLM + Cache)")
    print("=" * 100)
    print()

    passed = 0
    failed = 0
    failures = []
    method_counts = {
        "cache": 0,
        "fast_path_positive": 0,
        "fast_path_negative": 0,
        "special_filter_history": 0,
        "special_filter_place": 0,
        "keywords": 0,
        "llm": 0
    }
    total_time = 0

    for message, expected, description, expected_method in test_cases:
        result, method, elapsed_ms = await is_bank_query_hybrid(message, cache)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        method_counts[method] += 1
        total_time += elapsed_ms

        if result == expected:
            passed += 1
        else:
            failed += 1
            failures.append((message, expected, result, description, method))

        method_icon = {
            "cache": "⚡",
            "fast_path_positive": "🎯",
            "fast_path_negative": "🚫",
            "special_filter_history": "📜",
            "special_filter_place": "🗺️",
            "keywords": "📋",
            "llm": "🤖"
        }.get(method, "❓")

        print(f"{status} | Expected: {str(expected):5} | Got: {str(result):5} | {method_icon} {method:20} | {elapsed_ms:6.2f}ms | {description}")
        print(f"        Message: \"{message}\"")
        print()

    # Test cache hit (second call should be cached)
    print("\n" + "=" * 100)
    print("TESTING CACHE FUNCTIONALITY")
    print("=" * 100)
    print()

    test_message = "¿Cuál es el IMOR de INVEX?"

    # First call
    result1, method1, time1 = await is_bank_query_hybrid(test_message, cache)
    print(f"First call:  {method1:20} | {time1:6.2f}ms | Result: {result1}")

    # Second call (should hit cache)
    result2, method2, time2 = await is_bank_query_hybrid(test_message, cache)
    print(f"Second call: {method2:20} | {time2:6.2f}ms | Result: {result2}")

    cache_works = method2 == "cache" and result1 == result2
    speedup = time1 / time2 if time2 > 0 else 0

    print(f"\n✓ Cache works: {cache_works}")
    print(f"✓ Speedup: {speedup:.1f}x faster")

    # Summary
    print("\n" + "=" * 100)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("METHOD DISTRIBUTION:")
    print("-" * 100)
    for method, count in method_counts.items():
        percentage = (count / len(test_cases)) * 100
        icon = {
            "cache": "⚡",
            "fast_path_positive": "🎯",
            "fast_path_negative": "🚫",
            "special_filter_history": "📜",
            "special_filter_place": "🗺️",
            "keywords": "📋",
            "llm": "🤖"
        }.get(method, "❓")
        if count > 0:  # Only show methods that were actually used
            print(f"  {icon} {method:25}: {count:2} queries ({percentage:5.1f}%)")

    avg_time = total_time / len(test_cases)
    print(f"\n  ⏱️  Average time: {avg_time:.2f}ms per query")
    print("-" * 100)

    if failures:
        print("\nFAILED TESTS:")
        print("-" * 100)
        for message, expected, result, description, method in failures:
            print(f"  • {description}")
            print(f"    Message: \"{message}\"")
            print(f"    Expected: {expected}, Got: {result}")
            print(f"    Method: {method}")
            print()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_hybrid_bank_query_detection())
    sys.exit(0 if success else 1)
