# Research: CVC/CC — Cartera Vencida Comercial sin Castigos

## Objetivo

Identificar la formula exacta que Tableau usa en la vista "CATERA VENCIDA" y determinar
por que difiere de nuestro `hip_imor_comercial`.

## Resultado: RESUELTO

La vista "CATERA VENCIDA" usa `Cartera Vencida_` = `E3_SG / (E1+E2+E3)` **sin castigos**.
Nuestro `hip_imor_comercial` usa IMORA = `(E3_SG + Castigos) / (E1+E2+E3)` **con castigos**.
Son dos metricas distintas en Tableau que requieren dos columnas distintas en la BD.

## Analisis del TWB

### Campo "Cartera Vencida_" (TWB linea 1447-1448)

```xml
<column caption='Cartera Vencida_' datatype='real'
        name='[Calculation_4114741983628898323]' role='measure' type='quantitative'>
  <calculation class='tableau'
    formula='[Comercial Etapa 3 (copia)_2518356647910252548]
      /([Comercial Etapa 1 (copia)_2518356647910252549]
       +[Comercial Etapa 2 (copia)_2518356647910252550]
       +[Comercial Etapa 3 (copia)_2518356647910252548])' />
</column>
```

Formula: `E3_SG / (E1_SG + E2_SG + E3_SG)` — sin castigos.

### Campo "IMORA" (TWB linea 1510-1511)

```xml
<column caption='IMORA' datatype='real'
        name='[IMOR (copia)_2110921644171517952]' role='measure' type='quantitative'>
  <calculation class='tableau'
    formula='([Comercial Etapa 3 (copia)_2518356647910252548]
       +[CASTIGOS ACMULUADOS COMERCIAL])
      /([Comercial Etapa 1 (copia)_2518356647910252549]
       +[Comercial Etapa 2 (copia)_2518356647910252550]
       +[Comercial Etapa 3 (copia)_2518356647910252548])' />
</column>
```

Formula: `(E3_SG + Castigos) / (E1_SG + E2_SG + E3_SG)` — con castigos.

### Worksheets que usan cada formula

| Worksheet | Campo | Castigos | TWB linea |
|-----------|-------|:--------:|-----------|
| Cart_Venc ("CATERA VENCIDA") | `Cartera Vencida_` | NO | 7674 |
| Cart_Venc_GC | `Cartera Vencida_` | NO | 7801 |
| IMORA | `IMORA` | SI | 7680 |
| IMORA (dat) | `IMORA` | SI | 9089 |
| IMORA (dat) v2 | variante | SI | 9236 |

El screenshot del usuario corresponde a **Cart_Venc** (Cartera Vencida sin castigos).

## Campos SG (referencia)

Los campos "Comercial Etapa X (copia)" son las versiones SG (Sin Gobierno):

```xml
<!-- TWB lineas 1497-1504 -->
<column caption='Comercial Etapa 1 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 1]
                        +[Entidades Financieras Etapa 1]' />
</column>
<column caption='Comercial Etapa 2 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 2]
                        +[Entidades Financieras Etapa 2]' />
</column>
<column caption='Comercial Etapa 3 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 3]
                        +[Entidades Financieras Etapa 3]' />
</column>
```

SG = Act.Empresarial + Ent.Financieras (excluye Ent.Gubernamentales).

## Verificacion numerica: CVC/CC vs IMORA vs Tableau (01/2025)

Usando datos de CNBV_Cartera_Bancos_V2.xlsx + Castigos Comerciales.xlsx:

| Banco | CVC/CC | IMORA | Tableau | CVC match | Castigos (MDP) |
|-------|:------:|:-----:|:-------:|:---------:|:--------------:|
| BANSI | 5.67% | 5.67% | 5.67% | OK | 0 |
| AFIRME | 4.43% | 4.43% | 4.43% | OK | 2.56 |
| MULTIVA | 4.33% | 4.33% | 4.33% | OK | 0 |
| VE POR MAS | 3.51% | 3.52% | 3.51% | OK | 3.55 |
| BANCO BASE | 2.87% | 2.87% | 2.87% | OK | 0 |
| SABADELL | 2.58% | 2.58% | 2.58% | OK | 0 |
| INVEX | 2.36% | 2.36% | 2.36% | OK | 0 |
| MONEX | 1.58% | 1.58% | 1.58% | OK | 0.42 |
| BANCA MIFEL | 1.23% | **1.25%** | 1.23% | OK | **12.34** |
| BANCREA | 0.80% | 0.80% | 0.80% | OK | 0 |
| **Promedio** | **2.94%** | **2.95%** | **2.94%** | | |

