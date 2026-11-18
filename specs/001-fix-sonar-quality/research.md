# Decisiones técnicas

- Dar a cada rama de control de conectores un ID que coincida con su etiqueta. La selección, el texto y la contraseña mantienen sus tipos.
- Conservar los flujos asíncronos y gestionar los rechazos en el punto donde se decide iniciar cada operación.
- Activar los efectos de movimiento según la preferencia del navegador y mantener el contenido visible por defecto. Usar la cascada para las variantes de estilo.
- Ejecutar el cierre del ciclo de vida también si el contexto de la API termina con una excepción. Agrupar las adiciones contiguas de exportación respetando el orden.
