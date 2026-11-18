# Tareas de SonarCloud

## Preparación

- [X] T001 Inventariar los resultados del análisis de referencia en [spec.md](spec.md).

## P1 · Fiabilidad

- [X] T002 [US1] Resolver los IDs y sus etiquetas en `web/src/app/features/connectors/connectors.component.html`.
- [X] T003 [US1] Gestionar las promesas señaladas en `web/src/app/core/interceptors/error.interceptor.ts`, `web/src/app/core/services/auth.service.ts`, `web/src/app/features/auth/login/login.component.ts`, `web/src/app/features/landing/landing.component.ts`, `web/src/app/features/projects/project-new/project-new.component.ts`, `web/src/app/features/releases/release-detail/release-detail.component.ts`, `web/src/app/features/releases/release-new/release-new.component.ts`.
- [X] T004 [US1] Ejecutar el cierre de la API al salir del contexto en `api/src/main.py`.

## P2 · Accesibilidad y comportamiento

- [X] T005 [US2] Ajustar el tratamiento accesible de los SVG en `web/src/app/features/admin/admin.component.html`, `web/src/app/features/landing/feedback-modal/feedback-modal.component.html`, `web/src/app/features/logs/logs.component.html`, `web/src/app/features/releases/release-detail/release-detail.component.html`, `web/src/app/features/releases/releases.component.html`, `web/src/app/features/system/system.component.html`.
- [X] T006 [US2] Corregir la cascada en `web/src/app/features/auth/activate/activate-account.component.scss`, `web/src/app/features/landing/landing.component.scss`, `web/src/app/features/projects/projects.component.scss`, `web/src/app/features/system/system.component.scss`.
- [X] T007 [US2] Respetar la preferencia de movimiento en `web/src/app/core/components/confirm-dialog/confirm-dialog.component.scss`, `web/src/app/core/components/toast/toast.component.scss`, `web/src/app/features/access-request/access-request-form.component.scss`, `web/src/app/features/admin/admin.component.scss`, `web/src/app/features/landing/feedback-modal/feedback-modal.component.scss`, `web/src/app/features/landing/landing.component.scss`, `web/src/app/features/organization/org-settings.component.scss`, `web/src/app/features/releases/release-detail/release-detail.component.scss`.
- [X] T008 [US2] Acotar las transiciones en `web/src/app/core/components/confirm-dialog/confirm-dialog.component.scss`, `web/src/app/features/releases/releases.component.scss`.
- [X] T009 [US2] Agrupar adiciones contiguas en `api/src/application/use_cases/main/export_service.py`.

## Verificación

- [ ] T010 Ejecutar las comprobaciones de [quickstart.md](quickstart.md) y revisar el diff.
- [ ] T011 Confirmar los estados de SonarCloud en el commit corregido según [spec.md](spec.md).
