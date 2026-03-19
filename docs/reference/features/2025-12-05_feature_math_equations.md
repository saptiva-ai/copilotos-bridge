# Renderizado de Ecuaciones Matemáticas

OctaviOS Chat ahora soporta renderizado de ecuaciones matemáticas en formato LaTeX usando KaTeX.

## Sintaxis Soportada

### Ecuaciones en Línea

Para ecuaciones dentro de un párrafo, usa un solo signo de dólar `$`:

```markdown
La fórmula de Einstein es $E = mc^2$, donde $c$ es la velocidad de la luz.
```

**Renderiza como:** La fórmula de Einstein es $E = mc^2$, donde $c$ es la velocidad de la luz.

### Ecuaciones en Bloque

Para ecuaciones en su propia línea, usa doble signo de dólar `$$`:

```markdown
La ecuación de Schrödinger es:

$$
i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)
$$
```

**Renderiza como:**

La ecuación de Schrödinger es:

$$
i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)
$$

### Sintaxis LaTeX Tradicional (Auto-convertida)

El sistema también soporta sintaxis LaTeX tradicional que se convierte automáticamente:

- `\[ ... \]` → `$$ ... $$` (ecuaciones display)
- `\( ... \)` → `$ ... $` (ecuaciones inline)
- `[ ... ]` → `$$ ... $$` (si contiene comandos LaTeX)

**Ejemplo:** Los modelos de IA a veces generan `[ E = mc^2 ]` que se renderiza automáticamente como ecuación display.

## Ejemplos Comunes

### Fracciones

```markdown
$$\frac{a}{b}$$
```

### Raíces

```markdown
$$\sqrt{x^2 + y^2}$$
```

### Sumatorias e Integrales

```markdown
$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$

$$\int_{0}^{\infty} e^{-x} dx = 1$$
```

### Matrices

```markdown
$$
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
$$
```

### Ecuaciones Alineadas

```markdown
$$
\begin{aligned}
f(x) &= (x+1)^2 \\
     &= x^2 + 2x + 1
\end{aligned}
$$
```

## Símbolos Matemáticos Comunes

| LaTeX | Símbolo | Descripción |
|-------|---------|-------------|
| `\alpha`, `\beta`, `\gamma` | α, β, γ | Letras griegas |
| `\infty` | ∞ | Infinito |
| `\partial` | ∂ | Derivada parcial |
| `\nabla` | ∇ | Nabla (gradiente) |
| `\int` | ∫ | Integral |
| `\sum` | Σ | Sumatoria |
| `\prod` | Π | Productoria |
| `\le`, `\ge` | ≤, ≥ | Menor/mayor o igual |
| `\times` | × | Producto |
| `\cdot` | · | Punto multiplicación |
| `\pm` | ± | Más/menos |

## Implementación Técnica

### Dependencias

- **remark-math**: Plugin de remark para parsear sintaxis LaTeX en Markdown
- **rehype-katex**: Plugin de rehype para renderizar ecuaciones con KaTeX
- **katex**: Motor de renderizado matemático (alternativa ligera a MathJax)

### Ubicación del Código

El renderizado está implementado en:
- `/apps/web/src/components/chat/MarkdownMessage.tsx` - Componente de renderizado
- Plugins configurados: `remarkMath` y `rehypeKatex`
- Estilos: `katex/dist/katex.min.css` importado globalmente
- **Preprocesador LaTeX**: Función `normalizeLatexSyntax()` que convierte sintaxis LaTeX tradicional (`\[`, `\(`, `[`) a sintaxis Markdown (`$`, `$$`) antes de parsear

### Performance

- KaTeX es más rápido que MathJax (renderizado síncrono)
- Las ecuaciones se renderizan solo cuando el streaming completa (via `highlightCode` flag)
- Compatible con modo oscuro (estilos personalizados en prose-invert)

## Limitaciones

1. **Sintaxis LaTeX completa**: No todas las macros de LaTeX están soportadas, solo el subset de KaTeX
2. **No hay editor visual**: Los usuarios deben conocer sintaxis LaTeX
3. **Errores de sintaxis**: Si hay un error en la sintaxis LaTeX, KaTeX mostrará un mensaje de error en rojo
4. **Auto-conversión `[ ... ]`**: El preprocesador solo convierte `[ ... ]` a ecuación si detecta comandos LaTeX (backslash, subíndices, superíndices). Esto previene conflictos con arrays/listas de Markdown, pero puede fallar en casos edge como `[a]` (no se convierte porque no tiene comandos LaTeX)

## Referencias

- [KaTeX Supported Functions](https://katex.org/docs/supported.html)
- [LaTeX Math Wiki](https://en.wikibooks.org/wiki/LaTeX/Mathematics)
- [Markdown Math Syntax](https://github.com/remarkjs/remark-math)
