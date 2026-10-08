"""Claude + Gemini: Claude conversa y decide cuándo crear imágenes; Gemini las genera.

Requisitos:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="sk-ant-..."
    export GEMINI_API_KEY="AIza..."

Uso:
    python gemini.py "Créame una imagen de un kiosko hexagonal en Bogotá"
"""

import os
import sys
from datetime import datetime

import anthropic
from google import genai

CLAUDE_MODEL = "claude-opus-5-5"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"

# Las llaves se leen de variables de entorno: nunca las escribas en el código.
claude = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY
gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def crear_imagen_con_gemini(prompt_visual: str) -> str:
    print(f"🎨 Claude pidió crear: {prompt_visual}")
    response = gemini.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=prompt_visual,
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            nombre = f"imagen_{datetime.now():%Y%m%d_%H%M%S}.png"
            with open(nombre, "wb") as f:
                f.write(part.inline_data.data)
            return f"Imagen guardada como {nombre}"
    texto = response.text or "sin detalles"
    return f"Gemini no devolvió ninguna imagen: {texto}"


# Herramienta que Claude puede usar
tools = [
    {
        "name": "crear_imagen",
        "description": "Crea una imagen a partir de una descripción detallada. Úsala cuando el usuario pida dibujar, diseñar o visualizar algo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt_visual": {
                    "type": "string",
                    "description": "Prompt detallado en inglés para generar la imagen: sujeto, estilo, iluminación, encuadre, etc.",
                }
            },
            "required": ["prompt_visual"],
        },
    }
]


def conversar(mensaje_usuario: str) -> str:
    messages = [{"role": "user", "content": mensaje_usuario}]
    while True:
        response = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        # Claude pidió usar la herramienta: la ejecutamos y le devolvemos el resultado
        messages.append({"role": "assistant", "content": response.content})
        resultados = []
        for block in response.content:
            if block.type == "tool_use" and block.name == "crear_imagen":
                try:
                    resultado = crear_imagen_con_gemini(block.input["prompt_visual"])
                    resultados.append({"type": "tool_result", "tool_use_id": block.id, "content": resultado})
                except Exception as e:
                    resultados.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True})
        messages.append({"role": "user", "content": resultados})


if __name__ == "__main__":
    mensaje = " ".join(sys.argv[1:]) or (
        "Créame una imagen de un kiosko hexagonal con techo de teja española color terracota en Bogotá"
    )
    print(conversar(mensaje))
