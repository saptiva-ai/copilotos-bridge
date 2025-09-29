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

