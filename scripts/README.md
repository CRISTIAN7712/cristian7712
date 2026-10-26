# Gráficas del perfil

`python scripts/update_stats.py` genera tres SVG en `assets/stats/` con Python 3.12 y su biblioteca estándar. No requiere instalar paquetes.

## Fuentes y alcance

- API REST pública de GitHub: perfil y todos los repositorios públicos del usuario, con paginación. Las estrellas y la distribución de lenguajes excluyen forks.
- Calendario público de GitHub: celdas y sus etiquetas accesibles con el número de contribuciones. Si cambia el formato y no se pueden recuperar todos los conteos, el proceso falla antes de reemplazar las gráficas.
- Los porcentajes de lenguajes usan el lenguaje principal de cada repositorio, no bytes ni líneas de código. Los repositorios sin lenguaje se muestran por separado.
- El calendario y las cifras son una captura del momento de generación, no datos en vivo. No se consultan repositorios privados.

## Actualización

El workflow `profile-stats.yml` corre diariamente a las 11:17 UTC (06:17 de Colombia), al modificar el generador en `main`/`master`, o desde **Actions → Update profile charts → Run workflow**. Usa el token automático de GitHub Actions, sin secretos adicionales. Localmente el token es opcional y puede proporcionarse en `GITHUB_TOKEN` para ampliar el límite de la API.

El workflow necesita permiso de escritura sobre el contenido para guardar los SVG. Las reglas de protección de la rama pueden impedir el push automático; en ese caso las imágenes existentes permanecen disponibles y el fallo aparece en Actions. El calendario se obtiene desde HTML público y su parser se valida antes de escribir los archivos.
