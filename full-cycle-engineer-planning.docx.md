**PLANNING DOCUMENT**

Charla Interna

**Full Cycle Engineer**

El ingeniero transversal potenciado con Inteligencia Artificial

# **1\. Contexto y Propósito**

Este documento consolida las definiciones, decisiones y estructura acordadas para la charla interna sobre el perfil Full Cycle Engineer. Sirve como referencia para el equipo organizador y los presentadores.

## **¿Qué es el Full Cycle Engineer?**

Un profesional transversal a todo el ciclo de vida del desarrollo de software, que apoyado en herramientas de Inteligencia Artificial es capaz de participar activamente en cada etapa del proceso: desde el entendimiento del requerimiento hasta el deploy y la operación. No es un generalista superficial, sino un ingeniero empoderado que usa la IA como palanca para ampliar su radio de acción y velocidad de entrega.

## **Propósito de la Charla**

* Presentar el concepto de Full Cycle Engineer como una apuesta estratégica de la empresa.

* Demostrar en vivo cómo la IA transforma el proceso de desarrollo en cada etapa del ciclo.

* Generar confianza en la audiencia: tenemos la estrategia y el camino está definido.

* Inspirar adopción real, no solo conocimiento teórico.

# **2\. Definiciones de la Sesión**

| Duración total | 60 minutos |
| :---- | :---- |
| **Formato** | Híbrido: conversación \+ live coding intercalados (NO momento A / momento B) |
| **Herramienta principal** | Claude Code (CLI) |
| **Tono deseado** | Confianza — ya tenemos la estrategia, acá está el camino |
| **Caso de uso demo** | Microservicio de validación de transacciones sospechosas (contexto bancario) |

# **3\. Audiencia**

La sesión está diseñada para una audiencia mixta, lo que implica que las explicaciones deben ser accesibles sin sacrificar profundidad técnica. Se espera la presencia de:

| Perfiles Técnicos | Líderes Técnicos | Negocio / Decisores |
| ----- | ----- | ----- |
| Desarrolladores e ingenieros de software | Arquitectos y tech leads | PMs, perfiles admin. y tomadores de decisiones |
| *Familiaridad: uso esporádico de IA* | *Familiaridad: uso esporádico de IA* | *Familiaridad: baja exposición técnica* |

# **4\. Caso de Uso: Hilo Conductor de la Demo**

**Microservicio de validación de transacciones sospechosas**

Un sistema que recibe transacciones bancarias, las evalúa contra reglas de negocio (monto, frecuencia, país de origen) y expone un endpoint REST con resultado de riesgo.

**¿Por qué este caso?**

* Familiar para todos los perfiles presentes en una audiencia bancaria.

* Tiene una historia de negocio clara, sin necesidad de contexto técnico previo.

* Permite recorrer naturalmente todas las etapas del ciclo: requerimiento, diseño, código, test y deploy.

* Es acotado: un resultado visible en 60 minutos sin que la demo se sienta apresurada.

**Etapas del ciclo que se cubren en la demo:**

| 📋  Requerimientos | Traducir el brief de negocio a especificaciones técnicas con ayuda de la IA. |
| :---- | :---- |
| **🏗️  Diseño / Arq.** | Definir la estructura del microservicio: endpoints, modelos, reglas. |
| **💻  Codificación** | Generación del código del servicio con Claude Code (CLI). |
| **🧪  Testing / QA** | Generación automática de pruebas unitarias e integración. |
| **🚀  Deploy** | Pipeline básico de despliegue para cerrar el ciclo completo. |

# **5\. Estructura Propuesta de la Charla**

La clave del formato es que conversación y demo no son bloques separados: mientras la IA trabaja en segundo plano, el presentador conversa con la audiencia. Los momentos se intercalan de forma orgánica.

