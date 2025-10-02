# CompactChatComposer

Compositor de chat compacto con diseño tipo ChatGPT, alineación perfecta y animaciones suaves.

## 🎯 Características

### Diseño Visual
- **Layout Grid**: Sistema de 3 columnas (`auto 1fr auto`) para alineación perfecta
- **Sin separadores**: Estética limpia sin líneas visibles entre elementos
- **Fondo translúcido**: `bg-neutral-800/40 backdrop-blur-sm` con sombra suave
- **Bordes redondeados**: `rounded-2xl` para apariencia moderna

### Auto-crecimiento
- **Solo hacia abajo**: El textarea crece desde `min-h-11` (44px) hasta `max-h-48` (192px)
- **Scroll interno**: Al superar 192px, aparece scroll vertical dentro del textarea
- **Hero fijo**: El crecimiento no desplaza el hero hacia arriba
- **Transición suave**: `duration-150 ease-out` para cambios de altura

### Botones

#### Botón + (Herramientas)
- Altura: `h-11 w-11` (44px × 44px)
- Color: `text-neutral-300`
- Hover: `hover:bg-white/5`
- Accesibilidad: `aria-label="Abrir herramientas"`, `aria-expanded`, `aria-haspopup="menu"`

#### Botón Enviar (Flecha ↑)
- Icono: Flecha hacia arriba (`SendIconArrowUp`)
- Color activo: `bg-primary text-neutral-900` (verde #49F7D9)
- Color deshabilitado: `bg-neutral-700/40 text-neutral-500`
- Estados:
  - **Enabled**: `hover:bg-primary/90 active:scale-95`
  - **Disabled**: Cuando `value.trim().length === 0` o `loading` o `isSubmitting`
- Animación tap: `whileTap={{ scale: 0.92 }}`

### Teclado
- **Enter**: Envía el mensaje (si hay texto y no está disabled/loading)
- **Shift+Enter**: Inserta salto de línea
- **Escape**: Cierra el menú de herramientas o cancela (si `showCancel`)
- **Tab**: Navegación entre +, textarea, enviar

### Animaciones (Framer Motion)

#### Al enviar
```tsx
// Duración: 120ms antes del submit, 80ms para re-enfocar
setIsSubmitting(true)
await new Promise((resolve) => setTimeout(resolve, 120))
await onSubmit()
setIsSubmitting(false)
setTimeout(() => taRef.current?.focus(), 80)
```

#### Auto-resize
```tsx
// CSS transition en textarea
className="transition-[height] duration-150 ease-out"
```

#### Tool Menu
```tsx
initial={{ opacity: 0, y: 8, scale: 0.96 }}
animate={{ opacity: 1, y: 0, scale: 1 }}
exit={{ opacity: 0, y: 4, scale: 0.98 }}
transition={{ duration: 0.14, ease: [0.16, 1, 0.3, 1] }}
```

#### Tool Chips
```tsx
initial={{ opacity: 0, height: 0 }}
animate={{ opacity: 1, height: 'auto' }}
exit={{ opacity: 0, height: 0 }}
transition={{ duration: 0.16, ease: 'easeOut' }}
```

### Accesibilidad (WCAG 2.1 AA)

- **role="form"** en el contenedor principal
- **aria-label="Compositor de mensajes"** en el form
- **aria-label="Escribe tu mensaje"** en el textarea
- **aria-multiline="true"** en el textarea
- **aria-label="Abrir herramientas"** en botón +
- **aria-label="Enviar mensaje"** en botón enviar
- **aria-label="Detener generación"** en botón stop
- **Focus visible**: `focus-visible:ring-2 focus-visible:ring-primary/60`
- **Ring offset**: `focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-900`

## 📦 Props

```tsx
interface CompactChatComposerProps {
  value: string                              // Texto actual del mensaje
  onChange: (value: string) => void          // Callback al cambiar texto
  onSubmit: () => void | Promise<void>       // Callback al enviar (Enter o clic)
  onCancel?: () => void                      // Callback al cancelar (Stop)
  disabled?: boolean                         // Deshabilitar input y botones
  loading?: boolean                          // Estado de carga (muestra estado)
  layout?: 'center' | 'bottom'              // Modo: hero centrado o sticky bottom
  onActivate?: () => void                    // Callback al activar (transición hero→chat)
  placeholder?: string                       // Placeholder del textarea
  maxLength?: number                         // Longitud máxima (default: 10000)
  showCancel?: boolean                       // Mostrar botón Stop en lugar de Send
  className?: string                         // Clases adicionales para el wrapper
  selectedTools?: ToolId[]                   // IDs de tools seleccionadas
  onRemoveTool?: (id: ToolId) => void       // Callback al quitar tool
  onAddTool?: (id: ToolId) => void          // Callback al agregar tool
  attachments?: ChatComposerAttachment[]     // Archivos adjuntos (futuro)
  onAttachmentsChange?: (attachments: ChatComposerAttachment[]) => void
}
```

## 🚀 Uso

### Ejemplo básico

```tsx
import { CompactChatComposer } from '@/components/chat'

function ChatPage() {
  const [message, setMessage] = React.useState('')

  const handleSend = async () => {
    console.log('Sending:', message)
    // Enviar mensaje a la API
    setMessage('') // Limpiar después de enviar
  }

  return (
    <CompactChatComposer
      value={message}
      onChange={setMessage}
      onSubmit={handleSend}
      layout="bottom"
    />
  )
}
```

### Modo hero (centrado)

```tsx
<div className="flex h-screen items-center justify-center">
  <div className="w-full max-w-[640px]">
    <h1>¿Cómo puedo ayudarte?</h1>
    <CompactChatComposer
      value={message}
      onChange={setMessage}
      onSubmit={handleSend}
      layout="center"
      onActivate={() => setHeroMode(false)}
    />
  </div>
</div>
```

### Con herramientas seleccionadas

```tsx
const [selectedTools, setSelectedTools] = React.useState<ToolId[]>(['deep-research'])

<CompactChatComposer
  value={message}
  onChange={setMessage}
  onSubmit={handleSend}
  selectedTools={selectedTools}
  onAddTool={(id) => setSelectedTools([...selectedTools, id])}
  onRemoveTool={(id) => setSelectedTools(selectedTools.filter(t => t !== id))}
/>
```

### Con loading y cancel

```tsx
const [loading, setLoading] = React.useState(false)

const handleSend = async () => {
  setLoading(true)
  await sendMessage(message)
  setLoading(false)
}

const handleCancel = () => {
  // Cancelar operación en curso
  abortController.abort()
  setLoading(false)
}

<CompactChatComposer
  value={message}
  onChange={setMessage}
  onSubmit={handleSend}
  loading={loading}
  showCancel={loading}
  onCancel={handleCancel}
/>
```

## 🔄 Migración desde ChatComposerV2

### Cambios principales

1. **Import actualizado**:
   ```tsx
   // Antes
   import { ChatComposerV2 } from '@/components/chat'

   // Después
   import { CompactChatComposer } from '@/components/chat'
   ```

2. **Props iguales**: Todas las props son compatibles, no requiere cambios

3. **Diseño visual**:
   - Layout grid en lugar de flex
   - Botón enviar usa `bg-primary` (verde #49F7D9) en lugar de `bg-white/10`
   - Icono de flecha hacia arriba en lugar de flecha derecha
   - Sin bordes visibles entre elementos

### Checklist de migración

- [ ] Cambiar import de `ChatComposerV2` a `CompactChatComposer`
- [ ] Verificar que los colores se vean correctamente (botón verde)
- [ ] Probar auto-resize con mensajes largos (>10 líneas)
- [ ] Verificar Enter/Shift+Enter funcionen correctamente
- [ ] Probar navegación con Tab y focus visible
- [ ] Verificar animación al enviar (120ms fade + re-focus)
- [ ] Probar en breakpoints sm (≥640px) y lg (≥1024px)

## 🧪 Testing Manual

### Caso 1: Auto-resize básico
1. Escribir "Hola" → altura mínima (44px)
2. Pegar 10 líneas de texto → crece hasta max-h-48
3. Agregar más líneas → aparece scroll interno

### Caso 2: Envío con Enter
1. Escribir "Test message"
2. Presionar Enter → mensaje se envía
3. Input se limpia y vuelve a altura mínima
4. Re-enfoque automático en textarea después de 80ms

### Caso 3: Shift+Enter
1. Escribir "Línea 1"
2. Presionar Shift+Enter → inserta salto de línea
3. Escribir "Línea 2"
4. Textarea crece para acomodar ambas líneas

### Caso 4: Botón deshabilitado
1. Input vacío → botón enviar deshabilitado (gris, sin hover)
2. Escribir texto → botón se habilita (verde, con hover)
3. Borrar texto → botón se deshabilita de nuevo

### Caso 5: Accesibilidad
1. Tab → foco en botón +
2. Tab → foco en textarea (outline visible)
3. Tab → foco en botón enviar (outline visible)
4. Shift+Tab → navegación inversa funciona

### Caso 6: Herramientas
1. Clic en + → menú se abre con animación
2. Seleccionar "Deep Research" → chip aparece abajo
3. Escribir en textarea → menú se mantiene abierto
4. Clic fuera → menú se cierra
5. Escape → menú se cierra

## 🎨 Tokens de Diseño

### Colores
- **Primary**: `#49F7D9` (verde SAPTIVA)
- **Fondo**: `bg-neutral-800/40` (translúcido)
- **Texto**: `text-white`, `placeholder:text-neutral-400`
- **Botón +**: `text-neutral-300 hover:bg-white/5`
- **Botón enviar activo**: `bg-primary text-neutral-900`
- **Botón enviar disabled**: `bg-neutral-700/40 text-neutral-500`

### Espaciado
- **Gap interno**: `gap-2` (8px entre +, textarea, enviar)
- **Padding**: `p-2` (8px en el contenedor)
- **Altura botones**: `h-11 w-11` (44px)
- **Altura min textarea**: `44px`
- **Altura max textarea**: `192px`

### Radios
- **Contenedor**: `rounded-2xl` (16px)
- **Botones**: `rounded-xl` (12px)

### Sombras
- **Normal**: `shadow-lg shadow-black/20`
- **Focus**: `focus-within:shadow-xl focus-within:shadow-black/30`

## 🐛 Troubleshooting

### El textarea no crece
- Verificar que `handleAutoResize` se ejecuta en `useEffect([value])`
- Revisar que `scrollHeight` no sea 0
- Comprobar que `MIN_HEIGHT` y `MAX_HEIGHT` estén definidos

### El botón enviar no cambia de color
- Verificar que `canSubmit` se calcule correctamente
- Confirmar que `value.trim().length > 0`
- Revisar que `disabled` y `loading` sean `false`

### Focus visible no aparece
- Verificar clase `focus-visible:ring-2` en botones
- Comprobar que `focus-visible:ring-primary/60` esté aplicándose
- Revisar offset: `focus-visible:ring-offset-2`

### Animación al enviar no funciona
- Verificar que `isSubmitting` cambie a `true`
- Comprobar que `setTimeout` de 120ms se ejecute
- Revisar que `motion.div` tenga prop `animate`

## 📚 Referencias

- [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)
- [Framer Motion Docs](https://www.framer.com/motion/)
- [Ley de Fitts](https://lawsofux.com/fittss-law/)
- [ChatGPT UI Reference](https://chat.openai.com)
