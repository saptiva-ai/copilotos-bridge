# Plan: Fix PROMEDIO ME (WAVG + orphan point)

## Contexto

- **Causa raíz principal**: `peer_average.py:579` usa simple AVG; Tableau usa WAVG ponderado por cartera ME
- **Causa secundaria**: Punto huérfano INVEX por gaps en datos (NULL en meses adyacentes) + Plotly sin `connectgaps`
- **Evidencia completa**: Ver `research.md`

## Decisiones de diseño

### D1: Peso para WAVG — `cartera_total` como proxy

**Elegida**: Usar `cartera_total` (columna existente en `bank_fact_kpis_mensual`) como peso.

**Razón**:
- Ya está disponible, no requiere schema change ni re-backfill
- Es el portfolio total del banco (MN+ME+todo), no ME-específico
- Pero es mucho mejor que simple AVG (equal weighting)
- Si la precisión no es suficiente, se puede agregar `portfolio_me` en ticket separado

**Alternativa descartada**: Agregar columna `portfolio_me` al schema → requiere migration + re-backfill + riesgo. Se deja como mejora futura.

### D2: Alcance del WAVG — solo `tasa_me` y `tasa_mn`

- WAVG tiene sentido para tasas (pre-computed WAVG intra-banco, necesitan WAVG inter-banco)
- Otras métricas hip (imor, icor, icap, cvc, quebrantos) son ratios/montos directos, simple AVG es apropiado
- Discriminar por métrica con un set: `WAVG_METRICS = {"tasa_me", "tasa_mn"}`

### D3: Punto huérfano — `connectgaps: true`

- Agrega `"connectgaps": True` a los traces de Plotly en `build_plotly_config()`
- Esto conecta la línea INVEX sobre meses sin dato, eliminando el marker aislado
- Los datos son correctos — el huérfano es solo visual por gaps en la fuente

---

## Phase 1: WAVG en `_execute_hip_metric`

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py`

### Paso 1.1: Modificar SQL para incluir `cartera_total`

Líneas ~522-531. Agregar `kpi.cartera_total` al SELECT:

```python
sql = sa_text(
    "SELECT kpi.periodo_id::text AS periodo, "
    "  UPPER(kpi.banco_norm) AS banco, "
    f"  kpi.{db_column}, "
    "  kpi.cartera_total "                        # ← NUEVO
    "FROM bank_fact_kpis_mensual kpi "
    "WHERE UPPER(kpi.banco_norm) IN :banks"
    f"  AND kpi.{db_column} IS NOT NULL"
    f"{date_filter} "
    "ORDER BY kpi.periodo_id, kpi.banco_norm"
).bindparams(bindparam("banks", expanding=True))
```

### Paso 1.2: Almacenar pesos en `periodo_data`

Líneas ~550-558. Cambiar estructura de `periodo_data` para incluir peso:

```python
# Antes: periodo_data[periodo][banco] = value
# Después: periodo_data[periodo][banco] = (value, weight)

periodo_data: Dict[str, Dict[str, tuple[float, Optional[float]]]] = {}
for row in raw_rows:
    periodo = str(row[0])
    banco = str(row[1])
    value = float(row[2]) if row[2] is not None else None
    weight = float(row[3]) if row[3] is not None else None
    if periodo not in periodo_data:
        periodo_data[periodo] = {}
    if value is not None:
        periodo_data[periodo][banco] = (value, weight)
```

### Paso 1.3: Computar WAVG para tasa_me/tasa_mn, simple AVG para el resto

Líneas ~570-580. Agregar lógica condicional:

```python
WAVG_METRICS = {"tasa_me", "tasa_mn"}

