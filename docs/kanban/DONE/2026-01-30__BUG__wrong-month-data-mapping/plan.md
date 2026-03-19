# Plan: Simplificación del Flujo de Analytics Context

## Objetivo

Reemplazar 2,345 líneas de código fragmentado por ~300 líneas robustas que:
1. Pasen datos completos al LLM (con fechas)
2. Sean debuggeables (logging estructurado)
3. Fallen de forma explícita (validación)
4. No dependan de prompts gigantes para evitar alucinaciones

---

## Fase 1: Nueva Estructura de Datos

### 1.1 Contrato de Datos (Pydantic)

**Archivo nuevo**: `apps/backend/src/schemas/analytics_data.py`

```python
"""
Esquemas para datos analíticos - Single Source of Truth.

Principio: Los datos deben ser auto-descriptivos.
El LLM no debería necesitar inferir nada.
"""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DataPoint(BaseModel):
    """Un punto de datos con su fecha - NUNCA separar valor de fecha."""
    fecha: date
    valor: float

    @field_validator('valor')
    @classmethod
    def validate_reasonable_value(cls, v, info):
        # ICAP no puede ser > 100% ni < 0%
        # Detecta el bug de multiplicación x100
        if abs(v) > 1000:
            raise ValueError(f"Valor sospechoso: {v}. ¿Multiplicación x100 duplicada?")
        return v


class BankTimeSeries(BaseModel):
    """Serie temporal de un banco - datos completos, no resúmenes."""
    banco: str
    datos: list[DataPoint] = Field(min_length=1)

    @property
    def primer_valor(self) -> DataPoint:
        return self.datos[0]

    @property
    def ultimo_valor(self) -> DataPoint:
        return self.datos[-1]

    @property
    def cambio_porcentual(self) -> Optional[float]:
        if len(self.datos) < 2 or self.primer_valor.valor == 0:
            return None
        return ((self.ultimo_valor.valor - self.primer_valor.valor)
                / abs(self.primer_valor.valor)) * 100


class AnalyticsPayload(BaseModel):
    """
    Payload completo para el LLM - todo lo que necesita, nada más.

    Diseño: Si el LLM necesita inferir algo, este schema está incompleto.
    """
    metrica: str
    metrica_display: str
    tipo: str  # "ratio" | "currency" | "count"
    unidad: str  # "%" | "MDP" | "unidades"

    # Datos crudos con fechas - NO resúmenes
    series: list[BankTimeSeries]

    # Metadata de la consulta
    fecha_datos: date
    fecha_inicio: date
    fecha_fin: date

    # Para debugging
    trace_id: str
    sql_ejecutado: Optional[str] = None

    def to_llm_context(self) -> str:
        """Genera contexto mínimo y completo para el LLM."""
        lines = [
            f"## Datos de {self.metrica_display}",
            f"Período: {self.fecha_inicio} a {self.fecha_fin}",
            f"Actualizado al: {self.fecha_datos}",
            "",
            "### Valores por banco:",
        ]

        for serie in self.series:
            lines.append(f"\n**{serie.banco}:**")
            # Mostrar todos los puntos, no resúmenes
            for punto in serie.datos[-6:]:  # Últimos 6 meses máximo
                lines.append(f"  - {punto.fecha}: {punto.valor:.2f}{self.unidad}")

            if serie.cambio_porcentual is not None:
                lines.append(
                    f"  - Cambio ({serie.primer_valor.fecha} → {serie.ultimo_valor.fecha}): "
                    f"{serie.cambio_porcentual:+.1f}%"
                )

        return "\n".join(lines)
```

### 1.2 Por qué esta estructura

| Antes | Después |
|-------|---------|
| `{"current": 19.19}` | `{"fecha": "2025-01-01", "valor": 19.19}` |
| LLM infiere fechas | LLM lee fechas explícitas |
| 536 líneas de "no alucines" | Datos auto-descriptivos |

---

## Fase 2: Extractor Simplificado

### 2.1 Reemplazo de chart_normalizer + analytics_context

**Archivo nuevo**: `apps/backend/src/services/analytics_extractor.py`

