# Guía de Contribución

## Cómo Contribuir al Sistema de Generación de Páginas

### Configuración del Entorno de Desarrollo

1. **Clonar el repositorio**
   ```bash
   git clone <url-del-repositorio>
   cd Sistema_De_Generacion_Paginas_WP
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

### Estándares de Código

#### Estilo de Código
- **PEP 8**: Seguir las convenciones de estilo de Python
- **Nombres descriptivos**: Variables y funciones con nombres claros
- **Comentarios**: Documentar funciones complejas
- **Docstrings**: Documentar todas las funciones públicas

#### Estructura de Commits
```
tipo(alcance): descripción breve

Descripción detallada del cambio (opcional)

Fixes #123
```

**Tipos de commit:**
- `feat`: Nueva funcionalidad
- `fix`: Corrección de errores
- `docs`: Cambios en documentación
- `style`: Cambios de formato (sin afectar lógica)
- `refactor`: Refactorización de código
- `test`: Agregar o modificar tests
- `chore`: Tareas de mantenimiento

### Proceso de Desarrollo

1. **Crear rama para nueva funcionalidad**
   ```bash
   git checkout -b feature/nombre-funcionalidad
   ```

2. **Desarrollar y probar**
   - Escribir código siguiendo estándares
   - Probar funcionalidad manualmente
   - Verificar que no se rompa funcionalidad existente

3. **Commit de cambios**
   ```bash
   git add .
   git commit -m "feat(generacion): agregar soporte para nuevos templates"
   ```

4. **Push y Pull Request**
   ```bash
   git push origin feature/nombre-funcionalidad
   ```
   - Crear Pull Request en la plataforma
   - Describir cambios realizados
   - Solicitar revisión

### Áreas de Contribución

#### 🎯 Funcionalidades Prioritarias
- **Nuevos formatos de exportación**: PDF, Word, etc.
- **Integración con APIs**: WooCommerce, Shopify
- **Optimización de rendimiento**: Generación más rápida
- **Validación avanzada**: Más checks de calidad

#### 🐛 Corrección de Errores
- **Manejo de errores**: Mejorar mensajes y recuperación
- **Compatibilidad**: Soporte para más formatos de archivo
- **Interfaz**: Mejorar usabilidad y accesibilidad

#### 📚 Documentación
- **Tutoriales**: Guías paso a paso
- **Ejemplos**: Casos de uso reales
- **API**: Documentación de funciones internas

### Testing

#### Pruebas Manuales
1. **Carga de archivos**: Probar con diferentes formatos CSV/Excel
2. **Generación**: Verificar salida HTML correcta
3. **Validación**: Comprobar URLs y datos
4. **Interfaz**: Probar todos los botones y funciones

#### Casos de Prueba Importantes
- Archivos CSV con caracteres especiales
- URLs de imágenes inválidas
- Productos sin algunos campos opcionales
- Archivos muy grandes (>1000 productos)
- Diferentes formatos de precio

### Reportar Problemas

#### Información Requerida
1. **Descripción del problema**: Qué esperabas vs qué pasó
2. **Pasos para reproducir**: Lista detallada
3. **Archivos de ejemplo**: CSV o datos que causan el problema
4. **Entorno**: Versión de Python, SO, etc.
5. **Logs**: Mensajes de error completos

#### Template de Issue
```markdown
## Descripción del Problema
[Descripción clara y concisa]

## Pasos para Reproducir
1. Paso 1
2. Paso 2
3. Paso 3

## Comportamiento Esperado
[Qué debería pasar]

## Comportamiento Actual
[Qué está pasando]

## Entorno
- SO: [Windows 10/11, etc.]
- Python: [3.8, 3.9, etc.]
- Versión del sistema: [commit hash o versión]

## Archivos Adicionales
[Adjuntar CSV de ejemplo, screenshots, etc.]
```

### Revisión de Código

#### Checklist para Revisores
- [ ] El código sigue los estándares de estilo
- [ ] Las funciones están documentadas
- [ ] No hay código duplicado
- [ ] Los cambios no rompen funcionalidad existente
- [ ] Los nombres de variables son descriptivos
- [ ] Se manejan adecuadamente los errores
- [ ] La funcionalidad fue probada manualmente

#### Checklist para Contribuidores
- [ ] He probado mi código localmente
- [ ] He actualizado la documentación si es necesario
- [ ] Mi código sigue los estándares del proyecto
- [ ] He agregado comentarios para código complejo
- [ ] Los commits tienen mensajes descriptivos

### Contacto

Para preguntas sobre contribuciones:
- Crear un issue con la etiqueta `question`
- Contactar al equipo de desarrollo

---

¡Gracias por contribuir al proyecto! 🚀