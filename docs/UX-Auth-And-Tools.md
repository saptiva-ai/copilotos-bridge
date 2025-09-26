# UX Auth And Tools

## Errores de autenticación

| Código backend       | Mensaje en UI                                      | Contexto sugerido                     |
|----------------------|-----------------------------------------------------|----------------------------------------|
| `USER_EXISTS`        | Ya existe una cuenta con ese correo.                | Registro de nuevos usuarios.          |
| `USERNAME_EXISTS`    | Ya existe un usuario con ese nombre.                | Registro de nuevos usuarios.          |
| `WEAK_PASSWORD`      | Tu contraseña es demasiado débil (mínimo 8, 1 mayús, 1 número). | Registro / cambio de contraseña. |
| `BAD_CREDENTIALS`    | Correo o contraseña incorrectos.                    | Inicio de sesión.                     |
| `ACCOUNT_INACTIVE`   | Tu cuenta está inactiva. Contacta al administrador. | Inicio de sesión / refresh token.     |
| `INVALID_TOKEN`      | La sesión expiró. Inicia sesión nuevamente.         | Refresh token / peticiones autenticadas. |

Los errores con campo (`field`) se muestran inline sobre el input correspondiente. El resto aparece como alerta global sobre el formulario.

## Feature flags disponibles

Los flags se definen vía variables de entorno (`.env.local`, despliegues) y controlan visibilidad y comportamiento de herramientas:

```env
NEXT_PUBLIC_FEATURE_WEB_SEARCH=true
NEXT_PUBLIC_FEATURE_DEEP_RESEARCH=true
NEXT_PUBLIC_FEATURE_ADD_FILES=false
NEXT_PUBLIC_FEATURE_GOOGLE_DRIVE=false
NEXT_PUBLIC_FEATURE_CANVAS=false
NEXT_PUBLIC_FEATURE_AGENT_MODE=false
NEXT_PUBLIC_FEATURE_MIC=false
```

- Solo `Web Search` y `Deep Research` están habilitados por defecto.
- `Deep Research` aparece desactivado (estado OFF) hasta que el usuario lo enciende explícitamente en la barra de comandos.
- Al desactivar un flag la herramienta se oculta del menú y de la UI (sin eliminar el código subyacente).

## Cómo añadir nuevas tools detrás de flags

1. Definir un nuevo flag público en `.env` (`NEXT_PUBLIC_FEATURE_<NOMBRE>`).
2. Añadir el flag al objeto `featureFlags` y `visibleTools` en `src/lib/feature-flags.ts`.
3. Registrar la tool en `TOOL_REGISTRY` (si no existe) y su entrada en `ChatComposer` / `ToolMenu`.
4. Utilizar `visibleTools[toolId]` para condicionar la visibilidad en la UI.

Con este flujo la tool queda protegida por feature flag y puede activarse sin más cambios en el código.
