# Informe de trazabilidad - SVAES Plan de Pruebas

**Total en plan:** 79  |  **Cubiertas OK:** 68  |  **Fallan:** 0  |  **Sin implementar:** 11

| TC-ID | Nivel | Seccion | Estado | Herramienta | Descripcion |
|---|---|---|---|---|---|
| `TC-UNI-AGG-01` | Unitaria | 7.2.1 | ✅ PASS | cargo test | Todas OBL=OK, OPC=OK -> VALID |
| `TC-UNI-AGG-02` | Unitaria | 7.2.1 | ✅ PASS | cargo test | >=1 OBL=ERROR -> INVALID |
| `TC-UNI-AGG-03` | Unitaria | 7.2.1 | ✅ PASS | cargo test | OBL todas OK, >=1 OPC=WARNING -> VALID_WITH_WARNINGS |
| `TC-UNI-AGG-04` | Unitaria | 7.2.1 | ✅ PASS | cargo test | VL: 0 reglas OBL con ERROR -> veredicto!=INVALID |
| `TC-UNI-AGG-05` | Unitaria | 7.2.1 | ✅ PASS | cargo test | VL: 1 regla OBL con ERROR -> INVALID |
| `TC-UNI-AGG-06` | Unitaria | 7.2.1 | ✅ PASS | cargo test | VL: 1 NOT_EVALUATED -> sufijo _WITH_INCIDENTS |
| `TC-UNI-AGG-07` | Unitaria | 7.2.1 | ✅ PASS | cargo test | VL: 0 NOT_EVALUATED -> sin sufijo |
| `TC-UNI-MOT-01` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-01 Conector ACTIVO, artefacto OK |
| `TC-UNI-MOT-02` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-01 Conector INACTIVO -> NOT_EVALUATED |
| `TC-UNI-MOT-03` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-02 ID cruzado valido |
| `TC-UNI-MOT-04` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-02 ID en commit NOT_FOUND en Jira -> ERROR |
| `TC-UNI-MOT-05` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-03 Cobertura documental completa |
| `TC-UNI-MOT-06` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-04 Version coherente |
| `TC-UNI-MOT-07` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-05 Tarea bloqueante -> ERROR |
| `TC-UNI-MOT-08` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-06 Campo obligatorio vacio -> ERROR |
| `TC-UNI-MOT-09` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-07 Back-reference valida |
| `TC-UNI-MOT-10` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-08 Artefacto con antiguedad > umbral -> WARNING |
| `TC-UNI-MOT-11` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-09 Dos artefactos mismo external_id -> ERROR |
| `TC-UNI-MOT-12` | Unitaria | 7.2.2 | ✅ PASS | cargo test | RV-10 Documento aprobado existe |
| `TC-UNI-API-00` | Unitaria | 7.2.3 | ✅ PASS | pytest | Base OPERATOR valido+propia+completo -> 201 |
| `TC-UNI-API-01` | Unitaria | 7.2.3 | ✅ PASS | pytest | rol=ADMIN -> 201 |
| `TC-UNI-API-02` | Unitaria | 7.2.3 | ✅ PASS | pytest | rol=INVALID -> 403 |
| `TC-UNI-API-03` | Unitaria | 7.2.3 | ✅ PASS | pytest | autenticacion=token_caducado -> 401 |
| `TC-UNI-API-04` | Unitaria | 7.2.3 | ✅ PASS | pytest | autenticacion=sin_token -> 401 |
| `TC-UNI-API-05` | Unitaria | 7.2.3 | ✅ PASS | pytest | org_context=ajena -> 404 |
| `TC-UNI-API-06` | Unitaria | 7.2.3 | ✅ PASS | pytest | body campo faltante -> 422 |
| `TC-UNI-API-07` | Unitaria | 7.2.3 | ✅ PASS | pytest | body tipo incorrecto -> 422 |
| `TC-UNI-CON-01` | Unitaria | 7.2.4 | ✅ PASS | pytest | Credenciales OK, URL alcanzable -> ACTIVO |
| `TC-UNI-CON-02` | Unitaria | 7.2.4 | ✅ PASS | pytest | Token caducado -> AuthError / INACTIVO |
| `TC-UNI-CON-03` | Unitaria | 7.2.4 | ✅ PASS | pytest | URL inexistente -> ConnectionError / INACTIVO |
| `TC-UNI-CON-04` | Unitaria | 7.2.4 | ✅ PASS | pytest | VL latencia = timeout exacto -> TimeoutError |
| `TC-UNI-CON-05` | Unitaria | 7.2.4 | ✅ PASS | pytest | VL latencia = timeout-1ms -> OK |
| `TC-UNI-CON-06` | Unitaria | 7.2.4 | ✅ PASS | pytest | Conector INACTIVO en verificacion -> sin HTTP |
| `TC-UNI-FE-GRD-01` | Unitaria | 7.2.5.1 | ⬜ MISSING | Jest | Token valido, U2/OPERATOR, ruta permitida -> canActivate=true |
| `TC-UNI-FE-GRD-02` | Unitaria | 7.2.5.1 | ⬜ MISSING | Jest | Token caducado -> canActivate=false, redirige /login |
| `TC-UNI-FE-GRD-03` | Unitaria | 7.2.5.1 | ⬜ MISSING | Jest | Token ausente -> canActivate=false, redirige /login |
| `TC-UNI-FE-GRD-04` | Unitaria | 7.2.5.1 | ⬜ MISSING | Jest | U2/OPERATOR en /releases -> canActivate=true |
| `TC-UNI-FE-SVC-01` | Unitaria | 7.2.5.2 | ⬜ MISSING | Jest | POST /releases 201 -> Observable emite Release, Bearer presente |
| `TC-UNI-FE-SVC-02` | Unitaria | 7.2.5.2 | ⬜ MISSING | Jest | POST /releases 401 -> Observable emite AuthError |
| `TC-UNI-FE-SVC-03` | Unitaria | 7.2.5.2 | ⬜ MISSING | Jest | POST /releases 422 -> Observable emite ValidationError |
| `TC-UNI-FE-NGR-01` | Unitaria | 7.2.5.3 | ⬜ MISSING | Jest | API 202+taskId -> verifyReleaseSuccess con taskId |
| `TC-UNI-FE-NGR-02` | Unitaria | 7.2.5.3 | ⬜ MISSING | Jest | API 409 -> verifyReleaseFailure con INVALID_STATE |
| `TC-INT-EST-01` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T1 BORRADOR->EN_VERIFICACION -> HTTP 202 |
| `TC-INT-EST-02` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T2 EN_VERIFICACION->VALIDA |
| `TC-INT-EST-03` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T3 EN_VERIFICACION->CON_ADVERTENCIAS |
| `TC-INT-EST-04` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T4 EN_VERIFICACION->NO_VALIDA |
| `TC-INT-EST-05` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T5 VALIDA->ARCHIVADA (inmutable) |
| `TC-INT-EST-06` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T6 NO_VALIDA->EN_VERIFICACION (rework) |
| `TC-INT-EST-07` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T-NEG ARCHIVADA->EN_VERIFICACION -> 409 |
| `TC-INT-EST-08` | Integracion | 7.3.1 | ✅ PASS | pytest+Docker | T-NEG BORRADOR->VALIDA (salto) -> 422 |
| `TC-INT-FLW-01` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | CU-01 todas RV-01..10 conectores activos -> VALID |
| `TC-INT-FLW-02` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | CU-01 conector GitLab INACTIVO -> _WITH_INCIDENTS |
| `TC-INT-FLW-03` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | Re-verificacion tras NO_VALIDA -> VALIDA |
| `TC-INT-LIM-01` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | VL rate limit peticion 100/60s -> 200 |
| `TC-INT-LIM-02` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | VL rate limit peticion 101/60s -> 429+Retry-After |
| `TC-INT-RES-01` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | docker kill worker durante verificacion -> sin corrupcion |
| `TC-INT-RES-02` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | Redis caido al lanzar POST /verify -> 503 |
| `TC-INT-MIG-01` | Integracion | 7.3.2 | ✅ PASS | pytest+Docker | alembic upgrade head sobre BD vacia -> esquema OK |
| `TC-ACP-CU-00` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | CU-01 base -> VALIDA en <=5 acciones (RNF-19) |
| `TC-ACP-CU-01` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | CU-01 RV-04=WARNING -> semaforo naranja |
| `TC-ACP-CU-02` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | CU-01 RV-05=ERROR -> semaforo rojo, msg descriptivo |
| `TC-ACP-CU-03` | Aceptacion | 7.4 | ✅ PASS | Manual | Usuario nuevo completa flujo en <=15 min (RNF-24) |
| `TC-ACP-UI-01` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | Snapshot inmutable tras archivar (RNF-36) |
| `TC-ACP-FRM-01` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | Campo obligatorio vacio -> mensaje campo+accion |
| `TC-ACP-FRM-02` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | Campo numerico con texto -> error de tipo (RNF-20) |
| `TC-USA-NAV-01` | Aceptacion | 7.4 | ✅ PASS | Cypress | Each choice Chrome/Firefox/Edge/Safari (RNF-29) |
| `TC-USA-RES-01` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | VL resolucion 1920/768/375 -> sin desbordamiento (RNF-30) |
| `TC-USA-SEM-01` | Aceptacion | 7.4 | ✅ PASS | Manual+Cypress | Semaforo coherente en dashboard/historial/detalle (RNF-21) |
| `TC-PER-VL-01` | Rendimiento | 7.5 | ✅ PASS | Locust | Verificacion 10 reglas -> tiempo e2e <=5s p95 (RNF-06) |
| `TC-PER-VL-02` | Rendimiento | 7.5 | ✅ PASS | Locust | Motor Rust bucle -> p95 <500ms (RNF-07) |
| `TC-PER-VL-03` | Rendimiento | 7.5 | ✅ PASS | Locust | 50 POST /verify simultaneos -> todas 202 (RNF-06) |
| `TC-PER-CE-01` | Rendimiento | 7.5 | ⬜ MISSING | Locust | 50 health checks concurrentes -> sin timeout |
| `TC-PER-CE-02` | Rendimiento | 7.5 | ⬜ MISSING | Locust | Carga sostenida en /releases -> sin errores |
| `TC-PER-CE-04` | Rendimiento | 7.5 | ✅ PASS | SonarCloud | Suite completa -> SonarCloud cobertura >=70% (RNF-27) |
| `TC-SEC-AUT-01` | Seguridad | 7.6 | ✅ PASS | pytest | VL fuerza bruta: 5 intentos -> 403 + bloqueo 15min (RNF-14) |
| `TC-SEC-AUT-02` | Seguridad | 7.6 | ✅ PASS | pytest | JWT manipulado -> 401 (OWASP A2) |
| `TC-SEC-INY-01` | Seguridad | 7.6 | ✅ PASS | pytest | SQLi en nombre release -> neutralizado (OWASP A3) |
| `TC-SEC-INY-02` | Seguridad | 7.6 | ✅ PASS | pytest | XSS en release -> escapado al frontend (OWASP A3) |
| `TC-SEC-CIF-01` | Seguridad | 7.6 | ✅ PASS | pytest | Credenciales cifradas AES-256-GCM en BD (RNF-13) |
