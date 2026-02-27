# Plan: Demo "Full Cycle Engineer" — Preparación del Repositorio

## Contexto

El repositorio `Fin_tech_anomaly_detection` (rama `feature/ia-demo`) es un sistema de detección de fraude bancario ya construido: Clean Architecture, 16 user stories, 244+ tests, 2 frontends. Se usa como punto de partida real para una charla de 60 minutos.

**Flujo acordado del demo:**
1. **Exploración** → Claude Code lee el repo y presenta las capacidades al presentador
2. **Requerimiento vago** → Claude Code hace preguntas, resuelve ambigüedades, genera criterios de aceptación claros
3. **Implementación** → Claude Code trabaja solo; mientras tanto los presentadores conversan con la audiencia
4. **Hook sonoro** → cuando Claude Code termina un turno y necesita input, suena una alerta

Los momentos de espera se convierten en contenido: la audiencia ve que el ingeniero dirige, valida y decide — no escribe desde cero.

---

## Qué construir

### 1. Hook de alerta sonora (`.claude/settings.json`)

Añadir al settings del proyecto el hook `Stop` que toca un sonido cuando Claude Code termina un turno y espera input del presentador.

**Archivo**: `.claude/settings.json` (ya existe)

**Cambio**:
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "paplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null || aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || echo -e '\\a'"
          }
        ]
      }
    ]
  }
}
```

El comando tiene fallbacks: `paplay` (PulseAudio/Linux) → `aplay` → beep de terminal. Funciona sin instalar nada extra.

---

### 2. Prompt de Exploración (`demo/prompts/01-exploracion.md`)

Prompt para el Momento #3 (10–13 min). El presentador lo pega en Claude Code y la IA empieza a explorar. **Mientras Claude trabaja, el presentador conversa con la audiencia sobre el nuevo ciclo de desarrollo.**

```
Eres un ingeniero Full Cycle que acaba de recibir este repositorio.
Tu tarea es explorar el código y presentar en español:

1. ¿Qué problema resuelve este sistema? (contexto de negocio)
2. ¿Qué capacidades tiene actualmente? (listado funcional)
3. ¿Qué tecnologías y patrones usa? (stack y arquitectura)
4. ¿Qué tan probado está? (cobertura y estrategia de tests)
5. ¿Qué oportunidades de mejora identificas?

Presenta el resultado de forma clara, como si lo explicaras a una audiencia mixta
de técnicos y tomadores de decisión en un banco.
```

---

### 3. Requerimiento Vago (`demo/prompts/02-requerimiento.md`)

Prompt para el Momento #5 (20–25 min). Simula un brief de negocio incompleto. Claude Code debe **hacer preguntas de clarificación** y luego generar criterios de aceptación concretos.

```
Tenemos un requerimiento nuevo del área de riesgo:

"Necesitamos mejorar la detección de fraude para transacciones internacionales.
Los clientes están reportando cargos sospechosos desde otros países."

Antes de implementar, necesito que:
1. Identifiques qué información falta o es ambigua en este requerimiento
2. Hagas las preguntas necesarias para poder implementar esto correctamente
3. Una vez respondidas las preguntas, generes criterios de aceptación claros
   en formato Given/When/Then
4. Propongas cómo encajaría esto en la arquitectura existente del repo
```

*El presentador responde las preguntas de Claude en vivo — eso ES la demo.*

**Respuestas preparadas** (para que el presentador sepa qué decir):
- "Internacional" = país de la tarjeta distinto al país de la transacción
- Riesgo: HIGH_RISK si el usuario nunca ha operado en ese país, MEDIUM_RISK si es un país nuevo pero el monto es bajo
- Umbral: primer uso en país nuevo → MEDIUM, segundo uso en 24h en país nuevo → HIGH
- El país viene en el campo `metadata.country_code` (ISO 3166-1 alpha-2)

---

### 4. Prompt de Implementación (`demo/prompts/03-implementacion.md`)

Prompt para el Momento #7 (32–40 min). Se usa después de que se aprobaron los criterios de aceptación. Claude Code implementa TDD.

```
Con base en los criterios de aceptación que generamos, implementa la nueva
estrategia de fraude para transacciones internacionales siguiendo el patrón
TDD del proyecto:

1. Primero escribe los tests (archivo: tests/unit/test_international_strategy.py)
   - Sigue el patrón de tests existentes en tests/unit/test_fraud_strategies.py
