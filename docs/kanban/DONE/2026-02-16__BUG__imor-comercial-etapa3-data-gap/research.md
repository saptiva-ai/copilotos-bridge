# Research: IMOR Comercial — Hallazgo definitivo desde TWB de Tableau

## Objetivo
Identificar por que nuestros valores IMOR no coinciden con Tableau y determinar la formula correcta.

## Resultado: RESUELTO

La formula exacta se extrajo del archivo TWB de Tableau (`Invex_Tablero_V3.twb`, lineas 1497-1511).
Los codigos bancarios correctos se obtuvieron de `Instituciones.xlsx`.
**10/10 bancos coinciden exactamente con Tableau** usando formula + codigos corregidos.

## Formula IMORA (del TWB XML)

```xml
<!-- Invex_Tablero_V3.twb lineas 1497-1511 -->
<column caption='Comercial Etapa 1 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 1]+[Entidades Financieras Etapa 1]' />
</column>
<column caption='Comercial Etapa 2 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 2]+[Entidades Financieras Etapa 2]' />
</column>
<column caption='Comercial Etapa 3 SG'>
  <calculation formula='[Actividad Empresarial o Comercial Etapa 3]+[Entidades Financieras Etapa 3]' />
</column>
<column caption='IMORA'>
  <calculation formula='([Comercial Etapa 3 SG]+[CASTIGOS ACMULUADOS COMERCIAL])/([Comercial Etapa 1 SG]+[Comercial Etapa 2 SG]+[Comercial Etapa 3 SG])' />
</column>
```

### Formula en pseudocodigo

```
E1_SG = Act.Empresarial E1 + Ent.Financieras E1
E2_SG = Act.Empresarial E2 + Ent.Financieras E2
E3_SG = Act.Empresarial E3 + Ent.Financieras E3

IMORA = (E3_SG + CASTIGOS_ACUMULADOS_COMERCIAL) / (E1_SG + E2_SG + E3_SG)
```

### Diferencias criticas con nuestra formula anterior

| Aspecto | Formula anterior | Formula correcta |
|---------|-----------------|-----------------|
| Etapas | E1/E2/E3 totales ("Creditos Comerciales") | Solo AE + EF (Sin Gobierno) |
| VR | Incluido en denominador | NO incluido |
| Castigos | No incluidos | Sumados al numerador |
| Denominador | E1 + E2 + E3 + VR | E1_SG + E2_SG + E3_SG |

## Codigos bancarios (de Instituciones.xlsx)

El archivo `Instituciones.xlsx` del directorio del Tableau extract revela que 7 de 10
codigos que usabamos estaban cruzados:

| Banco | Codigo correcto | Codigo incorrecto que usabamos |
|-------|:--------------:|:------------------------------:|
| BANSÍ | 40060 | 40110 (= J.P. MORGAN) |
| MULTIVA | 40132 | 40112 (= MONEX) |
| BANCO BASE | 40145 | 40132 (= MULTIVA) |
| BANCREA | 40152 | 40113 (= VE POR MÁS) |
| SABADELL | 40156 | 40044 (= SCOTIABANK) |
| VE POR MÁS | 40113 | 40126 (= CREDIT SUISSE) |
| MONEX | 40112 | 40036 (= INBURSA) |

Bancos con codigo correcto: INVEX (40059), AFIRME (40062), BANCA MIFEL (40042).

## Verificacion numerica: 10/10 match

Usando formula SG + castigos + codigos correctos, promedio de ene2024 y ene2025:

| Banco | Tableau | Calculado | Delta |
|-------|:-------:|:---------:|------:|
| MULTIVA | 6.24% | 6.24% | 0.00pp |
| AFIRME | 5.43% | 5.43% | 0.00pp |
| BANSÍ | 5.18% | 5.18% | 0.00pp |
| VE POR MÁS | 3.22% | 3.22% | 0.00pp |
| BANCO BASE | 2.65% | 2.65% | 0.00pp |
| SABADELL | 2.63% | 2.63% | 0.00pp |
| INVEX | 2.35% | 2.35% | 0.00pp |
| MONEX | 1.56% | 1.56% | 0.00pp |
| BANCA MIFEL | 1.26% | 1.26% | 0.00pp |
| BANCREA | 0.69% | 0.69% | 0.00pp |

## Por que la investigacion anterior fue incompleta

### Hipotesis descartada: microdata CNBV
Los scripts R (`CorporateLoan_BM.R`) SI procesan microdata, pero para un data source DIFERENTE
en Tableau (creditos corporativos con IMOR pre-calculado a nivel de credito individual). El
worksheet "IMORA" que nos interesa usa los xlsx de balance + castigos con la formula SG.

