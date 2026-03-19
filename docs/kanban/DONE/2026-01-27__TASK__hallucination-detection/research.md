# Research: Análisis de Alucinaciones en Respuestas Bancarias

## Metodología de Investigación

1. Conexión a MongoDB de producción via SSH (servidor interno)
2. Identificación de usuario de prueba
3. Extracción de 3 feedbacks negativos
4. Análisis de conversación completa (24 mensajes)
5. Comparación de datos del bank-advisor vs respuestas del LLM

---

## Datos Extraídos

### Usuario
```json
{
  "_id": "7f5aa3b9-8f98-459e-abc2-0148b23486f9",
  "email": "test-user@example.com"
}
```

### Feedbacks Negativos
```json
[
  {
    "message_id": "02cbd8d9-4478-4ca4-81a1-9b45e1ec4230",
    "rating": "down",
    "created_at": "2026-01-21T20:27:36Z"
  },
  {
    "message_id": "1688173e-0fa3-4c25-aa17-d8bad44dd3e1",
    "rating": "down",
    "created_at": "2026-01-21T20:24:48Z"
  },
  {
    "message_id": "138f5c2a-e928-4d61-9f5c-c4d09b19f5ef",
    "rating": "down",
    "created_at": "2026-01-21T20:22:51Z"
  }
]
```

### Sesión de Chat Analizada
- **ID:** `ea9ea471-f54c-4153-801e-95c3f00597af`
- **Total mensajes:** 24
- **Duración:** ~14 minutos (20:13 - 20:27 UTC)
- **Tema:** Cartera Comercial de INVEX

---

## Cronología de la Conversación

| # | Hora | Rol | Contenido (resumen) | Problema |
|---|------|-----|---------------------|----------|
| 1 | 20:13 | User | ¿Cómo se ha comportado la cartera comercial de INVEX? | - |
| 2 | 20:14 | Assistant | Cartera = **16,402,586,992 MDP** ✅ | Correcto |
| 3 | 20:17 | User | Muéstrame la gráfica de evolución | - |
| 4 | 20:17 | Assistant | Gráfico disponible, valor = **16,402,586,992 MDP** ✅ | Correcto |
| 5 | 20:20 | User | ¿Qué es la cartera comercial? | - |
| 6 | 20:20 | Assistant | Definición correcta ✅ | Correcto |
| 7 | 20:20 | User | Saldo por entidad federativa a Oct 2025 | - |
| 8 | 20:21 | Assistant | Desglose por entidad **INVENTADO** ❌ | **ALUCINACIÓN** |
| 9 | 20:21 | User | Comparativo por región | - |
| 10 | 20:21 | Assistant | Desglose regional **INVENTADO** ❌ | **ALUCINACIÓN** |
| 11-14 | 20:22-23 | User/Asst | Repite pregunta, misma respuesta fabricada | **ALUCINACIÓN** |
| 15-18 | 20:23-24 | User/Asst | Tabla con % que suman 113.7% ❌ | **ALUCINACIÓN** |
| 19 | 20:25 | User | "¿Por qué el saldo es distinto?" | Usuario detecta error |
| 20 | 20:25 | Assistant | Intenta justificar con matemáticas incorrectas | **ALUCINACIÓN** |
| 21-24 | 20:26-27 | User/Asst | Sigue usando valor inventado (18.6B) | **ALUCINACIÓN** |

---

## Análisis Técnico de los Datos

### Datos Reales del Bank-Advisor (Metadata del Mensaje #12)

```json
{
  "bank_chart_data": {
    "type": "data",
    "metric_name": "CARTERA_COMERCIAL",
    "bank_names": ["INVEX"],
    "plotly_config": {
      "data": [{
        "x": ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01",
              "2025-05-01", "2025-06-01", "2025-07-01", "2025-08-01",
              "2025-09-01", "2025-10-01"],
        "y": [15047925032, 14971951116, 14650846075, 15067992191,
              15260561546, 15610402228, 16680672898, 16204194309,
              15956689215, 16402586992],
        "name": "INVEX"
      }]
    },
    "metadata": {
      "sql_generated": "SELECT fecha, banco_norm, cartera_comercial_total AS value FROM monthly_kpis WHERE banco_norm IN ('INVEX') ORDER BY fecha ASC;",
      "intent": "evolution"
    }
  }
}
```