```python
"""
Analytics Extractor - Extrae datos de Plotly traces de forma robusta.

Principios:
1. Fallar ruidosamente si los datos son inválidos
2. Loggear cada transformación
3. Nunca perder información (especialmente fechas)
"""
from datetime import date, datetime
from typing import Any
from uuid import uuid4

import structlog

from ..schemas.analytics_data import (
    AnalyticsPayload,
    BankTimeSeries,
    DataPoint,
)

logger = structlog.get_logger(__name__)


class AnalyticsExtractor:
    """
    Extrae datos de bank_chart_data de forma robusta.

    ~150 líneas vs 536 de analytics_context.py
    """

    def __init__(self):
        self.trace_id = str(uuid4())[:8]

    def extract(self, bank_chart_data: dict) -> AnalyticsPayload:
        """
        Extrae payload completo de bank_chart_data.

        Raises:
            ValueError: Si los datos son inválidos o incompletos
        """
        logger.info(
            "extractor.start",
            trace_id=self.trace_id,
            has_plotly=bool(bank_chart_data.get("plotly_config")),
            metric=bank_chart_data.get("metric_name"),
        )

        # 1. Extraer metadata
        metadata = self._extract_metadata(bank_chart_data)

        # 2. Extraer series temporales CON FECHAS
        series = self._extract_series(bank_chart_data)

        # 3. Validar que tenemos datos útiles
        if not series:
            raise ValueError(f"No se pudieron extraer series de datos. trace_id={self.trace_id}")

        payload = AnalyticsPayload(
            metrica=metadata["metric"],
            metrica_display=metadata["metric_display"],
            tipo=metadata["type"],
            unidad=metadata["unit"],
            series=series,
            fecha_datos=metadata["data_as_of"],
            fecha_inicio=metadata["start_date"],
            fecha_fin=metadata["end_date"],
            trace_id=self.trace_id,
            sql_ejecutado=metadata.get("sql"),
        )

        logger.info(
            "extractor.complete",
            trace_id=self.trace_id,
            banks_count=len(series),
            total_points=sum(len(s.datos) for s in series),
            date_range=f"{payload.fecha_inicio} to {payload.fecha_fin}",
        )

        return payload

    def _extract_metadata(self, data: dict) -> dict:
        """Extrae metadata con logging de cada campo."""
        metadata = data.get("metadata", {}) or {}
        time_range = data.get("time_range", {}) or {}

        result = {
            "metric": metadata.get("metric") or data.get("metric_name", "unknown"),
            "metric_display": data.get("metric_name", "Métrica"),
            "type": metadata.get("metric_type", "ratio"),
            "unit": "%" if metadata.get("metric_type") == "ratio" else "MDP",
            "data_as_of": self._parse_date(data.get("data_as_of")),
            "start_date": self._parse_date(time_range.get("start")),
            "end_date": self._parse_date(time_range.get("end")),
            "sql": metadata.get("sql_generated"),
        }

        logger.debug(
            "extractor.metadata",
            trace_id=self.trace_id,
            **{k: str(v) for k, v in result.items() if k != "sql"}
        )

        return result

    def _extract_series(self, data: dict) -> list[BankTimeSeries]:
        """
        Extrae series temporales de las trazas Plotly.

        CRÍTICO: Extrae tanto X (fechas) como Y (valores).
        """
        plotly_config = data.get("plotly_config", {})
        traces = plotly_config.get("data", []) if plotly_config else []

        if not traces:
            logger.warning("extractor.no_traces", trace_id=self.trace_id)
            return []

        series = []
        for i, trace in enumerate(traces):
            bank_name = trace.get("name", f"Bank_{i}")
            x_values = trace.get("x", [])  # FECHAS - antes se ignoraban!
            y_values = trace.get("y", [])  # VALORES

            # Validar que tenemos ambos
            if not x_values or not y_values:
                logger.warning(
                    "extractor.incomplete_trace",
                    trace_id=self.trace_id,
                    bank=bank_name,
                    has_x=bool(x_values),
                    has_y=bool(y_values),
                )
                continue

            if len(x_values) != len(y_values):
                logger.error(
                    "extractor.mismatched_lengths",
                    trace_id=self.trace_id,
                    bank=bank_name,
                    x_len=len(x_values),
                    y_len=len(y_values),
                )
                continue

            # Construir DataPoints con fecha+valor juntos
            data_points = []
            for x, y in zip(x_values, y_values):
                if y is None:
                    continue
                try:
                    data_points.append(DataPoint(
                        fecha=self._parse_date(x),
                        valor=float(y),
                    ))
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "extractor.invalid_point",
                        trace_id=self.trace_id,
                        bank=bank_name,
                        x=x,
                        y=y,
                        error=str(e),
                    )

            if data_points:
                series.append(BankTimeSeries(
                    banco=bank_name,
                    datos=sorted(data_points, key=lambda p: p.fecha),
                ))

                logger.debug(
                    "extractor.series_extracted",
                    trace_id=self.trace_id,
                    bank=bank_name,
                    points=len(data_points),
                    first_date=str(data_points[0].fecha),
                    last_date=str(data_points[-1].fecha),
                )

        return series

    def _parse_date(self, value: Any) -> date:
        """Parse fecha de múltiples formatos."""
        if value is None:
            return date.today()
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            # Intentar formatos comunes
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(value[:19], fmt).date()
                except ValueError:
                    continue
            # Fallback: tomar primeros 10 chars
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                pass

        logger.warning(
            "extractor.date_parse_failed",
            trace_id=self.trace_id,
            value=str(value)[:50],
        )
        return date.today()
```