### Por que la formula antigua no funcionaba
1. **"Creditos Comerciales Etapa X"** incluye tres sub-categorias: Act.Empresarial + Ent.Financieras + Ent.Gubernamentales. El TWB excluye Gubernamentales (formula "SG" = Sin Gobierno).
2. **VR (Vigencia Reclasificada)** estaba en nuestro denominador pero NO en el de Tableau.
3. **Sin castigos**: No sumabamos CASTIGOS_ACUMULADOS_COMERCIAL al numerador.

### Por que BANSI daba 0% antes
Con codigos CORRECTOS (40060), BANSÍ tiene E3_SG = 0 en ene2024 y ene2025 (castiga 100% de
cartera vencida en balance). Pero CASTIGOS_ACUMULADOS_COMERCIAL = 2,066 MDP (ene2024) y
1,988 MDP (ene2025). La suma E3_SG + Castigos da el 5.18% correcto.

Con el codigo INCORRECTO (40110 = J.P. MORGAN), obteniamos datos de otro banco.

## Fuentes de datos (actualizadas)

| # | Fuente | Uso en IMORA | Estado |
|---|--------|:------------:|--------|
| 1 | CNBV_Cartera_Bancos_V2.xlsx | E1_SG, E2_SG, E3_SG (sub-cols AE + EF) | Disponible |
| 2 | Castigos Comerciales.xlsx | CASTIGOS_ACUMULADOS_COMERCIAL | Disponible |
| 3 | Instituciones.xlsx | Mapeo codigo → nombre banco | Disponible |
| 4 | Invex_Tablero_V3.twb | Formula IMORA (evidencia) | Analizado |

### Fuentes descartadas
| # | Fuente | Razon de descarte |
|---|--------|-------------------|
| 5 | 040_R04A_419.csv | Data source separado en Tableau (worksheet "Castigos"), no usado en IMORA |
| 6 | CASTIGOS.xlsx | Resumen sin periodo, sin utilidad mensual |
| 7 | MD_Emp_PETOTAL...csv | Para otro dashboard (microdata), no para IMORA |
| 8 | Catera Analitica Benchmark v2.xlsx | Mismos datos que #1, formato diferente |
| 9 | CorporateLoan_CNBVDB.csv | Redundante con #1 |
| 10 | TDA.xlsx / TE_Invex_Sistema.xlsx | Sin datos IMOR |

## Columnas del xlsx necesarias para formula SG

Del `CNBV_Cartera_Bancos_V2.xlsx`, las sub-columnas requeridas son:

```
# Actividad Empresarial o Comercial
"Actividad Empresarial o Comercial Etapa 1"  → AE_E1
"Actividad Empresarial o Comercial Etapa 2"  → AE_E2
"Actividad Empresarial o Comercial Etapa 3"  → AE_E3

# Entidades Financieras
"Entidades Financieras Etapa 1"  → EF_E1
"Entidades Financieras Etapa 2"  → EF_E2
"Entidades Financieras Etapa 3"  → EF_E3

# Formula
E1_SG = AE_E1 + EF_E1
E2_SG = AE_E2 + EF_E2
E3_SG = AE_E3 + EF_E3
```

Del `Castigos Comerciales.xlsx`:
```
"CASTIGOS ACMULUADOS COMERCIAL"  → castigos (nota: typo "ACMULUADOS" en el original)
```

## Worksheets IMORA en el TWB

El TWB contiene 4 worksheets que usan la formula IMORA:

| Worksheet | Linea TWB | Subtitulo |
|-----------|-----------|-----------|
| IMORA | 7680 | Cartera Vencida Comercial / Cartera Comercial |
| IMORA (GC) | 7801 | Cartera Vencida Comercial / Cartera Comercial |
| IMORA (dat) | 9089 | Cartera Vencida Comercial + Castigos / Cartera Comercial |
| IMORA (dat) v2 | 9236 | Cartera Vencida Comercial +Castigos/ Cartera Comercial+Castigos |

El dashboard del screenshot del usuario corresponde a "IMORA (dat)" (linea 9089).

## Otras formulas encontradas en el TWB (referencia futura)

- **ICOR** (linea 1513): `Reservas Etapa todas / Calculation_4114741983628718098`
- **Quebrantos CC** (linea 1378): `LIB_CASTIGOS_COMERC + QUITAS_COMER`
- **Castigos Acumulados** (linea 1362): `RUNNING_SUM(SUM([LIB_CASTIGOS_COMERC]))`
