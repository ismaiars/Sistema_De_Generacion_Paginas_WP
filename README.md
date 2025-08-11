# Sistema de Generación de Páginas y Tarjetas de Productos

## Descripción
Sistema completo para la generación masiva de páginas de productos y tarjetas de catálogo para tienda óptica. Permite crear contenido HTML optimizado para WordPress con funcionalidades avanzadas de gestión de productos.

## Características Principales

### 🎯 Generación de Contenido
- **Páginas individuales de productos**: HTML completo con SEO optimizado
- **Tarjetas de catálogo masivas**: Grid responsivo con efectos hover
- **Vista previa en tiempo real**: Visualización antes de generar
- **Plantillas personalizables**: Soporte para templates HTML personalizados

### 📊 Gestión de Datos
- **Importación CSV/Excel**: Carga masiva de productos
- **Validación automática**: Verificación de datos y URLs
- **Historial de estados**: Seguimiento de cambios en productos
- **Filtros avanzados**: Selección por marca, precio, descuento

### 🎨 Características Visuales
- **Múltiples imágenes por producto**: Hasta 3 imágenes con hover
- **Logos de marca superpuestos**: Integración automática
- **Badges de descuento**: Cálculo automático de ofertas
- **Diseño responsivo**: Adaptable a móviles y tablets

### 🔗 Integración WordPress
- **Enlaces automáticos**: Generación de URLs amigables
- **Redirecciones personalizadas**: Archivo de enlaces configurables
- **Optimización SEO**: Meta tags y estructura semántica

## Instalación

### Requisitos Previos
- Python 3.8 o superior
- Tkinter (incluido en Python)
- Conexión a internet (para validación de URLs)

### Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Ejecución
```bash
python programa_2.py
```

## Estructura del Proyecto

```
Sistema_De_Generacion_Paginas_WP/
├── programa_2.py              # Aplicación principal
├── plantilla_tarjeta.html     # Template para tarjetas
├── Datos_2.csv               # Archivo de datos de productos
├── links_logos.txt           # URLs de logos de marcas
├── ligas-wp.txt             # Enlaces de redirección
├── Armazones.html           # Archivo de salida generado
├── historial_estado_productos.json  # Historial de cambios
├── README.md                # Este archivo
├── requirements.txt         # Dependencias Python
└── .gitignore              # Archivos excluidos de Git
```

## Uso

### 1. Preparación de Datos
1. **Archivo CSV**: Debe contener las columnas:
   - `SKU`: Código único del producto
   - `MARCA`: Nombre de la marca
   - `PRECIO PUBLICO`: Precio original
   - `PRECIO CON DESCUENTO`: Precio con oferta
   - `IMAGEN 1`, `IMAGEN 2`, `IMAGEN 3`: URLs de imágenes

2. **Archivo de logos** (`links_logos.txt`):
   ```
   marca1:https://ejemplo.com/logo1.webp
   marca2:https://ejemplo.com/logo2.webp
   ```

3. **Archivo de enlaces** (`ligas-wp.txt`):
   ```
   SKU1:https://tienda.com/producto1/
   SKU2:https://tienda.com/producto2/
   ```

### 2. Generación de Contenido

#### Páginas Individuales
1. Cargar archivo CSV
2. Seleccionar productos
3. Hacer clic en "Generar Páginas Seleccionadas"
4. Los archivos HTML se guardan en la carpeta del proyecto

#### Tarjetas de Catálogo
1. Cargar archivo CSV
2. Seleccionar productos para el catálogo
3. Hacer clic en "Generar Tarjetas Masivamente"
4. El resultado se guarda en `Armazones.html`

### 3. Personalización

#### Template de Tarjetas
Editar `plantilla_tarjeta.html` con los placeholders:
- `PLACEHOLDER_SKU`
- `PLACEHOLDER_MARCA`
- `PLACEHOLDER_LOGO`
- `PLACEHOLDER_IMAGEN_1`, `PLACEHOLDER_IMAGEN_2`, `PLACEHOLDER_IMAGEN_3`
- `PLACEHOLDER_PRECIO_ORIGINAL`
- `PLACEHOLDER_PRECIO_DESCUENTO`
- `PLACEHOLDER_ENLACE`

## Funcionalidades Avanzadas

### Filtros de Productos
- **Por marca**: Filtrar productos de marcas específicas
- **Por precio**: Rango de precios mínimo y máximo
- **Con descuento**: Solo productos en oferta
- **Con imágenes**: Solo productos con URLs de imagen válidas

### Validación Automática
- **URLs de imágenes**: Verificación de accesibilidad
- **Datos requeridos**: Validación de campos obligatorios
- **Formato de precios**: Conversión automática de formatos

### Historial y Seguimiento
- **Estados de productos**: Seguimiento de cambios
- **Log de operaciones**: Registro de generaciones
- **Backup automático**: Respaldo de configuraciones

## Solución de Problemas

### Problemas Comunes

**Las imágenes no aparecen:**
- Verificar que las URLs en el CSV sean correctas
- Comprobar que las columnas se llamen exactamente `IMAGEN 1`, `IMAGEN 2`, `IMAGEN 3`
- Validar conectividad a internet

**Error al cargar CSV:**
- Verificar codificación del archivo (UTF-8 recomendado)
- Comprobar que las columnas requeridas existan
- Revisar formato de datos (precios como números)

**Logos no aparecen:**
- Verificar formato del archivo `links_logos.txt`
- Comprobar que los nombres de marca coincidan exactamente
- Validar URLs de logos

## Contribución

1. Fork del proyecto
2. Crear rama para nueva funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## Licencia

Este proyecto es de uso interno para Ópticas Kairoz.

## Contacto

Para soporte técnico o consultas sobre el sistema, contactar al equipo de desarrollo.

---

**Versión**: 2.0  
**Última actualización**: Enero 2025  
**Compatibilidad**: Python 3.8+, Windows 10/11