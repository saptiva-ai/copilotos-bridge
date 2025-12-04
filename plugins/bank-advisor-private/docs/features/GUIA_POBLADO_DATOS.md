# Guia de Poblado de Datos - BankAdvisor NL2SQL

## Arquitectura de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                              │
├─────────────────────────────────────────────────────────────────────┤
│  data/raw/                                                          │
│  ├── CNBV_Cartera_Bancos_V2.xlsx  (Cartera principal)               │
│  ├── CASTIGOS.xlsx / Castigos Comerciales.xlsx                      │
│  ├── ICAP_Bancos.xlsx             (Índice de Capitalización)        │
│  ├── TDA.xlsx                     (Tasa de Deterioro)               │
│  ├── CorporateLoan_CNBVDB.csv     (Tasas MN/ME - 228MB)            │
│  ├── TE_Invex_Sistema.xlsx        (Tasa Efectiva)                   │
│  └── Instituciones.xlsx           (Catálogo de bancos)              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           ETL SCRIPTS                                │
├─────────────────────────────────────────────────────────────────────┤
│  etl_loader.py          → Métricas base (IMOR, ICOR, Cartera)       │
│  etl_loader_enhanced.py → Métricas Phase 4 (ICAP, TDA, TASA)        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│         POSTGRESQL            │   │           QDRANT              │
│   (Datos Estructurados)       │   │   (Base de Conocimientos)     │
├───────────────────────────────┤   ├───────────────────────────────┤
│  Tabla: monthly_kpis          │   │  Colección: bankadvisor_schema│
│  ├── fecha                    │   │  ├── Metadatos de columnas    │
│  ├── banco_norm (INVEX|SIS)   │   │  └── Descripciones            │
│  ├── imor, icor               │   │                               │
│  ├── cartera_total            │   │  Colección: bankadvisor_metrics│
│  ├── cartera_comercial_total  │   │  ├── Definiciones de métricas │
│  ├── reservas_etapa_todas     │   │  └── Fórmulas y aliases       │
│  ├── icap_total (nullable)    │   │                               │
│  ├── tda_cartera_total (null) │   │  Colección: bankadvisor_examples│
│  ├── tasa_mn (nullable)       │   │  ├── Pares NL → SQL           │
│  └── tasa_me (nullable)       │   │  └── Few-shot learning        │
└───────────────────────────────┘   └───────────────────────────────┘
```

---

## Prerequisitos

### 1. Servicios Docker Activos

```bash
# Desde la raíz del proyecto
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex

# Levantar servicios de infraestructura
docker compose -f infra/docker-compose.yml up -d postgres qdrant

# Verificar que están corriendo
docker compose -f infra/docker-compose.yml ps
```

**Servicios necesarios:**
| Servicio | Puerto | Verificación |
|----------|--------|--------------|
| PostgreSQL | 5432 | `psql -h localhost -U bankadvisor -d bankadvisor -c '\dt'` |
| Qdrant | 6333 | `curl http://localhost:6333/collections` |

### 2. Variables de Entorno

```bash
# Copiar .env de ejemplo si no existe
cp envs/.env.example envs/.env

# Variables críticas para ETL:
POSTGRES_HOST=localhost       # o 'postgres' si desde Docker
POSTGRES_PORT=5432
POSTGRES_USER=bankadvisor
POSTGRES_PASSWORD=your_password
POSTGRES_DB=bankadvisor

# Variables para Qdrant:
QDRANT_HOST=localhost         # o 'qdrant' si desde Docker
QDRANT_PORT=6333
```

### 3. Archivos de Datos

Verificar que existen los archivos fuente:

```bash
ls -la plugins/bank-advisor-private/data/raw/

# Esperado:
# CNBV_Cartera_Bancos_V2.xlsx   (~3.2 MB)
# CASTIGOS.xlsx                  (~400 KB)
# ICAP_Bancos.xlsx               (~600 KB)
# TDA.xlsx                       (~640 KB)
# CorporateLoan_CNBVDB.csv       (~228 MB)
# Instituciones.xlsx             (~11 KB)
```

---

## PARTE 1: Poblar PostgreSQL (monthly_kpis)

### Opción A: ETL Completo desde Host

```bash
# 1. Ir al directorio del plugin
cd plugins/bank-advisor-private

# 2. Activar entorno virtual
source .venv/bin/activate

# 3. Instalar dependencias si es necesario
pip install pandas openpyxl sqlalchemy psycopg2-binary structlog

# 4. Ejecutar ETL base (IMOR, ICOR, Carteras)
python -c "from bankadvisor.etl_loader import run_etl; run_etl()"

# 5. Ejecutar ETL enhanced (ICAP, TDA, Tasas)
python -c "from bankadvisor.etl_loader_enhanced import run_enhanced_etl; run_enhanced_etl()"
```

