export type HelpPresetIcon = "bar" | "bar-h" | "trend" | "currency" | "globe";

export interface HelpPreset {
  id: string;
  label: string;
  getPrompt: (targetPeriod: string) => string;
  icon: HelpPresetIcon;
}

export interface HelpPresetSection {
  id: string;
  title: string;
  presets: HelpPreset[];
}

// ── Period formatting utilities ───────────────────────────────────────

export const MESES_LARGO = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

/** "2025-01" → "enero 2025" (lowercase, for mid-sentence usage) */
export function formatPeriodLong(period: string): string {
  if (!period) return "";
  const [y, m] = period.split("-");
  return `${MESES_LARGO[parseInt(m, 10) - 1].toLowerCase()} ${y}`;
}

/** "2025-01" → "2025" */
export function formatPeriodYear(period: string): string {
  if (!period) return "";
  return period.split("-")[0];
}

/** "2025-01" → "01/2025" */
export function formatPeriodShort(period: string): string {
  if (!period) return "";
  const [y, m] = period.split("-");
  return `${m}/${y}`;
}

/** Subtract N years: "2025-01", 1 → "2024-01" */
export function subtractYears(period: string, years: number): string {
  if (!period) return "";
  const [y, m] = period.split("-");
  return `${parseInt(y, 10) - years}-${m}`;
}

/** Number of collapsed sections shown by default in the preset grid. */
export const VISIBLE_SECTIONS_DEFAULT = 6;

// ── Copy/paste helpers for multiline prompts (reference only) ─────────

export const HELP_PRESET_PROMPT_EXAMPLES = {
  variacionConTabla: (p: string) =>
    `Toma como periodo inicial ${formatPeriodLong(subtractYears(p, 1))} y como periodo actual ${formatPeriodLong(p)}.
Compara la cartera comercial entre los bancos:
MONEX, INVEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO.

Presenta:
1) valor del periodo inicial
2) valor del periodo actual
3) porcentaje de variación

Fórmula de variación: (periodo_actual / periodo_inicial - 1) * 100.
Genera una gráfica de barras y resalta INVEX en rojo.
Agrega una tabla final con columnas:
Banco | Valor ${formatPeriodYear(subtractYears(p, 1))} | Valor ${formatPeriodYear(p)} | % Variación`,

  invexVsPromedio: (_p: string) =>
    `Crea una gráfica de línea comparando INVEX vs promedio del grupo:
MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO.

Periodo: enero 2021 hasta el dato más reciente disponible.
Incluye al final un resumen breve con:
- nivel actual de INVEX
- nivel actual del promedio
- brecha porcentual actual`,

  rankingPeriodos: (p: string) =>
    `Construye un ranking de bancos por IMOR Comercial para ${formatPeriodLong(subtractYears(p, 1))} y ${formatPeriodLong(p)}.
Muestra el top 3 y el bottom 3 de cada periodo.
Marca la posición de INVEX en ambos periodos.
Incluye una tabla comparativa y una gráfica de barras horizontal.`,
};

export const HELP_PRESET_OBJECT_EXAMPLES: HelpPreset[] = [
  {
    id: "ejemplo-variacion",
    label: "Ejemplo Variación",
    icon: "bar-h",
    getPrompt: HELP_PRESET_PROMPT_EXAMPLES.variacionConTabla,
  },
  {
    id: "ejemplo-invex-promedio",
    label: "Ejemplo INVEX vs Promedio",
    icon: "trend",
    getPrompt: HELP_PRESET_PROMPT_EXAMPLES.invexVsPromedio,
  },
  {
    id: "ejemplo-ranking",
    label: "Ejemplo Ranking",
    icon: "bar-h",
    getPrompt: HELP_PRESET_PROMPT_EXAMPLES.rankingPeriodos,
  },
];

export const HELP_GUIDE_DOS: string[] = [
  "Pedir gráficas comparativas entre bancos.",
  "Comparar indicadores como IMOR, ICOR e ICAP.",
  "Analizar variaciones entre periodos.",
  "Solicitar tablas de tasas y datos financieros.",
  "Hacer preguntas sobre los datos presentados.",
  "Pedir cambios de colores, formatos o periodos.",
];

export const HELP_GUIDE_DONTS: string[] = [
  "Modificar datos reales en las bases de datos.",
  "Acceder a información confidencial de clientes.",
  "Ejecutar transacciones financieras.",
  "Garantizar precisión al 100%; siempre verifica.",
  "Reemplazar el juicio profesional de un analista.",
  "Acceder a datos en tiempo real del mercado.",
];