| \# | Tipo / Tiempo | Contenido |
| :---: | :---: | :---- |
| **\#1** | **CONVERSACIÓN** 0–5 min | **El gancho: ¿qué pasaría si…?** Abrir con una pregunta provocadora para la audiencia. No con slides. Generar curiosidad inmediata sobre el perfil Full Cycle Engineer. |
| **\#2** | **CONVERSACIÓN** 5–10 min | **¿Qué es el Full Cycle Engineer?** Definir el perfil. Por qué ahora, por qué en este contexto bancario. Conectar con la estrategia de la empresa. Plantear el reto del día: vamos a construir algo en vivo. |
| **\#3** | **LIVE CODING** 10–13 min | **🚀 Lanzar la IA — Entendimiento del requerimiento** Dar el prompt inicial a Claude Code: brief de negocio del microservicio. La IA empieza a trabajar. Mostrar en pantalla el proceso en segundo plano. |
| **\#4** | **CONVERSACIÓN** 13–20 min | **Mientras la IA diseña — El nuevo ciclo de desarrollo** Conversar sobre cómo cambia el rol del ingeniero. Ya no escribe desde cero: dirige, valida, decide. Comparar flujo tradicional vs. Full Cycle Engineer. |
| **\#5** | **LIVE CODING** 20–25 min | **✅ Revisión del diseño / arquitectura generado** Mostrar lo que produjo la IA: estructura, endpoints, modelos. El presentador hace ajustes en vivo para demostrar el rol de "piloto, no copiloto". |
| **\#6** | **CONVERSACIÓN** 25–32 min | **Mientras la IA codifica — El valor para el negocio** Hablar del impacto en velocidad, calidad y cobertura. Conectar con métricas que importan a los tomadores de decisión: time-to-market, reducción de bugs, cobertura de pruebas. |
| **\#7** | **LIVE CODING** 32–40 min | **✅ Código \+ Tests generados** Mostrar el microservicio funcionando. Correr los tests generados automáticamente. Hacer una demo del endpoint en tiempo real. |
| **\#8** | **CONVERSACIÓN** 40–47 min | **Mientras se configura el deploy — El camino a seguir** Hablar de la hoja de ruta de adopción en la empresa. Qué capacidades se están construyendo. Cómo se acompaña la transformación. |
| **\#9** | **LIVE CODING** 47–52 min | **✅ Pipeline de deploy** Mostrar el pipeline básico generado. Deploy ejecutado. El ciclo completo cubierto en menos de 45 minutos de trabajo real de IA. |
| **\#10** | **CIERRE** 52–60 min | **Reflexión \+ Q\&A** ¿Qué acaba de pasar aquí? Revisitar el objetivo. Llamado a la acción concreto. Espacio para preguntas de la audiencia. |

# **6\. Decisiones Clave Tomadas**

| Decisión | Rationale |
| :---- | :---- |
| **Formato intercalado (no A/B)** | Evita que la demo se sienta separada de la conversación. Mantiene la energía y simula el flujo real de trabajo con IA. |
| **Claude Code (CLI) como herramienta única** | Foco y consistencia. Mostrar una sola herramienta en profundidad es más poderoso que hacer un tour superficial de varias. |
| **Cubrir todo el ciclo, no solo codificación** | El mensaje central es el Full Cycle: si solo se muestra código, se pierde el punto diferencial del perfil. |
| **Caso de uso bancario** | Audiencia son bancos. Un caso propio del dominio genera identificación inmediata y reduce la barrera de abstracción para no técnicos. |
| **Tono: confianza, no urgencia** | La empresa ya tiene la estrategia. El objetivo no es alarmar sino mostrar el camino con seguridad y claridad. |
| **60 minutos con Q\&A incluido** | 8 minutos de cierre y preguntas garantizan que la audiencia procese y se comprometa, no solo observe. |

# **7\. Próximos Pasos**

| \# | Acción | Responsable / Notas |
| :---: | :---- | :---- |
| **1** | Confirmar el caso de uso exacto con el equipo técnico que hará la demo | *Pendiente definir presentador(es)* |
| **2** | Preparar el repositorio y los prompts de Claude Code con anticipación | *Ensayar el flujo completo al menos 2 veces* |
| **3** | Definir quién lleva la conversación y quién hace el live coding | *Puede ser 1 o 2 personas* |
| **4** | Preparar un backup del demo (versión grabada) por si falla la conexión | *Mitigación de riesgos en vivo* |
| **5** | Diseñar el slide o visual de apertura con la pregunta gancho | *Opcional: puede ser solo verbal* |

Documento generado el 27 de febrero de 2026  ·  Full Cycle Engineer — Planning Doc