---

## Fase 3: Contexto LLM Simplificado

### 3.1 Generador de Contexto Mínimo

**Archivo nuevo**: `apps/backend/src/services/llm_context_builder.py`

```python
"""
LLM Context Builder - Genera contexto mínimo y correcto.

Filosofía:
- Datos correctos > Instrucciones largas
- Si necesitas decir "NO hagas X", el dato está mal
- El LLM es inteligente, dale datos y déjalo trabajar
"""
from typing import Optional

import structlog

from ..schemas.analytics_data import AnalyticsPayload

logger = structlog.get_logger(__name__)


class LLMContextBuilder:
    """
    Construye contexto para el LLM.

    ~80 líneas vs 536 de analytics_context.py
    """

    # Contexto base - NO instrucciones negativas
    BASE_CONTEXT = """Eres un analista financiero del sistema bancario mexicano.
Responde basándote ÚNICAMENTE en los datos proporcionados.
Si no tienes un dato específico, dilo claramente."""

    def build(
        self,
        payload: AnalyticsPayload,
        user_query: str,
        include_sql: bool = False,
    ) -> str:
        """
        Genera contexto completo para el LLM.

        Args:
            payload: Datos analíticos extraídos
            user_query: Pregunta original del usuario
            include_sql: Si incluir el SQL ejecutado (para debugging)
        """
        sections = [
            self.BASE_CONTEXT,
            "",
            payload.to_llm_context(),
            "",
            f"**Pregunta del usuario:** {user_query}",
        ]

        if include_sql and payload.sql_ejecutado:
            sections.extend([
                "",
                "---",
                f"SQL ejecutado (referencia): `{payload.sql_ejecutado[:200]}...`",
            ])

        context = "\n".join(sections)

        logger.info(
            "context_builder.complete",
            trace_id=payload.trace_id,
            context_length=len(context),
            banks=len(payload.series),
            metric=payload.metrica,
        )

        return context

    def build_empty_context(self, metric: str, banks: list[str]) -> str:
        """Contexto cuando no hay datos."""
        return f"""No se encontraron datos de {metric} para {', '.join(banks)}.

Responde indicando que no hay datos disponibles y sugiere:
- Probar con otro período
- Probar con otros bancos
- Verificar el nombre de la métrica"""

    def build_error_context(self, metric: str, error: str) -> str:
        """Contexto cuando hay error."""
        return f"""Hubo un error al consultar {metric}: {error}

Responde indicando el problema técnico y ofrece reintentar."""
```

### 3.2 Comparación de Contextos

**Antes (536 líneas):**
```
**⚠️ INSTRUCCIONES CRÍTICAS - LEER ANTES DE RESPONDER:**
- Esta consulta ES sobre DATOS BANCARIOS ANALÍTICOS...
**🚫 FRASES ABSOLUTAMENTE PROHIBIDAS:**
- "no encuentro información"
- "no tengo datos"...
**✅ CÓMO DEBES RESPONDER:**
...
**CHECKLIST ANTI-ALUCINACIÓN:**
□ ¿Estoy citando valores que están en las estadísticas?
...
```

**Después (~50 líneas de contexto generado):**
```
## Datos de ICAP
Período: 2025-01-01 a 2025-10-01
Actualizado al: 2025-10-01

### Valores por banco:

**BBVA:**
  - 2025-01-01: 19.19%
  - 2025-09-01: 19.97%
  - 2025-10-01: 20.06%
  - Cambio (2025-01-01 → 2025-10-01): +4.5%

**Pregunta del usuario:** ¿Cómo obtuviste que BBVA creció 4.5%?
```

El LLM ve **exactamente** qué valor corresponde a qué fecha. No hay nada que inferir.

---

## Fase 4: Integración

### 4.1 Modificar chat_stream_producer.py