/**
 * Returns all preset IDs across all sections.
 * Used by ReportGenerator to default-select everything.
 */
export function getAllPresetIds(): string[] {
  return HELP_PRESET_SECTIONS.flatMap((s) => s.presets.map((p) => p.id));
}

// ── Preset sections ───────────────────────────────────────────────────

const BANCOS_FULL =
  "MONEX, INVEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO";
const BANCOS_SIN_INVEX =
  "MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO";
const BANCOS_BANCA =
  "MONEX, INVEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO";
const BANCOS_BANCA_SIN_INVEX =
  "MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO Y BAJIO";

/** Variación template: compares initial vs final period */
function variacionPrompt(
  metric: string,
  tableLabel: string,
): (p: string) => string {
  return (p) => {
    const prev = subtractYears(p, 1);
    return `Toma como periodo inicial ${formatPeriodLong(prev)} y como periodo actual ${formatPeriodLong(p)}.
Compara ${metric} entre el periodo inicial y el periodo final entre los bancos:
${BANCOS_FULL}
Presenta el dato del periodo inicial, el dato del periodo final y la variación entre el periodo inicial y periodo final.
Donde la variación es = (periodo actual / periodo inicial -1)
Haz una gráfica de barras donde se vea la variación graficada y marca a invex de color rojo. Así como una tabla con:
Banco | ${tableLabel} ${formatPeriodYear(prev)} | ${tableLabel} ${formatPeriodYear(p)} | % Variación`;
  };
}

/** Trend template: fixed start date to latest available */
function trendPrompt(metric: string, startDate: string): (p: string) => string {
  return (_p) =>
    `Crea una gráfica donde se compare ${metric} de INVEX contra el promedio de los bancos:
${BANCOS_SIN_INVEX}.
De ${startDate} hasta el dato más reciente que tengas.`;
}

/** Trend template with BANCA MIFEL variant */
function trendBancaPrompt(
  metric: string,
  startDate: string,
): (p: string) => string {
  return (_p) =>
    `Crea una gráfica donde se compare ${metric} de INVEX contra el promedio de los bancos:
${BANCOS_BANCA_SIN_INVEX}.
De ${startDate} hasta el dato más reciente que tengas.`;
}

