# Especificación de la corrección de SonarCloud

**Rama** `fix/sonar-quality`

**Fecha** 2026-11-18

**Estado** Borrador para aprobación

## Objetivo y alcance

Resolver los 67 avisos abiertos en el análisis de `main` del commit `b5c1f69` y recuperar el Quality Gate. La API de SonarCloud devuelve los 67 en código nuevo, repartidos entre 26 archivos web y 2 de la API. La fiabilidad está en D y la puerta exige A. La cobertura de código nuevo es del 84,4 %.

| Área | Avisos | Trabajo |
| --- | ---: | --- |
| Web, TypeScript | 11 | Gestionar las promesas de navegación y otras operaciones asíncronas señaladas. |
| Web, plantillas | 12 | Corregir la relación entre etiquetas y controles de conectores y dar tratamiento accesible a los SVG. |
| Web, estilos | 41 | Respetar la preferencia de movimiento reducido, acotar transiciones y corregir la cascada. |
| API, Python | 3 | Garantizar la limpieza al salir del ciclo de vida y ordenar la construcción de listas en las exportaciones. |

**Fuera de alcance**

Cambios de umbrales, perfiles de calidad, exclusiones o supresiones de SonarCloud. Nuevas dependencias, cambios de contratos y rediseños.

## Escenarios y verificación

### P1 · Fiabilidad y Quality Gate

1. Al analizar el cambio con el perfil vigente, cada uno de los 67 avisos originales figura corregido y el Quality Gate queda en `OK`.
2. Cada tipo de campo de conector conserva su etiqueta asociada y los IDs del formulario son únicos.
3. Si falla una operación asíncrona señalada, el flujo conserva su comportamiento esperado y evita rechazos sin gestionar.
4. Tras un arranque correcto, los recursos de la API se cierran tanto en una salida normal como si se produce una excepción durante el ciclo de vida.

### P2 · Accesibilidad y comportamiento existente

1. Los SVG informativos tienen nombre accesible y los decorativos quedan fuera del árbol de accesibilidad.
2. En las vistas afectadas, el ajuste de movimiento reducido evita las animaciones señaladas. Con el ajuste habitual, se conserva la presentación de esas vistas.
3. Las exportaciones conservan su contenido y orden.

### Riesgos

- Los cambios de cascada pueden afectar a estilos responsivos o estados interactivos. Comprobar ambos en las vistas afectadas.
- Desactivar animaciones puede dejar oculto contenido que se hace visible al terminar una animación. Comprobar visibilidad con movimiento reducido.
- Cambiar la espera de una promesa puede alterar la navegación y los estados de carga. Ejecutar las pruebas de los flujos afectados.

## Requisitos

- **FR-001** · Corregir los ocho grupos de reglas detectados en el código afectado y mantener el perfil y los umbrales vigentes.
- **FR-002** · Conservar el comportamiento funcional de la web y de las exportaciones de la API, incluyendo los caminos de error.
- **FR-003** · Verificar el cambio con las pruebas existentes de web y API y un análisis remoto del commit corregido.

## Criterios de aceptación

- **CA-001** · El nuevo análisis confirma 0 de los 67 avisos originales abiertos y fiabilidad A en código nuevo.
- **CA-002** · El Quality Gate devuelve `OK` con la configuración vigente, incluida la cobertura mínima del 80 % en código nuevo.
- **CA-003** · Pasan las pruebas existentes de Angular y de Python ejecutadas por el workflow correspondiente. Las comprobaciones en las vistas afectadas confirman los escenarios de accesibilidad y estilos.
- **CA-004** · El diff no incluye rediseños, cambios de contratos, dependencias, umbrales, exclusiones ni supresiones.

## Supuestos

- La referencia de cierre es el análisis de `main` del commit `b5c1f69`. El análisis remoto del código corregido es necesario para confirmar el estado de los avisos y del Quality Gate.
- La verificación local puede completarse antes de publicar. La verificación remota depende de que el commit corregido sea analizado en SonarCloud.
