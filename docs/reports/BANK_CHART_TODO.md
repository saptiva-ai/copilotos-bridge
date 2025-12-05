# Bank Chart Canvas - Mejoras y Tests Pendientes

## ✅ Completado (Sesión Actual)

- [x] Backend: Persistencia de artifacts con TTL
- [x] Frontend: Visualización en canvas con tabs
- [x] Auto-open para primera gráfica
- [x] Botón mejorado para abrir canvas
- [x] Tests unitarios (30/30 passing)
- [x] Fix 404 errors para artifacts temporales
- [x] Sincronización bidireccional chat ↔ canvas

---

## 🚀 Mejoras de Alto Impacto

### 1. Backend - Rendimiento y Escalabilidad

#### 1.1 Caché de Artifacts
**Prioridad: Alta**
```python
# Implementar caché en Redis para artifacts frecuentemente accedidos
class ArtifactService:
    async def get_artifact_cached(self, artifact_id: str) -> Optional[Artifact]:
        # Check Redis cache first
        # Fall back to MongoDB
        # Update cache on miss
```
- **Beneficio**: Reducir latencia de 50-100ms a 1-5ms
- **Test**: `test_artifact_cache_hit_rate()`

#### 1.2 Batch Operations
**Prioridad: Media**
```python
async def get_charts_by_session_batch(
    self,
    session_ids: List[str]
) -> Dict[str, List[Artifact]]:
    # Fetch multiple sessions in one query
```
- **Beneficio**: Reducir queries cuando usuario tiene múltiples sesiones abiertas
- **Test**: `test_batch_fetch_performance()`

#### 1.3 Cleanup Job para TTL
**Prioridad: Media**
```python
# Script de mantenimiento
async def cleanup_expired_artifacts():
    # Delete artifacts where expires_at < now()
    # Log cleanup stats
```
- **Beneficio**: Liberar espacio en MongoDB
- **Test**: `test_ttl_cleanup_job()`

---

### 2. Frontend - UX y Accesibilidad

#### 2.1 Loading States
**Prioridad: Alta**
```typescript
// Mostrar skeleton mientras carga la gráfica
{isLoading && <BankChartSkeleton />}
{error && <BankChartError message={error} />}
{data && <BankChartCanvasView data={data} />}
```
- **Beneficio**: Mejor feedback visual
- **Test**: `test_chart_loading_skeleton()`

#### 2.2 Keyboard Shortcuts
**Prioridad: Media**
```typescript
// Atajo de teclado para abrir/cerrar canvas
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'c' && e.metaKey) {
      toggleSidebar();
    }
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, []);
```
- **Beneficio**: Power users pueden navegar más rápido
- **Test**: `test_keyboard_shortcut_toggle_canvas()`

#### 2.3 Responsive Design
**Prioridad: Alta**
```typescript
// Canvas debe ser fullscreen en móvil
const isMobile = useMediaQuery('(max-width: 768px)');
return (
  <motion.aside
    className={cn(
      isMobile ? 'fixed inset-0 z-50' : 'w-96',
      // ...
    )}
  />
);
```
- **Beneficio**: Mejor experiencia móvil
- **Test**: `test_canvas_mobile_fullscreen()`

#### 2.4 Download Chart as PNG
**Prioridad: Media**
```typescript
const downloadChart = async () => {
  const plotElement = document.querySelector('.plotly');
  const blob = await Plotly.downloadImage(plotElement, {
    format: 'png',
    width: 1200,
    height: 800
  });
  saveAs(blob, `${chartData.metric_name}.png`);
};
```
- **Beneficio**: Usuarios pueden guardar gráficas
- **Test**: `test_download_chart_as_png()`

---

### 3. Testing - Cobertura y E2E

