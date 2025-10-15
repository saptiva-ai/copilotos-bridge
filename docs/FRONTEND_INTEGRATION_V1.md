# Frontend Integration - Files V1

Guía completa para integrar el sistema de files V1 en el frontend.

## Resumen de Cambios

El sistema de files V1 unifica la ingesta de archivos en un solo flujo:

- **Endpoint único**: `/api/files/upload`
- **Hook simplificado**: `useFiles()`
- **Tipos completos**: `types/files.ts`
- **Validación client-side**: Antes de upload
- **Errores tipados**: Mensajes user-friendly
- **Idempotencia**: Hash-based deduplication

---

## 1. Arquitectura Frontend

```
apps/web/src/
├── hooks/
│   ├── useFiles.ts              ← Nuevo hook V1
│   └── useDocumentReview.ts     ← Legacy (mantener por ahora)
├── types/
│   └── files.ts                 ← Tipos y constantes V1
└── components/
    ├── files/
    │   ├── FileUploadButton.tsx ← A crear
    │   ├── FileAttachmentList.tsx ← A crear
    │   └── FileErrorMessage.tsx  ← A crear
    └── document-review/          ← Legacy
        ├── FileCard.tsx
        └── FileDropzone.tsx
```

---

## 2. Uso del Hook `useFiles`

### Instalación

```typescript
import { useFiles } from "@/hooks/useFiles";
import type { FileAttachment } from "@/types/files";
```

### Ejemplo Básico

```typescript
function MyComponent() {
  const {
    uploadFile,
    uploadFiles,
    isUploading,
    uploadProgress,
    error,
    clearError,
    attachments,
    addAttachment,
    removeAttachment,
    clearAttachments,
  } = useFiles();

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);

    for (const file of files) {
      const attachment = await uploadFile(file, conversationId);
      if (attachment) {
        addAttachment(attachment);
      }
    }
  };

  return (
    <div>
      <input type="file" onChange={handleFileSelect} multiple />
      {error && <div className="error">{error}</div>}
      {isUploading && <div>Uploading...</div>}
      <FileAttachmentList
        attachments={attachments}
        onRemove={removeAttachment}
      />
    </div>
  );
}
```

### Ejemplo con Validación

```typescript
import { validateFile, MAX_UPLOAD_SIZE } from "@/types/files";

const handleFileSelect = async (files: FileList) => {
  const fileArray = Array.from(files);

  for (const file of fileArray) {
    // Validación client-side
    const validation = validateFile(file);
    if (!validation.valid) {
      toast.error(validation.error);
      continue;
    }

    // Upload
    const attachment = await uploadFile(file, conversationId);
    if (attachment) {
      addAttachment(attachment);
      toast.success(`${file.name} subido correctamente`);
    }
  }
};
```

---

## 3. Componentes Sugeridos

### FileUploadButton

```typescript
// apps/web/src/components/files/FileUploadButton.tsx

import { useFiles } from "@/hooks/useFiles";
import { Button } from "@/components/ui/button";
import { FileUp, Loader2 } from "lucide-react";
import { validateFile } from "@/types/files";
import { useToast } from "@/hooks/use-toast";

interface FileUploadButtonProps {
  conversationId?: string;
  onUploadComplete?: (attachments: FileAttachment[]) => void;
  maxFiles?: number;
}

export function FileUploadButton({
  conversationId,
  onUploadComplete,
  maxFiles = 5,
}: FileUploadButtonProps) {
  const { uploadFiles, isUploading, error, clearError } = useFiles();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);

    if (files.length === 0) return;

    // Validación
    const validFiles = files.filter((file) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        toast({
          title: "Error de validación",
          description: `${file.name}: ${validation.error}`,
          variant: "destructive",
        });
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) return;

    // Upload
    const attachments = await uploadFiles(validFiles, conversationId);

    if (attachments.length > 0) {
      toast({
        title: "Archivos subidos",
        description: `${attachments.length} archivo(s) subido(s) correctamente`,
      });
      onUploadComplete?.(attachments);
    }

    // Clear input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        disabled={isUploading}
      >
        {isUploading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Subiendo...
          </>
        ) : (
          <>
            <FileUp className="mr-2 h-4 w-4" />
            Agregar archivos
          </>
        )}
      </Button>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.gif,.heic"
        onChange={handleFileChange}
      />
    </>
  );
}
```

### FileAttachmentList

