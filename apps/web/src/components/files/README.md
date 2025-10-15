# Files V1 Components

Componentes React para el sistema unificado de files V1.

## Componentes Implementados

### ✅ `FileUploadButton`

Botón para subir archivos con validación client-side.

**Features:**

- Validación de tamaño (max 10MB)
- Validación de MIME types
- Multiple file selection
- Upload progress
- Error handling con mensajes user-friendly
- Rate limiting awareness

**Uso:**

```tsx
import { FileUploadButton } from "@/components/files";

<FileUploadButton
  conversationId={chatId}
  onUploadComplete={(attachments) => {
    attachments.forEach(addAttachment);
  }}
  maxFiles={5}
  variant="outline"
/>;
```

**Props:**

- `conversationId?: string` - ID de la conversación
- `onUploadComplete?: (attachments) => void` - Callback con archivos subidos
- `maxFiles?: number` - Máximo de archivos (default: 5)
- `variant?: 'default' | 'outline' | 'ghost'` - Estilo del botón
- `size?: 'default' | 'sm' | 'lg'` - Tamaño del botón
- `disabled?: boolean` - Deshabilitar
- `className?: string` - Clases adicionales

### ✅ `FileAttachmentList`

Lista de archivos adjuntos con status indicators.

**Features:**

- Status badges (READY, PROCESSING, FAILED)
- File metadata (size, pages, MIME type)
- Remove action
- Color-coded borders por status

**Uso:**

```tsx
import { FileAttachmentList } from "@/components/files";

<FileAttachmentList attachments={attachments} onRemove={removeAttachment} />;
```

**Props:**

- `attachments: FileAttachment[]` - Lista de archivos
- `onRemove?: (fileId: string) => void` - Callback para remover
- `className?: string` - Clases adicionales

### ✅ `FilesToggle`

Toggle switch para "Usar archivos en esta pregunta".

**Features:**

- Switch accesible (ARIA)
- Label con contador de archivos
- Disabled state cuando no hay archivos

**Uso:**

```tsx
import { FilesToggle } from "@/components/files";

<FilesToggle
  enabled={useFilesInQuestion}
  onChange={setUseFilesInQuestion}
  disabled={attachments.length === 0}
  fileCount={attachments.length}
/>;
```

**Props:**

- `enabled: boolean` - Estado del toggle
- `onChange: (enabled: boolean) => void` - Callback de cambio
- `disabled?: boolean` - Deshabilitar
- `fileCount?: number` - Número de archivos (para label)
- `className?: string` - Clases adicionales

---

## Hooks

### `useFiles`

Hook principal para file management.

**Returns:**

```typescript
{
  uploadFile: (file, conversationId?) => Promise<FileAttachment | null>
  uploadFiles: (files[], conversationId?) => Promise<FileAttachment[]>
  isUploading: boolean
  uploadProgress: UploadProgress | null
  error: string | null
  clearError: () => void
  attachments: FileAttachment[]
  addAttachment: (attachment) => void
  removeAttachment: (fileId) => void
  clearAttachments: () => void
}
```

**Ejemplo:**

```tsx
const {
  uploadFile,
  attachments,
  addAttachment,
  removeAttachment,
  clearAttachments,
} = useFiles();

const handleFileSelect = async (file: File) => {
  const attachment = await uploadFile(file, conversationId);
  if (attachment) {
    addAttachment(attachment);
  }
};
```

---

## Tipos

Ver `src/types/files.ts` para tipos completos:

```typescript
type FileStatus = "RECEIVED" | "PROCESSING" | "READY" | "FAILED";

interface FileAttachment {
  file_id: string;
  filename: string;
  status: FileStatus;
  bytes: number;
  pages?: number;
  mimetype?: string;
}

type FileErrorCode =
  | "UPLOAD_TOO_LARGE"
  | "UNSUPPORTED_MIME"
  | "EXTRACTION_FAILED"
  | "RATE_LIMITED"
  | "OCR_TIMEOUT"
  | "QUOTA_EXCEEDED";
```

---

## Integración en ChatComposer

Ver `FilesPanel.example.tsx` para un ejemplo completo.

### Paso 1: Import hooks y componentes

```tsx
import { useFiles } from "@/hooks/useFiles";
import {
  FileUploadButton,
  FileAttachmentList,
  FilesToggle,
} from "@/components/files";
import type { FileAttachment } from "@/types/files";
```

### Paso 2: State management

```tsx
const { attachments, addAttachment, removeAttachment, clearAttachments } =
  useFiles();

const [useFilesInQuestion, setUseFilesInQuestion] = useState(false);
```

### Paso 3: UI en Composer

```tsx
<div className="composer-controls">
  <FileUploadButton
    conversationId={conversationId}
    onUploadComplete={(newAttachments) => {
      newAttachments.forEach(addAttachment);
      setUseFilesInQuestion(true); // Auto-enable
    }}
  />

  {attachments.length > 0 && (
    <FilesToggle
      enabled={useFilesInQuestion}
      onChange={setUseFilesInQuestion}
      fileCount={attachments.length}
    />
  )}
</div>;

{
  attachments.length > 0 && (
    <FileAttachmentList attachments={attachments} onRemove={removeAttachment} />
  );
}
```