```python
# En chat_stream_producer.py, reemplazar:

# ANTES:
from .analytics_context import BankAnalyticsContextService
# ...
context, context_type = BankAnalyticsContextService.build_llm_context(bank_chart_data)

# DESPUÉS:
from .analytics_extractor import AnalyticsExtractor
from .llm_context_builder import LLMContextBuilder

# ...
try:
    extractor = AnalyticsExtractor()
    payload = extractor.extract(bank_chart_data)
    context = LLMContextBuilder().build(payload, user_message.content)
except ValueError as e:
    logger.error("analytics.extraction_failed", error=str(e))
    context = LLMContextBuilder().build_error_context(
        metric=bank_chart_data.get("metric_name", "unknown"),
        error=str(e)
    )
```

---

## Fase 5: Testing

### 5.1 Tests de Extracción

```python
# tests/unit/test_analytics_extractor.py

def test_extractor_preserves_dates():
    """Las fechas NUNCA deben perderse."""
    data = {
        "metric_name": "ICAP",
        "plotly_config": {
            "data": [{
                "name": "BBVA",
                "x": ["2025-01-01", "2025-10-01"],
                "y": [19.19, 20.06],
            }]
        }
    }

    payload = AnalyticsExtractor().extract(data)

    assert payload.series[0].datos[0].fecha == date(2025, 1, 1)
    assert payload.series[0].datos[0].valor == 19.19
    assert payload.series[0].datos[1].fecha == date(2025, 10, 1)


def test_extractor_detects_suspicious_values():
    """Detecta multiplicación x100 duplicada."""
    data = {
        "metric_name": "ICAP",
        "plotly_config": {
            "data": [{
                "name": "BBVA",
                "x": ["2025-01-01"],
                "y": [2005.94],  # Claramente mal - ICAP no puede ser 2000%
            }]
        }
    }

    with pytest.raises(ValueError, match="sospechoso"):
        AnalyticsExtractor().extract(data)


def test_context_has_explicit_dates():
    """El contexto LLM debe tener fechas explícitas."""
    payload = AnalyticsPayload(
        metrica="icap_total",
        metrica_display="ICAP Total",
        tipo="ratio",
        unidad="%",
        series=[BankTimeSeries(
            banco="BBVA",
            datos=[
                DataPoint(fecha=date(2025, 1, 1), valor=19.19),
                DataPoint(fecha=date(2025, 10, 1), valor=20.06),
            ]
        )],
        fecha_datos=date(2025, 10, 1),
        fecha_inicio=date(2025, 1, 1),
        fecha_fin=date(2025, 10, 1),
        trace_id="test123",
    )

    context = payload.to_llm_context()

    assert "2025-01-01: 19.19%" in context
    assert "2025-10-01: 20.06%" in context
    assert "Cambio (2025-01-01 → 2025-10-01)" in context
```

---

## Resumen de Cambios

| Métrica | Antes | Después |
|---------|-------|---------|
| Líneas de código | 2,345 | ~400 |
| Archivos involucrados | 3 | 3 (nuevos, más simples) |
| Instrucciones negativas al LLM | 15+ | 0 |
| Datos con fechas | No | Sí |
| Logging estructurado | Parcial | Completo |
| Validación de datos | No | Sí |
| Tests específicos | No | Sí |

---

## Plan de Ejecución

1. **Crear schemas** (`analytics_data.py`) - Sin romper nada existente
2. **Crear extractor** (`analytics_extractor.py`) - Nuevo, paralelo
3. **Crear context builder** (`llm_context_builder.py`) - Nuevo, paralelo
4. **Escribir tests** - Validar que funciona
5. **Integrar** - Reemplazar en `chat_stream_producer.py`
6. **Deprecar** - Marcar `analytics_context.py` como deprecated
7. **Limpiar** - Eliminar código viejo después de validar en prod

---

## Archivos a Crear

```
apps/backend/src/
├── schemas/
│   └── analytics_data.py       # NUEVO - Contratos de datos
├── services/
│   ├── analytics_extractor.py  # NUEVO - Extrae datos con fechas
│   └── llm_context_builder.py  # NUEVO - Genera contexto mínimo
└── tests/unit/
    └── test_analytics_extractor.py  # NUEVO - Tests
```

## Archivos a Deprecar (después de validar)

```
apps/backend/src/services/streaming/
├── analytics_context.py   # 536 líneas → DEPRECATED
└── chart_normalizer.py    # extract_chart_statistics() → DEPRECATED
```