```typescript
// apps/web/src/components/files/FileAttachmentList.tsx

import { FileAttachment } from "@/types/files";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X, FileText, CheckCircle, AlertCircle } from "lucide-react";

interface FileAttachmentListProps {
  attachments: FileAttachment[];
  onRemove?: (fileId: string) => void;
}

export function FileAttachmentList({
  attachments,
  onRemove,
}: FileAttachmentListProps) {
  if (attachments.length === 0) return null;

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-2">
      {attachments.map((attachment) => (
        <div
          key={attachment.file_id}
          className="flex items-center gap-3 rounded-lg border p-3"
        >
          <FileText className="h-5 w-5 text-muted-foreground" />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium truncate">
                {attachment.filename}
              </p>
              {attachment.status === "READY" && (
                <CheckCircle className="h-4 w-4 text-green-500" />
              )}
              {attachment.status === "FAILED" && (
                <AlertCircle className="h-4 w-4 text-red-500" />
              )}
              {attachment.status === "PROCESSING" && (
                <Badge variant="secondary">Procesando</Badge>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              {formatBytes(attachment.bytes)}
              {attachment.pages && ` • ${attachment.pages} página(s)`}
            </p>
          </div>

          {onRemove && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => onRemove(attachment.file_id)}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## 4. Integración en Chat Composer

### Agregar Toggle "Usar archivos"

```typescript
// apps/web/src/components/chat/Composer.tsx

import { useFiles } from "@/hooks/useFiles";
import { FileUploadButton } from "@/components/files/FileUploadButton";
import { FileAttachmentList } from "@/components/files/FileAttachmentList";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export function Composer({ conversationId }: { conversationId: string }) {
  const {
    attachments,
    addAttachment,
    removeAttachment,
    clearAttachments,
  } = useFiles();

  const [useFiles, setUseFiles] = useState(false);

  const handleSendMessage = async (message: string) => {
    const payload: any = {
      message,
      conversation_id: conversationId,
    };

    // Agregar file_ids si el toggle está ON y hay archivos READY
    if (useFiles && attachments.length > 0) {
      const readyFiles = attachments.filter((a) => a.status === "READY");
      payload.file_ids = readyFiles.map((a) => a.file_id);
    }

    await sendMessage(payload);

    // Limpiar attachments después de enviar
    clearAttachments();
  };

  return (
    <div className="space-y-4">
      {/* Controles de archivos */}
      <div className="flex items-center justify-between">
        <FileUploadButton
          conversationId={conversationId}
          onUploadComplete={(newAttachments) => {
            newAttachments.forEach(addAttachment);
          }}
        />

        <div className="flex items-center space-x-2">
          <Switch
            id="use-files"
            checked={useFiles}
            onCheckedChange={setUseFiles}
            disabled={attachments.length === 0}
          />
          <Label htmlFor="use-files">
            Usar archivos en esta pregunta
          </Label>
        </div>
      </div>

      {/* Lista de archivos adjuntos */}
      {attachments.length > 0 && (
        <FileAttachmentList
          attachments={attachments}
          onRemove={removeAttachment}
        />
      )}

      {/* Resto del composer... */}
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Escribe tu mensaje..."
      />

      <Button onClick={() => handleSendMessage(message)}>
        Enviar
      </Button>
    </div>
  );
}
```

---

## 5. Feature Flags

### Backend Feature Flag

El backend expone el flag en `/api/features/tools`:

```json
{
  "files": {
    "enabled": true
  }
}
```

### Frontend Check

```typescript
// apps/web/src/lib/features.ts

interface ToolsFeatures {
  files?: { enabled: boolean };
}

export async function getToolsFeatures(): Promise<ToolsFeatures> {
  const response = await fetch("/api/features/tools");
  return response.json();
}

// Usage
const features = await getToolsFeatures();
if (features.files?.enabled) {
  // Show Files V1 UI
}
```

### Environment Variable (Fallback)

```bash
# .env.local
NEXT_PUBLIC_TOOL_FILES=true
```

```typescript
const isFilesEnabled =
  process.env.NEXT_PUBLIC_TOOL_FILES === "true" ||
  features.files?.enabled;
```

---

## 6. Error Handling

### Tipos de Errores

El backend devuelve error codes tipados:

| Error Code | Descripción | UI Message |
|------------|-------------|------------|
| `UPLOAD_TOO_LARGE` | Archivo >10MB | "El archivo es demasiado grande. Máximo 10 MB." |
| `UNSUPPORTED_MIME` | MIME no soportado | "Tipo de archivo no soportado. Usa PDF, PNG, JPG, GIF o HEIC." |
| `RATE_LIMITED` | >5 uploads/min | "Demasiados archivos subidos. Espera un minuto..." |
| `EXTRACTION_FAILED` | Error de procesamiento | "Error al procesar el archivo. Intenta de nuevo." |

### Mapeo de Errores

El hook `useFiles` ya mapea automáticamente:

```typescript
import { getErrorMessage } from "@/types/files";

// En useFiles
if (errorData.error) {
  const userMessage = getErrorMessage(errorData.error);
  throw new Error(userMessage);
}
```

### Toast Notifications

```typescript
import { useToast } from "@/hooks/use-toast";

const { toast } = useToast();

// En handleUpload
try {
  const attachment = await uploadFile(file);
  toast({
    title: "Archivo subido",
    description: attachment.filename,
  });
} catch (error) {
  toast({
    title: "Error al subir archivo",
    description: error.message,
    variant: "destructive",
  });
}
```

---

## 7. Testing

### Unit Tests (Jest/Vitest)

```typescript
// useFiles.test.ts

