import pytest
import asyncio
from bankadvisor.services.query_spec_parser import QuerySpecParser
from bankadvisor.services.clarification_service import ClarificationService

@pytest.mark.asyncio
async def test_hu3_thresholds_robustness():
    """
    Test HU3: Verify that ambiguous queries trigger clarification.
    """
    parser = QuerySpecParser()
    clarification_service = ClarificationService()
    
    # 1. Query without bank (requires bank for evolution)
    query_no_bank = "Dame el IMOR de los últimos 3 meses"
    spec = await parser.parse(query_no_bank)
    enriched = clarification_service.enrich_with_clarifications(spec)
    
    assert enriched.requires_clarification is True
    assert "bank" in enriched.missing_fields or any(f.field == "bank" for f in enriched.ambiguity_flags)
    
    # 2. Query without metric
    query_no_metric = "Dime algo de INVEX"
    spec = await parser.parse(query_no_metric)
    enriched = clarification_service.enrich_with_clarifications(spec)
    
    assert enriched.requires_clarification is True
    assert "metric" in enriched.missing_fields
    
    # 3. Very ambiguous query
    query_ambiguous = "Quiero ver gráficas"
    spec = await parser.parse(query_ambiguous)
    enriched = clarification_service.enrich_with_clarifications(spec)
    
    assert enriched.requires_clarification is True
    assert len(enriched.missing_fields) >= 2 # metric and bank
    
    # 4. Valid query (should NOT trigger clarification)
    query_valid = "IMOR de INVEX"
    spec = await parser.parse(query_valid)
    assert spec.requires_clarification is False
    assert spec.confidence_score >= 0.7

@pytest.mark.asyncio
async def test_hu3_payload_structure():
    """
    Test HU3: Verify that the clarification payload is compatible with frontend.
    """
    parser = QuerySpecParser()
    clarification_service = ClarificationService()
    
    query = "Dime el IMOR" # Missing bank
    spec = await parser.parse(query)
    enriched = clarification_service.enrich_with_clarifications(spec)
    payload = clarification_service.get_clarification_payload(enriched)
    
    assert payload["type"] == "clarification"
    assert "clarifications" in payload
    assert len(payload["clarifications"]) > 0
    
    # Verify each clarification has the required fields for the UI
    for clar in payload["clarifications"]:
        assert "field" in clar
        assert "question" in clar
        assert "options" in clar
        assert len(clar["options"]) > 0