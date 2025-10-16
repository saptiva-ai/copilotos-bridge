"""Tests for the intent classification endpoint."""

import os
import sys
from typing import List, Optional

import pytest
from fastapi.testclient import TestClient


# Ensure the application package is importable when running tests directly
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(CURRENT_DIR, '..', 'src')
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, SRC_DIR)


@pytest.fixture(scope="module")
def client() -> TestClient:
    try:
        from src.main import app
    except ModuleNotFoundError:
        from fastapi import FastAPI
        from pydantic import BaseModel

        from src.services.intent_service import IntentClassifier

        classifier = IntentClassifier()
        fallback_app = FastAPI()

        class _IntentRequest(BaseModel):
            text: str

        class _IntentResponse(BaseModel):
            intent: str
            confidence: float
            reasons: List[str]
            model: str
            fallback_used: bool
            raw_intent: Optional[str]

        @fallback_app.post("/api/intent", response_model=_IntentResponse)
        async def classify_intent(request: _IntentRequest) -> _IntentResponse:
            prediction = await classifier.classify(request.text)
            return _IntentResponse(
                intent=prediction.intent,
                confidence=prediction.confidence,
                reasons=prediction.reasons,
                model=prediction.model,
                fallback_used=False,
                raw_intent=None,
            )

        app = fallback_app

    return TestClient(app)


class TestIntentEndpoint:
    """Behavioural coverage for /api/intent."""

    def test_greeting_detected(self, client: TestClient) -> None:
        response = client.post("/api/intent", json={"text": "Hola, buen día"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["intent"] == "Greeting"
        assert payload["confidence"] >= 0.6

    def test_question_mark_researchable(self, client: TestClient) -> None:
        response = client.post(
            "/api/intent",
            json={"text": "¿Cuál es el impacto del nearshoring en México 2024?"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["intent"] == "Researchable"
        assert payload["confidence"] >= 0.7
        assert any("Pregunta" in reason for reason in payload["reasons"])

    def test_ambiguous_when_no_signals(self, client: TestClient) -> None:
        response = client.post("/api/intent", json={"text": "Necesito ayuda"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["intent"] in {"Ambiguous", "Command"}
        assert payload["confidence"] <= 0.75