import { renderHook, act, waitFor } from "@testing-library/react";
import { useFiles } from "@/hooks/useFiles";
import { validateFile } from "@/types/files";

describe("useFiles", () => {
  it("validates file size", () => {
    const largeFile = new File(["x".repeat(11 * 1024 * 1024)], "large.pdf", {
      type: "application/pdf",
    });

    const validation = validateFile(largeFile);
    expect(validation.valid).toBe(false);
    expect(validation.error).toContain("demasiado grande");
  });

  it("validates MIME type", () => {
    const invalidFile = new File(["data"], "file.exe", {
      type: "application/x-msdownload",
    });

    const validation = validateFile(invalidFile);
    expect(validation.valid).toBe(false);
    expect(validation.error).toContain("no soportado");
  });

  it("uploads file successfully", async () => {
    const { result } = renderHook(() => useFiles());

    const file = new File(["content"], "test.pdf", {
      type: "application/pdf",
    });

    await act(async () => {
      const attachment = await result.current.uploadFile(file);
      expect(attachment).not.toBeNull();
      expect(attachment?.filename).toBe("test.pdf");
    });
  });
});
```

### E2E Tests

Ver `tests/e2e/files-v1.spec.ts` para tests completos.

---

## 8. Rollout Plan

### Fase 1: Canary (5% usuarios) - 48h

```typescript
// Feature flag check
const isCanaryUser = userId % 20 === 0; // 5% canary
const showFilesV1 = isCanaryUser && features.files?.enabled;
```

**Monitoreo:**
- p95 latency en `/api/files/upload`
- Error rate: `copilotos_pdf_ingest_errors_total`
- User feedback

### Fase 2: Gradual Rollout (10% → 50% → 100%)

```typescript
const rolloutPercentage = parseFloat(
  process.env.NEXT_PUBLIC_FILES_V1_ROLLOUT || "100"
);
const showFilesV1 =
  (userId % 100) < rolloutPercentage && features.files?.enabled;
```

### Fase 3: Deprecar Legacy (2-4 semanas)

1. Mantener redirect 307 en `/api/documents/upload`
2. Ocultar UI de `document-review` (pero mantener código)
3. Después de 2 semanas: remover componentes legacy
4. Después de 4 semanas: remover endpoint `/api/documents/upload`

---

## 9. Checklist de Integración

### Backend (✅ Completado)

- [x] Endpoint `/api/files/upload`
- [x] Redirect 307 en `/api/documents/upload`
- [x] Rate limiting (5 uploads/min)
- [x] Validación tamaño/MIME
- [x] Idempotencia
- [x] Métricas Prometheus
- [x] Logs con trace_id

### Frontend (⏳ Pendiente)

- [ ] Tipos TypeScript (`types/files.ts`) ✅ Creado
- [ ] Hook `useFiles` ✅ Creado
- [ ] Componente `FileUploadButton` ⏳ Esqueleto
- [ ] Componente `FileAttachmentList` ⏳ Esqueleto
- [ ] Integración en Composer ⏳ Guía
- [ ] Toggle "Usar archivos en esta pregunta" ⏳
- [ ] Feature flag check ⏳
- [ ] Error handling & toast notifications ⏳
- [ ] Unit tests ⏳
- [ ] E2E tests ✅ Creado

### Testing

- [x] E2E tests Playwright ✅
- [ ] Unit tests frontend ⏳
- [ ] Integration tests ⏳
- [ ] Smoke tests en postprod ⏳

---

## 10. Referencias

- **Reporte validación**: `VALIDATION_REPORT_V1.md`
- **Backend router**: `apps/api/src/routers/files.py`
- **Backend servicio**: `apps/api/src/services/file_ingest.py`
- **E2E tests**: `tests/e2e/files-v1.spec.ts`
- **Hook useFiles**: `apps/web/src/hooks/useFiles.ts`
- **Tipos**: `apps/web/src/types/files.ts`

---

## 11. FAQ

### ¿Debo remover `useDocumentReview` ahora?

No. Mantenerlo por ahora como fallback durante la migración. Deprecar después de 2-4 semanas de rollout exitoso.

### ¿Cómo manejo el contexto de archivos en el chat?

Agregar `file_ids` array al payload del mensaje cuando el toggle está ON y hay attachments READY.

### ¿Qué pasa si el usuario sube el mismo archivo dos veces?

El backend usa idempotencia (hash-based), devolverá el mismo `file_id`. El frontend puede detectar duplicados comparando file_ids.

### ¿Cómo muestro progreso de upload?

El hook `useFiles` expone `uploadProgress` con `{ loaded, total, percentage }`. Usar un progress bar o spinner.

### ¿Qué hacer con archivos FAILED?

Mostrar error message con el error code mapeado. Ofrecer botón "Reintentar" que vuelva a llamar `uploadFile()`.

---

**Próximo paso:** Implementar los componentes y integrar en el Composer según esta guía.
