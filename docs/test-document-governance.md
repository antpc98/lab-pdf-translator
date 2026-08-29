# Gobierno de documentos de prueba: uso personal y publicación

> Bitácora: 30/08/2026 — definida la estrategia documental privada y pública del laboratorio.

## 1. Propósito

El pipeline necesita documentos reales para comprobar texto, fuentes, imágenes, columnas, código y numeración. Esa necesidad técnica no concede derechos para redistribuir los documentos. Esta guía separa expresamente el laboratorio personal de una futura versión pública y evita que una muestra de prueba se convierta en un riesgo del repositorio.

Esta guía organiza el trabajo técnico; no sustituye asesoramiento jurídico.

## 2. Opción personal

Mientras el laboratorio sea privado, el documento actual puede mantenerse como una dependencia local temporal y aislada, pero su falta de autorización debe considerarse un riesgo aceptado expresamente, no un derecho adquirido. Su uso concreto depende de la legislación y de cómo se obtuvo la copia; esta guía únicamente impide que llegue a una distribución del proyecto.

Reglas:

- El repositorio debe permanecer privado.
- El documento se usa únicamente para desarrollo y validación personal.
- No se publica en releases, paquetes, artefactos de CI o demostraciones descargables.
- Ninguna salida traducida se distribuye si no existe autorización para crear y compartir esa adaptación.
- El README no debe dar a entender que el documento pertenece al proyecto o que tiene licencia abierta.
- Antes de colaborar con terceros se revisará de nuevo su presencia y acceso.

El PDF actual sirve como caso privado, pero no tiene derechos de redistribución confirmados. Por tanto, **no forma parte del material publicable**.

## 3. Opción pública recomendada

Antes de hacer público el repositorio se sustituirá el documento privado por uno de estos dos tipos:

### 3.1 Muestra creada por el proyecto

Es la opción preferida porque ofrece control completo. La fixture sintética existente puede evolucionar a un documento estable de prueba con:

- Portada, índice y capítulos.
- Párrafos con varias familias, tamaños y estilos.
- Listas, tablas, código, enlaces y caracteres Unicode.
- Imágenes creadas por el proyecto y apariciones repetidas.
- Páginas con una y dos columnas.
- Cabeceras, pies, numeración física e impresa diferente.
- Página vacía y página compuesta únicamente por imagen.
- Entre 20 y 50 páginas para integración rápida, más una generación parametrizable de hasta 1000 páginas para pruebas de escala.

La muestra, sus imágenes y su texto tendrán autoría propia. El repositorio indicará de forma explícita qué licencia les aplica.

### 3.2 Documento de terceros con licencia abierta

Solo se incorporará cuando la fuente declare de forma expresa que se permite copiar y adaptar el documento. “Gratis”, “descargable” o “acceso libre” no son licencias.

Un candidato revisado es la **Creative Commons Style Guide 2019**, cuyo propio PDF declara licencia CC BY 4.0. Esta licencia permite compartir y adaptar el material, incluso comercialmente, siempre que se proporcione atribución, enlace a la licencia y aviso de cambios.

Fuentes oficiales consultadas el 30/08/2026:

- Documento: <https://creativecommons.org/wp-content/uploads/2019/10/Creative-Commons-Style-Guide-2019.pdf>
- Resumen oficial CC BY 4.0 en español: <https://creativecommons.org/licenses/by/4.0/deed.es>
- Texto legal: <https://creativecommons.org/licenses/by/4.0/legalcode.es>

La licencia debe comprobarse nuevamente al descargar la versión exacta. También se revisarán las atribuciones individuales de imágenes o materiales de terceros que aparezcan dentro del documento.

## 4. Atribución mínima para una muestra CC BY 4.0

`input/README.md` deberá registrar como mínimo:

```text
Título: Creative Commons Style Guide 2019
Autor o entidad: Creative Commons
Fuente: URL exacta del PDF
Licencia: Creative Commons Attribution 4.0 International
Licencia URL: https://creativecommons.org/licenses/by/4.0/
Uso en el proyecto: fixture de extracción, traducción y renderizado
Cambios: indicar si el documento fue recortado, transformado o traducido
Fecha de descarga: AAAA-MM-DD
SHA-256: hash de los bytes versionados
```

La atribución acompañará al documento y a cualquier adaptación pública. No se sugerirá que el autor original respalda el laboratorio.

## 5. Migración antes de publicar

La publicación queda bloqueada hasta completar esta lista:

1. Elegir y registrar la muestra propia o abierta.
2. Incorporar su licencia y atribución verificadas.
3. Actualizar `tests/fixtures/pdf-samples.yaml` con páginas y expectativas nuevas.
4. Ejecutar la barrera automática completa.
5. Revisar visualmente todas las páginas seleccionadas.
6. Eliminar el PDF privado del árbol de trabajo.
7. Eliminarlo también del historial que vaya a publicarse; un commit de borrado no borra versiones anteriores.
8. Comprobar que tags, releases, cachés y artefactos no contienen copias.
9. Revisar el repositorio desde un clon limpio antes de cambiar su visibilidad.

La reescritura del historial cambia hashes y requiere coordinación. Se realizará como una tarea independiente, con copia de seguridad y revisión de los objetivos exactos antes de ejecutar comandos destructivos.

## 6. Registro de procedencia de futuras muestras

Cada documento público tendrá un registro con:

- Nombre y versión exactos.
- Autor, editor y fuente oficial.
- Tipo y versión de licencia.
- Obligaciones de atribución y compatibilidad con adaptaciones.
- Restricciones adicionales conocidas.
- Fecha de verificación.
- SHA-256 del archivo.
- Persona que aprobó su incorporación.
- Páginas utilizadas y motivo de selección.

Una licencia ambigua, contradictoria o ausente produce un resultado **NO OK**. En ese caso se utiliza la muestra propia.

## 7. Criterio del Team Leader

- **Laboratorio personal y privado:** permitido como entorno temporal, dejando documentado que el PDF no es publicable.
- **Repositorio público:** prohibido publicar el PDF actual sin autorización.
- **Aprobación para exposición:** requiere muestra propia o abierta, atribución completa, historial limpio y barrera automática en verde.

Esta separación permite continuar el desarrollo personal ahora sin confundirlo con la autorización necesaria para distribuir el proyecto más adelante.