2. Corre los tests para confirmar que fallan (RED)
3. Implementa la estrategia en services/fraud-evaluation-service/src/domain/strategies/
   - Extiende FraudStrategy ABC
   - Nombre de clase: InternationalTransactionStrategy
4. Corre los tests para confirmar que pasan (GREEN)
5. Registra la estrategia en el factory (services/fraud-evaluation-service/src/adapters.py)
6. Muestra el resultado final y el coverage actualizado
```

---

### 5. Prompt de Deploy (`demo/prompts/04-deploy.md`)

Prompt para el Momento #9 (47–52 min).

```
La nueva estrategia está implementada y los tests pasan.
Ahora cierra el ciclo:

1. Muestra el archivo .github/workflows/ci.yml y explica qué valida el pipeline
2. Ejecuta docker-compose build para reconstruir la imagen con el nuevo código
3. Levanta el stack completo con docker-compose up -d
4. Envía una transacción de prueba al endpoint POST /transaction usando curl,
   donde country_code sea diferente al historial del usuario
5. Muestra el resultado de la evaluación en el audit trail
```

---

### 6. Guía del Presentador (`demo/DEMO-RUNBOOK.md`)

Guía minuto a minuto con timestamps, comandos exactos y plan B.

**Estructura**:
```
## Pre-charla (15 min antes)
- [ ] docker-compose up mongodb redis rabbitmq -d
- [ ] Verificar http://localhost:8000/health
- [ ] Abrir Claude Code en el repo: claude
- [ ] Tener demo/prompts/ abierto en otra ventana
- [ ] Probar el hook sonoro

## Timeline
| Tiempo | Tipo         | Acción                                      |
|--------|--------------|---------------------------------------------|
| 0-10   | Conversación | Gancho + definición Full Cycle Engineer     |
| 10-13  | LIVE CODING  | Pegar Prompt #1 → exploración               |
| 13-20  | Conversación | (Claude trabaja) Nuevo ciclo de desarrollo  |
| [RING] | ATENDER      | Claude terminó → mostrar resultados         |
| 20-25  | LIVE CODING  | Pegar Prompt #2 → requerimiento vago        |
| 25-32  | Conversación | (Claude pregunta) Valor para el negocio     |
| [RING] | ATENDER      | Responder preguntas de Claude en vivo       |
| 32-40  | LIVE CODING  | Pegar Prompt #3 → implementación TDD        |
| 40-47  | Conversación | (Claude implementa) Hoja de ruta adopción   |
| [RING] | ATENDER      | Claude necesita confirmación                |
| 47-52  | LIVE CODING  | Pegar Prompt #4 → deploy                    |
| 52-60  | Cierre       | Reflexión + Q&A                             |

## Plan B
- Si Claude Code falla: abrir rama `feature/ia-demo` y mostrar código ya hecho
- Si Docker falla: mostrar tests locales: pytest tests/unit/ -v
- Si la red falla: usar mock de respuesta pre-grabada
```

---

## Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `.claude/settings.json` | Modificar | Agregar hook `Stop` con alerta sonora |
| `demo/prompts/01-exploracion.md` | Crear | Prompt de exploración del repo |
| `demo/prompts/02-requerimiento.md` | Crear | Prompt con requerimiento vago + respuestas preparadas |
| `demo/prompts/03-implementacion.md` | Crear | Prompt de implementación TDD |
| `demo/prompts/04-deploy.md` | Crear | Prompt de cierre del ciclo |
| `demo/DEMO-RUNBOOK.md` | Crear | Guía minuto a minuto para el presentador |

---

## Lo que NO se construye (fuera del alcance)

- **Streamlit app**: El demo muestra Claude Code CLI directamente. Una Streamlit añade complejidad sin valor diferencial para este formato.
- **La estrategia `InternationalTransactionStrategy`**: Claude Code la construye en vivo — es el punto de la demo. No se pre-construye.

---

## Verificación end-to-end

1. Abrir Claude Code en el repo: `claude`
2. Pegar Prompt #1 → Claude explora y responde
3. Al terminar → suena el hook (probar con `paplay` directo)
4. Pegar Prompt #2 → Claude hace preguntas de clarificación
5. Responder las preguntas preparadas → Claude genera criterios Given/When/Then
6. Pegar Prompt #3 → Claude escribe tests, los corre, implementa, pasan
7. `pytest tests/unit/ -v` muestra la nueva suite integrada al proyecto
8. Pegar Prompt #4 → Claude cierra el ciclo con docker y curl