### Paso 4: Modificar sendMessage

```tsx
const handleSendMessage = async (message: string) => {
  const payload: any = {
    message,
    conversation_id: conversationId,
  };

  // Agregar file_ids si toggle está ON
  if (useFilesInQuestion && attachments.length > 0) {
    const readyFiles = attachments.filter((a) => a.status === "READY");
    payload.file_ids = readyFiles.map((a) => a.file_id);
  }

  await apiClient.sendMessage(payload);

  // Limpiar después de enviar
  clearAttachments();
  setUseFilesInQuestion(false);
};
```

---

## Feature Flags

### Backend Check

El backend expone el flag en `/api/features/tools`:

```json
{
  "tools": {
    "files": {
      "enabled": true
    }
  }
}
```

### Frontend Check

```tsx
import { useFeatureFlags } from '@/lib/features'

function MyComponent() {
  const { features, loading } = useFeatureFlags()

  if (loading) return <Spinner />

  if (!features.files?.enabled) {
    return null // Hide files UI
  }

  return <FileUploadButton ... />
}
```

### Environment Variable (Fallback)

```bash
# .env.local
NEXT_PUBLIC_TOOL_FILES=true
```

---

## Validación

### Client-Side

El hook `useFiles` valida automáticamente:

- ✅ Tamaño máximo: 10 MB
- ✅ MIME types soportados: PDF, PNG, JPG, GIF, HEIC
- ✅ Rate limiting: 5 uploads/min (informational)

### Server-Side

El backend valida:

- ✅ Tamaño máximo: 10 MB (413 si excede)
- ✅ MIME types: whitelist strict (415 si no soportado)
- ✅ Rate limiting: 5 uploads/min con Redis (429 si excede)

---

## Error Handling

Los errores del backend se mapean automáticamente a mensajes user-friendly:

| Backend Error       | User Message                                         |
| ------------------- | ---------------------------------------------------- |
| `UPLOAD_TOO_LARGE`  | "El archivo es demasiado grande. Máximo 10 MB."      |
| `UNSUPPORTED_MIME`  | "Tipo de archivo no soportado. Usa PDF, PNG, JPG..." |
| `RATE_LIMITED`      | "Demasiados archivos subidos. Espera un minuto..."   |
| `EXTRACTION_FAILED` | "Error al procesar el archivo. Intenta de nuevo."    |

Los errores se muestran automáticamente en el `FileUploadButton`.

---

## Testing

### Unit Tests

```tsx
import { render, fireEvent } from "@testing-library/react";
import { FileUploadButton } from "./FileUploadButton";

test("validates file size", () => {
  const { getByRole, getByText } = render(<FileUploadButton />);

  const input = getByRole("button");
  // ... test file selection

  expect(getByText(/demasiado grande/i)).toBeInTheDocument();
});
```

### E2E Tests

Ver `tests/e2e/files-v1.spec.ts` para tests completos de API.

---

## Próximos Pasos

### Para Go-Live

1. ✅ Componentes creados
2. ⏳ Integrar en `ChatComposer` real
3. ⏳ Agregar feature flag check en UI
4. ⏳ Testing manual en dev
5. ⏳ Unit tests para componentes
6. ⏳ Canary deployment (5% usuarios, 48h)
7. ⏳ Rollout gradual (10% → 50% → 100%)

### Para V1.1 (Async)

- Usar SSE: `/api/files/events/{file_id}`
- Mostrar progress real-time
- Eventos: upload, extract, cache, complete

---

## Archivos Creados

```
apps/web/src/
├── components/files/
│   ├── FileUploadButton.tsx         ✅ Component
│   ├── FileAttachmentList.tsx       ✅ Component
│   ├── FilesToggle.tsx              ✅ Component
│   ├── FilesPanel.example.tsx       ✅ Integration example
│   ├── index.ts                     ✅ Barrel export
│   └── README.md                    ✅ This file
├── hooks/
│   └── useFiles.ts                  ✅ Main hook
├── types/
│   └── files.ts                     ✅ Complete types
└── lib/
    └── features.ts                  ✅ Feature flags
```

---

## Referencias

- **Backend API**: `apps/api/src/routers/files.py`
- **Backend Service**: `apps/api/src/services/file_ingest.py`
- **Validation Report**: `VALIDATION_REPORT_V1.md`
- **Integration Guide**: `FRONTEND_INTEGRATION_V1.md`
- **E2E Tests**: `tests/e2e/files-v1.spec.ts`

---

## Soporte

Si tienes problemas:

1. Revisa la consola del browser para errores
2. Verifica que el backend esté corriendo (`docker-compose ps`)
3. Revisa `/api/metrics` para ver rate limiting
4. Consulta `FRONTEND_INTEGRATION_V1.md` para troubleshooting

**Happy coding! 🚀**
