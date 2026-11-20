# TFM — Verificación semántica con modelos de lenguaje locales

> **Trabajo Fin de Máster (en curso)** — Máster en Ingeniería Web, especialidad Ciberseguridad, Universidad de Oviedo.
> **Título:** *Verificación semántica de entregas software mediante modelos de lenguaje locales: extensión de SVAES.*
> Autor: Adrián Martínez Fuentes

Continuación del TFG. La documentación del TFG (resto de `docs/`) se conserva como histórico.

## Motivación

Las reglas actuales de SVAES (RV-01…RV-10) comprueban aspectos **estructurales y de trazabilidad**: pueden verificar que un commit está asociado a una tarea, pero no si el código implementa lo que la tarea pide.

## Objetivo

Ampliar SVAES con **verificaciones semánticas** basadas en LLM **ejecutados localmente** (sin enviar código ni requisitos a servicios externos):

- ¿La implementación responde a su requisito?
- ¿Se cumplen los criterios de aceptación?
- ¿Hay contradicciones entre fuentes de especificación (Jira, Confluence, Git)?

## Alcance previsto

1. Diseño de un conjunto representativo de reglas semánticas.
2. Construcción del contexto a partir de la trazabilidad ya disponible en SVAES.
3. Formato de salida estructurado: veredicto, evidencias y opción de **abstención**.
4. Integración en el flujo de verificación existente (motor/conectores/informes).
5. Evaluación experimental sobre casos de referencia, comparando modelos por precisión, exhaustividad, abstención y tiempo de respuesta, con atención a falsos positivos y tipos de error.

> Estado: alcance de la propuesta. La implementación en este repositorio aún no está reflejada en el resto de la documentación.

## Prueba de concepto de viabilidad

Repositorio: [`TFM-Investigacion`](https://github.com/adrianmfuentes/TFM-Investigacion) (local: `D:\34644\Documents\Github\TFM-Investigacion`).

Caso común: ticket `SEC-402` (contraseña ≥ 12 caracteres y con número) frente a un diff que solo exige ≥ 8. Respuesta esperada: **NO CUMPLE**.

| Experimento | Entorno | Resultado |
|---|---|---|
| 1 | Gemini CLI (WSL) | NO CUMPLE (correcto) |
| 2 | Ollama en la GPU de la Escuela, 12 modelos abiertos | **10/12** detectan el incumplimiento |
| 3 | DeepEval (LLM-as-a-judge) sobre los resultados del exp. 2 | Configurado; ejecución pendiente |

Fallos del exp. 2 (veredicto CUMPLE): `codellama:7b`, `llama3.2:3b`. Tiempos observados: 15 s (`qwen2.5-coder:3b`) a 200 s (`qwen2.5-coder:7b`).

## Referencias

- Propuesta del TFM y propuesta al tutor (documentos académicos, fuera del repositorio).
- Documentación técnica de SVAES: [../README.md](../README.md).
