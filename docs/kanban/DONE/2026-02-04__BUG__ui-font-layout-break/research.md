


## Research: Markdown Malformado en LLM Streaming

### El Problema
Cuando los LLMs envían markdown token-por-token, sintaxis incompleta como `**negrita` (sin cerrar `**`) causa renderizado roto. Esto es común con:
- Negritas incompletas: `**texto` sin `**` de cierre
- Itálicas incompletas: `*texto` o `_texto`
- Links incompletos: `[texto](https://...`
- Code blocks sin cerrar

### Soluciones de la Comunidad

| Solución | Enfoque |
|----------|---------|
| **remend** (Vercel) | Completa automáticamente markdown incompleto |
| **streamdown** | Reemplazo drop-in de react-markdown para streaming |
| **llm-ui** | Remueve sintaxis rota antes de renderizar |
| **streaming-markdown** | Parser optimista que renderiza inmediatamente |

### Solución Implementada

Se eligió **remend** (paquete de Vercel) porque:
1. Es standalone y liviano
2. Se integra fácilmente con react-markdown existente
3. Maneja casos edge como LaTeX con underscores

Funciona como preprocesador:
- `**texto incompleto` → `**texto incompleto**`
- `*italica` → `*italica*`
- `[link](http://...` → `[link](http://...)`

### Referencias
- https://www.npmjs.com/package/remend
- https://github.com/vercel/streamdown
- https://llm-ui.com/
- https://developer.chrome.com/docs/ai/render-llm-responses
