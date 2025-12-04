#!/usr/bin/env python3
"""
Test script for is_bank_query function.

Tests the enhanced bank query detection logic with various test cases.
This is a standalone version that copies the logic for testing purposes.
"""

import asyncio
import sys
import re


async def is_bank_query(message: str) -> bool:
    """
    Enhanced heuristic to detect if a message is a banking query.

    (Copied from bank_analytics_client.py for standalone testing)
    """
    message_lower = message.lower()

    # 1. Financial metrics and indicators (high priority)
    financial_metrics = [
        "imor", "icor", "icap", "roi", "roe", "roa",
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

    # 2. Bank names (Mexican financial institutions)
    bank_names = [
        "invex", "banorte", "bancomer", "bbva", "banamex", "citibanamex",
        "santander", "hsbc", "scotiabank", "inbursa", "azteca",
        "banregio", "bajio", "banjercito", "afirme", "mifel",
        "ve por mas", "multiva", "intercam", "actinver",
        "banco", "bancos", "banca", "bancario", "bancaria", "bancarios"
    ]

    # 3. Banking product types
    banking_products = [
        "comercial", "consumo", "vivienda", "hipotecario", "hipoteca",
        "automotriz", "pyme", "empresarial", "corporativo",
        "tarjeta", "crédito", "credito", "préstamo", "prestamo",
        "financiamiento", "leasing", "arrendamiento",
        "ahorro", "inversión", "inversion", "cuenta", "depósito", "deposito"
    ]

    # 4. Regulatory and institutional terms
    regulatory_terms = [
        "cnbv", "banxico", "banco de méxico", "banco de mexico",
        "comisión nacional", "comision nacional",
        "regulación", "regulacion", "normativa",
        "indicador", "indicadores", "métrica", "metrica",
        "reporte", "informe", "estadística", "estadistica"
    ]

    # 5. Query patterns that suggest comparison or analysis
    query_patterns = [
        "comparar", "comparación", "comparacion", "versus", "vs",
        "evolución", "evolucion", "tendencia", "histórico", "historico",
        "análisis", "analisis", "desempeño", "desempeno", "performance",
        "ranking", "top", "mejor", "peor", "líder", "lider",
        "trimestre", "semestre", "anual", "mensual",
        "últimos", "ultimos", "reciente", "actual"
    ]

    # 6. Financial/banking context words
    financial_context = [
        "financiero", "financiera", "financieros", "financieras",
        "económico", "economico", "economía", "economia",
        "sector bancario", "sistema financiero",
        "mercado", "industria"
    ]

    # Check all categories
    all_keywords = (
        financial_metrics +
        bank_names +
        banking_products +
        regulatory_terms +
        query_patterns +
        financial_context
    )

    # Words that are too ambiguous and need word boundary checking
    ambiguous_words = ["banco", "bancos", "capital", "cartera", "comercial", "consumo"]

    # Return True if any keyword is found
    for keyword in all_keywords:
        if keyword in ambiguous_words:
            # Use word boundary for ambiguous words to avoid false positives
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, message_lower):
                # Additional context check for these ambiguous words
                context_nearby = message_lower[max(0, message_lower.find(keyword) - 50):
                                              min(len(message_lower), message_lower.find(keyword) + 50)]

                # Check if other banking keywords appear nearby
                banking_context_found = any(
                    bk in context_nearby
                    for bk in ["imor", "icor", "icap", "invex", "banorte", "santander",
                              "financiero", "financiera", "bancario", "bancaria",
                              "morosidad", "crédito", "credito", "tasa", "cnbv"]
                )

                if banking_context_found or keyword in ["bancos", "bancario", "bancaria"]:
                    return True
        else:
            # For non-ambiguous keywords, simple substring match is fine
            if keyword in message_lower:
                return True

    # Additional pattern matching for metric-like queries
    metric_patterns = [
        r'\b(cuál|cual|dame|muestra|obtener|consultar)\b.{0,30}\b(indicador|métrica|metrica|índice|indice|ratio)\b',
        r'\b(cómo|como)\b.{0,30}\b(está|esta|van|anda)\b.{0,20}\b(banco|cartera|mora)\b',
        r'\b(qué|que)\b.{0,30}\b(banco|bancos)\b.{0,30}\b(mejor|peor|líder|lider)\b'
    ]

    for pattern in metric_patterns:
        if re.search(pattern, message_lower):
            return True

    return False


