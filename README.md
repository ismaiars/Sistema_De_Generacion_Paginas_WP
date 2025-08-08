## Sistema de Generación de Páginas y Catálogo (WordPress)

Aplicación de escritorio (Tkinter) para generar:
- Páginas HTML individuales de productos a partir de datos en CSV/Excel
- Tarjetas de producto para catálogos HTML, con opción de insertarlas automáticamente

El flujo está pensado para alimentar páginas/tiendas tipo WordPress/WooCommerce a través de HTML estático basado en plantillas.

### Características principales
- Carga de CSV/Excel y visualización en tabla con selección por fila
- Generación de página individual de producto desde una plantilla HTML
- Generación de tarjeta individual y copia/insertado directo en un catálogo HTML existente
- Generación masiva de múltiples páginas HTML a partir de una plantilla
- Validación de URLs de imagen en segundo plano
- Historial de estados por SKU (verde/rojo/normal) persistido en `historial_estado_productos.json`

---

## Requisitos
- Windows 10/11 (probado en Windows)
- Python 3.9+ (recomendado 3.10+)

Dependencias Python:
- `pandas`
- `requests`
- `pyperclip`
- `openpyxl` (solo si vas a cargar archivos `.xlsx`)

Instalación rápida (PowerShell):

```powershell
cd C:\Users\LENOVO\Desktop\Sistema_De_Generacion_Paginas_WP\Sistema_De_Generacion_Paginas_WP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pandas requests pyperclip openpyxl
```

---

## Ejecución

```powershell
python programa_2.py
```

La aplicación abre una ventana con 3 pestañas:
1) Página Individual
2) Catálogo y Tarjetas
3) Generación Masiva

---

## Flujo de trabajo

### 1) Preparar los datos (CSV/Excel)
El archivo debe contener, con estos nombres exactos, al menos las siguientes columnas usadas por la app:
- `IMAGEN 1`, `IMAGEN 2`, `IMAGEN 3` (URLs públicas de imágenes)
- `Precio normal`, `Porcentajede descuento`, `precio con descuento`
- `Valor(es) del atributo 1` (SKU)
- `Valor(es) del atributo 2` (Marca)
- `Valor(es) del atributo 3` … `Valor(es) del atributo 13` (Tipo, Color, Forma, Material, Varillas, Clip, Color de Mica, Medida, Puente, Accesorios, Garantía)
- Opcionalmente pueden existir: `SKU`, `Etiquetas`, `Tipo`, `Categorías`, `¿Existencias?`, `Inventario`

Notas:
- Las 3 imágenes son obligatorias para generar la página individual.
- En generación masiva, se usa `SKU` y/o `Valor(es) del atributo 1` como identificador.

### 2) Formato del archivo de logos de marcas
Puedes cargar:
- CSV de 2 columnas: `marca, url_logo`
- TXT donde cada línea puede ser: `marca:url_logo` o `marca, url_logo` o `marca url_logo`

Ejemplos válidos de TXT/CSV:
```
rayban:https://cdn.ejemplo.com/logos/rayban.svg
oakley, https://cdn.ejemplo.com/logos/oakley.svg
vogue https://cdn.ejemplo.com/logos/vogue.svg
```

Importante: la app normaliza la marca eliminando espacios, guiones y guiones bajos y usando minúsculas. Asegúrate que la clave en el archivo de logos coincida con la marca del CSV tras esa normalización.

### 3) Pestaña: Página Individual
1. Carga tu CSV/Excel con “Cargar CSV”.
2. (Opcional) Selecciona la plantilla de producto con “Buscar Plantilla”. Si no seleccionas, el código intenta usar una plantilla por defecto. En este proyecto tienes un ejemplo `pagina_producto_RB2398.html`. Si el programa no encuentra la plantilla por defecto, selecciona manualmente la tuya.
3. Selecciona un producto en la tabla. Los campos de imágenes se auto-rellenan con `IMAGEN 1/2/3`.
4. Asegúrate de que haya 3 URLs válidas en Imagen 1/2/3.
5. Haz clic en “Crear Página Individual” y elige dónde guardar el `.html` generado.