export const HELP_PRESET_SECTIONS: HelpPresetSection[] = [
  {
    id: "cartera-total",
    title: "Cartera Total",
    presets: [
      {
        id: "cartera-total-variacion",
        label: "Variación Cartera Total",
        icon: "bar-h",
        getPrompt: variacionPrompt("la cartera total", "Cartera Total"),
      },
      {
        id: "cartera-total-invex-promedio",
        label: "Invex vs Promedio (Total)",
        icon: "trend",
        getPrompt: trendPrompt("la cartera total", "enero 2021"),
      },
    ],
  },
  {
    id: "cartera-comercial",
    title: "Cartera Comercial",
    presets: [
      {
        id: "cartera-comercial-variacion",
        label: "Variación Cartera Comercial",
        icon: "bar-h",
        getPrompt: variacionPrompt("la cartera comercial", "Cartera Comercial"),
      },
      {
        id: "cartera-comercial-invex-promedio",
        label: "Invex vs Promedio (Comercial)",
        icon: "trend",
        getPrompt: trendPrompt("la cartera comercial", "enero 2021"),
      },
    ],
  },
  {
    id: "cartera-comercial-sin-gob",
    title: "Cartera Comercial Sin Gobierno",
    presets: [
      {
        id: "cartera-comercial-variacion-sin-gob",
        label: "Variación sin Gob.",
        icon: "bar-h",
        getPrompt: variacionPrompt(
          "la cartera comercial sin considerar la cartera de entidades gubernamentales",
          "Cartera C Sin Gob",
        ),
      },
      {
        id: "cartera-comercial-invex-promedio-sin-gob",
        label: "Invex vs Promedio sin Gob.",
        icon: "trend",
        getPrompt: trendPrompt(
          "la cartera comercial sin gobierno",
          "enero 2021",
        ),
      },
    ],
  },
  {
    id: "perdida-esperada-sg",
    title: "Pérdida Esperada SG",
    presets: [
      {
        id: "pe-sg-variacion",
        label: "Variación Pérdida Esperada Total SG",
        icon: "bar-h",
        getPrompt: variacionPrompt(
          "la pérdida esperada total sin gobierno",
          "PE SG",
        ),
      },
      {
        id: "pe-sg-invex-promedio",
        label: "Invex vs Promedio (P.E. SG.)",
        icon: "trend",
        getPrompt: trendPrompt(
          "la pérdida esperada total sin entidades gubernamentales",
          "enero 2021",
        ),
      },
    ],
  },
  {
    id: "reservas",
    title: "Reservas",
    presets: [
      {
        id: "reservas-promedio-periodos",
        label: "Reservas Totales Promedio",
        icon: "bar-h",
        getPrompt: (p) => {
          const prev = subtractYears(p, 2);
          return `Toma como periodo inicial ${formatPeriodLong(prev)} y como periodo actual ${formatPeriodLong(p)}.
Presenta una gráfica de barras donde se vea el promedio de PE Total SG para los meses seleccionados entre los bancos: ${BANCOS_FULL}. Marca a INVEX de color rojo.
Así como una tabla con:
Banco | PROM PE Total SG`;
        },
      },
      {
        id: "reservas-sin-gob",
        label: "Reservas sin Gob.",
        icon: "bar-h",
        getPrompt: (p) => {
          const prev = subtractYears(p, 1);
          return `Toma como periodo inicial ${formatPeriodLong(prev)} y como periodo actual ${formatPeriodLong(p)}.
Compara las reservas sin reservas de entidades gubernamentales entre el periodo inicial y el periodo final entre los bancos: ${BANCOS_FULL}.
Presenta el dato del periodo inicial, el dato del periodo final y la variacion entre el periodo inicial.
Donde la variacion es = (periodo actual / periodo inicial -1)
Haz una gráfica de barras donde se vea la variación graficada y marca a INVEX de color rojo. Así como una tabla con:
Banco | Reservas SG ${formatPeriodYear(prev)} | Reservas SG ${formatPeriodYear(p)} | % Variación.`;
        },
      },
    ],
  },
  {
    id: "imor",
    title: "IMOR",
    presets: [
      {
        id: "imor-promedio",
        label: "Promedio IMOR Comercial",
        icon: "bar-h",
        getPrompt: (p) => {
          const prev = subtractYears(p, 1);
          return `Toma como periodo inicial ${formatPeriodLong(prev)} y como periodo actual ${formatPeriodLong(p)}.
Presenta una gráfica de barras donde se vea el promedio de IMOR Comercial para los meses seleccionados entre los bancos: ${BANCOS_FULL}. Marca a INVEX de color rojo.
Así como una tabla con:
Banco | PROM IMOR Comercial`;
        },
      },
      {
        id: "imor-invex-promedio",
        label: "Invex vs Promedio (IMOR)",
        icon: "trend",
        getPrompt: trendPrompt("el IMOR Comercial", "enero 2024"),
      },
    ],
  },
  {
    id: "cartera-vencida-comercial",
    title: "Cartera Vencida Comercial",
    presets: [
      {
        id: "cartera-vencida-comercial-ranking",
        label: "Ranking CVC/CC",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la razón de cartera vencida comercial entre la cartera comercial para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | CVC/CC ${formatPeriodShort(p)}`,
      },
      {
        id: "cartera-vencida-comercial-invex-promedio",
        label: "Invex vs Prom. (CVC/CC)",
        icon: "trend",
        getPrompt: trendBancaPrompt(
          "razón de cartera vencida comercial entre la cartera comercial",
          "octubre 2022",
        ),
      },
    ],
  },
  {
    id: "icor",
    title: "ICOR",
    presets: [
      {
        id: "icor-ranking",
        label: "Ranking ICOR",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra el ICOR (Reservas / Cartera Vencida) para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | ICOR ${formatPeriodShort(p)}`,
      },
      {
        id: "icor-invex-promedio",
        label: "Invex vs Prom. (ICOR)",
        icon: "trend",
        getPrompt: trendBancaPrompt("el ICOR", "octubre 2022"),
      },
    ],
  },
  {
    id: "icap",
    title: "ICAP",
    presets: [
      {
        id: "icap-ranking",
        label: "Ranking ICAP",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra el ICAP para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | ICAP ${formatPeriodShort(p)}`,
      },
      {
        id: "icap-invex-promedio",
        label: "Invex vs Promedio (ICAP)",
        icon: "trend",
        getPrompt: (_p) =>
          `Crea una gráfica de enero 2017 hasta el dato más reciente que tengas donde se compare el ICAP de INVEX contra el promedio de los bancos:
${BANCOS_BANCA_SIN_INVEX}.`,
      },
    ],
  },
  {
    id: "tasas-mn",
    title: "Tasas MN",
    presets: [
      {
        id: "tasa-mn-ranking",
        label: "Ranking Tasa MN",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la tasa promedio en Moneda Nacional de ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | Tasa MN`,
      },
      {
        id: "tasa-mn-invex-promedio",
        label: "Invex vs Prom. (Tasa MN)",
        icon: "trend",
        getPrompt: trendBancaPrompt(
          "la tasa promedio en Moneda Nacional",
          "enero 2017",
        ),
      },
    ],
  },
  {
    id: "tasas-me",
    title: "Tasas ME",
    presets: [
      {
        id: "tasa-me-ranking",
        label: "Ranking Tasa ME",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la tasa promedio en Moneda Extranjera de ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | Tasa ME`,
      },
      {
        id: "tasa-me-invex-promedio",
        label: "Invex vs Prom. (Tasa ME)",
        icon: "trend",
        getPrompt: trendBancaPrompt(
          "la tasa promedio en Moneda Extranjera",
          "enero 2017",
        ),
      },
    ],
  },
  {
    id: "quebrantos",
    title: "Quebrantos",
    presets: [
      {
        id: "quebrantos-promedio",
        label: "Ranking Quebrantos CC",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra los quebrantos comerciales de ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | Quebrantos CC (MDP)`,
      },
      {
        id: "quebrantos-anio",
        label: "Invex vs Total (Quebrantos CC T1)",
        icon: "bar",
        getPrompt: (_p) =>
          `Crea una gráfica de barras VERTICALES que compare los quebrantos comerciales de INVEX contra el total del grupo:
MONEX, BANCREA, SABADELL, MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS, BANCO BASE, CIBANCO, BANREGIO y BAJIO.
Importante: compara únicamente el primer trimestre (T1) de cada año disponible desde 2023 hasta el más reciente.
Agregación: para cada (año, T1) calcula el TOTAL del trimestre (SUM de los 3 meses) para INVEX y el TOTAL del sistema (SUM de los totales trimestrales de TODOS los bancos incluyendo INVEX).
Visual: por cada año muestra dos barras: TOTAL (gris) e INVEX (rojo), con etiquetas de valor en MDP y el eje/leyenda indicando 'T1'.
Orden: años ascendente.`,
      },
    ],
  },
  {
    id: "etapas-de-cartera",
    title: "Etapas de Cartera",
    presets: [
      {
        id: "etapas-ranking",
        label: "Distribución Etapas CT",
        icon: "bar",
        getPrompt: (p) =>
          `Muestra la distribución porcentual de etapas de cartera total (Etapa 1, Etapa 2, Etapa 3) para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras apiladas al 100% y marca a INVEX de color rojo.
Incluye una tabla con: Banco | % Etapa 1 | % Etapa 2 | % Etapa 3`,
      },
      {
        id: "etapas-invex-promedio",
        label: "Invex vs Promedio (Etapa 3 %)",
        icon: "trend",
        getPrompt: trendBancaPrompt(
          "el porcentaje de Etapa 3 de cartera total",
          "enero 2021",
        ),
      },
    ],
  },
  {
    id: "tda",
    title: "TDA",
    presets: [
      {
        id: "tda-ranking",
        label: "Ranking TDA Cartera Total",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la TDA de cartera total para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | TDA Cartera Total`,
      },
      {
        id: "tda-invex-promedio",
        label: "Invex vs Promedio (TDA)",
        icon: "trend",
        getPrompt: trendBancaPrompt("la TDA de cartera total", "enero 2021"),
      },
    ],
  },
  {
    id: "tasa-interes-efectiva",
    title: "Tasa Interés Efectiva",
    presets: [
      {
        id: "tasa-ie-ranking",
        label: "Ranking Tasa Int. Efectiva",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la tasa de interés efectiva para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | Tasa Int. Efectiva`,
      },
      {
        id: "tasa-ie-invex-promedio",
        label: "Invex vs Promedio (Tasa IE)",
        icon: "trend",
        getPrompt: trendBancaPrompt(
          "la tasa de interés efectiva",
          "enero 2021",
        ),
      },
    ],
  },
  {
    id: "pe-total",
    title: "Pérdida Esperada Total",
    presets: [
      {
        id: "pe-total-ranking",
        label: "Ranking PE Total",
        icon: "bar-h",
        getPrompt: (p) =>
          `Muestra la pérdida esperada total (incluyendo gobierno) para ${formatPeriodLong(p)} para los bancos:
${BANCOS_BANCA}.
Haz una gráfica de barras horizontales ordenadas de mayor a menor y marca a INVEX de color rojo.
Incluye una tabla con: Banco | PE Total`,
      },
      {
        id: "pe-total-invex-promedio",
        label: "Invex vs Promedio (PE Total)",
        icon: "trend",
        getPrompt: trendBancaPrompt("la pérdida esperada total", "enero 2021"),
      },
    ],
  },
];
