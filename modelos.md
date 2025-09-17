# Modelos Disponibles

La API de **Saptiva** ofrece una amplia variedad de modelos diseñados para satisfacer diferentes necesidades y presupuestos. Además, tienes la posibilidad de personalizar estos modelos para casos de uso específicos, optimizando su desempeño mediante técnicas avanzadas de ajuste y configuración personalizada.

## Descripción general de los modelos

| Nombre               | Modelo Base            | Mejor para                                                 | Caso de Uso                                                         | Precio por M de tokens IN | Precio por M de tokens OUT |
| -------------------- | ---------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------- | -------------------------- |
| `Saptiva Turbo`      | gemma2:27b             | Respuestas rápidas, bajo costo                             | Chats simples, asistentes de alta concurrencia                      | $0.20                     | $0.40                      |
| `Saptiva Cortex`     | qwen3:30b              | Tareas de razonamiento                                     | Agentes con lógica, comprensión profunda                            | $0.15                     | $0.50                      |
| `Saptiva Ops`        | qwen2.5:72b-instruct   | Casos complejos con tools y SDK                            | Agentes autónomos, RAG, websearch                                   | $0.25                     | $0.60                      |
| `Saptiva Legacy`     | llama3.3:70b           | Compatibilidad con herramientas legacy                     | SDK avanzado, pruebas, compatibilidad técnica                       | $0.30                     | $0.60                      |
| `Saptiva Coder`      | deepseek-coder-v2:236b | Programación y codegen                                     | Copilotos técnicos, generación de código                            | $0.18                     | $0.35                      |
| `Saptiva OCR`        | Nanonets-OCR-s:F16     | Extracción inteligente de texto                            | OCR, estructuración de documentos, VLM                              | $0.15                     | $0.5                       |
| `Saptiva Embed`      | qwen3-embedding:8b     | Vectorización semántica                                    | Memoria contextual, búsqueda, RAG (generación embeddings)           | $0.01                     | -                          |
| `Saptiva Guard`      | llama-guard3:8b        | Moderación y cumplimiento                                  | Protección de contenido, validación de incumplimiento legal en LLMs | $0.10                     | $0.15                      |
| `Saptiva Multimodal` | gemma3:27b             | Comprensión multimodal, interpretación de texto e imágenes | Interpretación de documentos, imágenes o textos. Ej. Onboarding.    | .15                       | .3                         |

> **Nota:**
>
> * Para usar cualquiera de estos modelos en una petición, utiliza exactamente el valor indicado en la columna **Nombre**.
> * La columna "Precio por M de tokens IN" se refiere al costo por cada millón de tokens que envías al modelo.
> * La columna "Precio por M de tokens OUT" corresponde al costo por cada millón de tokens que el modelo genera como respuesta.

***

### Explicación de los campos

A continuación, encontrarás una descripción breve de los principales términos utilizados en esta tabla:

* **Modelo Base**: Es el modelo fundacional sobre el que está construido cada modelo específico de **Saptiva**. Indica su arquitectura y tamaño (cantidad aproximada de parámetros), afectando directamente su capacidad y rendimiento.
* **Mejor para (Best for)**: Indica cuál es la fortaleza principal del modelo, es decir, el tipo de tarea o función para la cual fue especialmente diseñado y optimizado.
* **Caso de Uso (Use Case)**: Ejemplifica claramente los contextos y situaciones concretas en los que el modelo muestra el mejor desempeño y utilidad.