for periodo in sorted(periodo_data.keys()):
    fecha_str = f"{periodo[:4]}-{periodo[4:6]}-01"
    bank_entries = periodo_data[periodo]

    # Normalize values
    norm_entries = {
        banco: (self._normalizer.normalize(metric_lower, val), weight)
        for banco, (val, weight) in bank_entries.items()
    }

    target_entry = norm_entries.get(target_upper)
    target_norm = target_entry[0] if target_entry else None

    # Compute peer average
    if db_column in WAVG_METRICS:
        # WAVG: SUM(value * weight) / SUM(weight)
        weighted_pairs = [
            (v, w) for v, w in norm_entries.values()
            if v is not None and w is not None and w > 0
        ]
        if weighted_pairs:
            peer_avg = (
                sum(v * w for v, w in weighted_pairs)
                / sum(w for _, w in weighted_pairs)
            )
        else:
            # Fallback to simple AVG if no weights available
            all_norm = [v for v, _ in norm_entries.values() if v is not None]
            peer_avg = sum(all_norm) / len(all_norm) if all_norm else None
    else:
        # Simple AVG for non-tasa metrics
        all_norm = [v for v, _ in norm_entries.values() if v is not None]
        peer_avg = sum(all_norm) / len(all_norm) if all_norm else None

    dates.append(fecha_str)
    target_values.append(round(target_norm, 4) if target_norm is not None else None)
    peer_values.append(round(peer_avg, 4) if peer_avg is not None else None)
```

### Paso 1.4: Actualizar response_text

Línea ~219. Cambiar "AVG" → "WAVG" cuando aplica:

```python
# En _build_response_text, ajustar la línea de fórmula
f"{self.peer_label} = WAVG({self.target_bank}, {peer_list}), ponderado por cartera."
```

Solo para métricas de tasa. Requiere pasar un flag `is_wavg` al result o checar el nombre de la métrica.

---

## Phase 2: Orphan point fix

**Archivo**: `plugins/bank-advisor-private/src/bankadvisor/application/use_cases/peer_average.py`

### Paso 2.1: Agregar `connectgaps` a traces

En `build_plotly_config()` (líneas ~96-126), agregar `"connectgaps": True` a ambos traces:

```python
{
    "x": self.dates,
    "y": self.target_values,
    "type": "scatter",
    "mode": "lines+markers",
    "name": self.target_bank,
    "connectgaps": True,          # ← NUEVO
    "line": {"color": "#DC2626", "width": 3},
    ...
},
{
    "x": self.dates,
    "y": self.peer_average_values,
    "type": "scatter",
    "mode": "lines+markers",
    "name": self.peer_label,
    "connectgaps": True,          # ← NUEVO
    "line": {"color": "#4B5563", "width": 2.5},
    ...
},
```

---

## Phase 3: Tests

### Paso 3.1: Unit test para WAVG

Crear test que verifique:
- WAVG con pesos conocidos produce resultado correcto
- Fallback a simple AVG cuando pesos son NULL
- Métricas no-tasa siguen usando simple AVG

### Paso 3.2: Actualizar E2E test reference values

`tests/e2e/charts/test_peer_avg_tasa_me_chart.py` tiene `TABLEAU_REFERENCE` dict.
Los valores cambiarán con WAVG. Actualizar tras verificar contra DB.

### Paso 3.3: Validar punto huérfano

Verificar que Plotly JSON de la respuesta E2E tenga `connectgaps: true` en ambos traces.

---

## Archivos a modificar

| # | Archivo | Cambio |
|---|---------|--------|
| 1 | `plugins/.../use_cases/peer_average.py` | WAVG en `_execute_hip_metric` + `connectgaps` en `build_plotly_config` |
| 2 | `tests/e2e/charts/test_peer_avg_tasa_me_chart.py` | Actualizar reference values |
| 3 | `plugins/.../tests/unit/` | Nuevo test para WAVG |

## Riesgos

1. **`cartera_total` puede ser NULL** para algunos bancos/periodos → fallback a simple AVG
2. **Cambio afecta `tasa_mn` también** → verificar que no hay regresión en tests de MN
3. **E2E values cambiarán** → necesitan actualización cuidadosa

## Criterio de éxito

- [ ] PROMEDIO ME se acerca más a valores de Tableau (dirección correcta, no necesariamente exact match porque usamos proxy weight)
- [ ] No hay puntos huérfanos aislados en la gráfica INVEX
- [ ] E2E tests pasan con nuevos valores de referencia
- [ ] Métricas no-tasa (imor, icor, etc.) no cambian (simple AVG preservado)
