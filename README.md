# SVAES  
## Sistema de Verificación Automática de Entregas de Software

Trabajo Fin de Grado  
Grado en Ingeniería Informática del Software  
Universidad de Oviedo  

Autor: Adrián Martínez Fuentes  
Tutora: María del Carmen Suárez Torrente  
Curso: 2025/2026  

---

## 1. Descripción del proyecto

SVAES (Sistema de Verificación Automática de Entregas de Software) es una plataforma orientada a la validación automatizada de entregas de software en entornos de desarrollo profesional.

El sistema permite verificar de forma automática la calidad, completitud y coherencia de entregas software (releases), integrándose con herramientas externas como gestores de tareas, repositorios de código o sistemas de documentación.

Su objetivo principal es reducir errores manuales en la validación de entregas, mejorar la trazabilidad y garantizar el cumplimiento de criterios de calidad definidos.

---

## 2. Objetivos

### Objetivo general
Diseñar e implementar un sistema genérico capaz de verificar automáticamente entregas de software mediante reglas configurables.

### Objetivos específicos
- Definir un modelo de verificación desacoplado de herramientas externas
- Implementar un motor de verificación eficiente y seguro
- Diseñar una arquitectura escalable basada en principios modernos
- Permitir la integración con sistemas externos mediante conectores
- Proporcionar una interfaz de usuario para la gestión de verificaciones
- Garantizar la trazabilidad entre requisitos y diseño

---

## 3. Arquitectura del sistema

El sistema sigue una arquitectura híbrida basada en:

- Arquitectura hexagonal (Ports & Adapters)
- Clean Architecture

Principios clave:

- El dominio es independiente de la infraestructura  
- Las dependencias siempre apuntan hacia el núcleo  
- Las integraciones externas se realizan mediante interfaces (puertos)  

### Componentes principales

- Frontend (Angular SPA)  
- Backend (FastAPI - Python)  
- Motor de verificación (Rust)  
- Sistema de colas (Celery + Redis)  
- Base de datos (PostgreSQL)  

---

## 4. Tecnologías utilizadas

| Capa                | Tecnología                  |
|---------------------|---------------------------|
| Frontend           | Angular + TypeScript       |
| Backend            | Python (FastAPI)           |
| Motor verificación | Rust                       |
| Base de datos      | PostgreSQL                 |
| ORM                | SQLAlchemy + Alembic       |
| Cola de tareas     | Celery + Redis             |
| API                | OpenAPI 3.x                |
| Contenerización    | Docker + Docker Compose    |

---

## 5. Estructura del repositorio

```
svaes/
│
├── frontend/              
├── backend/               
├── verifier-engine/       
├── connectors/            
├── database/              
├── docs/                  
├── docker/                
├── .env.example           
└── README.md
```

---

## 6. Funcionalidades principales

- Gestión de entregas (releases)
- Configuración de perfiles de verificación
- Ejecución automática de verificaciones
- Integración con herramientas externas
- Consulta de resultados y métricas
- Sistema de roles y autenticación

---

## 7. Instalación y ejecución

### Requisitos

- Docker
- Docker Compose

### Pasos

```bash
git clone https://github.com/adrianmfuentes/svaes.git
cd svaes
cp .env.example .env
docker-compose up --build
```

Acceso:
http://localhost:8080

---

## 8. Uso básico

1. Acceder a la aplicación web  
2. Crear una organización/proyecto  
3. Configurar conectores externos  
4. Definir reglas de verificación  
5. Lanzar verificación sobre una entrega  
6. Consultar resultados  

---

## 9. Seguridad

- Autenticación mediante JWT  
- Control de acceso basado en roles (RBAC)  
- Aislamiento del motor de verificación  
- Gestión segura de credenciales  

---

## 10. Limitaciones

- No incluye despliegue en entorno productivo real  
- Integraciones externas limitadas  
- No incluye análisis predictivo  

---

## 11. Trabajo futuro

- Nuevos conectores  
- Dashboard avanzado  
- Integración CI/CD  
- Despliegue en cloud  

---

## 12. Licencia

Proyecto desarrollado con fines académicos.

---

## 13. Contacto

Adrián Martínez Fuentes  
Universidad de Oviedo  