**Observaciones:**
1. SQL solo consulta `cartera_comercial_total` - **NO hay columna de región**
2. Intent detectado: `evolution` - **NO `regional_breakdown`**
3. Datos disponibles: Serie temporal de 10 meses
4. **NO existe desglose regional en la fuente de datos**

### Datos Fabricados por el LLM

El LLM generó esta tabla (Mensaje #16 y #18):

```markdown
| Región    | Saldo (MDP)       | Participación (%) |
|-----------|-------------------|-------------------|
| Centro    | 7,745,103,317     | 47.2%             |
| Occidente | 4,471,864,208     | 27.3%             |
| Norte     | 3,249,782,454     | 19.8%             |
| Sur       | 1,935,836,993     | 11.8%             |
| Sureste   | 1,243,876,543     | 7.6%              |
| **Total** | **18,646,463,515**| **100.0%**        |
```

### Verificación Matemática

```python
# Suma de saldos fabricados
centro = 7_745_103_317
occidente = 4_471_864_208
norte = 3_249_782_454
sur = 1_935_836_993
sureste = 1_243_876_543

total_calculado = centro + occidente + norte + sur + sureste
# = 18,646,463,515 ✓ (suma correcta de valores fabricados)

# Suma de porcentajes
pct_total = 47.2 + 27.3 + 19.8 + 11.8 + 7.6
# = 113.7% ❌ (IMPOSIBLE)

# Porcentajes reales si los datos fueran correctos
pct_centro_real = (centro / total_calculado) * 100
# = 41.54% (no 47.2%)

# Valor real del bank-advisor
valor_real_oct_2025 = 16_402_586_992

# Diferencia
diferencia = total_calculado - valor_real_oct_2025
# = 2,243,876,523 MDP de diferencia (13.7% más)
```

---

## Patrones de Alucinación Detectados

### Patrón 1: Invención de Desgloses No Disponibles
- **Trigger:** Usuario pide desglose que no existe en datos
- **Comportamiento:** LLM inventa datos plausibles pero falsos
- **Frecuencia:** 100% cuando se pide regional/entidad federativa

### Patrón 2: Inconsistencia de Valores Base
- **Trigger:** LLM pierde track del valor original
- **Comportamiento:** Usa valor inventado (18.6B) en lugar del real (16.4B)
- **Frecuencia:** Después de primera alucinación, persiste

### Patrón 3: Errores Matemáticos Básicos
- **Trigger:** Cálculo de porcentajes
- **Comportamiento:** Porcentajes que no suman 100%
- **Frecuencia:** En todos los casos de datos fabricados

### Patrón 4: Confianza Excesiva
- **Trigger:** Respuesta con datos inventados
- **Comportamiento:** Presenta datos falsos como verificados
- **Ejemplo:** "datos actualizados al 2025-10-01 00:00:00" (pero inventados)

---

## Queries de MongoDB Utilizadas

### Encontrar usuario
```javascript
db.users.findOne({
  $or: [
    {email: /fsaavedra/i},
    {name: /fsaavedra/i}
  ]
})
```

### Obtener feedbacks negativos
```javascript
db.message_feedback.find({
  user_id: "7f5aa3b9-8f98-459e-abc2-0148b23486f9",
  rating: "down"
}).sort({created_at: -1})
```

### Obtener conversación completa
```javascript
db.messages.find({
  chat_id: "ea9ea471-f54c-4153-801e-95c3f00597af"
}).sort({created_at: 1})
```

### Obtener metadata de chart
```javascript
db.messages.findOne({
  _id: "138f5c2a-e928-4d61-9f5c-c4d09b19f5ef"
}, {metadata: 1})
```

---

## Conclusiones de la Investigación

1. **El problema es sistémico:** Cuando el usuario pide datos que no existen, el LLM inventa en lugar de declinar.

2. **El bank-advisor funciona correctamente:** Los datos devueltos son precisos y consistentes.

3. **El LLM no tiene constraints de grounding:** No hay validación de que las respuestas coincidan con los datos de la fuente.

4. **Usuarios expertos detectan el problema:** fsaavedra (analista bancario) notó la inconsistencia inmediatamente.

5. **El daño es a la confianza:** Aunque solo hay 3 feedbacks negativos, el impacto en credibilidad es significativo para usuarios expertos.
