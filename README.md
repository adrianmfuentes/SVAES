# SVAES  
## Sistema de Verificación Automática de Entregas de Software  

Trabajo Fin de Grado  
Grado en Ingeniería Informática del Software  
Universidad de Oviedo  

Autor: Adrián Martínez Fuentes  
Tutora: María del Carmen Suárez Torrente  
Curso: 2025/2026  

---

# 1. Introducción

El Sistema de Verificación Automática de Entregas de Software (SVAES) es una plataforma diseñada para automatizar la validación de entregas de software dentro de procesos de desarrollo modernos basados en integración continua.

El sistema actúa como un mecanismo de control de calidad (Quality Gate), evaluando de forma automática la coherencia, integridad y completitud de los artefactos asociados a una release, mediante la integración con múltiples sistemas externos.

El objetivo principal es eliminar procesos manuales de validación, reducir errores humanos y garantizar la trazabilidad completa del ciclo de vida de las entregas.

---

# 2. Objetivos del sistema

## 2.1 Objetivo general

Diseñar e implementar un sistema extensible y desacoplado capaz de verificar automáticamente entregas de software en entornos multi-herramienta.

## 2.2 Objetivos específicos

- Automatizar la validación de releases  
- Garantizar trazabilidad completa de verificaciones  
- Integrarse con herramientas externas sin acoplamiento  
- Proporcionar métricas y observabilidad del proceso de calidad  
- Permitir su uso como Quality Gate en pipelines CI/CD  

---

# 3. Alcance funcional

El sistema cubre las siguientes capacidades:

- Gestión de organizaciones (multi-tenant)  
- Gestión de proyectos y releases  
- Configuración de conectores externos  
- Definición de perfiles de verificación  
- Ejecución automática de verificaciones  
- Registro de resultados y auditoría  
- Exposición de API REST para integración  

Quedan fuera del alcance:

- Ejecución de pipelines CI/CD  
- Modificación de sistemas externos  
- Análisis predictivo o inteligencia artificial  

---

# 4. Arquitectura del sistema

## 4.1 Enfoque arquitectónico

El sistema adopta una arquitectura híbrida basada en:

- Arquitectura hexagonal (Ports & Adapters)  
- Clean Architecture  

Principio clave:

Las dependencias solo pueden apuntar hacia el dominio.

---

## 4.2 Descomposición en contenedores

El sistema se divide en los siguientes componentes:

- Frontend (Angular SPA)  
- Backend (FastAPI)  
- Motor de verificación (Rust)  
- Cola de tareas (Celery + Redis)  
- Base de datos (PostgreSQL)  
- Conectores externos  

---

## 4.3 Flujo de ejecución

1. El usuario lanza una verificación  
2. El backend valida el estado de la release  
3. Se encola una tarea  
4. Un worker procesa la tarea  
5. Se obtienen datos mediante conectores  
6. Se ejecuta el motor  
7. Se guarda el resultado  
8. El frontend consulta el estado  

---

# 5. Modelo de dominio

Entidades principales:

- Organization  
- Project  
- Release  
- Artifact  
- VerificationProfile  
- VerificationRule  
- VerificationResult  
- ConnectorInstance  

Cada verificación almacena un snapshot completo del estado evaluado.

---

# 6. Ciclo de vida de una release

El ciclo de vida de una release define los estados por los que pasa una entrega desde su creación hasta el resultado final de la verificación.

```text
BORRADOR
   |
   v
PENDIENTE
   |
   v
EN_VERIFICACION
   |
   +--> VALIDA
   +--> NO_VALIDA
   +--> CON_ADVERTENCIAS
```

| Estado | Descripción |
| --- | --- |
| `BORRADOR` | Release creada, todavía editable y sin enviar a verificación. |
| `PENDIENTE` | Release preparada para ser verificada. |
| `EN_VERIFICACION` | Verificación en curso por parte del worker. |
| `VALIDA` | Release verificada correctamente. |
| `NO_VALIDA` | Release rechazada por incumplir reglas obligatorias. |
| `CON_ADVERTENCIAS` | Release aceptable, pero con incidencias no bloqueantes. |

