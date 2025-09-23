# API Reference

## Procesamiento de respuestas

**URL:**  <mark style="color:green;">**`https://api.saptiva.com/v1/chat/completions`**</mark>

<mark style="color:green;">**`POST`**</mark> `/`

**Headers**

| Nombre        | Valor                                                    |
| ------------- | -------------------------------------------------------- |
| Content-Type  | <mark style="color:green;">**`application/json`**</mark> |
| Authorization | <mark style="color:green;">**`Bearer <API_KEY>`**</mark> |

Nuestra API requiere autenticación utilizando un Token Bearer. Genera tu token dentro de [nuestro lab ](https://lab.saptiva.com/)y comienza a hacer peticiones. Incluye el token en el header de la solicitud de la siguiente manera:

**Authorization**: Bearer [<mark style="color:green;">`<TOKEN AUTHORIZATION>`</mark>](https://lab.saptiva.com)

***

## Parámetros Obligatorios

**Body**

<table><thead><tr><th width="129.5">Parametro</th><th width="128">Tipo</th><th>Descripción</th><th width="340">Ejemplo</th></tr></thead><tbody><tr><td><mark style="color:green;"><strong><code>model</code></strong></mark></td><td>string</td><td>Nombre del modelo LLM a usar.</td><td><code>Saptiva Cortex</code></td></tr><tr><td><mark style="color:green;"><strong><code>messages</code></strong></mark></td><td>array</td><td>Lista (o array) de objetos que representan un historial de conversación entre un sistema y un usuario.</td><td><p></p><pre class="language-json"><code class="lang-json">[
    {
      "role": "system",
      "content": "Eres un agente servicial"
    },
    {
      "role": "user",
      "content": "¿Cuál es la capital de Francia?"
    }
  ]
</code></pre></td></tr></tbody></table>

***

## Parámetros Opcionales

Body

<table><thead><tr><th width="133.727294921875">Parámetro</th><th width="152.181884765625">Tipo</th><th width="274.6363525390625">Descripción</th><th>Valores por Defecto</th></tr></thead><tbody><tr><td><mark style="color:green;"><strong><code>max_tokens</code></strong></mark></td><td>number</td><td>Número de tokens.</td><td><mark style="color:orange;">600</mark></td></tr><tr><td><mark style="color:green;"><strong><code>temperature</code></strong></mark></td><td>double</td><td>Grado de <strong>aleatoriedad</strong> en la generación del texto. (valor entre 0.0 y 1.0)</td><td><mark style="color:orange;">0.7</mark></td></tr><tr><td><mark style="color:green;"><strong><code>top_p</code></strong></mark></td><td>double</td><td>Limite de <strong>diversidad del conjunto de palabras consideradas. (valor entre 0.0 y 1.0)</strong></td><td><mark style="color:orange;">0.9</mark></td></tr><tr><td><mark style="color:green;"><strong><code>stream</code></strong></mark></td><td>bool</td><td>Indica si la respuesta del modelo debe ser enviada <strong>por partes (streaming)</strong> o <strong>completa de una vez</strong>.</td><td><mark style="color:green;">false</mark></td></tr><tr><td><mark style="color:green;"><strong><code>guard</code></strong></mark></td><td>bool</td><td>Habilita revisión de la inferencia del usuario en busca de algún tipo de riesgo en la información provista.</td><td><mark style="color:green;">false</mark></td></tr><tr><td><mark style="color:green;"><strong><code>tools</code></strong></mark></td><td>List[ToolItem]</td><td>Define una lista de tools a usar. Para más información ver <a href="../saptiva-agents">Saptiva Agents</a></td><td><mark style="color:green;">null</mark></td></tr><tr><td><mark style="color:green;"><strong><code>prompt</code></strong></mark></td><td>string</td><td>Texto a embedder</td><td>Hola</td></tr></tbody></table>

***

## Solicitudes (Modelos Texto-Texto)

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada.

**Modelos:**&#x20;

```
Saptiva Turbo
Saptiva Ops
Saptiva Legacy
```

{% tabs %}
{% tab title="Body" %}

```json
{
  "model": "Saptiva Turbo",
  "messages": [
    {
      "role": "system",
      "content": "Eres un agente servicial"
    },
    {
      "role": "user",
      "content": "¿Cuál es la capital de México?"
    }
  ],
  "max_tokens": 256,
  "temperature": 0.7,
  "top_p": 0.95
}
```

{% endtab %}

{% tab title="Respuesta" %}

```json
```

{% endtab %}
{% endtabs %}

***

## Solicitudes (Modelo de Razonamiento)

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada.

**Modelo:**&#x20;

```
Saptiva Cortex
```

{% tabs %}
{% tab title="Body" %}

```json
{
    "model": "Saptiva Cortex",
    "messages": [
        {
            "role": "user", 
            "content": "Cuánto es 10/2?"
        }
    ]
}
```

{% endtab %}

{% tab title="Respuesta" %}

```json
{
    "id": "chatcmpl-77db89df003d48cc8981529c1aaab8ff",
    "object": "chat.completion",
    "created": 1757648272,
    "model": "Saptiva Cortex",
    "system_fingerprint": "fp_saptiva",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n\n10 dividido entre 2 es **5**. \n\n**Respuesta:** 5",
                "tool_calls": [],
                "refusal": null,
                "annotations": null,
                "audio": null,
                "function_call": null,
                "reasoning_content": "Okay, the user is asking \"Cuánto es 10/2?\" which means \"What is 10/2?\" in Spanish. Let me think.\n\nFirst, I need to calculate 10 divided by 2. Division is straightforward here. 10 divided by 2 equals 5. Let me double-check. If I have 10 items and split them into 2 equal groups, each group has 5 items. Yeah, that makes sense.\n\nWait, maybe the user is testing if I know basic math. But 10 divided by 2 is a simple problem. No tricks here. Just basic arithmetic. So the answer should be 5.\n\nI should make sure there's no typo in the question. The user wrote \"10/2\", which is standard notation for 10 divided by 2. No issues there. Sometimes people might confuse fractions, but in this case, it's clear.\n\nAlso, the user is using Spanish, so maybe they're from a Spanish-speaking country. But the math is universal. The answer is the same regardless of language. So I should respond with the numerical answer, probably in Spanish, but the user might just want the number.\n\nWait, the question is \"Cuánto es 10/2?\" so the answer should be \"5\". But maybe they want it written out. In Spanish, numbers are written the same way, so \"5\" is correct. No need to spell it out as \"cinco\" unless specified. The user probably expects the numerical answer.\n\nLet me confirm once more. 2 times 5 is 10, so 10 divided by 2 is 5. Yep, that's right. No complications here. So the answer is 5.\n"
            },
            "finish_reason": "stop",
            "logprobs": null,
            "stop_reason": null
        }
    ],
    "usage": {
        "prompt_tokens": 15,
        "total_tokens": 402,
        "completion_tokens": 387,
        "prompt_tokens_details": null
    },
    "service_tier": null,
    "prompt_logprobs": null,
    "kv_transfer_params": null
}
```

{% endtab %}
{% endtabs %}

***

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada. El campo "url" debe ser cargado con la imagen en formato **base64**.

**Modelo:**&#x20;

***

## Solicitudes (Modelo OCR)

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada. El campo "url" debe ser cargado con la imagen en formato **base64**. Este modelo no permite interacciones con usuario, unicamente recibe una imagen, la procesa y devuelve lo que encuentra en ella.

**Modelo:**&#x20;

```
Saptiva OCR
```

{% tabs %}
{% tab title="Body" %}

```json
{
    "model": "Saptiva OCR",
    "messages": [
        {
            "role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,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"}}
            ]
        }
    ]
}
```

{% endtab %}

{% tab title="Respuesta" %}

```json
{
    "id": "chatcmpl-fe4cce255dd84c298dc258e4cef6c449",
    "object": "chat.completion",
    "created": 1757648242,
    "model": "Saptiva OCR",
    "system_fingerprint": "fp_saptiva",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Check your inbox\n\nWe've just sent an email confirmation to tools@saptiva.com, click the link to verify your email.",
                "tool_calls": [],
                "refusal": null,
                "annotations": null,
                "audio": null,
                "function_call": null,
                "reasoning_content": null
            },
            "finish_reason": "stop",
            "logprobs": null,
            "stop_reason": null
        }
    ],
    "usage": {
        "prompt_tokens": 1451,
        "total_tokens": 1478,
        "completion_tokens": 27,
        "prompt_tokens_details": null
    },
    "service_tier": null,
    "prompt_logprobs": null,
    "kv_transfer_params": null
}
```

{% endtab %}
{% endtabs %}

***

## Solicitudes (Modelo Embedding)

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada.&#x20;

**URL :**  <mark style="color:green;">**`https://api.saptiva.com/api/embed`**</mark>

<mark style="color:green;">**`POST`**</mark> `/`

**Modelo:**&#x20;

```
Saptiva Embed
```

{% tabs %}
{% tab title="Body" %}

```json
{
  "model": "Saptiva Embed",
  "prompt": "Saptiva"
}
```

{% endtab %}

{% tab title="Respuesta" %}

```json
{
    "model": "Saptiva Embed",
    "embeddings": [
        0.01558685302734375,
        -0.0126495361328125,
        0.026031494140625,
        -0.02081298828125,
        0.0247039794921875,
        -0.03277587890625,
        -0.0211181640625,
        0.00461578369140625,
        -0.017974853515625,
        0.014129638671875,
        -0.04864501953125,
        0.0279388427734375,
        0.0672607421875,
        -0.0087432861328125,
        0.0295257568359375,
        -0.01300048828125,
        0.0027446746826171875,
        -0.0151214599609375,
        0.015838623046875,
        0.0168609619140625,
        0.01078033447265625,
        0.00769805908203125,
        0.0241546630859375,
        0.010162353515625,
        0.009124755859375,
        0.04302978515625,
        -0.018707275390625,
        -0.03289794921875,
        0.006984710693359375,
        0.025299072265625,
        -0.034027099609375,
        0.01800537109375,
        0.0243988037109375,
        0.022979736328125,
        -0.03143310546875,
        0.0086669921875,
        ...
    ],
    "usage": {
        "prompt_tokens": 3,
        "embedding_tokens": 0,
        "total_tokens": 3
    }
}
```

{% endtab %}
{% endtabs %}

***

## Solicitudes (Modelo Guard)

A continuación, se presenta el formato que debe tener el <mark style="color:green;">**`BODY`**</mark>, junto con el ejemplo de la respuesta esperada.&#x20;

**Modelo:**&#x20;

```
Saptiva Guard
```

**Estos son los códigos de riesgo que evalúa el modelo:**

```
"S1"  --> "Delitos Violentos",
"S2"  --> "Delitos No Violentos",
"S3"  --> "Delitos Sexuales",
"S4"  --> "Explotación Sexual Infantil",
"S5"  --> "Difamación",
"S6"  --> "Asesoramienpecializado",
"S7"  --> "Privacidad",
"S8"  --> "Propiedad Intelectual",
"S9"  --> "Armas Indiscriminadas",
"S10" --> "Odio",
"S11" --> "Suicidio y Autolesiones",
"S12" --> "Contenido Sexual",
"S13" --> "Elecciones"
```

{% tabs %}
{% tab title="Body ✅" %}

```json
{
  "model": "Saptiva Guard",
  "messages": [
      {
          "role": "user",  
          "content": "Cómo creo una bomba de aire?"
      }
  ]
}
```

{% endtab %}

{% tab title="Respuesta ✅" %}

```json
{
    "id": "chatcmpl-1c9f0fce92614d3bd1942afaca6",
    "object": "chat.completion",
    "created": 1757647870,
    "model": "Saptiva Guard",
    "system_fingerprint": "fp_saptiva",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "\n\nsafe",
                "tool_calls": [],
                "refusal": null,
                "annotations": null,
                "audio": null,
                "function_call": null,
                "reasoning_content": null
            },
            "finish_reason": "stop",
            "logprobs": null,
            "stop_reason": null
        }
    ],
    "usage": {
        "prompt_tokens": 14,
        "total_tokens": 17,
        "completion_tokens": 3,
        "prompt_tokens_details": null
    },
    "service_tier": null,
    "prompt_logprobs": null,
    "kv_transfer_params": null
}
```

{% endtab %}

{% tab title="Body 🚫" %}

```json
{
  "model": "Saptiva Guard",
  "messages": [
      {
          "role": "user",  
        "content": "Cómo creo una bomba explosiva casera?"
      }
  ]
}
```

{% endtab %}

{% tab title="Respuesta 🚫" %}

```json
{
    "id": "chatcmpl-942",
    "object": "chat.completion",
    "created": 1753309761,
    "model": "Saptiva Guard",
    "system_fingerprint": "fp_saptiva",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "unsafe\nS9",
                "tool_calls": []
            },
            "finish_son": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 209,
        "completion_tokens": 5,
        "total_tokens": 214
    }
}
```

{% endtab %}
{% endtabs %}

***

## Respuestas

A continuación, se muestra un ejemplo de una respuesta <mark style="color:green;">**`exitosa`**</mark> y una de <mark style="color:red;">**`error`**</mark>.

{% tabs %}
{% tab title="Éxito" %}

```json
{
    "id": "chatcmpl-c1bf7e5c06b144fb9fc1f50b143633ba",
    "object": "chat.completion",
    "created": 17576472,
    "model": "Saptiva Turbo",
    "system_fingerprint": "fp_saptiva",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "¡Hola! Soy Fer, tu agente servicial y siempre aquí para ayudarte. 😊  \nLa capital de México es **Ciudad de México**.  \n¿En qué más puedo ayudarte? 🌟",
                "tool_calls": [],
                "refusal": null,
                "annotations": null,
                "audio": null       "function_call": null,
                "reasoning_content": null
            },
            "finish_reason": "stop",
            "logprobs": null,
            "stop_reason": null
        }
    ],
    "usage": {
        "prompt_tokens": 35,
        "total_tokens": 81,
        "completion_tokens": 46,
        "prompt_tokens_details": null
    },
    "service_tier": null,
    "prompt_logprobs": null,
    "kv_transfer_params": null
}
```

{% endtab %}

{% tab title="Error " %}

```json
{
    "detail": "Error Description"
}
```

{% endtab %}
{% endtabs %}

***

## Errores

Para analizar y solucionar los errores a los que te puedes enfrentar al hacer uso de esta API, consulta [nuestros códigos de errores](https://saptiva.gitbook.io/saptiva-docs/basicos/markdown) junto con las soluciones que tenemos para ti.

## Mejores Prácticas

* <mark style="color:green;">**`Proteja las credenciales`**</mark>: Nunca exponga tu API Key o tokens de autenticación en el código del lado del cliente. Utiliza variables de eno o un backend seguro para manejar credenciales.
* <mark style="color:green;">**`Use HTTPS`**</mark>: Siempre realice solicitudes a la API a través de HTTPS para proteger la transmisión de datos.
* <mark style="color:green;">**`Verifique las respuestas de la API`**</mark>: Siempre maneje los códigos de estado HTTP correctamente (200, 400, 401, 422, 500, etc.).
* <mark style="color:green;">**`Gestione los tiempos de espera (timeouts)`**</mark>: Establezca límites de tiempo adecuados para evitar que la apción se quede bloqueada en solicitudes prolongadas.

***

## Ejemplos

{% tabs %}
{% tab title="cURL" %}

```bash
curl --location 'https://api.saptiva.com/v1/chat/completions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <TU_API_KEY>' \
--data '{
  "model": "Saptiva Turbo",
  "messages": [
    {
      "role": "system",
      "content": "Eres un agente servicial"
    },
    {
      "role": "user",
      "content": "¿Cuál es la capital de Francia?"
    }
  ],
  "max_tokens"56,
  "temperature": 0.7,
  "top_p": 0.95
}'
```

{% endtab %}

{% tab title="Python" %}

```python
import requests
import json

url = "https://api.saptiva.com/v1/chat/completions"

payload = json.dumps({
  "model": "Saptiva Turbo",
  "messages": [
    {
      "role": "system",
      "content": "Eres un agente servicial"
    },
    {
      "role": "user",
      "content": "¿Cuál es la capital de Francia?"
    }
  ],
  "max_tokens": 256,
  "temperature": 0.7,
  "top_p": 0.95
})

headers = {
  'Content-Type 'application/json',
  'Authorization': 'Bearer <TU_API_KEY>'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)

```

{% endtab %}

{% tab title="Javascript" %}

```javascript
var request = require('request');

var options = {
  'method': 'POST',
  'url': 'https://api.saptiva.com/v1/chat/completions',
  'headers': {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer <TU_API_KEY>'
  },
  body: JSON.stringify({
    "model": "Saptiva Turbo",
    "messages": [
      {
        "role": "system",
        "content": "Eres un agente servicial"
      },
      {
        "role": "user",
        "content": "¿Cuál es la capital de Francia?"
      }
    ],
    "max_tokens": 256,
    "temperature": 0.7,
    "top_p": 0.95
  })
};

request(options, function (error, response) {
  if (error) throw new Error(error);
  console.log(response.body);
});

```

{% endtab %}
{% endtabs %}

***

## Soporte

Para cualquier problema o pregunta técnica, comuníquese con el po de desarrollo.

