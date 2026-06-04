# Informe de trazabilidad — SVAES Plan de Pruebas

**Total en plan:** 77  |  **Cubiertas OK:** 8  |  **Fallan:** 1  |  **Sin implementar:** 68

| TC-ID | Nivel | Sección | Estado | Herramienta | Descripción |
|---|---|---|---|---|---|
| `TC-UNI-AGG-01` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | Todas OBL=OK, OPC=OK → VALID |
| `TC-UNI-AGG-02` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | ≥1 OBL=ERROR → INVALID |
| `TC-UNI-AGG-03` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | OBL todas OK, ≥1 OPC=WARNING → VALID_WITH_WARNINGS |
| `TC-UNI-AGG-04` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | VL: 0 reglas OBL con ERROR → veredicto≠INVALID |
| `TC-UNI-AGG-05` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | VL: 1 regla OBL con ERROR → INVALID |
| `TC-UNI-AGG-06` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | VL: 1 NOT_EVALUATED → sufijo _WITH_INCIDENTS |
| `TC-UNI-AGG-07` | Unitaria | §7.2.1 | ⬜ MISSING | cargo test | VL: 0 NOT_EVALUATED → sin sufijo |
| `TC-UNI-MOT-01` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-01 Conector ACTIVO, artefacto OK |
| `TC-UNI-MOT-02` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-01 Conector INACTIVO → NOT_EVALUATED |
| `TC-UNI-MOT-03` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-02 ID cruzado válido |
| `TC-UNI-MOT-04` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-02 ID en commit NOT_FOUND en Jira → ERROR |
| `TC-UNI-MOT-05` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-03 Cobertura documental completa |
| `TC-UNI-MOT-06` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-04 Versión coherente |
| `TC-UNI-MOT-07` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-05 Tarea bloqueante → ERROR |
| `TC-UNI-MOT-08` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-06 Campo obligatorio vacío → ERROR |
| `TC-UNI-MOT-09` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-07 Back-reference válida |
| `TC-UNI-MOT-10` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-08 Artefacto con antigüedad > umbral → WARNING |
| `TC-UNI-MOT-11` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-09 Dos artefactos mismo external_id → ERROR |
| `TC-UNI-MOT-12` | Unitaria | §7.2.2 | ⬜ MISSING | cargo test | RV-10 Documento aprobado existe |
| `TC-UNI-API-00` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | Base OPERATOR+válido+propia+completo → 201 |
| `TC-UNI-API-01` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | rol=ADMIN → 201 |
| `TC-UNI-API-02` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | rol=VIEWER → 403 |
| `TC-UNI-API-03` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | autenticación=token_caducado → 401 |
| `TC-UNI-API-04` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | autenticación=sin_token → 401 |
| `TC-UNI-API-05` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | org_context=ajena → 404 |
| `TC-UNI-API-06` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | body campo faltante → 422 |
| `TC-UNI-API-07` | Unitaria | §7.2.3 | ⬜ MISSING | pytest | body tipo incorrecto → 422 |
| `TC-UNI-CON-01` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | Credenciales OK, URL alcanzable → ACTIVO |
| `TC-UNI-CON-02` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | Token caducado → AuthError / INACTIVO |
| `TC-UNI-CON-03` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | URL inexistente → ConnectionError / INACTIVO |
| `TC-UNI-CON-04` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | VL latencia = timeout exacto → TimeoutError |
| `TC-UNI-CON-05` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | VL latencia = timeout−1 ms → OK |
| `TC-UNI-CON-06` | Unitaria | §7.2.4 | ⬜ MISSING | pytest | Conector INACTIVO en verificación → sin HTTP |
| `TC-UNI-FE-GRD-01` | Unitaria | §7.2.5.1 | ✅ PASS | Jest | Token válido, U2/OPERATOR, ruta permitida → canActivate=true |
| `TC-UNI-FE-GRD-02` | Unitaria | §7.2.5.1 | ✅ PASS | Jest | Token caducado → canActivate=false, redirige /login |
| `TC-UNI-FE-GRD-03` | Unitaria | §7.2.5.1 | ✅ PASS | Jest | Token ausente → canActivate=false, redirige /login |
| `TC-UNI-FE-GRD-04` | Unitaria | §7.2.5.1 | ✅ PASS | Jest | U1/VIEWER en /releases/verify → canActivate=false, /forbidden |
| `TC-UNI-FE-SVC-01` | Unitaria | §7.2.5.2 | ✅ PASS | Jest | POST /releases 201 → Observable emite Release, Bearer presente |
| `TC-UNI-FE-SVC-02` | Unitaria | §7.2.5.2 | ❌ FAIL | Jest | POST /releases 401 → Observable emite AuthError |
| `TC-UNI-FE-SVC-03` | Unitaria | §7.2.5.2 | ✅ PASS | Jest | POST /releases 422 → Observable emite ValidationError |
| `TC-UNI-FE-NGR-01` | Unitaria | §7.2.5.3 | ✅ PASS | Jest | API 202+taskId → verifyReleaseSuccess con taskId |
| `TC-UNI-FE-NGR-02` | Unitaria | §7.2.5.3 | ✅ PASS | Jest | API 409 → verifyReleaseFailure con INVALID_STATE |
| `TC-INT-EST-01` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T1 BORRADOR→EN_VERIFICACION → HTTP 202 |
| `TC-INT-EST-02` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T2 EN_VERIFICACION→VÁLIDA |
| `TC-INT-EST-03` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T3 EN_VERIFICACION→CON_ADVERTENCIAS |
| `TC-INT-EST-04` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T4 EN_VERIFICACION→NO_VÁLIDA |
| `TC-INT-EST-05` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T5 VÁLIDA→ARCHIVADA (inmutable) |
| `TC-INT-EST-06` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T6 NO_VÁLIDA→EN_VERIFICACION (rework) |
| `TC-INT-EST-07` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T-NEG ARCHIVADA→EN_VERIFICACION → 409 |
| `TC-INT-EST-08` | Integración | §7.3.1 | ⬜ MISSING | pytest+Docker | T-NEG BORRADOR→VÁLIDA (salto) → 422 |
| `TC-INT-FLW-01` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | CU-01 todas RV-01..10 conectores activos → VALID |
| `TC-INT-FLW-02` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | CU-01 conector GitLab INACTIVO → _WITH_INCIDENTS |
| `TC-INT-FLW-03` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | Re-verificación tras NO_VÁLIDA → VÁLIDA |
| `TC-INT-LIM-01` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | VL rate limit petición 100/60s → 200 |
| `TC-INT-LIM-02` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | VL rate limit petición 101/60s → 429+Retry-After |
| `TC-INT-RES-01` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | docker kill worker durante verificación → sin corrupción |
| `TC-INT-RES-02` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | Redis caído al lanzar POST /verify → 503 |
| `TC-INT-MIG-01` | Integración | §7.3.2 | ⬜ MISSING | pytest+Docker | alembic upgrade head sobre BD vacía → esquema OK |
| `TC-ACP-CU-00` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | CU-01 base → VÁLIDA en ≤5 acciones (RNF-19) |
| `TC-ACP-CU-01` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | CU-01 RV-04=WARNING → semáforo naranja |
| `TC-ACP-CU-02` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | CU-01 RV-05=ERROR → semáforo rojo, msg descriptivo |
| `TC-ACP-CU-03` | Aceptación | §7.4 | ⬜ MISSING | Manual | Usuario nuevo completa flujo en ≤15 min (RNF-24) |
| `TC-ACP-UI-01` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | Snapshot inmutable tras archivar (RNF-36) |
| `TC-ACP-FRM-01` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | Campo obligatorio vacío → mensaje campo+acción |
| `TC-ACP-FRM-02` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | Campo numérico con texto → error de tipo (RNF-20) |
| `TC-USA-NAV-01` | Aceptación | §7.4 | ⬜ MISSING | Cypress | Each choice Chrome/Firefox/Edge/Safari (RNF-29) |
| `TC-USA-RES-01` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | VL resolución 1920/768/375 → sin desbordamiento (RNF-30) |
| `TC-USA-SEM-01` | Aceptación | §7.4 | ⬜ MISSING | Manual+Cypress | Semáforo coherente en dashboard/historial/detalle (RNF-21) |
| `TC-PER-VL-01` | Rendimiento | §7.5 | ⬜ MISSING | Locust | Verificación 10 reglas → tiempo e2e ≤5s p95 (RNF-06) |
| `TC-PER-VL-02` | Rendimiento | §7.5 | ⬜ MISSING | Locust | Motor Rust bucle → p95 <500ms (RNF-07) |
| `TC-PER-VL-03` | Rendimiento | §7.5 | ⬜ MISSING | Locust | 50 POST /verify simultáneos → todas 202 (RNF-06) |
| `TC-PER-CE-04` | Rendimiento | §7.5 | ⬜ MISSING | SonarCloud | Suite completa → SonarCloud cobertura ≥70% (RNF-27) |
| `TC-SEC-AUT-01` | Seguridad | §7.6 | ⬜ MISSING | pytest | VL fuerza bruta: 5 intentos → 403 + bloqueo 15min (RNF-14) |
| `TC-SEC-AUT-02` | Seguridad | §7.6 | ⬜ MISSING | pytest | JWT manipulado → 401 (OWASP A2) |
| `TC-SEC-INY-01` | Seguridad | §7.6 | ⬜ MISSING | pytest | SQLi en nombre release → neutralizado (OWASP A3) |
| `TC-SEC-INY-02` | Seguridad | §7.6 | ⬜ MISSING | pytest | XSS en release → escapado al frontend (OWASP A3) |
| `TC-SEC-CIF-01` | Seguridad | §7.6 | ⬜ MISSING | pytest | Credenciales cifradas AES-256-GCM en BD (RNF-13) |