async def test_bank_query_detection():
    """Test is_bank_query with various inputs."""

    # Test cases: (message, expected_result, description)
    test_cases = [
        # Banking queries - Should return True
        ("¿Cuál es el IMOR de INVEX?", True, "Direct IMOR query"),
        ("Muéstrame la cartera vencida de Banorte", True, "Cartera vencida query"),
        ("Compara el ICAP de INVEX con Santander", True, "Comparison query"),
        ("¿Cómo ha evolucionado la morosidad en 2024?", True, "Trend query"),
        ("Dame el indicador de capitalización", True, "Indicator query"),
        ("¿Qué banco tiene mejor ROE?", True, "Bank comparison"),
        ("Análisis de cartera comercial de HSBC", True, "Product analysis"),
        ("Reportes de CNBV sobre liquidez", True, "Regulatory query"),
        ("Tendencia histórica de créditos hipotecarios", True, "Historical trend"),
        ("¿Cuál es el ranking de bancos por activos?", True, "Ranking query"),
        ("Utilidades de Banamex último trimestre", True, "Financial metric"),
        ("Provisiones para cartera vencida", True, "Risk metric"),
        ("Desempeño de la banca múltiple", True, "Sector analysis"),
        ("Tasas de interés promedio del sistema", True, "Rate query"),
        ("¿Cómo está el mercado bancario mexicano?", True, "Market query"),

        # Non-banking queries - Should return False
        ("¿Cuál es el clima hoy?", False, "Weather query"),
        ("Dame una receta de pasta", False, "Recipe query"),
        ("¿Quién es el presidente de México?", False, "Political query"),
        ("Resumen de la película Inception", False, "Movie query"),
        ("¿Cómo se dice hello en francés?", False, "Translation query"),
        ("Código Python para factorial", False, "Programming query"),
        ("Historia de la revolución mexicana", False, "History query"),
        ("Consejos para hacer ejercicio", False, "Health query"),
        ("Mejores restaurantes en CDMX", False, "Restaurant query"),
        ("¿Qué hora es en Japón?", False, "Time query"),

        # Edge cases - Words that could be ambiguous
        ("Capital de Francia", False, "Geographic capital (not financial)"),
        ("Cartera de mano de cuero", False, "Wallet/purse product"),
        ("Reservar mesa en restaurante", False, "Restaurant reservation"),
        ("Consumo de energía eléctrica", False, "Energy consumption"),
        ("Comercial de televisión", False, "TV commercial"),
        ("Hipotecario el nombre de una calle", False, "Street name"),
        ("Banco de madera para jardín", False, "Wooden bench"),
    ]

    print("=" * 80)
    print("TESTING ENHANCED is_bank_query FUNCTION")
    print("=" * 80)
    print()

    passed = 0
    failed = 0
    failures = []

    for message, expected, description in test_cases:
        result = await is_bank_query(message)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        if result == expected:
            passed += 1
        else:
            failed += 1
            failures.append((message, expected, result, description))

        print(f"{status} | Expected: {expected:5} | Got: {result:5} | {description}")
        print(f"        Message: \"{message}\"")
        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    if failures:
        print("\nFAILED TESTS:")
        print("-" * 80)
        for message, expected, result, description in failures:
            print(f"  • {description}")
            print(f"    Message: \"{message}\"")
            print(f"    Expected: {expected}, Got: {result}")
            print()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_bank_query_detection())
    sys.exit(0 if success else 1)