#### 3.1 Backend Integration Tests
**Prioridad: Alta**
```python
# tests/integration/test_bank_chart_flow.py
async def test_full_chart_persistence_flow():
    # 1. Create chat session
    # 2. Send message requesting chart
    # 3. Verify bank_chart SSE event
    # 4. Verify artifact_created SSE event
    # 5. Verify artifact in MongoDB
    # 6. Fetch artifact via API
    # 7. Verify TTL index
```
- **Cobertura**: Flujo completo backend
- **Archivos**: `tests/integration/test_bank_chart_flow.py`

#### 3.2 Frontend E2E Tests
**Prioridad: Media**
```typescript
// e2e/bank-chart.spec.ts (Playwright)
test('should open canvas when clicking chart button', async ({ page }) => {
  await page.goto('/chat');
  await page.fill('[data-testid="chat-input"]', 'Muestra IMOR para BBVA');
  await page.click('[data-testid="send-button"]');
  await page.waitForSelector('[data-testid="bank-chart-button"]');
  await page.click('[data-testid="bank-chart-button"]');
  await expect(page.locator('[data-testid="canvas-panel"]')).toBeVisible();
});
```
- **Cobertura**: Flujo completo usuario
- **Setup**: Instalar Playwright

#### 3.3 Performance Tests
**Prioridad: Baja**
```python
# tests/performance/test_artifact_service.py
async def test_artifact_service_latency():
    # Benchmark create_bank_chart_artifact
    # Assert < 50ms p95
    # Assert < 100ms p99
```
- **Métricas**: Latencia p50, p95, p99
- **Archivos**: `tests/performance/test_artifact_service.py`

---

### 4. Features Nuevas

#### 4.1 Multi-Chart Comparison
**Prioridad: Baja**
```typescript
// Permitir comparar 2 gráficas lado a lado
const [selectedCharts, setSelectedCharts] = useState<string[]>([]);

return (
  <div className="grid grid-cols-2 gap-4">
    {selectedCharts.map(chartId => (
      <BankChartCanvasView key={chartId} data={charts[chartId]} />
    ))}
  </div>
);
```
- **Beneficio**: Comparación visual de métricas
- **Test**: `test_multi_chart_comparison()`

#### 4.2 Chart Annotations
**Prioridad**: Baja
```typescript
// Permitir agregar anotaciones a la gráfica
interface Annotation {
  x: string;
  y: number;
  text: string;
  author: string;
}

const [annotations, setAnnotations] = useState<Annotation[]>([]);
```
- **Beneficio**: Colaboración en análisis
- **Test**: `test_chart_annotations()`

#### 4.3 Export to Excel/CSV
**Prioridad: Media**
```typescript
const exportToExcel = () => {
  const ws = XLSX.utils.json_to_sheet(chartData.plotly_config.data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Data');
  XLSX.writeFile(wb, `${chartData.metric_name}.xlsx`);
};
```
- **Beneficio**: Análisis offline en Excel
- **Test**: `test_export_chart_to_excel()`

#### 4.4 Share Chart via URL
**Prioridad: Media**
```typescript
// Generar URL compartible con token
const shareChart = async () => {
  const shareToken = await apiClient.createShareToken(artifactId);
  const shareUrl = `${window.location.origin}/shared/${shareToken}`;
  copyToClipboard(shareUrl);
};
```
- **Beneficio**: Compartir análisis con colegas
- **Test**: `test_share_chart_via_url()`

---

### 5. Observabilidad y Monitoring

#### 5.1 Métricas de Uso
**Prioridad: Alta**
```python
# Track chart creation metrics
metrics.increment('bank_chart.created', tags={
    'metric_name': chart_data.metric_name,
    'bank_count': len(chart_data.bank_names)
})

metrics.histogram('bank_chart.render_time_ms', render_time)
```
- **Métricas**: Charts creados, tiempo de render, errores
- **Dashboard**: Grafana

#### 5.2 Error Tracking
**Prioridad: Alta**
```python
# Sentry integration para errores de persistencia
try:
    artifact = await artifact_service.create_bank_chart_artifact(request)
except Exception as e:
    sentry_sdk.capture_exception(e)
    logger.error("Failed to persist artifact", exc_info=True)
```
- **Beneficio**: Detectar errores en producción
- **Tool**: Sentry