Estados finales: `VALIDA`, `NO_VALIDA` y `CON_ADVERTENCIAS`.

---

# 7. Motor de verificación

Implementado en Rust.

Características:

- Ejecución paralela  
- Sin llamadas de red  
- Procesamiento en memoria  
- Resultado determinista  

Pipeline:

1. Validación  
2. Evaluación de reglas  
3. Agregación  
4. Veredicto  

---

# 8. Conectores

Puerto principal:

IConnector

Permite integrar sistemas externos sin modificar el núcleo.

---

# 9. Persistencia

Base de datos PostgreSQL:

- UUID como identificadores  
- JSONB para datos dinámicos  
- Integridad referencial  
- Auditoría  

---

# 10. Seguridad

- JWT  
- RBAC  
- Cifrado de credenciales  
- HTTPS  
- Protección contra ataques  

---

# 11. Tecnologías

- Angular  
- FastAPI  
- Rust  
- PostgreSQL  
- Celery  
- Redis  
- Docker  

---

# 12. Estructura

```text
SVAES/
|-- apps/
|   |-- api/                         # API principal
|   |   |-- src/
|   |   |   |-- main/
|   |   |   `-- test/
|   |   `-- package.json
|   `-- web/                         # Aplicacion frontend
|       |-- public/
|       |-- src/
|       |   |-- app/
|       |   |-- components/
|       |   |-- features/
|       |   |-- hooks/
|       |   |-- pages/
|       |   |-- routes/
|       |   |-- services/
|       |   `-- styles/
|       `-- package.json
|-- docs/
|   |-- api/
|   |   `-- openapi.yaml
|   |-- database/
|   |   `-- erd.puml
|   |-- diagrams/
|   |   |-- exported/
|   |   `-- plantuml/
|   `-- tfg/
|-- packages/
|   |-- application/
|   |   |-- src/
|   |   |   |-- dto/
|   |   |   |-- ports/
|   |   |   |-- services/
|   |   |   `-- use-cases/
|   |   `-- tests/
|   |-- connectors/
|   |   |-- change-management/
|   |   |-- confluence/
|   |   |-- gitlab/
|   |   |-- jira/
|   |   |-- planning/
|   |   `-- shared/
|   |-- domain/
|   |   |-- src/
|   |   |   |-- organizations/
|   |   |   |-- policies/
|   |   |   |-- projects/
|   |   |   |-- releases/
|   |   |   |-- users/
|   |   |   `-- verification/
|   |   `-- tests/
|   |-- infrastructure/
|   |   |-- src/
|   |   |   |-- external/
|   |   |   |-- logging/
|   |   |   |-- persistence/
|   |   |   |-- queue/
|   |   |   `-- security/
|   |   `-- tests/
|   `-- shared/
|       |-- constants/
|       |-- errors/
|       |-- types/
|       `-- utils/
|-- scripts/
|   |-- db/
|   |-- deploy/
|   `-- dev/
|-- tests/
|   |-- e2e/
|   |-- integration/
|   |-- performance/
|   |-- security/
|   `-- unit/
|-- workers/
|   `-- verification-worker/
|       |-- src/
|       |   |-- executors/
|       |   |-- jobs/
|       |   |-- result-writers/
|       |   `-- rules/
|       |-- tests/
|       `-- package.json
|-- .env.example
|-- docker-compose.yml
|-- LICENSE
`-- README.md
```

---

# 15. Ejecución
```
git clone https://github.com/adrianmfuentes/svaes.git  
cd svaes  
docker-compose up  
```

---

# 16. Conclusión

El sistema proporciona una solución desacoplada, extensible y robusta para la verificación automática de entregas de software.