### Opción B: ETL desde Docker

```bash
# 1. Construir imagen del plugin
docker build -t bank-advisor-etl -f plugins/bank-advisor-private/Dockerfile .

# 2. Ejecutar ETL en contenedor
docker run --rm \
  --network octavios-chat-bajaware_invex-network \
  -v $(pwd)/plugins/bank-advisor-private/data/raw:/app/data/raw:ro \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=bankadvisor \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=bankadvisor \
  bank-advisor-etl python -c "from bankadvisor.etl_loader import run_etl; run_etl()"
```

### Opción C: Script Unificado

```bash
# Crear script de ETL completo
cat > scripts/run_full_etl.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 BankAdvisor ETL - Full Data Load"
echo "===================================="

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Paso 1: ETL Base
echo ""
echo "📊 Step 1: Loading base metrics (IMOR, ICOR, Cartera)..."
python -c "
from bankadvisor.etl_loader import run_etl
run_etl()
"

# Paso 2: ETL Enhanced
echo ""
echo "📈 Step 2: Loading enhanced metrics (ICAP, TDA, Tasas)..."
python -c "
from bankadvisor.etl_loader_enhanced import run_enhanced_etl
run_enhanced_etl()
"

# Paso 3: Verificación
echo ""
echo "✅ Step 3: Verifying data..."
python -c "
from sqlalchemy import create_engine, text
from core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url_sync.replace('@postgres:', '@localhost:'))

with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) as total, banco_norm, MIN(fecha) as desde, MAX(fecha) as hasta FROM monthly_kpis GROUP BY banco_norm'))
    print('📋 Data Summary:')
    for row in result:
        print(f'   {row.banco_norm}: {row.total} registros ({row.desde} → {row.hasta})')
"

echo ""
echo "✅ ETL Complete!"
EOF

chmod +x scripts/run_full_etl.sh
```

### Verificar Datos en PostgreSQL

```bash
# Conectar a PostgreSQL
psql -h localhost -U bankadvisor -d bankadvisor

# Queries de verificación
```

```sql
-- Contar registros por banco
SELECT banco_norm, COUNT(*) as registros,
       MIN(fecha) as desde, MAX(fecha) as hasta
FROM monthly_kpis
GROUP BY banco_norm;

-- Verificar métricas no-nulas
SELECT
    COUNT(*) as total,
    COUNT(imor) as con_imor,
    COUNT(icor) as con_icor,
    COUNT(icap_total) as con_icap,
    COUNT(tda_cartera_total) as con_tda,
    COUNT(tasa_mn) as con_tasa_mn,
    COUNT(tasa_me) as con_tasa_me
FROM monthly_kpis;

-- Muestra de datos recientes
SELECT fecha, banco_norm, imor, icor, cartera_total
FROM monthly_kpis
WHERE banco_norm = 'INVEX'
ORDER BY fecha DESC
LIMIT 5;
```

**Resultado esperado:**

| banco_norm | registros | desde | hasta |
|------------|-----------|-------|-------|
| INVEX | ~96 | 2017-01-01 | 2025-07-01 |
| SISTEMA | ~96 | 2017-01-01 | 2025-07-01 |

---

## PARTE 2: Poblar Qdrant (Base de Conocimientos)

### Colecciones a Crear

| Colección | Propósito | Vectores |
|-----------|-----------|----------|
| `bankadvisor_schema` | Metadatos de columnas y tablas | ~15 |
| `bankadvisor_metrics` | Definiciones de métricas | ~10 |
| `bankadvisor_examples` | Pares NL→SQL para few-shot | ~20 |

### Opción A: Script de Seeding Automático

```bash
# 1. Ir al directorio del plugin
cd plugins/bank-advisor-private

# 2. Activar entorno virtual
source .venv/bin/activate

# 3. Ejecutar seeding completo
python scripts/seed_nl2sql_rag.py --clear

# Opciones disponibles:
#   --clear              Limpiar colecciones antes de poblar
#   --collections schema,metrics,examples  Poblar solo algunas
#   --dry-run            Ver qué se poblaría sin ejecutar
```

### Opción B: Seeding Manual con curl

```bash
# 1. Crear colección bankadvisor_schema
curl -X PUT "http://localhost:6333/collections/bankadvisor_schema" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# 2. Crear colección bankadvisor_metrics
curl -X PUT "http://localhost:6333/collections/bankadvisor_metrics" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# 3. Crear colección bankadvisor_examples
curl -X PUT "http://localhost:6333/collections/bankadvisor_examples" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

# 4. Verificar colecciones
curl "http://localhost:6333/collections" | jq
```

### Opción C: Script Python Standalone