Qué reemplaza la plantilla:
- Marca (elemento con id `product-brand`)
- Modelo/SKU (elemento con id `product-model`)
- Precios: precio normal (tachado), badge de descuento y precio con descuento
- Imágenes principales y miniaturas (y el array JS `const imageSources = [..]`)
- Tabla de especificaciones (SKU, Marca, Tipo, Color, Forma, Material, Varillas, Clip, Color de Mica, Medida, Puente, Accesorios, Garantía)

### 4) Pestaña: Catálogo y Tarjetas
1. Selecciona el archivo de catálogo HTML (ej. una página de tienda) para extraer la plantilla de la tarjeta.
2. Carga el archivo de logos de marcas (CSV/TXT). La app buscará el logo por marca normalizada.
3. Con un producto seleccionado en la tabla, presiona “Vista previa de Tarjeta”.
4. Puedes:
   - “Copiar Código”: copia el HTML de la tarjeta al portapapeles.
   - “Agregar al Catálogo”: inserta la tarjeta justo antes de `</main>` en el catálogo seleccionado.

Consejos:
- Si no se encuentra el logo para la marca, revisa el archivo de logos y que la clave coincida (normalización).
- Puedes escribir manualmente un link de redirección para la tarjeta (campo de enlace en la pestaña).

### 5) Pestaña: Generación Masiva
1. Elige la plantilla HTML base para producto.
2. Selecciona el directorio de salida.
3. Marca los productos (checkbox en la primera columna) o usa las acciones para seleccionar en bloque.
4. Pulsa “Generar” y confirma. Se crearán múltiples `.html` con nombres seguros basados en el SKU.

Estados y sincronización:
- Los estados por SKU (verde/rojo/normal) se guardan en `historial_estado_productos.json` y se sincronizan entre pestañas.

---

## Validación de imágenes
La app valida en segundo plano que cada URL de imagen responda `200` y tenga `content-type` de imagen mediante una petición `HEAD`. Si alguna falla, verás una advertencia. Aun así, puedes previsualizar/generar, pero es recomendable corregir enlaces.

---

## Personalizar tu plantilla HTML
Para que los reemplazos funcionen, tu plantilla debe contener (o ser compatible con) estos marcadores/selectores:
- Imágenes principales y miniaturas con rutas “placeholder” que el programa sustituye (se esperan tres)
- Array JS `const imageSources = ["", "", ""];`
- Marca en un elemento con id `product-brand`
- Modelo/SKU en un elemento con id `product-model`
- Spans de precios con clases: `old-price` y `new-price`; badge de descuento visible en el HTML
- Tabla de especificaciones con filas de texto identificables (SKU, Marca, Tipo, Color, Forma, Material, Varillas, Clip, Color de Mica, Medida, Puente, Accesorios, Garantía)

Si partís de `pagina_producto_RB2398.html`, ya tienes un ejemplo funcional.

---

## Solución de problemas
- “Faltan los 3 links de imagen”: agrega `IMAGEN 1/2/3` en tu CSV/Excel o complétalos en la UI antes de generar.
- “No se encuentra la plantilla por defecto”: selecciona manualmente tu plantilla HTML desde el botón “Buscar Plantilla”.
- “No aparece el logo”: revisa el archivo de logos; la marca se normaliza (minúsculas, sin espacios/guiones/guiones bajos).
- “Números de precio se ven mal”: incluye el símbolo `$` en tus columnas de precios o ajusta el formato en el CSV/Excel.

---

## Estructura del proyecto (resumen)
- `programa_2.py`: aplicación principal (Tkinter)
- `pagina_producto_RB2398.html`: ejemplo de plantilla de página de producto
- `Datos_2.csv` / `Datos_2.xlsx`: ejemplos de datos
- `links_logos.txt`: ejemplo de mapeo de marcas a logos
- `historial_estado_productos.json`: se crea/actualiza automáticamente por la app

---

## Licencia
Proyecto de uso interno/educativo. Ajusta según tus necesidades.


