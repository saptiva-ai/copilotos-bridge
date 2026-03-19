# Research: Rust Acceleration for Document Processing

## Executive Summary

**Recommendation:** Implementar un enfoque híbrido usando **PyO3 + Maturin** para módulos críticos de rendimiento, con migración opcional a **Rust puro con Tonic gRPC** para el microservicio completo.

**Beneficios esperados:**
- 12-50x más rápido en parsing de PDFs
- 47.9x más rápido con PDF Oxide vs PyMuPDF
- Memory safety (sin segfaults)
- Paralelismo con rayon crate

---

## 1. Opciones Evaluadas

### Opción A: PyO3 Native Modules (Híbrido)

**Descripción:** Escribir módulos críticos en Rust, exponer como extensiones nativas de Python.

| Aspecto | Evaluación |
|---------|------------|
| Complejidad | ⭐⭐ Baja-Media |
| Rendimiento | ⭐⭐⭐⭐ 12-15x vs Python puro |
| Integración | ⭐⭐⭐⭐⭐ Transparente con código Python existente |
| Mantenibilidad | ⭐⭐⭐⭐ Familiar para devs Python |

**Herramientas:**
- [PyO3](https://github.com/PyO3/pyo3): Rust bindings para Python
- [Maturin](https://github.com/PyO3/maturin): Build y publish de crates con PyO3

**Ejemplo de uso:**
```python
# Desde Python
from document_processing_rs import extract_text_fast

result = extract_text_fast(pdf_bytes)  # Llama a Rust
```

### Opción B: Rust Microservice con Tonic gRPC

**Descripción:** Reescribir el microservicio completo en Rust con gRPC nativo.

| Aspecto | Evaluación |
|---------|------------|
| Complejidad | ⭐⭐⭐⭐ Alta |
| Rendimiento | ⭐⭐⭐⭐⭐ Máximo |
| Integración | ⭐⭐⭐ Requiere gRPC client en Python |
| Mantenibilidad | ⭐⭐ Requiere expertise en Rust |

**Herramientas:**
- [Tonic](https://github.com/hyperium/tonic): gRPC nativo para Rust
- HTTP/2 multiplexing, streaming, TLS

### Opción C: Híbrido Progresivo (Recomendada)

**Fase 1:** PyO3 modules para operaciones críticas
**Fase 2:** Evaluar migración a Rust puro si PyO3 no es suficiente

---

## 2. Bibliotecas Rust para Procesamiento de Documentos

### 2.1 PDF Parsing

| Biblioteca | Propósito | Performance | Estado |
|------------|-----------|-------------|--------|
| [PDF Oxide](https://github.com/yfedoseev/pdf_oxide) | Parsing + conversión | **47.9x más rápido que PyMuPDF4LLM** | Production Ready (2025) |
| [lopdf](https://github.com/J-F-Liu/lopdf) | Manipulación low-level | Muy rápido, <2ms para 1000 objetos | Stable (v0.39.0) |
| [pdf-extract](https://lib.rs/crates/pdf-extract) | Extracción de texto | Rápido | Stable |
| [pdf-rs](https://github.com/pdf-rs/pdf) | Lectura/escritura | Moderado | Active |

#### PDF Oxide Benchmarks (2025)

```
Test: 103 PDFs
├── PDF Oxide:      5.43 segundos (53ms promedio)
├── PyMuPDF4LLM:    259.94 segundos
└── Speedup:        47.9x más rápido

Precisión:
├── Texto:          100% exactitud
├── Bold detection: 37% más preciso que PyMuPDF
└── Output size:    4% más pequeño
```

### 2.2 OCR Libraries

| Biblioteca | Propósito | Notas |
|------------|-----------|-------|
| [leptess](https://github.com/houqp/leptess) | Tesseract bindings | Safe Rust wrapper, soporta región específica |
| [tesseract-rs](https://crates.io/crates/tesseract-rs) | Tesseract con compilación incluida | Descarga automática de training data |

**Dependencias del sistema:**
```bash
# Ubuntu
sudo apt-get install libleptonica-dev libtesseract-dev clang
sudo apt-get install tesseract-ocr-spa tesseract-ocr-eng
```

### 2.3 Image Processing

| Biblioteca | Propósito |
|------------|-----------|
| [image](https://crates.io/crates/image) | Manipulación de imágenes |
| [imageproc](https://crates.io/crates/imageproc) | Procesamiento avanzado |

---

## 3. Arquitectura Propuesta

### 3.1 Opción A: PyO3 Modules

```
plugins/public/file-manager/
├── src/
│   ├── services/
│   │   ├── extraction.py          # Llama a Rust module
│   │   └── thumbnail.py           # Llama a Rust module
│   └── ...
├── rust_modules/
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs
│   │   ├── pdf_extractor.rs       # PDF Oxide wrapper
│   │   ├── ocr_processor.rs       # leptess wrapper
│   │   └── thumbnail_gen.rs       # image crate
│   └── pyproject.toml             # maturin config
```

**Cargo.toml:**
```toml
[package]
name = "document_processing_rs"
version = "0.1.0"
edition = "2024"

[lib]
name = "document_processing_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.27", features = ["extension-module"] }
pdf_oxide = "0.2"
leptess = "0.8"
image = "0.25"
rayon = "1.10"  # Paralelismo
```

**Ejemplo lib.rs:**
```rust
use pyo3::prelude::*;
use pdf_oxide::PdfDocument;

#[pyfunction]
fn extract_text_fast(pdf_bytes: &[u8]) -> PyResult<String> {
    let doc = PdfDocument::from_bytes(pdf_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let text = doc.extract_text()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok(text)
}

#[pyfunction]
fn extract_text_parallel(pdf_paths: Vec<String>) -> PyResult<Vec<String>> {
    use rayon::prelude::*;

    let results: Vec<_> = pdf_paths
        .par_iter()  // Parallel iteration
        .map(|path| {
            // Process each PDF in parallel
            let bytes = std::fs::read(path).ok()?;
            let doc = PdfDocument::from_bytes(&bytes).ok()?;
            doc.extract_text().ok()
        })
        .collect();

    Ok(results.into_iter().flatten().collect())
}

#[pymodule]
fn document_processing_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(extract_text_fast, m)?)?;
    m.add_function(wrap_pyfunction!(extract_text_parallel, m)?)?;
    Ok(())
}
```

### 3.2 Opción B: Full Rust gRPC

```
services/document-processor-rs/
├── Cargo.toml
├── build.rs
├── proto/
│   └── document_processor.proto
├── src/
│   ├── main.rs
│   ├── server.rs
│   ├── services/
│   │   ├── mod.rs
│   │   ├── pdf_extractor.rs
│   │   ├── ocr_processor.rs
│   │   └── thumbnail_gen.rs
│   └── grpc/
│       └── generated/
└── Dockerfile
```

**Proto para Rust service:**
```protobuf
syntax = "proto3";
package document_processor;

service DocumentProcessor {
    rpc ExtractText(ExtractRequest) returns (ExtractResponse);
    rpc ExtractTextStream(ExtractRequest) returns (stream PageContent);
    rpc GenerateThumbnail(ThumbnailRequest) returns (ThumbnailResponse);
    rpc ProcessBatch(stream ExtractRequest) returns (stream ExtractResponse);
}
```

---

## 4. Comparación de Rendimiento Esperado

### 4.1 PDF Text Extraction

| Método | Tiempo (100 PDFs) | Speedup |
|--------|-------------------|---------|
| PyMuPDF (Python) | ~260s | 1x |
| pypdf (Python) | ~180s | 1.4x |
| PDF Oxide (Rust) | ~5.4s | **47.9x** |
| PDF Oxide + PyO3 | ~6s | **43x** |

### 4.2 OCR Processing

| Método | Tiempo (100 images) | Notas |
|--------|---------------------|-------|
| pytesseract (Python) | ~120s | Subprocess overhead |
| leptess (Rust) | ~40s | Direct bindings |
| leptess + rayon | ~12s | Parallel processing |

### 4.3 Memory Usage

| Método | Peak Memory | Notas |
|--------|-------------|-------|
| PyMuPDF | ~2GB | Large PDFs |
| PDF Oxide | ~500MB | Streaming parsing |
| Rust + mmap | ~100MB | Memory-mapped files |

---

## 5. Pros y Contras

### PyO3 Modules (Opción A)

**Pros:**
- ✅ Integración transparente con Python existente
- ✅ Menor curva de aprendizaje
- ✅ Reutiliza infraestructura Python (FastAPI, Redis)
- ✅ Deploy como wheel pip-installable
- ✅ Sin overhead de red (mismo proceso)

**Contras:**
- ❌ Aún requiere Python runtime
- ❌ GIL limitations para algunos casos
- ❌ Más complejo que Python puro

### Full Rust gRPC (Opción B)

**Pros:**
- ✅ Máximo rendimiento posible
- ✅ Mínimo memory footprint
- ✅ Sin Python dependencies
- ✅ Horizontal scaling independiente

**Contras:**
- ❌ Overhead de red (gRPC calls)
- ❌ Mayor complejidad de deployment
- ❌ Requiere expertise en Rust
- ❌ Duplicación de lógica (Rust + Python)

---

## 6. Recomendación

### Fase 1: PyO3 Quick Wins (1-2 semanas)

Implementar módulos Rust para:
1. **PDF text extraction** con PDF Oxide → 47x speedup
2. **Parallel OCR** con leptess + rayon → 3x speedup
3. **Thumbnail generation** con image crate → 5x speedup

**ROI esperado:** 80% del beneficio con 20% del esfuerzo.

### Fase 2: Evaluar Full Rust (Si necesario)

Si PyO3 modules no son suficientes:
- Migrar a full Rust gRPC service
- Mantener Python wrapper para compatibilidad

### Fase 3: Optimizaciones Adicionales

- Memory-mapped file processing
- SIMD optimizations
- GPU acceleration (wgpu)

---

## 7. Dependencias y Setup

### 7.1 Rust Toolchain

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install maturin
pip install maturin

# System dependencies (Ubuntu)
sudo apt-get install \
    libleptonica-dev \
    libtesseract-dev \
    clang \
    tesseract-ocr-spa \
    tesseract-ocr-eng
```

### 7.2 Docker Integration

```dockerfile
# Multi-stage build for Rust module
FROM rust:1.85 as rust-builder
WORKDIR /app
COPY rust_modules/ .
RUN cargo build --release

FROM python:3.11-slim
# Install Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libleptonica-dev

# Copy Rust module
COPY --from=rust-builder /app/target/release/*.so /app/

# Install Python deps
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## 8. Referencias

### PyO3 y Maturin
- [PyO3 GitHub](https://github.com/PyO3/pyo3)
- [Maturin GitHub](https://github.com/PyO3/maturin)
- [PyO3 User Guide](https://pyo3.rs/)
- [Building Python Extensions with Rust](https://medium.com/@sanjeev-bhandari/supercharge-python-with-rust-building-fast-python-extensions-with-pyo3-and-maturin-da09306d97a8)

### PDF Libraries
- [PDF Oxide](https://github.com/yfedoseev/pdf_oxide) - **47.9x faster than PyMuPDF4LLM**
- [lopdf](https://github.com/J-F-Liu/lopdf)
- [pdf-extract](https://lib.rs/crates/pdf-extract)

### OCR Libraries
- [leptess](https://github.com/houqp/leptess)
- [tesseract-rs](https://crates.io/crates/tesseract-rs)

### gRPC
- [Tonic](https://github.com/hyperium/tonic)
- [gRPC Basics for Rust](https://dockyard.com/blog/2025/04/08/grpc-basics-for-rust-developers)

### Performance Research
- [PyO3 Academic Paper (2025)](https://link.springer.com/chapter/10.1007/978-3-031-85902-1_4)
- [Python Developers Turning to Rust with PyO3](https://medium.com/@muruganantham52524/why-python-developers-are-turning-to-rust-with-pyo3-for-faster-ai-and-data-science-in-2025-cd5991973a4d)