#### 5.3 User Analytics
**Prioridad: Media**
```typescript
// Track user interactions
analytics.track('bank_chart_opened', {
  metric_name: chartData.metric_name,
  bank_count: chartData.bank_names.length,
  source: 'chat_button'
});
```
- **Métricas**: Charts más vistos, tiempo en canvas
- **Tool**: Mixpanel / PostHog

---

### 6. Seguridad y Validación

#### 6.1 Rate Limiting
**Prioridad: Alta**
```python
# Limitar creación de artifacts por usuario
@rate_limit(max_requests=100, window_seconds=3600)
async def create_bank_chart_artifact(request: BankChartArtifactRequest):
    # ...
```
- **Beneficio**: Prevenir abuso
- **Test**: `test_artifact_rate_limiting()`

#### 6.2 Input Validation
**Prioridad: Alta**
```python
# Validar que metric_name sea válido
ALLOWED_METRICS = {'imor', 'cartera', 'capitalizacion', ...}

class BankChartArtifactRequest(BaseModel):
    metric_name: str

    @validator('metric_name')
    def validate_metric(cls, v):
        if v not in ALLOWED_METRICS:
            raise ValueError(f'Invalid metric: {v}')
        return v
```
- **Beneficio**: Prevenir datos inválidos
- **Test**: `test_invalid_metric_rejected()`

#### 6.3 XSS Protection
**Prioridad: Alta**
```typescript
// Sanitizar texto en metadata
import DOMPurify from 'dompurify';

const sanitizedInterpretation = DOMPurify.sanitize(
  chartData.metadata.metric_interpretation
);
```
- **Beneficio**: Prevenir XSS
- **Test**: `test_xss_protection_in_metadata()`

---

## 📋 Plan de Acción Recomendado

### Sprint 1 (Alta Prioridad - 1 semana)
1. ✅ Loading states y error handling
2. ✅ Responsive design para móvil
3. ✅ Backend integration tests
4. ✅ Rate limiting
5. ✅ Input validation

### Sprint 2 (Media Prioridad - 1 semana)
1. ✅ Keyboard shortcuts
2. ✅ Download chart as PNG
3. ✅ Export to Excel
4. ✅ Share chart via URL
5. ✅ Frontend E2E tests

### Sprint 3 (Baja Prioridad - 1 semana)
1. ✅ Caché en Redis
2. ✅ Batch operations
3. ✅ Multi-chart comparison
4. ✅ User analytics
5. ✅ Performance tests

---

## 🔧 Quick Wins (< 1 hora cada uno)

1. **Add data-testid attributes**: Facilitar E2E testing
2. **Add error boundary**: Prevenir crashes en canvas
3. **Add retry logic**: Reintentar fetch de artifacts fallidos
4. **Add keyboard focus**: Mejorar accesibilidad
5. **Add aria-labels**: Mejorar screen reader support
6. **Add chart title in canvas header**: Mejor contexto visual
7. **Add "Close" button**: Alternativa al toggle sidebar
8. **Add chart metadata tooltip**: Info adicional on hover

---

## 📚 Documentación Pendiente

1. **API Documentation**: Swagger/OpenAPI para endpoints de artifacts
2. **User Guide**: Cómo usar canvas en docs/
3. **Developer Guide**: Arquitectura de bank_chart system
4. **Troubleshooting Guide**: Errores comunes y soluciones

---

## 🐛 Bugs Conocidos

1. **Canvas no se cierra en móvil al hacer click fuera**: Falta overlay click handler
2. **Plotly no se redimensiona al cambiar tamaño de canvas**: Falta `useResizeHandler`
3. **chartHistory puede crecer indefinidamente**: Falta limit de 20 charts
4. **Auto-open puede fallar si SSE llega después de navegación**: Race condition

---

**Última actualización**: 2025-12-01
**Autor**: Sistema de desarrollo Octavios Chat