**10/10 CVC/CC match Tableau. IMORA difiere para MIFEL (+0.02pp) y VE POR MAS (+0.01pp).**

## Bancos donde CVC/CC != IMORA

Para la mayoria de bancos castigos=0, asi que CVC/CC = IMORA. Las diferencias aparecen
solo donde castigos > 0:

| Banco | Castigos | CVC/CC | IMORA | Delta |
|-------|:--------:|:------:|:-----:|------:|
| BANCA MIFEL | 12.34 | 1.23% | 1.25% | 0.02pp |
| VE POR MAS | 3.55 | 3.51% | 3.52% | 0.01pp |
| AFIRME | 2.56 | 4.43% | 4.43% | <0.01pp |
| MONEX | 0.42 | 1.58% | 1.58% | <0.01pp |
| BANCREA (2024) | 18.29 | - | - | visible en 202401 |

En periodos historicos donde los castigos son mayores, la diferencia sera mas pronunciada.

## Impacto en el loader existente

El loader `loaders_imor_comercial.py` ya computa `e1_sg`, `e2_sg`, `e3_sg` y `castigos`
por separado. La formula CVC/CC es simplemente `e3_sg / denom` (sin sumar castigos),
mientras que IMORA es `(e3_sg + castigos) / denom`.

El cambio en el loader es minimo: agregar una segunda columna al DataFrame de salida.

```python
# Linea 159-162 del loader actual:
agg["imor_comercial"] = agg.apply(
    lambda r: compute_imora_sg(r["e1_sg"], r["e2_sg"], r["e3_sg"], r["castigos"]),
    axis=1,
)

# Agregar:
agg["cvc_cc"] = agg.apply(
    lambda r: compute_cvc_cc(r["e1_sg"], r["e2_sg"], r["e3_sg"]),
    axis=1,
)
```

## Prompt de onboarding actual vs esperado

### Actual (help-onboarding-content.ts:282)

Pide **variacion entre dos periodos** (grafica de barras con % cambio):
```
Compara la razon de cartera vencida comercial entre la cartera comercial
para el periodo inicial y el periodo final...
Donde la variacion es = (periodo actual / periodo inicial -1)
tabla con: Banco | CVC/CC 2024 | CVC/CC 2025 | % Variacion
```

### Esperado (match con screenshot Tableau)

Pide **ranking de valores absolutos** para un solo periodo:
```
Muestra la razon de cartera vencida comercial entre la cartera comercial
para enero 2025 para los bancos: [lista].
Haz una grafica de barras horizontales ordenadas de mayor a menor.
Marca a INVEX de color rojo. Incluye el promedio.
tabla con: Banco | CVC/CC 01/2025
```

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `migrations/059_add_cvc_cc.sql` | ALTER TABLE + UPDATE MVs |
| `models/kpi.py` | Agregar `cvc_cc = Column(Float, nullable=True)` |
| `etl/core/loaders/loaders_imor_comercial.py` | Agregar compute_cvc_cc() + columna de salida |
| `services/template_sql_generator.py` | Registrar `hip_cvc_cc` en METRIC_TABLE_ROUTING |
| `tools/comparison_tools.py` | Agregar `hip_cvc_cc` al enum |
| `domain/services/metric_normalizer.py` | Registrar cvc_cc como ratio metric |
| `handlers/evolucion_banco_handler.py` | Mapear "cartera vencida comercial" -> hip_cvc_cc |
| `apps/web/.../help-onboarding-content.ts` | Reescribir prompt CVC/CC |
| `tests/unit/domain/test_cvc_cc_computation.py` | Tests de formula + Tableau match |

## Data sources (ya disponibles)

| Fuente | Archivo | Columnas usadas |
|--------|---------|-----------------|
| Cartera por etapa | `CNBV_Cartera_Bancos_V2.xlsx` | AE E1-E3 + EF E1-E3 |
| Instituciones | `Instituciones.xlsx` | Mapeo codigo -> nombre |
| Castigos | `Castigos Comerciales.xlsx` | Solo para IMORA, NO para CVC/CC |