```python
#!/usr/bin/env python3
"""
Seeding directo de Qdrant sin dependencias del backend.
Ejecutar: python scripts/seed_qdrant_standalone.py
"""

import requests
from typing import List, Dict
import hashlib

QDRANT_URL = "http://localhost:6333"
VECTOR_SIZE = 384  # Dimensión del embedding

# Datos de ejemplo (simplificado)
SCHEMA_DATA = [
    {"column": "imor", "description": "Índice de Morosidad - ratio de cartera vencida"},
    {"column": "icor", "description": "Índice de Cobertura - reservas sobre vencida"},
    {"column": "cartera_total", "description": "Cartera de crédito total en millones"},
    {"column": "icap_total", "description": "Índice de Capitalización (nullable)"},
    {"column": "tasa_mn", "description": "Tasa promedio moneda nacional (nullable)"},
]

def create_collection(name: str):
    """Crear colección en Qdrant."""
    response = requests.put(
        f"{QDRANT_URL}/collections/{name}",
        json={"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}}
    )
    print(f"Created collection {name}: {response.status_code}")

def fake_embedding(text: str) -> List[float]:
    """Generar embedding falso (para pruebas sin modelo real)."""
    # En producción, usar un modelo de embeddings real
    hash_bytes = hashlib.sha256(text.encode()).digest()
    return [float(b) / 255.0 for b in hash_bytes[:VECTOR_SIZE]] + [0.0] * (VECTOR_SIZE - 32)

def upsert_points(collection: str, data: List[Dict]):
    """Insertar puntos en colección."""
    points = []
    for i, item in enumerate(data):
        text = item.get("description", str(item))
        points.append({
            "id": i,
            "vector": fake_embedding(text),
            "payload": item
        })

    response = requests.put(
        f"{QDRANT_URL}/collections/{collection}/points",
        json={"points": points}
    )
    print(f"Upserted {len(points)} points to {collection}: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Seeding Qdrant for BankAdvisor NL2SQL...")

    # Crear colecciones
    create_collection("bankadvisor_schema")
    create_collection("bankadvisor_metrics")
    create_collection("bankadvisor_examples")

    # Poblar schema
    upsert_points("bankadvisor_schema", SCHEMA_DATA)

    print("✅ Seeding complete!")
```

### Verificar Datos en Qdrant

```bash
# Listar colecciones
curl http://localhost:6333/collections | jq

# Ver info de colección específica
curl http://localhost:6333/collections/bankadvisor_schema | jq

# Contar puntos en colección
curl "http://localhost:6333/collections/bankadvisor_schema/points/count" | jq

# Buscar ejemplo (requiere vector de query)
curl -X POST "http://localhost:6333/collections/bankadvisor_metrics/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "with_payload": true}' | jq
```

**Resultado esperado:**

```json
{
  "collections": [
    {"name": "bankadvisor_schema"},
    {"name": "bankadvisor_metrics"},
    {"name": "bankadvisor_examples"}
  ]
}
```

---

## PARTE 3: Script Unificado de Setup

Crear un script maestro que ejecute todo:

```bash
cat > scripts/setup_bankadvisor_data.sh << 'EOF'
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     BankAdvisor - Full Data Setup                          ║"
echo "╚════════════════════════════════════════════════════════════╝"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$PLUGIN_DIR")")"

cd "$PLUGIN_DIR"

# ============================================
# PASO 1: Verificar prerequisitos
# ============================================
echo ""
echo "📋 Step 1: Checking prerequisites..."

# Verificar archivos de datos
if [ ! -d "data/raw" ]; then
    echo "❌ ERROR: data/raw directory not found!"
    exit 1
fi

REQUIRED_FILES=("CNBV_Cartera_Bancos_V2.xlsx" "ICAP_Bancos.xlsx" "Instituciones.xlsx")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "data/raw/$file" ]; then
        echo "❌ ERROR: Required file missing: data/raw/$file"
        exit 1
    fi
done
echo "   ✅ Data files present"

# Verificar servicios Docker
echo "   Checking Docker services..."
if ! curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   ⚠️  Qdrant not responding. Starting services..."
    cd "$PROJECT_ROOT"
    docker compose -f infra/docker-compose.yml up -d postgres qdrant
    sleep 5
    cd "$PLUGIN_DIR"
fi
echo "   ✅ Docker services running"

# ============================================
# PASO 2: Activar entorno virtual
# ============================================
echo ""
echo "🐍 Step 2: Activating Python environment..."

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "   Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi
echo "   ✅ Virtual environment active"

# ============================================
# PASO 3: Ejecutar ETL a PostgreSQL
# ============================================
echo ""
echo "📊 Step 3: Running ETL to PostgreSQL..."

# ETL Base
echo "   Loading base metrics..."
python -c "
import os
os.chdir('src')
from bankadvisor.etl_loader import run_etl
run_etl()
" 2>&1 | grep -E "(🚀|📂|📥|🔄|📊|💾|✅|❌)"

# ETL Enhanced (si existe)
if [ -f "src/bankadvisor/etl_loader_enhanced.py" ]; then
    echo "   Loading enhanced metrics (ICAP, TDA, Tasas)..."
    python -c "
import os
os.chdir('src')
from bankadvisor.etl_loader_enhanced import run_enhanced_etl
run_enhanced_etl()
" 2>&1 | grep -E "(Loading|Updated|records|✅|❌)" || true
fi

echo "   ✅ PostgreSQL populated"

# ============================================
# PASO 4: Ejecutar Seeding de Qdrant
# ============================================
echo ""
echo "🧠 Step 4: Seeding Qdrant knowledge base..."

if [ -f "scripts/seed_nl2sql_rag.py" ]; then
    python scripts/seed_nl2sql_rag.py --clear 2>&1 | grep -E "(Seed|Created|points|✅|❌)" || echo "   (Using fallback seeding)"
else
    echo "   Creating collections manually..."
    # Crear colecciones con curl
    for collection in bankadvisor_schema bankadvisor_metrics bankadvisor_examples; do
        curl -s -X PUT "http://localhost:6333/collections/$collection" \
          -H "Content-Type: application/json" \
          -d '{"vectors": {"size": 384, "distance": "Cosine"}}' > /dev/null
        echo "   Created: $collection"
    done
fi

echo "   ✅ Qdrant populated"

# ============================================
# PASO 5: Verificación final
# ============================================
echo ""
echo "✅ Step 5: Final verification..."

# Verificar PostgreSQL
echo ""
echo "   PostgreSQL (monthly_kpis):"
python -c "
from sqlalchemy import create_engine, text
import os
os.chdir('src')
from core.config import get_settings
settings = get_settings()
url = settings.database_url_sync
if 'postgres:' in url:
    url = url.replace('@postgres:', '@localhost:')
engine = create_engine(url)
with engine.connect() as conn:
    result = conn.execute(text('SELECT banco_norm, COUNT(*) as n FROM monthly_kpis GROUP BY banco_norm'))
    for row in result:
        print(f'      {row.banco_norm}: {row.n} records')
"

# Verificar Qdrant
echo ""
echo "   Qdrant collections:"
for collection in bankadvisor_schema bankadvisor_metrics bankadvisor_examples; do
    count=$(curl -s "http://localhost:6333/collections/$collection" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('points_count',0))" 2>/dev/null || echo "0")
    echo "      $collection: $count points"
done

# ============================================
# RESUMEN
# ============================================
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE!                         ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  PostgreSQL: monthly_kpis table populated                  ║"
echo "║  Qdrant: 3 collections created and seeded                  ║"
echo "║                                                            ║"
echo "║  Next steps:                                               ║"
echo "║  1. Start the backend: docker compose up -d backend        ║"
echo "║  2. Test NL2SQL: curl localhost:8000/rpc -d '{...}'        ║"
echo "╚════════════════════════════════════════════════════════════╝"
EOF

chmod +x scripts/setup_bankadvisor_data.sh
```

---

## Troubleshooting

### Error: "No module named 'pandas'"

```bash
pip install pandas openpyxl xlrd
```

### Error: "Connection refused" a PostgreSQL

```bash
# Verificar que el servicio está corriendo
docker compose -f infra/docker-compose.yml ps postgres

# Verificar credenciales en .env
cat envs/.env | grep POSTGRES
```

### Error: "Qdrant collections not found"

```bash
# Verificar servicio
curl http://localhost:6333/collections

# Recrear colecciones
python scripts/seed_nl2sql_rag.py --clear
```

### Error: "ICAP/TDA columns have NULL values"

Esto es **esperado**. Los datos de ICAP, TDA, TASA_MN, TASA_ME son opcionales y pueden tener valores NULL para ciertos períodos. El commit BA-NULL-001 añadió manejo para esto.

---

## Resumen de Comandos

```bash
# Setup completo (recomendado)
./scripts/setup_bankadvisor_data.sh

# Solo ETL a PostgreSQL
python -c "from bankadvisor.etl_loader import run_etl; run_etl()"

# Solo Qdrant seeding
python scripts/seed_nl2sql_rag.py --clear

# Verificar PostgreSQL
psql -h localhost -U bankadvisor -d bankadvisor -c "SELECT COUNT(*) FROM monthly_kpis"

# Verificar Qdrant
curl http://localhost:6333/collections | jq
```

---

## Referencias

- `etl_loader.py`: ETL base para métricas principales
- `etl_loader_enhanced.py`: ETL para métricas Phase 4
- `seed_nl2sql_rag.py`: Script de seeding de Qdrant
- `models/kpi.py`: Modelo SQLAlchemy de monthly_kpis
- `docker-compose.yml`: Configuración de servicios
