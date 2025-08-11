import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import pyperclip
import re
import json
import threading
from urllib.parse import urlparse
import requests
from concurrent.futures import ThreadPoolExecutor

# Cache global para plantillas HTML
_PLANTILLA_CACHE = {}

# Cache para validación de URLs
_URL_VALIDATION_CACHE = {}

# Función para validar URLs de imágenes en background
def validar_url_imagen(url, timeout=5):
    """Valida si una URL de imagen es accesible."""
    if not url or url in _URL_VALIDATION_CACHE:
        return _URL_VALIDATION_CACHE.get(url, False)
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            _URL_VALIDATION_CACHE[url] = False
            return False
            
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        is_valid = response.status_code == 200 and 'image' in response.headers.get('content-type', '')
        _URL_VALIDATION_CACHE[url] = is_valid
        return is_valid
    except:
        _URL_VALIDATION_CACHE[url] = False
        return False

# Patrones regex compilados para mejor rendimiento
_REGEX_PATTERNS = {
    'img_src_1': re.compile(r'src="[^"]*RB2398-1_resultado\.webp"'),
    'img_src_2': re.compile(r'src="[^"]*RB2398-2_resultado\.webp"'),
    'img_src_3': re.compile(r'src="[^"]*RB2398-3_resultado\.webp"'),
    'thumb_1': re.compile(r'src="[^"]*1_resultado\.webp"'),
    'thumb_2': re.compile(r'src="[^"]*2_resultado\.webp"'),
    'thumb_3': re.compile(r'src="[^"]*3_resultado\.webp"'),
    'image_sources': re.compile(r'const imageSources = \[[^\]]*\];'),
    'product_brand': re.compile(r'<h1[^>]*id="product-brand"[^>]*>[^<]*</h1>'),
    'product_model': re.compile(r'<p[^>]*id="product-model"[^>]*>[^<]*</p>'),
    'old_price': re.compile(r'<span class="text-2xl text-gray-400 line-through mr-2">[^<]*</span>'),
    'discount_badge': re.compile(r'<span class="inline-block bg-red-100 text-red-600 text-lg font-bold px-2 py-1 rounded align-middle mr-2">[^<]*</span>'),
    'new_price': re.compile(r'<span class="text-5xl font-extrabold text-black">[^<]*</span>')
}

# ---------------- FUNCIONES AUXILIARES PARA HTML ----------------
def cargar_plantilla_html(path):
    if not os.path.exists(path):
        messagebox.showerror("Error", f"No se encontró la plantilla base '{os.path.basename(path)}'.")
        return None
    
    # Usar cache para evitar lecturas repetidas
    if path in _PLANTILLA_CACHE:
        return _PLANTILLA_CACHE[path]
    
    with open(path, 'r', encoding='utf-8') as f:
        contenido = f.read()
        _PLANTILLA_CACHE[path] = contenido
        return contenido

def buscar_logo_marca(marca, logos_dict):
    # Normaliza la marca quitando espacios, minúsculas y caracteres especiales
    # Optimización: usar translate para mejor rendimiento
    if not marca:
        return ''
    
    # Tabla de traducción para eliminar caracteres especiales de una vez
    trans_table = str.maketrans('', '', ' -_')
    clave = str(marca).strip().lower().translate(trans_table)
    
    print(f"[DEBUG] Buscando logo para marca: '{clave}' en {logos_dict}")
    logo = logos_dict.get(clave, '')
    if not logo:
        print(f"[DEBUG] No se encontró logo para la marca: '{clave}'")
    return logo

def generar_tarjeta_catalogo(row, imagenes, logo_marca, link_producto, old_price, new_price, descuento, plantilla_tarjeta):
    # Usa la plantilla de tarjeta del catálogo (de Armazones-Tienda.html)
    # Reemplaza los campos clave
    html = plantilla_tarjeta
    html = re.sub(r'src="[^"]+" alt="[^"]+ - Vista 1" class="product-img active"', f'src="{imagenes[0]}" alt="{row.get('SKU','')} - {row.get('Marca','')} - Vista 1" class="product-img active"', html)
    html = re.sub(r'src="[^"]+" alt="[^"]+ - Vista 2" class="product-img"', f'src="{imagenes[1]}" alt="{row.get('SKU','')} - {row.get('Marca','')} - Vista 2" class="product-img"', html)
    html = re.sub(r'src="[^"]+" alt="[^"]+ - Vista 3" class="product-img"', f'src="{imagenes[2]}" alt="{row.get('SKU','')} - {row.get('Marca','')} - Vista 3" class="product-img"', html)
    html = re.sub(r'<div class="product-brand-overlay"><img src="[^"]+" alt="[^"]+"></div>', f'<div class="product-brand-overlay"><img src="{logo_marca}" alt="Logo {row.get('Marca','')}"></div>', html)
    html = re.sub(r'<div class="discount-badge">[^<]*</div>', f'<div class="discount-badge">{descuento} de descuento</div>' if descuento else '', html)
    html = re.sub(r'onclick="window.open\([^)]+\)"', f'onclick="window.open(\'{link_producto}\',\'_blank\')"', html)
    # --- Ajuste de bloque de info: marca azul mayúsculas, SKU negritas debajo ---
    # Reemplazo de bloque product-info
    marca = row.get('Valor(es) del atributo 2', '').upper()
    sku = row.get('Valor(es) del atributo 1', '')
    bloque_info = (
        f'<span class="product-brand text-blue-600 uppercase">{marca}</span>\n'
        f'<h2 class="product-name font-bold">{sku}</h2>'
    )
    # Reemplaza el bloque de marca y SKU
    html = re.sub(r'<span class="product-brand">[^<]+</span>\s*<h2 class="product-name">[^<]+</h2>', bloque_info, html)
    # Precios
    html = re.sub(r'<span class="old-price">[^<]*</span>', f'<span class="old-price">{old_price}</span>', html)
    html = re.sub(r'<span class="new-price">[^<]*</span>', f'<span class="new-price">{new_price}</span>', html)
    return html

def generar_pagina_individual_desde_plantilla(row, imagenes, plantilla_path):
    # Cargar la plantilla seleccionada o la predeterminada
    if plantilla_path and os.path.exists(plantilla_path):
        path = plantilla_path
    else:
        path = os.path.join(os.path.dirname(__file__), 'pagina_producto_VLE41684.html')
    html = cargar_plantilla_html(path)
    if html is None:
        return None

    # --- Reemplazo de imágenes principales y thumbnails (6 veces: 3 en <img>, 3 en JS) ---
    # Si no hay imagen, dejar src=""
    img1 = row.get('IMAGEN 1', '') or ''
    img2 = row.get('IMAGEN 2', '') or ''
    img3 = row.get('IMAGEN 3', '') or ''
    
    # Usar patrones regex compilados para mejor rendimiento
    html = _REGEX_PATTERNS['img_src_1'].sub(f'src="{img1}"', html)
    html = _REGEX_PATTERNS['img_src_2'].sub(f'src="{img2}"', html)
    html = _REGEX_PATTERNS['img_src_3'].sub(f'src="{img3}"', html)
    
    # Reemplazo en miniaturas (puede haber más de una aparición por imagen)
    html = _REGEX_PATTERNS['thumb_1'].sub(f'src="{img1}"', html)
    html = _REGEX_PATTERNS['thumb_2'].sub(f'src="{img2}"', html)
    html = _REGEX_PATTERNS['thumb_3'].sub(f'src="{img3}"', html)
    
    # Reemplazo en el script JS (array imageSources, siempre 3, solo links del CSV/campos, o vacío)
    img1_js = f'"{img1}"'
    img2_js = f'"{img2}"'
    img3_js = f'"{img3}"'
    html = _REGEX_PATTERNS['image_sources'].sub(f'const imageSources = [{img1_js}, {img2_js}, {img3_js}];', html)

    # --- Reemplazo de textos principales (marca, modelo, precios, descuento) ---
    # Usar patrones regex compilados para mejor rendimiento
    html = _REGEX_PATTERNS['product_brand'].sub(f'<h1 id="product-brand" class="text-4xl md:text-5xl font-bold text-orange-500 uppercase">{row.get("Valor(es) del atributo 2", "")}</h1>', html)
    html = _REGEX_PATTERNS['product_model'].sub(f'<p id="product-model" class="text-xl text-gray-400 mb-4">{row.get("Valor(es) del atributo 1", "")}</p>', html)
    html = _REGEX_PATTERNS['old_price'].sub(f'<span class="text-2xl text-gray-400 line-through mr-2">{row.get("Precio normal", "")}</span>', html)
    html = _REGEX_PATTERNS['discount_badge'].sub(f'<span class="inline-block bg-red-100 text-red-600 text-lg font-bold px-2 py-1 rounded align-middle mr-2">{row.get("Porcentajede descuento", "")}</span>', html)
    html = _REGEX_PATTERNS['new_price'].sub(f'<span class="text-5xl font-extrabold text-black">{row.get("precio con descuento", "")}</span>', html)

    # --- Reemplazo de tabla de especificaciones ---
    # Mapeo de campos: (ajusta si tus columnas cambian)
    # Usar lambda functions para evitar problemas con group references
    tabla_replacements = [
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 1", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 2", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 3", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 4", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 5", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 6", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 7", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 8", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 9", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 10", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 11", "")),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 12", "")),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', row.get("Valor(es) del atributo 13", "")),
    ]
    
    for patron, valor in tabla_replacements:
        # Use lambda function to safely replace without group reference issues
        html = re.sub(patron, lambda m: m.group(0).replace('[^<]*', valor), html)

    return html

# ---------------- GUI PRINCIPAL ----------------
class GeneradorCatalogoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Productos para Catálogo")
        self.root.configure(bg='#f8f9fa')
        # --- INICIAR EN PANTALLA COMPLETA ---
        try:
            self.root.state('zoomed')  # Windows
        except:
            self.root.attributes('-zoomed', True)  # Linux/Mac
        self.root.minsize(1000, 700)
        self.df = None
        self.producto_actual = None
        self.catalogo_path = ''
        self.campos_csv = []
        self.plantilla_ind_path = ''
        self.plantilla_tarjeta = ''
        self.logos_dict = {}
        self.tarjeta_html_actual = ''
        self.checked_rows = {}  # Dict para saber qué filas están marcadas
        self.checkbox_images = {
            True: tk.PhotoImage(data='''R0lGODlhEAAQAMQfAFVVVf///wAAAMzMzPz8/Obm5gAAAFhYWPj4+P39/fb29gAAAJmZmQAAAPDw8AAAAGZmZgAAAJmZmf///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAB8ALAAAAAAQABAAAAVu4CeOZGmeaKqubOu+cCzPdFQFACHhQAOw=='''),
            False: tk.PhotoImage(data='''R0lGODlhEAAQAMQfAFVVVf///wAAAMzMzPz8/Obm5gAAAFhYWPj4+P39/fb29gAAAJmZmQAAAPDw8AAAAGZmZgAAAJmZmf///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAB8ALAAAAAAQABAAAAVu4CeOZGmeaKqubOu+cCzPdFQFACHhQAOw=='''),
        }
        self.estado_filas = {}  # Dict para el estado visual de cada fila
        self.historial_estado_path = 'historial_estado_productos.json'
        
        # Variables para optimizaciones de Fase 2
        self.progress_var = tk.StringVar(value="")
        self.progress_label = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Variables para pestaña de tarjetas masivas
        self.productos_seleccionados_tarjetas = set()
        self.tarjetas_generadas = {}
        self.links_redireccion = {}  # Dict para almacenar links de redirección por SKU
        self.progress_var_tarjetas = None  # Se inicializa en _configurar_tab4
        
        self.cargar_historial_estado()
        
        # Tabla de traducción para normalización de marcas (optimización)
        self.trans_table = str.maketrans('', '', ' -_')
        
        # Configurar limpieza al cerrar
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Configuración de estilos modernos ---
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar estilo para las pestañas
        style.configure('Modern.TNotebook', background='#f8f9fa', borderwidth=0)
        style.configure('Modern.TNotebook.Tab', 
                       padding=[24, 12], 
                       font=('Segoe UI', 10, 'normal'),
                       background='#ffffff',
                       foreground='#495057',
                       borderwidth=1,
                       relief='solid')
        style.map('Modern.TNotebook.Tab', 
                 background=[('selected', '#007bff'), ('!selected', '#ffffff')],
                 foreground=[('selected', '#ffffff'), ('!selected', '#495057')],
                 borderwidth=[('selected', 0), ('!selected', 1)])
        
        # Crear frame principal con scrollbar
        main_frame = tk.Frame(root, bg='#f8f9fa')
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear canvas y scrollbar
        self.canvas = tk.Canvas(main_frame, bg='#f8f9fa', highlightthickness=0)
        self.scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#f8f9fa')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Hacer que el frame se expanda al ancho del canvas
        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=event.width)
        
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
        # Configurar scroll con rueda del mouse
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Empaquetar canvas y scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.notebook = ttk.Notebook(self.scrollable_frame, style='Modern.TNotebook')
        self.notebook.pack(fill="both", expand=True)

        # --- Pestaña 1: Página individual ---
        self.tab1 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab1, text="  Página Individual  ")
        # --- Pestaña 2: Tarjeta individual y catálogo ---
        self.tab2 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab2, text="  Catálogo y Tarjetas  ")
        
        # --- Pestaña 3: Generación masiva ---
        self.tab3 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab3, text="  Generación Masiva  ")
        
        # --- Pestaña 4: Generación masiva de tarjetas ---
        self.tab4 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab4, text="  Tarjetas Masivas  ")

        # --- Pestaña 1 ---
        # Header con título
        header1 = tk.Frame(self.tab1, bg="#ffffff", height=60)
        header1.pack(fill="x", padx=20, pady=(20, 10))
        header1.pack_propagate(False)
        title1 = tk.Label(header1, text="Generación de Páginas Individuales", 
                         font=('Segoe UI', 16, 'bold'), fg="#212529", bg="#ffffff")
        title1.pack(side="left", pady=15)
        
        # Indicador de progreso
        self.progress_label = tk.Label(header1, textvariable=self.progress_var,
                                     font=('Segoe UI', 9), fg="#6c757d", bg="#ffffff")
        self.progress_label.pack(side="right", pady=15)
        
        # Top frame horizontal para carga CSV y edición imágenes
        top_main1 = tk.Frame(self.tab1, bg="#ffffff")
        top_main1.pack(fill="x", padx=20, pady=10)
        
        # Frame de carga CSV con estilo moderno
        csv_frame = tk.LabelFrame(top_main1, text="Configuración", 
                                 font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                 relief="solid", bd=1)
        csv_frame.pack(fill="x", pady=(0, 15))
        
        # Contenedor interno para los controles
        csv_controls = tk.Frame(csv_frame, bg="#ffffff")
        csv_controls.pack(fill="x", padx=15, pady=15)
        
        # Fila 1: Cargar CSV y Reiniciar Historial
        csv_row1 = tk.Frame(csv_controls, bg="#ffffff")
        csv_row1.pack(fill="x", pady=(0, 10))
        self.btn_cargar = tk.Button(csv_row1, text="📁 Cargar CSV", command=self.cargar_csv,
                                   font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#007bff",
                                   relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_cargar.pack(side="left")
        
        self.btn_reiniciar_historial = tk.Button(csv_row1, text="🔄 Reiniciar Historial", command=self.reiniciar_historial,
                                                 font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#dc3545",
                                                 relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_reiniciar_historial.pack(side="left", padx=(10, 0))
        
        # Fila 2: Plantilla
        csv_row2 = tk.Frame(csv_controls, bg="#ffffff")
        csv_row2.pack(fill="x")
        tk.Label(csv_row2, text="Plantilla página individual:", 
                font=('Segoe UI', 9), fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_plantilla_ind = tk.Entry(csv_row2, width=40, font=('Segoe UI', 9),
                                           relief="solid", bd=1, bg="#ffffff")
        self.entry_plantilla_ind.pack(side="left", padx=(0, 10))
        self.btn_buscar_plantilla_ind = tk.Button(csv_row2, text="🔍 Buscar", command=self.buscar_plantilla_ind,
                                                 font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                                 relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_buscar_plantilla_ind.pack(side="left")
        
        # Tabla de productos
        self.tree = None
        self.tree_frame = tk.Frame(self.tab1, bg="#ffffff")
        self.tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Scrollbars para el TreeView individual
        self.yscroll = tk.Scrollbar(self.tree_frame, orient='vertical')
        self.xscroll = tk.Scrollbar(self.tree_frame, orient='horizontal')
        
        # Configurar grid para scrollbars
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        # Frame horizontal para edición de imágenes y datos producto
        edit_main1 = tk.Frame(top_main1, bg="#ffffff")
        edit_main1.pack(fill="x", pady=(0, 10))
        
        # --- Info producto seleccionado ---
        self.info_producto_frame = tk.LabelFrame(edit_main1, text="Información del Producto", 
                                               font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                               relief="solid", bd=1)
        self.info_producto_frame.pack(side="left", fill="y", padx=(0, 15))
        
        info_content = tk.Frame(self.info_producto_frame, bg="#ffffff")
        info_content.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.lbl_info_sku = tk.Label(info_content, text="SKU: ", anchor="w", bg="#ffffff", 
                                    font=("Segoe UI", 10, "bold"), fg="#212529")
        self.lbl_info_sku.pack(fill="x", pady=(0, 8))
        self.lbl_info_marca = tk.Label(info_content, text="Marca: ", anchor="w", bg="#ffffff", 
                                      font=("Segoe UI", 10), fg="#495057")
        self.lbl_info_marca.pack(fill="x", pady=(0, 8))
        self.lbl_info_tipo = tk.Label(info_content, text="Tipo: ", anchor="w", bg="#ffffff", 
                                     font=("Segoe UI", 10), fg="#495057")
        self.lbl_info_tipo.pack(fill="x", pady=(0, 8))
        
        # Frame de edición de imágenes
        edit_frame1 = tk.LabelFrame(edit_main1, text="Configuración de Imágenes", 
                                   font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                   relief="solid", bd=1)
        edit_frame1.pack(side="left", fill="both", expand=True)
        
        img_content = tk.Frame(edit_frame1, bg="#ffffff")
        img_content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Grid para las imágenes con mejor organización
        tk.Label(img_content, text="Imagen 1:", bg="#ffffff", font=("Segoe UI", 9), fg="#495057").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.img1 = tk.Entry(img_content, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img1.grid(row=0, column=1, padx=(10, 0), pady=(0, 10), sticky="ew")
        
        tk.Label(img_content, text="Imagen 2:", bg="#ffffff", font=("Segoe UI", 9), fg="#495057").grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.img2 = tk.Entry(img_content, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img2.grid(row=1, column=1, padx=(10, 0), pady=(0, 10), sticky="ew")
        
        tk.Label(img_content, text="Imagen 3:", bg="#ffffff", font=("Segoe UI", 9), fg="#495057").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.img3 = tk.Entry(img_content, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img3.grid(row=2, column=1, padx=(10, 0), pady=(0, 15), sticky="ew")
        
        # Configurar peso de columnas
        img_content.grid_columnconfigure(1, weight=1)
        
        # Botón para generar página individual
        self.btn_pagina_individual = tk.Button(img_content, text="🚀 Generar Página Individual", 
                                              command=self.crear_pagina_individual,
                                              font=('Segoe UI', 10, 'bold'), fg="#ffffff", bg="#28a745",
                                              relief="flat", padx=25, pady=10, cursor="hand2")
        self.btn_pagina_individual.grid(row=3, column=0, columnspan=2, pady=(10, 0))

        # --- Pestaña 2 ---
        # Header con título
        header2 = tk.Frame(self.tab2, bg="#ffffff", height=60)
        header2.pack(fill="x", padx=20, pady=(20, 10))
        header2.pack_propagate(False)
        title2 = tk.Label(header2, text="Generación de Catálogo y Tarjetas", 
                         font=('Segoe UI', 16, 'bold'), fg="#212529", bg="#ffffff")
        title2.pack(side="left", pady=15)
        
        # Frame de configuración
        config_frame2 = tk.LabelFrame(self.tab2, text="Configuración de Archivos", 
                                     font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                     relief="solid", bd=1)
        config_frame2.pack(fill="x", padx=20, pady=(0, 15))
        
        config_content = tk.Frame(config_frame2, bg="#ffffff")
        config_content.pack(fill="x", padx=15, pady=15)
        
        # Fila 1: Catálogo
        catalogo_row = tk.Frame(config_content, bg="#ffffff")
        catalogo_row.pack(fill="x", pady=(0, 10))
        tk.Label(catalogo_row, text="Archivo de catálogo:", 
                font=('Segoe UI', 9), fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_catalogo = tk.Entry(catalogo_row, width=50, font=('Segoe UI', 9),
                                      relief="solid", bd=1, bg="#ffffff")
        self.entry_catalogo.pack(side="left", padx=(0, 10))
        self.btn_buscar_catalogo = tk.Button(catalogo_row, text="🔍 Buscar", command=self.buscar_catalogo,
                                            font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                            relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_buscar_catalogo.pack(side="left")
        
        # Fila 2: Logos
        logos_row = tk.Frame(config_content, bg="#ffffff")
        logos_row.pack(fill="x")
        tk.Label(logos_row, text="Archivo de logos de marcas:", 
                font=('Segoe UI', 9), fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_logos = tk.Entry(logos_row, width=50, font=('Segoe UI', 9),
                                   relief="solid", bd=1, bg="#ffffff")
        self.entry_logos.pack(side="left", padx=(0, 10))
        self.btn_cargar_logos = tk.Button(logos_row, text="📁 Cargar", command=self.cargar_logos,
                                         font=('Segoe UI', 9), fg="#ffffff", bg="#007bff",
                                         relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_cargar_logos.pack(side="left")
        # Info del producto seleccionado
        info_frame2 = tk.LabelFrame(self.tab2, text="Información del Producto Seleccionado", 
                                   font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                   relief="solid", bd=1)
        info_frame2.pack(fill="x", padx=20, pady=(0, 15))
        
        info_content2 = tk.Frame(info_frame2, bg="#ffffff")
        info_content2.pack(fill="x", padx=15, pady=15)
        
        # Columna izquierda: Datos del producto
        left_col = tk.Frame(info_content2, bg="#ffffff")
        left_col.pack(side="left", fill="y", padx=(0, 30))
        
        tk.Label(left_col, text="Información del Producto:", 
                font=('Segoe UI', 10, 'bold'), fg="#212529", bg="#ffffff").pack(anchor="w", pady=(0, 10))
        
        self.lbl_marca = tk.Label(left_col, text="Marca: ", bg="#ffffff", 
                                 font=("Segoe UI", 9, "bold"), fg="#495057")
        self.lbl_marca.pack(anchor="w", pady=(0, 5))
        self.lbl_sku = tk.Label(left_col, text="SKU: ", bg="#ffffff", 
                               font=("Segoe UI", 9), fg="#495057")
        self.lbl_sku.pack(anchor="w", pady=(0, 5))
        self.lbl_precio_normal = tk.Label(left_col, text="Precio normal: ", bg="#ffffff", 
                                         font=("Segoe UI", 9), fg="#495057")
        self.lbl_precio_normal.pack(anchor="w", pady=(0, 5))
        self.lbl_precio_desc = tk.Label(left_col, text="Precio con descuento: ", bg="#ffffff", 
                                       font=("Segoe UI", 9), fg="#495057")
        self.lbl_precio_desc.pack(anchor="w", pady=(0, 5))
        self.lbl_descuento = tk.Label(left_col, text="% Descuento: ", bg="#ffffff", 
                                     font=("Segoe UI", 9), fg="#495057")
        self.lbl_descuento.pack(anchor="w", pady=(0, 5))
        
        # Columna derecha: Imágenes editables
        right_col = tk.Frame(info_content2, bg="#ffffff")
        right_col.pack(side="left", fill="both", expand=True)
        
        tk.Label(right_col, text="Configuración de Imágenes:", 
                font=('Segoe UI', 10, 'bold'), fg="#212529", bg="#ffffff").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        tk.Label(right_col, text="Imagen 1:", bg="#ffffff", 
                font=("Segoe UI", 9), fg="#495057").grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.img1_2 = tk.Entry(right_col, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img1_2.grid(row=1, column=1, padx=(10, 0), pady=(0, 8), sticky="ew")
        
        tk.Label(right_col, text="Imagen 2:", bg="#ffffff", 
                font=("Segoe UI", 9), fg="#495057").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.img2_2 = tk.Entry(right_col, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img2_2.grid(row=2, column=1, padx=(10, 0), pady=(0, 8), sticky="ew")
        
        tk.Label(right_col, text="Imagen 3:", bg="#ffffff", 
                font=("Segoe UI", 9), fg="#495057").grid(row=3, column=0, sticky="w", pady=(0, 5))
        self.img3_2 = tk.Entry(right_col, width=50, font=('Segoe UI', 9), relief="solid", bd=1)
        self.img3_2.grid(row=3, column=1, padx=(10, 0), pady=(0, 8), sticky="ew")
        
        # Configurar peso de columnas
        right_col.grid_columnconfigure(1, weight=1)
        # Link de redirección
        link_frame = tk.LabelFrame(self.tab2, text="Configuración de Enlace", 
                                  font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                  relief="solid", bd=1)
        link_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        link_content = tk.Frame(link_frame, bg="#ffffff")
        link_content.pack(fill="x", padx=15, pady=15)
        
        tk.Label(link_content, text="Link de redirección:", 
                font=('Segoe UI', 9), fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_link_tarjeta = tk.Entry(link_content, width=70, font=('Segoe UI', 9),
                                          relief="solid", bd=1, bg="#ffffff")
        self.entry_link_tarjeta.pack(side="left", fill="x", expand=True)
        
        # Botones de acción
        actions_frame = tk.LabelFrame(self.tab2, text="Acciones", 
                                     font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                     relief="solid", bd=1)
        actions_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        actions_content = tk.Frame(actions_frame, bg="#ffffff")
        actions_content.pack(fill="x", padx=15, pady=15)
        
        self.btn_generar_tarjeta = tk.Button(actions_content, text="🎨 Generar Tarjeta", 
                                            command=self.vista_previa_tarjeta,
                                            font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#007bff",
                                            relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_generar_tarjeta.pack(side="left", padx=(0, 10))
        
        self.btn_copiar_tarjeta = tk.Button(actions_content, text="📋 Copiar Código", 
                                           command=self.copiar_tarjeta, state="disabled",
                                           font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#6c757d",
                                           relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_copiar_tarjeta.pack(side="left", padx=(0, 10))
        
        self.btn_insertar_tarjeta = tk.Button(actions_content, text="➕ Agregar al Catálogo", 
                                             command=self.insertar_en_catalogo, state="disabled",
                                             font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#28a745",
                                             relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_insertar_tarjeta.pack(side="left")
        
        # Área de previsualización
        preview_frame = tk.LabelFrame(self.tab2, text="Previsualización del Código", 
                                     font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                     relief="solid", bd=1)
        preview_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.txt_tarjeta_frame = tk.Frame(preview_frame, bg="#ffffff")
        self.txt_tarjeta_frame.pack(fill="both", expand=True, padx=15, pady=15)
        self.txt_tarjeta_scroll_y = tk.Scrollbar(self.txt_tarjeta_frame, orient="vertical")
        self.txt_tarjeta_scroll_y.pack(side="right", fill="y")
        self.txt_tarjeta_scroll_x = tk.Scrollbar(self.txt_tarjeta_frame, orient="horizontal")
        self.txt_tarjeta_scroll_x.pack(side="bottom", fill="x")
        self.txt_tarjeta = tk.Text(self.txt_tarjeta_frame, height=18, wrap="none", 
                                  yscrollcommand=self.txt_tarjeta_scroll_y.set, 
                                  xscrollcommand=self.txt_tarjeta_scroll_x.set,
                                  font=('Consolas', 9), bg="#f8f9fa", fg="#212529",
                                  relief="solid", bd=1, selectbackground="#007bff",
                                  selectforeground="#ffffff", insertbackground="#007bff")
        self.txt_tarjeta.pack(fill="both", expand=True)
        self.txt_tarjeta_scroll_y.config(command=self.txt_tarjeta.yview)
        self.txt_tarjeta_scroll_x.config(command=self.txt_tarjeta.xview)
        
        # Los efectos hover se configurarán al final del constructor

        # Sincronización de imágenes y datos entre pestañas
        self.img1.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img2.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img3.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img1_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.img2_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.img3_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.notebook.bind('<<NotebookTabChanged>>', self.update_tab2_fields)
        
        # --- Pestaña 3: Generación Masiva ---
        # Header con título
        header3 = tk.Frame(self.tab3, bg="#ffffff", height=60)
        header3.pack(fill="x", padx=20, pady=(20, 10))
        header3.pack_propagate(False)
        title3 = tk.Label(header3, text="Generación Masiva de Páginas", 
                         font=('Segoe UI', 16, 'bold'), fg="#212529", bg="#ffffff")
        title3.pack(side="left", pady=15)
        
        # Indicador de progreso para pestaña 3
        self.progress_var_masiva = tk.StringVar(value="")
        self.progress_label_masiva = tk.Label(header3, textvariable=self.progress_var_masiva,
                                            font=('Segoe UI', 9), fg="#6c757d", bg="#ffffff")
        self.progress_label_masiva.pack(side="right", pady=15)
        
        # Frame principal de configuración
        config_frame3 = tk.LabelFrame(self.tab3, text="Configuración para Generación Masiva",
                                     font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                     relief="solid", bd=1)
        config_frame3.pack(fill="x", padx=20, pady=10)
        
        config_controls3 = tk.Frame(config_frame3, bg="#ffffff")
        config_controls3.pack(fill="x", padx=15, pady=15)
        
        # Fila 1: Plantilla HTML
        row1_3 = tk.Frame(config_controls3, bg="#ffffff")
        row1_3.pack(fill="x", pady=(0, 10))
        
        tk.Label(row1_3, text="Plantilla HTML:", font=('Segoe UI', 9, 'bold'), 
                fg="#495057", bg="#ffffff").pack(side="left")
        self.plantilla_masiva_path = tk.StringVar()
        self.entry_plantilla_masiva = tk.Entry(row1_3, textvariable=self.plantilla_masiva_path,
                                              font=('Segoe UI', 9), width=50)
        self.entry_plantilla_masiva.pack(side="left", padx=(10, 5))
        
        self.btn_buscar_plantilla_masiva = tk.Button(row1_3, text="📁 Buscar", 
                                                    command=self.buscar_plantilla_masiva,
                                                    font=('Segoe UI', 9), fg="#ffffff", bg="#28a745",
                                                    relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_buscar_plantilla_masiva.pack(side="left", padx=5)
        
        # Fila 2: Directorio de salida
        row2_3 = tk.Frame(config_controls3, bg="#ffffff")
        row2_3.pack(fill="x", pady=(0, 10))
        
        tk.Label(row2_3, text="Directorio de salida:", font=('Segoe UI', 9, 'bold'), 
                fg="#495057", bg="#ffffff").pack(side="left")
        self.directorio_salida = tk.StringVar()
        self.entry_directorio_salida = tk.Entry(row2_3, textvariable=self.directorio_salida,
                                               font=('Segoe UI', 9), width=50)
        self.entry_directorio_salida.pack(side="left", padx=(10, 5))
        
        self.btn_buscar_directorio = tk.Button(row2_3, text="📁 Buscar", 
                                              command=self.buscar_directorio_salida,
                                              font=('Segoe UI', 9), fg="#ffffff", bg="#28a745",
                                              relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_buscar_directorio.pack(side="left", padx=5)
        
        # Frame de selección de productos
        selection_frame = tk.LabelFrame(self.tab3, text="Selección de Productos",
                                       font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                       relief="solid", bd=1)
        selection_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        selection_controls = tk.Frame(selection_frame, bg="#ffffff")
        selection_controls.pack(fill="x", padx=15, pady=(15, 10))
        
        # Botones de selección
        self.btn_seleccionar_todos = tk.Button(selection_controls, text="✅ Seleccionar Todos",
                                              command=self.seleccionar_todos_masiva,
                                              font=('Segoe UI', 9), fg="#ffffff", bg="#17a2b8",
                                              relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_seleccionar_todos.pack(side="left", padx=(0, 10))
        
        self.btn_deseleccionar_todos = tk.Button(selection_controls, text="❌ Deseleccionar Todos",
                                                 command=self.deseleccionar_todos_masiva,
                                                 font=('Segoe UI', 9), fg="#ffffff", bg="#6c757d",
                                                 relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_deseleccionar_todos.pack(side="left", padx=(0, 10))
        
        self.btn_seleccionar_marcados = tk.Button(selection_controls, text="✅ Solo Marcados (Verde)",
                                                  command=self.seleccionar_marcados_masiva,
                                                  font=('Segoe UI', 9), fg="#ffffff", bg="#28a745",
                                                  relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_seleccionar_marcados.pack(side="left")
        
        # Información de selección
        info_selection = tk.Frame(selection_controls, bg="#ffffff")
        info_selection.pack(side="right")
        
        self.lbl_seleccionados = tk.Label(info_selection, text="Seleccionados: 0",
                                          font=('Segoe UI', 9, 'bold'), fg="#495057", bg="#ffffff")
        self.lbl_seleccionados.pack(side="right")
        
        # TreeView para mostrar productos en pestaña masiva
        tree_frame_masiva = tk.Frame(selection_frame, bg="#ffffff")
        tree_frame_masiva.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Scrollbars para el TreeView masiva
        scrollbar_y_masiva = ttk.Scrollbar(tree_frame_masiva, orient="vertical")
        scrollbar_x_masiva = ttk.Scrollbar(tree_frame_masiva, orient="horizontal")
        
        # Configurar estilo para TreeView masivo
        style = ttk.Style()
        style.configure('Masiva.Treeview', 
                       background='#ffffff',
                       foreground='#212529',
                       fieldbackground='#ffffff',
                       borderwidth=1,
                       relief='solid')
        style.configure('Masiva.Treeview.Heading', 
                       background='#f8f9fa',
                       foreground='#495057',
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=1,
                       relief='solid')
        # Evitar selección visual en azul
        style.map('Masiva.Treeview', 
                 background=[('selected', '#ffffff')],
                 foreground=[('selected', '#212529')])
        
        # TreeView masiva
        self.tree_masiva = ttk.Treeview(tree_frame_masiva, 
                                       yscrollcommand=scrollbar_y_masiva.set,
                                       xscrollcommand=scrollbar_x_masiva.set,
                                       selectmode="none", height=12, style='Masiva.Treeview')
        
        # Configurar scrollbars
        scrollbar_y_masiva.config(command=self.tree_masiva.yview)
        scrollbar_x_masiva.config(command=self.tree_masiva.xview)
        
        # Las columnas se configurarán dinámicamente al cargar CSV
        self.tree_masiva['show'] = 'headings'
        
        # Empaquetar TreeView y scrollbars
        self.tree_masiva.grid(row=0, column=0, sticky="nsew")
        scrollbar_y_masiva.grid(row=0, column=1, sticky="ns")
        scrollbar_x_masiva.grid(row=1, column=0, sticky="ew")
        
        # Configurar grid weights
        tree_frame_masiva.grid_rowconfigure(0, weight=1)
        tree_frame_masiva.grid_columnconfigure(0, weight=1)
        
        # Eventos para selección en TreeView masiva
        self.tree_masiva.bind('<Button-1>', self.on_treeview_masiva_click)
        self.tree_masiva.bind('<Double-1>', self.on_treeview_masiva_double_click)
        self.tree_masiva.bind('<Button-3>', self.on_treeview_masiva_right_click)
        
        # Menú contextual para TreeView masiva
        self.menu_contextual_masiva = tk.Menu(self.tree_masiva, tearoff=0)
        self.menu_contextual_masiva.add_command(label="Marcar como OK (Verde)", 
                                               command=lambda: self.menu_marcar_estado_masiva('verde'))
        self.menu_contextual_masiva.add_command(label="Marcar como Sin imágenes (Amarillo)", 
                                               command=lambda: self.menu_marcar_estado_masiva('amarillo'))
        self.menu_contextual_masiva.add_command(label="Marcar como Error (Rojo)", 
                                               command=lambda: self.menu_marcar_estado_masiva('rojo'))
        self.menu_contextual_masiva.add_command(label="Quitar marca", 
                                               command=lambda: self.menu_marcar_estado_masiva('normal'))
        
        # Frame de acciones
        actions_frame3 = tk.LabelFrame(self.tab3, text="Acciones de Generación Masiva",
                                      font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                      relief="solid", bd=1)
        actions_frame3.pack(fill="x", padx=20, pady=10)
        
        actions_controls3 = tk.Frame(actions_frame3, bg="#ffffff")
        actions_controls3.pack(fill="x", padx=15, pady=15)
        
        # Botón de reiniciar historial en pestaña masiva
        self.btn_reiniciar_historial_masiva = tk.Button(actions_controls3, text="🔄 Reiniciar Historial", 
                                                       command=self.reiniciar_historial_masiva,
                                                       font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#dc3545",
                                                       relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_reiniciar_historial_masiva.pack(side="left", padx=(0, 10))
        
        self.btn_generar_masivo = tk.Button(actions_controls3, text="🚀 Generar Páginas Masivamente",
                                           command=self.generar_masivo,
                                           font=('Segoe UI', 11, 'bold'), fg="#ffffff", bg="#dc3545",
                                           relief="flat", padx=30, pady=10, cursor="hand2")
        self.btn_generar_masivo.pack(side="left")
        
        # Variables para generación masiva
        self.productos_seleccionados_masiva = set()
        
        # Variables para generación masiva de tarjetas
        self.productos_seleccionados_tarjetas = set()
        self.tarjetas_generadas = {}  # Dict para almacenar tarjetas generadas
        
        # Configurar pestaña 4 después de configurar las otras pestañas
        self._configurar_tab4()
        
        # Configurar efectos hover para botones (al final, después de crear todos los botones)
        self._setup_button_hover_effects()
    
    def _configurar_tab4(self):
        """Configura la pestaña 4 para generación masiva de tarjetas"""
        # Header con título
        header4 = tk.Frame(self.tab4, bg="#ffffff", height=60)
        header4.pack(fill="x", padx=20, pady=(20, 10))
        header4.pack_propagate(False)
        title4 = tk.Label(header4, text="Generación Masiva de Tarjetas para Catálogo", 
                         font=('Segoe UI', 16, 'bold'), fg="#212529", bg="#ffffff")
        title4.pack(side="left", pady=15)
        
        # Indicador de progreso para pestaña 4
        self.progress_var_tarjetas = tk.StringVar(value="")
        self.progress_label_tarjetas = tk.Label(header4, textvariable=self.progress_var_tarjetas,
                                              font=('Segoe UI', 9), fg="#6c757d", bg="#ffffff")
        self.progress_label_tarjetas.pack(side="right", pady=15)
        
        # Frame de configuración
        config_frame4 = tk.LabelFrame(self.tab4, text="Configuración",
                                     font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                     relief="solid", bd=1)
        config_frame4.pack(fill="x", padx=20, pady=10)
        
        config_controls4 = tk.Frame(config_frame4, bg="#ffffff")
        config_controls4.pack(fill="x", padx=15, pady=15)
        
        # Fila 1: Plantilla de tarjeta y catálogo
        row1_4 = tk.Frame(config_controls4, bg="#ffffff")
        row1_4.pack(fill="x", pady=(0, 10))
        
        tk.Label(row1_4, text="Plantilla de tarjeta:", font=('Segoe UI', 9), 
                fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_plantilla_tarjeta_masiva = tk.Entry(row1_4, width=40, font=('Segoe UI', 9),
                                                      relief="solid", bd=1, bg="#ffffff")
        self.entry_plantilla_tarjeta_masiva.pack(side="left", padx=(0, 10))
        self.btn_buscar_plantilla_tarjeta = tk.Button(row1_4, text="🔍 Buscar", 
                                                     command=self.buscar_plantilla_tarjeta_masiva,
                                                     font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                                     relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_buscar_plantilla_tarjeta.pack(side="left")
        
        # Fila 2: Archivo de catálogo
        row2_4 = tk.Frame(config_controls4, bg="#ffffff")
        row2_4.pack(fill="x")
        
        tk.Label(row2_4, text="Archivo de catálogo:", font=('Segoe UI', 9), 
                fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_catalogo_masivo = tk.Entry(row2_4, width=40, font=('Segoe UI', 9),
                                             relief="solid", bd=1, bg="#ffffff")
        self.entry_catalogo_masivo.pack(side="left", padx=(0, 10))
        self.btn_buscar_catalogo_masivo = tk.Button(row2_4, text="🔍 Buscar", 
                                                   command=self.buscar_catalogo_masivo,
                                                   font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                                   relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_buscar_catalogo_masivo.pack(side="left")
        
        # Fila 3: Logos de marcas
        row3_4 = tk.Frame(config_controls4, bg="#ffffff")
        row3_4.pack(fill="x", pady=(10, 0))
        
        tk.Label(row3_4, text="Logos de marcas:", font=('Segoe UI', 9), 
                fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_logos_tarjetas = tk.Entry(row3_4, width=40, font=('Segoe UI', 9),
                                            relief="solid", bd=1, bg="#ffffff")
        self.entry_logos_tarjetas.pack(side="left", padx=(0, 10))
        self.btn_cargar_logos_tarjetas = tk.Button(row3_4, text="📁 Cargar", 
                                                  command=self.cargar_logos_tarjetas,
                                                  font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                                  relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_cargar_logos_tarjetas.pack(side="left")
        
        # Fila 4: Links de redirección
        row4_4 = tk.Frame(config_controls4, bg="#ffffff")
        row4_4.pack(fill="x", pady=(10, 0))
        
        tk.Label(row4_4, text="Links de redirección:", font=('Segoe UI', 9), 
                fg="#495057", bg="#ffffff").pack(side="left", padx=(0, 10))
        self.entry_links_redireccion = tk.Entry(row4_4, width=40, font=('Segoe UI', 9),
                                               relief="solid", bd=1, bg="#ffffff")
        self.entry_links_redireccion.pack(side="left", padx=(0, 10))
        self.btn_cargar_links = tk.Button(row4_4, text="📁 Cargar", 
                                         command=self.cargar_links_redireccion,
                                         font=('Segoe UI', 9), fg="#495057", bg="#f8f9fa",
                                         relief="solid", bd=1, padx=15, pady=5, cursor="hand2")
        self.btn_cargar_links.pack(side="left")
        
        # Frame de selección de productos
        selection_frame4 = tk.LabelFrame(self.tab4, text="Selección de Productos",
                                        font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                        relief="solid", bd=1)
        selection_frame4.pack(fill="both", expand=True, padx=20, pady=10)
        
        selection_controls4 = tk.Frame(selection_frame4, bg="#ffffff")
        selection_controls4.pack(fill="x", padx=15, pady=(15, 10))
        
        # Botones de selección
        self.btn_seleccionar_todos_tarjetas = tk.Button(selection_controls4, text="✅ Seleccionar Todos",
                                                       command=self.seleccionar_todos_tarjetas,
                                                       font=('Segoe UI', 9), fg="#ffffff", bg="#17a2b8",
                                                       relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_seleccionar_todos_tarjetas.pack(side="left", padx=(0, 10))
        
        self.btn_deseleccionar_todos_tarjetas = tk.Button(selection_controls4, text="❌ Deseleccionar Todos",
                                                          command=self.deseleccionar_todos_tarjetas,
                                                          font=('Segoe UI', 9), fg="#ffffff", bg="#6c757d",
                                                          relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_deseleccionar_todos_tarjetas.pack(side="left", padx=(0, 10))
        
        self.btn_seleccionar_marcados_tarjetas = tk.Button(selection_controls4, text="✅ Solo Marcados (Verde)",
                                                           command=self.seleccionar_marcados_tarjetas,
                                                           font=('Segoe UI', 9), fg="#ffffff", bg="#28a745",
                                                           relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_seleccionar_marcados_tarjetas.pack(side="left")
        
        # Información de selección
        info_selection4 = tk.Frame(selection_controls4, bg="#ffffff")
        info_selection4.pack(side="right")
        
        self.lbl_seleccionados_tarjetas = tk.Label(info_selection4, text="Seleccionados: 0",
                                                   font=('Segoe UI', 9, 'bold'), fg="#495057", bg="#ffffff")
        self.lbl_seleccionados_tarjetas.pack(side="right")
        
        # TreeView para mostrar productos en pestaña de tarjetas
        tree_frame_tarjetas = tk.Frame(selection_frame4, bg="#ffffff")
        tree_frame_tarjetas.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Scrollbars para el TreeView tarjetas
        scrollbar_y_tarjetas = ttk.Scrollbar(tree_frame_tarjetas, orient="vertical")
        scrollbar_x_tarjetas = ttk.Scrollbar(tree_frame_tarjetas, orient="horizontal")
        
        # Configurar estilo para TreeView tarjetas
        style = ttk.Style()
        style.configure('Tarjetas.Treeview', 
                       background='#ffffff',
                       foreground='#212529',
                       fieldbackground='#ffffff',
                       borderwidth=1,
                       relief='solid')
        style.configure('Tarjetas.Treeview.Heading', 
                       background='#f8f9fa',
                       foreground='#495057',
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=1,
                       relief='solid')
        # Evitar selección visual en azul
        style.map('Tarjetas.Treeview', 
                 background=[('selected', '#ffffff')],
                 foreground=[('selected', '#212529')])
        
        # TreeView tarjetas
        self.tree_tarjetas = ttk.Treeview(tree_frame_tarjetas, 
                                         yscrollcommand=scrollbar_y_tarjetas.set,
                                         xscrollcommand=scrollbar_x_tarjetas.set,
                                         selectmode="none", height=12, style='Tarjetas.Treeview')
        
        # Configurar scrollbars
        scrollbar_y_tarjetas.config(command=self.tree_tarjetas.yview)
        scrollbar_x_tarjetas.config(command=self.tree_tarjetas.xview)
        
        # Las columnas se configurarán dinámicamente al cargar CSV
        self.tree_tarjetas['show'] = 'headings'
        
        # Empaquetar TreeView y scrollbars
        self.tree_tarjetas.grid(row=0, column=0, sticky="nsew")
        scrollbar_y_tarjetas.grid(row=0, column=1, sticky="ns")
        scrollbar_x_tarjetas.grid(row=1, column=0, sticky="ew")
        
        # Configurar grid weights
        tree_frame_tarjetas.grid_rowconfigure(0, weight=1)
        tree_frame_tarjetas.grid_columnconfigure(0, weight=1)
        
        # Eventos para selección en TreeView tarjetas
        self.tree_tarjetas.bind('<Button-1>', self.on_treeview_tarjetas_click)
        self.tree_tarjetas.bind('<Double-1>', self.on_treeview_tarjetas_double_click)
        self.tree_tarjetas.bind('<Button-3>', self.on_treeview_tarjetas_right_click)
        
        # Menú contextual para TreeView tarjetas
        self.menu_contextual_tarjetas = tk.Menu(self.tree_tarjetas, tearoff=0)
        self.menu_contextual_tarjetas.add_command(label="Marcar como OK (Verde)", 
                                                 command=lambda: self.menu_marcar_estado_tarjetas('verde'))
        self.menu_contextual_tarjetas.add_command(label="Marcar como Sin imágenes (Amarillo)", 
                                                 command=lambda: self.menu_marcar_estado_tarjetas('amarillo'))
        self.menu_contextual_tarjetas.add_command(label="Marcar como Error (Rojo)", 
                                                 command=lambda: self.menu_marcar_estado_tarjetas('rojo'))
        self.menu_contextual_tarjetas.add_command(label="Marcar como Generado (Morado)", 
                                                 command=lambda: self.menu_marcar_estado_tarjetas('morado'))
        self.menu_contextual_tarjetas.add_command(label="Quitar marca", 
                                                 command=lambda: self.menu_marcar_estado_tarjetas('normal'))
        
        # Frame de acciones
        actions_frame4 = tk.LabelFrame(self.tab4, text="Acciones de Generación Masiva de Tarjetas",
                                      font=('Segoe UI', 10, 'bold'), fg="#495057", bg="#ffffff",
                                      relief="solid", bd=1)
        actions_frame4.pack(fill="x", padx=20, pady=10)
        
        actions_controls4 = tk.Frame(actions_frame4, bg="#ffffff")
        actions_controls4.pack(fill="x", padx=15, pady=15)
        
        # Botón de reiniciar historial en pestaña tarjetas
        self.btn_reiniciar_historial_tarjetas = tk.Button(actions_controls4, text="🔄 Reiniciar Historial", 
                                                         command=self.reiniciar_historial_tarjetas,
                                                         font=('Segoe UI', 9, 'bold'), fg="#ffffff", bg="#dc3545",
                                                         relief="flat", padx=20, pady=8, cursor="hand2")
        self.btn_reiniciar_historial_tarjetas.pack(side="left", padx=(0, 10))
        
        self.btn_generar_tarjetas_masivo = tk.Button(actions_controls4, text="🎨 Generar Tarjetas Masivamente",
                                                    command=self.generar_tarjetas_masivo,
                                                    font=('Segoe UI', 11, 'bold'), fg="#ffffff", bg="#6f42c1",
                                                    relief="flat", padx=30, pady=10, cursor="hand2")
        self.btn_generar_tarjetas_masivo.pack(side="left", padx=(0, 10))
        
        self.btn_insertar_tarjetas_catalogo = tk.Button(actions_controls4, text="➕ Añadir al Catálogo",
                                                       command=self.insertar_tarjetas_en_catalogo,
                                                       font=('Segoe UI', 11, 'bold'), fg="#ffffff", bg="#28a745",
                                                       relief="flat", padx=30, pady=10, cursor="hand2")
        self.btn_insertar_tarjetas_catalogo.pack(side="left")
    
    def _setup_button_hover_effects(self):
        """Configura efectos hover para los botones"""
        buttons_config = [
            (self.btn_cargar, "#007bff", "#0056b3"),
            (self.btn_reiniciar_historial, "#dc3545", "#c82333"),
            (self.btn_reiniciar_historial_masiva, "#dc3545", "#c82333"),
            (self.btn_reiniciar_historial_tarjetas, "#dc3545", "#c82333"),
            (self.btn_buscar_plantilla_ind, "#f8f9fa", "#e9ecef"),
            (self.btn_buscar_plantilla_tarjeta, "#f8f9fa", "#e9ecef"),
            (self.btn_buscar_catalogo_masivo, "#f8f9fa", "#e9ecef"),
            (self.btn_pagina_individual, "#28a745", "#1e7e34"),
            (self.btn_buscar_catalogo, "#f8f9fa", "#e9ecef"),
            (self.btn_cargar_logos, "#007bff", "#0056b3"),
            (self.btn_generar_tarjeta, "#007bff", "#0056b3"),
            (self.btn_copiar_tarjeta, "#6c757d", "#545b62"),
            (self.btn_insertar_tarjeta, "#28a745", "#1e7e34"),
            (self.btn_generar_tarjetas_masivo, "#6f42c1", "#5a32a3"),
            (self.btn_insertar_tarjetas_catalogo, "#28a745", "#1e7e34")
        ]
        
        for button, normal_color, hover_color in buttons_config:
            self._add_hover_effect(button, normal_color, hover_color)
    
    def _add_hover_effect(self, button, normal_color, hover_color):
        """Agrega efecto hover a un botón específico"""
        def on_enter(e):
            button.config(bg=hover_color)
        
        def on_leave(e):
            if button['state'] != 'disabled':
                button.config(bg=normal_color)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def cargar_historial_estado(self):
        try:
            with open(self.historial_estado_path, 'r', encoding='utf-8') as f:
                self.estado_filas = json.load(f)
        except Exception:
            self.estado_filas = {}

    def guardar_historial_estado(self):
        try:
            with open(self.historial_estado_path, 'w', encoding='utf-8') as f:
                json.dump(self.estado_filas, f)
        except Exception:
            pass
    
    def limpiar_cache_plantillas(self):
        """Limpia el cache de plantillas HTML para liberar memoria"""
        global _PLANTILLA_CACHE
        _PLANTILLA_CACHE.clear()
        print("[DEBUG] Cache de plantillas limpiado")
        
    def _on_closing(self):
        """Limpia recursos al cerrar la aplicación."""
        try:
            # Cerrar el executor de threads
            self.executor.shutdown(wait=False)
            # Limpiar caches
            global _PLANTILLA_CACHE, _URL_VALIDATION_CACHE
            _PLANTILLA_CACHE.clear()
            _URL_VALIDATION_CACHE.clear()
        except:
            pass
        finally:
            self.root.destroy()
    
    # --- Métodos para Generación Masiva ---
    
    def buscar_plantilla_masiva(self):
        """Busca archivo de plantilla HTML para generación masiva"""
        filename = filedialog.askopenfilename(
            title="Seleccionar plantilla HTML",
            filetypes=[("Archivos HTML", "*.html"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.plantilla_masiva_path.set(filename)
    
    def buscar_directorio_salida(self):
        """Busca directorio de salida para las páginas generadas"""
        directory = filedialog.askdirectory(title="Seleccionar directorio de salida")
        if directory:
            self.directorio_salida.set(directory)
    
    def seleccionar_todos_masiva(self):
        """Selecciona todos los productos para generación masiva"""
        if not hasattr(self, 'tree_masiva') or not self.tree_masiva.get_children():
            messagebox.showwarning("Advertencia", "Primero debe cargar un archivo CSV.")
            return
        
        self.productos_seleccionados_masiva.clear()
        for item in self.tree_masiva.get_children():
            self.productos_seleccionados_masiva.add(item)
            self.tree_masiva.set(item, 'sel', '☑')
        
        self.tree_masiva.update_idletasks()  # Forzar actualización visual
        self.actualizar_contador_seleccionados()
    
    def deseleccionar_todos_masiva(self):
        """Deselecciona todos los productos"""
        if hasattr(self, 'tree_masiva'):
            for item in self.tree_masiva.get_children():
                self.tree_masiva.set(item, 'sel', '☐')
        
        self.productos_seleccionados_masiva.clear()
        if hasattr(self, 'tree_masiva'):
            self.tree_masiva.update_idletasks()  # Forzar actualización visual
        self.actualizar_contador_seleccionados()
    
    def seleccionar_marcados_masiva(self):
        """Selecciona solo los productos marcados en verde"""
        if not hasattr(self, 'tree_masiva') or not self.tree_masiva.get_children():
            messagebox.showwarning("Advertencia", "Primero debe cargar un archivo CSV.")
            return
        
        self.productos_seleccionados_masiva.clear()
        # Primero deseleccionar todos
        for item in self.tree_masiva.get_children():
            self.tree_masiva.set(item, 'sel', '☐')
        
        # Luego seleccionar solo los verdes
        for item in self.tree_masiva.get_children():
            tags = self.tree_masiva.item(item, 'tags')
            if 'verde' in tags:
                self.productos_seleccionados_masiva.add(item)
                self.tree_masiva.set(item, 'sel', '☑')
        
        self.tree_masiva.update_idletasks()  # Forzar actualización visual
        self.actualizar_contador_seleccionados()
    
    def actualizar_contador_seleccionados(self):
        """Actualiza el contador de productos seleccionados"""
        count = len(self.productos_seleccionados_masiva)
        self.lbl_seleccionados.config(text=f"Seleccionados: {count}")
    
    def generar_masivo(self):
        """Genera páginas de productos de forma masiva"""
        # Validaciones
        if not self.plantilla_masiva_path.get():
            messagebox.showerror("Error", "Debe seleccionar una plantilla HTML.")
            return
        
        if not self.directorio_salida.get():
            messagebox.showerror("Error", "Debe seleccionar un directorio de salida.")
            return
        
        if not self.productos_seleccionados_masiva:
            messagebox.showerror("Error", "Debe seleccionar al menos un producto.")
            return
        
        if not os.path.exists(self.plantilla_masiva_path.get()):
            messagebox.showerror("Error", "El archivo de plantilla no existe.")
            return
        
        if not os.path.exists(self.directorio_salida.get()):
            messagebox.showerror("Error", "El directorio de salida no existe.")
            return
        
        # Confirmar generación
        count = len(self.productos_seleccionados_masiva)
        respuesta = messagebox.askyesno(
            "Confirmar Generación Masiva",
            f"¿Está seguro de generar {count} páginas de productos?\n\n"
            f"Plantilla: {os.path.basename(self.plantilla_masiva_path.get())}\n"
            f"Directorio: {self.directorio_salida.get()}"
        )
        
        if not respuesta:
            return
        
        # Ejecutar generación en hilo separado
        self.executor.submit(self._generar_masivo_async)
    
    def _generar_masivo_async(self):
        """Ejecuta la generación masiva en segundo plano"""
        try:
            self.progress_var_masiva.set("Iniciando generación masiva...")
            
            # Cargar plantilla
            with open(self.plantilla_masiva_path.get(), 'r', encoding='utf-8') as f:
                plantilla_content = f.read()
            
            total_productos = len(self.productos_seleccionados_masiva)
            productos_generados = 0
            productos_fallidos = 0
            
            for i, item_id in enumerate(self.productos_seleccionados_masiva, 1):
                try:
                    # Marcar como procesando
                    self.set_estado_fila_masiva(item_id, 'procesando')
                    
                    # Actualizar progreso
                    self.progress_var_masiva.set(f"Generando página {i}/{total_productos}...")
                    
                    # Obtener datos del producto
                    values = self.tree_masiva.item(item_id, 'values')
                    if not values:
                        continue
                    
                    # Crear diccionario de datos del producto
                    # Estructura TreeView masivo: ['sel', '_numero', '_checked'] + campos_csv
                    # Los datos CSV empiezan en índice 3
                    
                    # Crear mapeo dinámico basado en los campos CSV
                    def get_value_by_column_name(column_name):
                        try:
                            if column_name in self.campos_csv:
                                csv_index = self.campos_csv.index(column_name)
                                values_index = csv_index + 3  # +3 por ['sel', '_numero', '_checked']
                                return values[values_index] if len(values) > values_index else ''
                            return ''
                        except (ValueError, IndexError):
                            return ''
                    
                    producto_data = {
                        'tipo': get_value_by_column_name('Etiquetas'),
                        'sku': get_value_by_column_name('SKU'),
                        'nombre': get_value_by_column_name('SKU'),  # SKU como nombre
                        'precio_normal': get_value_by_column_name('Precio normal'),
                        'porcentaje_descuento': get_value_by_column_name('Porcentajede descuento'),
                        'precio_descuento': get_value_by_column_name('precio con descuento'),
                        'marca': get_value_by_column_name('Valor(es) del atributo 2'),  # Marca
                        'descripcion': get_value_by_column_name('Tipo'),  # Tipo como descripción
                        'imagen1': get_value_by_column_name('IMAGEN 1'),
                        'imagen2': get_value_by_column_name('IMAGEN 2'),
                        'imagen3': get_value_by_column_name('IMAGEN 3'),
                        'logo': '',
                        # Información adicional para la tabla
                        'color': get_value_by_column_name('Valor(es) del atributo 4'),  # Color
                        'forma': get_value_by_column_name('Valor(es) del atributo 5'),  # Forma
                        'material': get_value_by_column_name('Valor(es) del atributo 6'),  # Material
                        'varillas': get_value_by_column_name('Valor(es) del atributo 7'),  # Varillas
                        'clip': get_value_by_column_name('Valor(es) del atributo 8'),  # Clip
                        'color_mica': get_value_by_column_name('Valor(es) del atributo 9'),  # Color de Mica
                        'medida': get_value_by_column_name('Valor(es) del atributo 10'),  # Medida
                        'puente': get_value_by_column_name('Valor(es) del atributo 11'),  # Puente
                        'accesorios': get_value_by_column_name('Valor(es) del atributo 12'),  # Accesorios
                        'garantia': get_value_by_column_name('Valor(es) del atributo 13')  # Garantía
                    }
                    
                    # Generar contenido HTML
                    html_content = self._procesar_plantilla_masiva(plantilla_content, producto_data)
                    
                    # Crear nombre de archivo seguro
                    nombre_archivo = self._crear_nombre_archivo_seguro(producto_data['nombre'], i)
                    ruta_archivo = os.path.join(self.directorio_salida.get(), f"{nombre_archivo}.html")
                    
                    # Guardar archivo
                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Marcar como generado exitosamente (color verde)
                    self.set_estado_fila_masiva(item_id, 'verde')
                    
                    # Guardar en historial y sincronizar con TreeView individual
                    sku = producto_data['sku']
                    if sku:
                        print(f"DEBUG: Guardando estado 'verde' para SKU {sku} en generación masiva")
                        self.estado_filas[sku] = 'verde'
                        self.guardar_historial_estado()
                        print(f"DEBUG: Historial guardado. Estado actual: {self.estado_filas}")
                        self.sincronizar_estado_individual(sku, 'verde')
                    
                    productos_generados += 1
                    
                except Exception as e:
                    print(f"Error generando producto {i}: {str(e)}")
                    
                    # Marcar como error (color rojo) y sincronizar
                    self.set_estado_fila_masiva(item_id, 'rojo')
                    
                    # Obtener SKU para sincronización
                    try:
                        values = self.tree_masiva.item(item_id, 'values')
                        if values and len(values) > 4:
                            sku = values[4]  # SKU está en índice 4 (sel, _numero, _checked, Tipo, SKU)
                            if sku:
                                self.estado_filas[sku] = 'rojo'
                                self.guardar_historial_estado()
                                self.sincronizar_estado_individual(sku, 'rojo')
                    except Exception:
                        pass
                    
                    productos_fallidos += 1
                    continue
            
            # Mostrar resultado final
            self.progress_var_masiva.set(
                f"Completado: {productos_generados} generados, {productos_fallidos} fallidos"
            )
            
            # Limpiar mensaje después de 5 segundos
            self.root.after(5000, lambda: self.progress_var_masiva.set(""))
            
            # Mostrar mensaje de éxito
            messagebox.showinfo(
                "Generación Completada",
                f"Generación masiva completada:\n\n"
                f"✅ Páginas generadas: {productos_generados}\n"
                f"❌ Páginas fallidas: {productos_fallidos}\n\n"
                f"Directorio: {self.directorio_salida.get()}"
            )
            
        except Exception as e:
            self.progress_var_masiva.set("Error en generación masiva")
            messagebox.showerror("Error", f"Error durante la generación masiva:\n{str(e)}")
    
    def _procesar_plantilla_masiva(self, plantilla_content, producto_data):
        """Procesa la plantilla HTML con los datos del producto usando regex como en generación individual"""
        html_content = plantilla_content
        
        # Obtener imágenes del producto
        img1 = producto_data.get('imagen1', '') or ''
        img2 = producto_data.get('imagen2', '') or ''
        img3 = producto_data.get('imagen3', '') or ''
        
        # Usar patrones regex compilados para reemplazar imágenes (igual que en generación individual)
        html_content = _REGEX_PATTERNS['img_src_1'].sub('src="' + img1 + '"', html_content)
        html_content = _REGEX_PATTERNS['img_src_2'].sub('src="' + img2 + '"', html_content)
        html_content = _REGEX_PATTERNS['img_src_3'].sub('src="' + img3 + '"', html_content)
        
        # Reemplazo en miniaturas
        html_content = _REGEX_PATTERNS['thumb_1'].sub('src="' + img1 + '"', html_content)
        html_content = _REGEX_PATTERNS['thumb_2'].sub('src="' + img2 + '"', html_content)
        html_content = _REGEX_PATTERNS['thumb_3'].sub('src="' + img3 + '"', html_content)
        
        # Reemplazo en el script JS (array imageSources)
        img1_js = '"' + img1 + '"'
        img2_js = '"' + img2 + '"'
        img3_js = '"' + img3 + '"'
        html_content = _REGEX_PATTERNS['image_sources'].sub('const imageSources = [' + img1_js + ', ' + img2_js + ', ' + img3_js + '];', html_content)
        
        # Reemplazar información del producto (marca, modelo, precios)
        sku = producto_data.get('sku', '')
        marca = producto_data.get('marca', '')
        precio_normal = producto_data.get('precio_normal', '')
        precio_descuento = producto_data.get('precio_descuento', '')
        porcentaje_descuento = producto_data.get('porcentaje_descuento', '')
        
        # Reemplazar marca y modelo usando regex
        html_content = _REGEX_PATTERNS['product_brand'].sub('<h1 id="product-brand" class="text-4xl md:text-5xl font-bold text-orange-500 uppercase">' + marca + '</h1>', html_content)
        html_content = _REGEX_PATTERNS['product_model'].sub('<p id="product-model" class="text-xl text-gray-400 mb-4">' + sku + '</p>', html_content)
        
        # Reemplazar precios
        try:
            if precio_normal and precio_descuento and porcentaje_descuento:
                # Validar que los precios no sean SKUs o valores inválidos
                if '$' in str(precio_normal) and '$' in str(precio_descuento):
                    # Formatear precio normal (tachado)
                    precio_normal_float = float(str(precio_normal).replace('$', '').replace(',', ''))
                    precio_normal_formateado = f'${precio_normal_float:,.2f}'
                    
                    # Formatear precio con descuento
                    precio_descuento_float = float(str(precio_descuento).replace('$', '').replace(',', ''))
                    precio_descuento_formateado = f'${precio_descuento_float:,.2f}'
                    
                    # Formatear porcentaje de descuento
                    porcentaje_float = float(str(porcentaje_descuento).replace('%', ''))
                    porcentaje_formateado = f'{porcentaje_float:.0f}%'
                    
                    # Reemplazar precio tachado
                    html_content = _REGEX_PATTERNS['old_price'].sub('<span class="text-2xl text-gray-400 line-through mr-2">' + precio_normal_formateado + '</span>', html_content)
                    
                    # Reemplazar badge de descuento
                    html_content = _REGEX_PATTERNS['discount_badge'].sub('<span class="inline-block bg-red-100 text-red-600 text-lg font-bold px-2 py-1 rounded align-middle mr-2">' + porcentaje_formateado + '</span>', html_content)
                    
                    # Reemplazar precio actual
                    html_content = _REGEX_PATTERNS['new_price'].sub('<span class="text-5xl font-extrabold text-black">' + precio_descuento_formateado + '</span>', html_content)
            elif precio_normal and '$' in str(precio_normal):
                # Solo precio normal disponible
                precio_normal_float = float(str(precio_normal).replace('$', '').replace(',', ''))
                precio_normal_formateado = f'${precio_normal_float:,.2f}'
                html_content = _REGEX_PATTERNS['new_price'].sub('<span class="text-5xl font-extrabold text-black">' + precio_normal_formateado + '</span>', html_content)
        except Exception as e:
            print(f"Error procesando precios: {e}")
        
        # --- Reemplazo de tabla de especificaciones ---
        # Usar el mismo enfoque que la función individual para consistencia
        tabla_replacements = [
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('sku', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('marca', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('tipo', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('color', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('forma', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('material', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('varillas', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('clip', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('color_mica', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('medida', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('puente', '')),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('accesorios', '')),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', producto_data.get('garantia', '')),
            # Patrones específicos para valores hardcodeados en la plantilla
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">RB2398</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">{producto_data.get("sku", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">RAYBAN</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">{producto_data.get("marca", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">Lente oftálmico</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">{producto_data.get("tipo", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">Transparente con negro</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">{producto_data.get("color", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">Ovalado</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">{producto_data.get("forma", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">Acetato</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">{producto_data.get("material", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">Acetato</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">{producto_data.get("varillas", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">Sin clip</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">{producto_data.get("clip", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">Transparente</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">{producto_data.get("color_mica", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">Mediano</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">{producto_data.get("medida", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">Puente anatómico</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">{producto_data.get("puente", "")}</td></tr>'),
            (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">Lente, paño, estuche y líquido antirreflejante</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">{producto_data.get("accesorios", "")}</td></tr>'),
            (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">30 días de garantía contra defectos de fábrica.</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">{producto_data.get("garantia", "")}</td></tr>'),
        ]
        
        for patron, valor in tabla_replacements:
            # Para patrones con [^<]*, usar lambda function
            if '[^<]*' in patron:
                html_content = re.sub(patron, lambda m, v=valor: m.group(0).replace('[^<]*', v), html_content)
            else:
                # Para patrones específicos con valores hardcodeados, usar reemplazo directo
                html_content = re.sub(patron, valor, html_content)
        
        return html_content
    
    def _crear_nombre_archivo_seguro(self, nombre_producto, indice):
        """Crea un nombre de archivo seguro basado en el nombre del producto"""
        if not nombre_producto:
            return f"producto_{indice}"
        
        # Limpiar caracteres no válidos para nombres de archivo
        nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_producto)
        nombre_limpio = re.sub(r'\s+', '_', nombre_limpio.strip())
        nombre_limpio = nombre_limpio[:50]  # Limitar longitud
        
        if not nombre_limpio:
            return f"producto_{indice}"
        
        return f"{nombre_limpio}_{indice}"
    
    def on_treeview_masiva_click(self, event):
        """Maneja clics en el TreeView de generación masiva"""
        # Detectar si se hizo click en la columna de checkbox
        region = self.tree_masiva.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree_masiva.identify_column(event.x)
        if col != "#1":  # La columna 'sel' es la primera
            return
        rowid = self.tree_masiva.identify_row(event.y)
        if not rowid:
            return
        
        # Alternar selección solo si se hizo click en el checkbox
        if rowid in self.productos_seleccionados_masiva:
            self.productos_seleccionados_masiva.remove(rowid)
            self.tree_masiva.set(rowid, 'sel', '☐')
        else:
            self.productos_seleccionados_masiva.add(rowid)
            self.tree_masiva.set(rowid, 'sel', '☑')
        
        self.actualizar_contador_seleccionados()
    
    def on_treeview_masiva_double_click(self, event):
        """Maneja doble clic en el TreeView de generación masiva"""
        # Mismo comportamiento que clic simple
        self.on_treeview_masiva_click(event)
    
    def on_treeview_masiva_right_click(self, event):
        """Maneja clic derecho en el TreeView de generación masiva"""
        rowid = self.tree_masiva.identify_row(event.y)
        if not rowid:
            return
        # No establecer selección para evitar resaltado en azul
        self.menu_contextual_masiva.post(event.x_root, event.y_root)
        self._menu_contextual_masiva_rowid = rowid
    
    def menu_marcar_estado_masiva(self, estado):
        """Marca el estado de una fila en el TreeView masiva"""
        rowid = getattr(self, '_menu_contextual_masiva_rowid', None)
        if not rowid:
            return
        self.set_estado_fila_masiva(rowid, estado)
        # Usar SKU como clave del historial
        values = self.tree_masiva.item(rowid, 'values')
        if values and len(values) > 4:  # Asegurar que hay SKU (índice 4 en masiva)
            sku = values[4]  # SKU está en el índice 4 (sel, _numero, _checked, Tipo, SKU)
            self.estado_filas[sku] = estado
            self.guardar_historial_estado()
            # Sincronizar con TreeView individual
            self.sincronizar_estado_individual(sku, estado)
    
    def reiniciar_historial_masiva(self):
        """Reinicia el historial de estados en la pestaña masiva"""
        respuesta = messagebox.askyesno("Confirmar", 
                                       "¿Estás seguro de que quieres reiniciar el historial?\n\n"
                                       "Esto eliminará todos los estados guardados (verde, amarillo, rojo) "
                                       "y restablecerá todas las filas a su estado normal.")
        if respuesta:
            # Limpiar el diccionario de estados
            self.estado_filas = {}
            
            # Eliminar el archivo de historial
            try:
                if os.path.exists(self.historial_estado_path):
                    os.remove(self.historial_estado_path)
            except Exception:
                pass
            
            # Restablecer estados visuales en ambos TreeViews
            if self.tree:
                for item in self.tree.get_children():
                    self.set_estado_fila(item, 'normal')
                    self.checked_rows[item] = False
            
            if self.tree_masiva:
                for item in self.tree_masiva.get_children():
                    self.set_estado_fila_masiva(item, 'normal')
            
            messagebox.showinfo("Éxito", "Historial reiniciado correctamente.")
    
    def set_estado_fila_masiva(self, rowid, estado):
        """Establece el estado visual de una fila en el TreeView masiva"""
        if not self.tree_masiva:
            return
            
        # Quitar todos los tags
        self.tree_masiva.item(rowid, tags=())
        
        if estado == 'verde':
            self.tree_masiva.item(rowid, tags=("verde",))
            self.tree_masiva.tag_configure("verde", background="#d4edda", foreground="#155724")  # Verde éxito
        elif estado == 'amarillo':
            self.tree_masiva.item(rowid, tags=("amarillo",))
            self.tree_masiva.tag_configure("amarillo", background="#fff3cd", foreground="#856404")  # Amarillo advertencia
        elif estado == 'rojo':
            self.tree_masiva.item(rowid, tags=("rojo",))
            self.tree_masiva.tag_configure("rojo", background="#f8d7da", foreground="#721c24")  # Rojo error
        elif estado == 'procesando':
            self.tree_masiva.item(rowid, tags=("procesando",))
            self.tree_masiva.tag_configure("procesando", background="#e2e3e5", foreground="#383d41")  # Gris procesando
        else:
            # Normal - sin color de fondo especial
            pass
        
        # Forzar actualización visual
        self.tree_masiva.update_idletasks()
    
    def configurar_columnas_masiva(self):
        """Configura las columnas del TreeView masiva basándose en los campos CSV"""
        if not hasattr(self, 'campos_csv'):
            return
        
        # Configurar columnas: sel + número + checkbox + campos CSV
        cols = ['sel', '_numero', '_checked'] + self.campos_csv
        self.tree_masiva['columns'] = cols
        
        # Configurar encabezados
        self.tree_masiva.heading('sel', text='Sel', anchor='center')
        self.tree_masiva.heading('_numero', text='#', anchor='center')
        self.tree_masiva.heading('_checked', text='✔', anchor='center')
        
        # Configurar anchos
        self.tree_masiva.column('sel', width=40, anchor='center', stretch=False)
        self.tree_masiva.column('_numero', width=50, anchor='center', stretch=False)
        self.tree_masiva.column('_checked', width=40, anchor='center', stretch=False)
        
        # Configurar campos CSV con los mismos anchos que el TreeView principal
        col_widths = {
            "Tipo": 90,
            "SKU": 100,
            "¿Existencias?": 80,
            "Inventario": 80,
            "Precio normal": 110,
            "Porcentajede descuento": 90,
            "precio con descuento": 120,
            "Categorías": 90,
            "Etiquetas": 120,
            "Valor(es) del atributo 1": 100,
            "Valor(es) del atributo 2": 100,
            "Valor(es) del atributo 3": 120,
            "Valor(es) del atributo 4": 120,
            "Valor(es) del atributo 5": 120,
            "Valor(es) del atributo 6": 120,
            "Valor(es) del atributo 7": 120,
            "Valor(es) del atributo 8": 120,
            "Valor(es) del atributo 9": 120,
            "Valor(es) del atributo 10": 120,
            "Valor(es) del atributo 11": 120,
            "Valor(es) del atributo 12": 120,
            "Valor(es) del atributo 13": 180,
            "IMAGEN 1": 180,
            "IMAGEN 2": 180,
            "IMAGEN 3": 180,
        }
        
        for col in self.campos_csv:
            self.tree_masiva.heading(col, text=col)
            width = col_widths.get(col, 100)
            self.tree_masiva.column(col, width=width, anchor='center', stretch=False)
    
    def sincronizar_datos_masiva(self):
        """Sincroniza los datos del TreeView principal con el TreeView masiva"""
        if not hasattr(self, 'tree') or not hasattr(self, 'tree_masiva'):
            return
        
        # Configurar columnas primero
        self.configurar_columnas_masiva()
        
        # Limpiar TreeView masiva
        for item in self.tree_masiva.get_children():
            self.tree_masiva.delete(item)
        
        # Limpiar selecciones
        self.productos_seleccionados_masiva.clear()
        
        # Copiar datos del TreeView principal
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            tags = self.tree.item(item, 'tags')
            if values:
                # Insertar en TreeView masiva: sel + valores originales
                new_values = ('☐',) + values
                new_item = self.tree_masiva.insert('', 'end', values=new_values, tags=tags)
                
                # Restaurar estado del historial si existe (usar SKU como clave)
                if len(values) > 3:  # Asegurar que hay SKU
                    sku = values[3]  # SKU está en el índice 3 en el TreeView principal (_numero, _checked, Tipo, SKU)
                    if sku in self.estado_filas:
                        estado = self.estado_filas[sku]
                        self.set_estado_fila_masiva(new_item, estado)
        
        self.actualizar_contador_seleccionados()

    def sincronizar_estado_individual(self, sku, estado):
        """Sincroniza el estado desde TreeView masivo hacia TreeView individual"""
        if not hasattr(self, 'tree') or not self.tree:
            return
        
        # Buscar la fila correspondiente en TreeView individual por SKU
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 3 and values[3] == sku:  # SKU está en índice 3
                self.set_estado_fila(item, estado)
                break
    
    def sincronizar_estado_masivo(self, sku, estado):
        """Sincroniza el estado desde TreeView individual hacia TreeView masivo"""
        if not hasattr(self, 'tree_masiva') or not self.tree_masiva:
            return
        
        # Buscar la fila correspondiente en TreeView masivo por SKU
        for item in self.tree_masiva.get_children():
            values = self.tree_masiva.item(item, 'values')
            if values and len(values) > 4 and values[4] == sku:  # SKU está en índice 4 (sel, _numero, _checked, Tipo, SKU)
                self.set_estado_fila_masiva(item, estado)
                break
    
    def forzar_sincronizacion_completa(self):
        """Fuerza la sincronización completa del historial en ambos TreeViews"""
        print("DEBUG: Iniciando sincronización completa...")
        print(f"DEBUG: Estados en historial: {self.estado_filas}")
        
        # Aplicar estados del historial al TreeView individual
        if hasattr(self, 'tree') and self.tree:
            print("DEBUG: Revisando TreeView individual...")
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                if values and len(values) > 3:
                    sku = values[3]  # SKU está en índice 3 (_numero, _checked, Tipo, SKU)
                    print(f"DEBUG: Encontrado SKU '{sku}' en TreeView individual")
                    if sku in self.estado_filas:
                        estado = self.estado_filas[sku]
                        print(f"DEBUG: Aplicando estado {estado} a SKU {sku} en TreeView individual")
                        self.set_estado_fila(item, estado)
                    else:
                        print(f"DEBUG: SKU '{sku}' no encontrado en historial")
        
        # Aplicar estados del historial al TreeView masivo
        if hasattr(self, 'tree_masiva') and self.tree_masiva:
            print("DEBUG: Revisando TreeView masivo...")
            for item in self.tree_masiva.get_children():
                values = self.tree_masiva.item(item, 'values')
                if values and len(values) > 3:  # En masivo, SKU está en índice 3 (después de checkbox)
                    sku = values[3]  # SKU está en índice 3
                    print(f"DEBUG: Encontrado SKU '{sku}' en TreeView masivo")
                    if sku in self.estado_filas:
                        estado = self.estado_filas[sku]
                        print(f"DEBUG: Aplicando estado {estado} a SKU {sku} en TreeView masivo")
                        self.set_estado_fila_masiva(item, estado)
                    else:
                        print(f"DEBUG: SKU '{sku}' no encontrado en historial")
        
        print("DEBUG: Sincronización completa finalizada")

    def reiniciar_historial(self):
        """Reinicia el historial de estados de productos"""
        respuesta = messagebox.askyesno("Confirmar", 
                                       "¿Estás seguro de que quieres reiniciar el historial?\n\n"
                                       "Esto eliminará todos los estados guardados (verde, amarillo, rojo) "
                                       "y restablecerá todas las filas a su estado normal.")
        if respuesta:
            # Limpiar el diccionario de estados
            self.estado_filas = {}
            
            # Eliminar el archivo de historial
            try:
                if os.path.exists(self.historial_estado_path):
                    os.remove(self.historial_estado_path)
            except Exception:
                pass
            
            # Restablecer estados visuales en ambos TreeViews
            if self.tree:
                for item in self.tree.get_children():
                    self.set_estado_fila(item, 'normal')
                    self.checked_rows[item] = False
            
            if self.tree_masiva:
                for item in self.tree_masiva.get_children():
                    self.set_estado_fila_masiva(item, 'normal')
            
            messagebox.showinfo("Éxito", "Historial reiniciado correctamente.")

    def buscar_plantilla_ind(self):
        path = filedialog.askopenfilename(filetypes=[("HTML Files", "*.html")])
        if path:
            self.entry_plantilla_ind.delete(0, tk.END)
            self.entry_plantilla_ind.insert(0, path)
            self.plantilla_ind_path = path

    def cargar_logos(self):
        path = filedialog.askopenfilename(filetypes=[("CSV or TXT", "*.csv;*.txt")])
        if not path:
            return
        self.entry_logos.delete(0, tk.END)
        self.entry_logos.insert(0, path)
        self.logos_dict = {}
        # Tabla de traducción para normalización optimizada
        trans_table = str.maketrans('', '', ' -_')
        
        if path.endswith('.csv'):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                marca = str(row.iloc[0]).strip().lower().translate(trans_table)
                logo = str(row.iloc[1]).strip()
                self.logos_dict[marca] = logo
        else:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if ':' in line:
                        marca, logo = line.split(':', 1)
                    elif ',' in line:
                        marca, logo = line.split(',', 1)
                    else:
                        marca, logo = line.split(None, 1)
                    # Usar la misma normalización optimizada
                    marca_normalizada = marca.strip().lower().translate(trans_table)
                    self.logos_dict[marca_normalizada] = logo.strip()
        messagebox.showinfo("Éxito", "Archivo de logos cargado correctamente.")

    def cargar_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if not path:
            return
            
        # Mostrar indicador de progreso
        self.progress_var.set("Cargando archivo...")
        self.root.update_idletasks()
        
        try:
            if path.endswith('.xlsx'):
                self.df = pd.read_excel(path)
            else:
                self.df = pd.read_csv(path)
            
            # Limpiar datos: remover filas completamente vacías
            self.df = self.df.dropna(how='all')
            
            # Resetear índices después de limpiar
            self.df = self.df.reset_index(drop=True)
            
            self.campos_csv = list(self.df.columns)
            
            # Actualizar progreso
            self.progress_var.set(f"Procesando {len(self.df)} filas...")
            self.root.update_idletasks()
            
        except Exception as e:
            self.progress_var.set("")
            messagebox.showerror("Error", f"Error al cargar archivo: {str(e)}")
            return
        # Eliminar tabla anterior si existe
        if self.tree:
            self.tree.destroy()
        # --- Configurar estilo moderno para TreeView ---
        style = ttk.Style()
        style.configure('Modern.Treeview', 
                       background='#ffffff',
                       foreground='#212529',
                       fieldbackground='#ffffff',
                       borderwidth=1,
                       relief='solid')
        style.configure('Modern.Treeview.Heading', 
                       background='#f8f9fa',
                       foreground='#495057',
                       font=('Segoe UI', 9, 'bold'),
                       borderwidth=1,
                       relief='solid')
        style.map('Modern.Treeview', 
                 background=[('selected', '#007bff')],
                 foreground=[('selected', '#ffffff')])
        
        # --- Agregar columna de numeración y checkbox al inicio ---
        cols = ["_numero", "_checked"] + self.campos_csv
        self.tree = ttk.Treeview(self.tree_frame, columns=cols, show="headings", 
                                height=10, yscrollcommand=self.yscroll.set, 
                                xscrollcommand=self.xscroll.set, style='Modern.Treeview')
        self.tree.heading("_numero", text="#", anchor="center")
        self.tree.column("_numero", width=50, anchor="center", stretch=False)
        self.tree.heading("_checked", text="✔", anchor="center")
        self.tree.column("_checked", width=40, anchor="center", stretch=False)
        # Definir anchos fijos para columnas clave
        col_widths = {
            "Tipo": 90,
            "SKU": 100,
            "¿Existencias?": 80,
            "Inventario": 80,
            "Precio normal": 110,
            "Porcentajede descuento": 90,
            "precio con descuento": 120,
            "Categorías": 90,
            "Etiquetas": 120,
            "Valor(es) del atributo 1": 100,
            "Valor(es) del atributo 2": 100,
            "Valor(es) del atributo 3": 120,
            "Valor(es) del atributo 4": 120,
            "Valor(es) del atributo 5": 120,
            "Valor(es) del atributo 6": 120,
            "Valor(es) del atributo 7": 120,
            "Valor(es) del atributo 8": 120,
            "Valor(es) del atributo 9": 120,
            "Valor(es) del atributo 10": 120,
            "Valor(es) del atributo 11": 120,
            "Valor(es) del atributo 12": 120,
            "Valor(es) del atributo 13": 180,
            "IMAGEN 1": 180,
            "IMAGEN 2": 180,
            "IMAGEN 3": 180,
        }
        for col in self.campos_csv:
            self.tree.heading(col, text=col)
            width = col_widths.get(col, 100)
            self.tree.column(col, width=width, anchor="center", stretch=False)
        
        # Configurar scrollbars
        self.yscroll.config(command=self.tree.yview)
        self.xscroll.config(command=self.tree.xview)
        
        # Empaquetar TreeView y scrollbars usando grid
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.yscroll.grid(row=0, column=1, sticky="ns")
        self.xscroll.grid(row=1, column=0, sticky="ew")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_select_producto)
        self.tree.bind("<Button-1>", self.on_treeview_click)
        self.tree.delete(*self.tree.get_children())
        self.checked_rows = {}
        
        # Optimización: Insertar filas en lotes para mejor rendimiento
        total_rows = len(self.df)
        batch_size = 100
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            
            # Actualizar progreso
            progress = int((batch_start / total_rows) * 100)
            self.progress_var.set(f"Cargando filas: {progress}% ({batch_start}/{total_rows})")
            self.root.update_idletasks()
            
            # Procesar lote
            for idx in range(batch_start, batch_end):
                row = self.df.iloc[idx]
                iid = str(idx)
                self.checked_rows[iid] = False
                
                # Manejar valores NaN y nulos correctamente
                csv_values = []
                for col in self.campos_csv:
                    value = row.get(col, "")
                    # Convertir NaN, None y valores nulos a string vacío
                    if pd.isna(value) or value is None:
                        csv_values.append("")
                    else:
                        csv_values.append(str(value))
                
                values = [str(idx + 1), "", *csv_values]
                self.tree.insert("", "end", iid=iid, values=values)
        
        # Restaurar colores/estados desde historial
        self.progress_var.set("Restaurando estados...")
        self.root.update_idletasks()
        
        # Buscar rowid correcto basado en SKU
        for sku, estado in self.estado_filas.items():
            for item in self.tree.get_children():
                values = self.tree.item(item, 'values')
                if values and len(values) > 3 and values[3] == sku:  # SKU está en índice 3
                    self.set_estado_fila(item, estado)
                    break
            
        # Sincronizar datos con pestaña masiva
        self.sincronizar_datos_masiva()
        
        # Sincronizar datos con pestaña de tarjetas
        self.sincronizar_datos_tarjetas()
        
        # Forzar sincronización del historial después de cargar CSV
        print(f"DEBUG: Estado filas después de cargar CSV: {self.estado_filas}")
        self.forzar_sincronizacion_completa()
        
        # Limpiar indicador de progreso
        self.progress_var.set("")
        messagebox.showinfo("Éxito", f"Archivo CSV cargado: {total_rows} productos")
        
    def _mostrar_resultado_validacion(self, urls_invalidas):
        """Muestra el resultado de la validación de URLs."""
        self.progress_var.set("")
        
        if urls_invalidas:
            msg = f"⚠️ URLs no válidas detectadas: {', '.join(urls_invalidas)}\n\nPuedes continuar, pero verifica estas imágenes."
            messagebox.showwarning("Validación de URLs", msg)
        else:
            self.progress_var.set("✅ URLs validadas")
            # Limpiar mensaje después de 3 segundos
            self.root.after(3000, lambda: self.progress_var.set(""))
        # Menú contextual
        self.menu_contextual = tk.Menu(self.tree, tearoff=0)
        self.menu_contextual.add_command(label="Marcar como OK (Verde)", command=lambda: self.menu_marcar_estado('verde'))
        self.menu_contextual.add_command(label="Marcar como Sin imágenes (Amarillo)", command=lambda: self.menu_marcar_estado('amarillo'))
        self.menu_contextual.add_command(label="Marcar como Error (Rojo)", command=lambda: self.menu_marcar_estado('rojo'))
        self.menu_contextual.add_command(label="Quitar marca", command=lambda: self.menu_marcar_estado('normal'))
        self.tree.bind("<Button-3>", self.on_treeview_right_click)

    def on_treeview_click(self, event):
        # Detectar si se hizo click en la columna de checkbox
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#2":  # Ahora la columna de checkbox es la segunda
            return
        rowid = self.tree.identify_row(event.y)
        if not rowid:
            return
        # Cambiar el estado del checkbox
        self.checked_rows[rowid] = not self.checked_rows.get(rowid, False)
        self.update_checkbox_and_color(rowid)

    def on_treeview_right_click(self, event):
        rowid = self.tree.identify_row(event.y)
        if not rowid:
            return
        self.tree.selection_set(rowid)
        self.menu_contextual.post(event.x_root, event.y_root)
        self._menu_contextual_rowid = rowid

    def menu_marcar_estado(self, estado):
        rowid = getattr(self, '_menu_contextual_rowid', None)
        if not rowid:
            return
        self.set_estado_fila(rowid, estado)
        # Usar SKU como clave del historial
        values = self.tree.item(rowid, 'values')
        if values and len(values) > 3:  # Asegurar que hay SKU
            sku = values[3]  # SKU está en el índice 3
            self.estado_filas[sku] = estado
            self.guardar_historial_estado()
            # Sincronizar con TreeView masivo
            self.sincronizar_estado_masivo(sku, estado)

    def set_estado_fila(self, rowid, estado):
        # Quitar todos los tags
        self.tree.item(rowid, tags=())
        if estado == 'verde':
            self.tree.item(rowid, tags=("checked",))
            self.tree.tag_configure("checked", background="#c8f7c5")  # Verde claro
            # Marcar checkbox visualmente
            vals = list(self.tree.item(rowid, "values"))
            vals[1] = "✔"  # Ahora el checkbox está en el índice 1
            self.tree.item(rowid, values=vals)
            self.checked_rows[rowid] = True
        elif estado == 'amarillo':
            self.tree.item(rowid, tags=("amarillo",))
            self.tree.tag_configure("amarillo", background="#fff9c4")  # Amarillo claro
            vals = list(self.tree.item(rowid, "values"))
            vals[1] = ""  # Ahora el checkbox está en el índice 1
            self.tree.item(rowid, values=vals)
            self.checked_rows[rowid] = False
        elif estado == 'rojo':
            self.tree.item(rowid, tags=("rojo",))
            self.tree.tag_configure("rojo", background="#ffcdd2")  # Rojo claro
            vals = list(self.tree.item(rowid, "values"))
            vals[1] = ""  # Ahora el checkbox está en el índice 1
            self.tree.item(rowid, values=vals)
            self.checked_rows[rowid] = False
        else:
            # Normal
            vals = list(self.tree.item(rowid, "values"))
            vals[1] = ""  # Ahora el checkbox está en el índice 1
            self.tree.item(rowid, values=vals)
            self.checked_rows[rowid] = False

    def update_checkbox_and_color(self, rowid):
        checked = self.checked_rows.get(rowid, False)
        
        # Optimización: Usar tree.set() en lugar de tree.item() para mejor rendimiento
        checkbox_symbol = "✓" if checked else ""
        self.tree.set(rowid, "_checked", checkbox_symbol)
        
        # Cambiar color de fondo
        if checked:
            self.set_estado_fila(rowid, 'verde')
            # Usar SKU como clave del historial para sincronización
            values = self.tree.item(rowid, 'values')
            if values and len(values) > 3:
                sku = values[3]  # SKU está en índice 3
                self.estado_filas[sku] = 'verde'
                self.guardar_historial_estado()
                # Sincronizar con TreeView masivo
                self.sincronizar_estado_masivo(sku, 'verde')
        else:
            self.set_estado_fila(rowid, 'normal')
            # Usar SKU como clave del historial para sincronización
            values = self.tree.item(rowid, 'values')
            if values and len(values) > 3:
                sku = values[3]  # SKU está en índice 3
                self.estado_filas[sku] = 'normal'
                self.guardar_historial_estado()
                # Sincronizar con TreeView masivo
                self.sincronizar_estado_masivo(sku, 'normal')

    def cargar_plantilla_tarjeta_catalogo(self):
        # Busca la primera tarjeta en el catálogo y la usa como plantilla
        if not self.catalogo_path or not os.path.exists(self.catalogo_path):
            return
        with open(self.catalogo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        match = re.search(r'(<!-- Tarjeta de Producto:[\s\S]+?product-card[\s\S]+?</div>\s*</div>)', contenido)
        if match:
            self.plantilla_tarjeta = match.group(1)

    def buscar_catalogo(self):
        path = filedialog.askopenfilename(filetypes=[("HTML Files", "*.html")])
        if path:
            self.entry_catalogo.delete(0, tk.END)
            self.entry_catalogo.insert(0, path)
            self.catalogo_path = path
            self.cargar_plantilla_tarjeta_catalogo()

    def on_select_producto(self, event):
        selected = self.tree.selection()
        if not selected or self.df is None:
            return
        idx = self.tree.index(selected[0])
        row = self.df.iloc[idx]
        self.producto_actual = row
        # Autollenar campos de imágenes en ambas pestañas
        self.img1.delete(0, tk.END)
        self.img2.delete(0, tk.END)
        self.img3.delete(0, tk.END)
        self.img1_2.delete(0, tk.END)
        self.img2_2.delete(0, tk.END)
        self.img3_2.delete(0, tk.END)
        self.img1.insert(0, row.get("IMAGEN 1", ""))
        self.img2.insert(0, row.get("IMAGEN 2", ""))
        self.img3.insert(0, row.get("IMAGEN 3", ""))
        self.img1_2.insert(0, row.get("IMAGEN 1", ""))
        self.img2_2.insert(0, row.get("IMAGEN 2", ""))
        self.img3_2.insert(0, row.get("IMAGEN 3", ""))
        # Actualizar info en pestaña 2
        self.lbl_marca.config(text=f"Marca: {row.get('Valor(es) del atributo 2', '')}")
        self.lbl_sku.config(text=f"SKU: {row.get('Valor(es) del atributo 1', '')}")
        self.lbl_precio_normal.config(text=f"Precio normal: {row.get('Precio normal', '')}")
        self.lbl_precio_desc.config(text=f"Precio con descuento: {row.get('precio con descuento', '')}")
        self.lbl_descuento.config(text=f"% Descuento: {row.get('Porcentajede descuento', '')}")
        # Actualizar info en frame de info producto seleccionado (pestaña 1)
        self.lbl_info_sku.config(text=f"SKU: {row.get('Valor(es) del atributo 1', '')}")
        self.lbl_info_marca.config(text=f"Marca: {row.get('Valor(es) del atributo 2', '')}")
        self.lbl_info_tipo.config(text=f"Tipo: {row.get('Valor(es) del atributo 3', '')}")

    def crear_pagina_individual(self):
        if self.producto_actual is None:
            messagebox.showwarning("Advertencia", "Selecciona un producto de la tabla.")
            return
        # Tomar los valores actuales de los campos de imágenes
        imagenes = [self.img1.get(), self.img2.get(), self.img3.get()]
        # --- Si falta algún link de imagen, NO generar la página ---
        if any(not img or str(img).lower() == 'nan' for img in imagenes):
            messagebox.showerror("Error", "Debes proporcionar los 3 links de imagen (Imagen 1, 2 y 3) para generar la página individual.")
            return
        # Usar los datos actuales de producto_actual, pero con las imágenes editadas
        row = self.producto_actual.copy()
        row["IMAGEN 1"] = imagenes[0]
        row["IMAGEN 2"] = imagenes[1]
        row["IMAGEN 3"] = imagenes[2]
        html = generar_pagina_individual_desde_plantilla(row, imagenes, self.plantilla_ind_path)
        if html is None:
            return
        nombre_archivo = f"{row.get('SKU','producto')}.html"
        save_path = filedialog.asksaveasfilename(defaultextension=".html", initialfile=nombre_archivo, filetypes=[("HTML Files", "*.html")])
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)
            messagebox.showinfo("Éxito", f"Página individual creada: {os.path.basename(save_path)}")
            # --- Marcar automáticamente el checkbox y color de la fila ---
            if self.tree:
                selected = self.tree.selection()
                if selected:
                    rowid = selected[0]
                    self.checked_rows[rowid] = True
                    self.update_checkbox_and_color(rowid)

    def vista_previa_tarjeta(self):
        if self.producto_actual is None:
            messagebox.showwarning("Advertencia", "Selecciona un producto de la tabla.")
            return
            
        imagenes = [self.img1.get(), self.img2.get(), self.img3.get()]
        
        # Validación de URLs en background (Fase 2)
        self.progress_var.set("Validando imágenes...")
        self.root.update_idletasks()
        
        def validar_imagenes_async():
            urls_invalidas = []
            for i, img_url in enumerate(imagenes, 1):
                if img_url and str(img_url).lower() != 'nan':
                    if not validar_url_imagen(img_url):
                        urls_invalidas.append(f"Imagen {i}")
            
            # Actualizar UI en el hilo principal
            self.root.after(0, lambda: self._mostrar_resultado_validacion(urls_invalidas))
        
        # Ejecutar validación en background
        self.executor.submit(validar_imagenes_async)
        faltan = [i for i, img in enumerate(imagenes, 1) if not img or str(img).lower() == 'nan']
        if faltan:
            msg = "Faltan los siguientes links: " + ", ".join([f"Imagen {i}" for i in faltan]) + ". Puedes continuar, pero revisa que la tarjeta tenga todos los recursos."
            messagebox.showwarning("Advertencia", msg)
        # Usar normalización optimizada
        marca_original = self.producto_actual.get("Valor(es) del atributo 2", "")
        logo = buscar_logo_marca(marca_original, self.logos_dict)
        if not logo:
            messagebox.showwarning("Advertencia", f"No se encontró logo para la marca '{self.producto_actual.get('Valor(es) del atributo 2', '')}'. Verifica el archivo de logos.")
        plantilla_tarjeta = self.plantilla_tarjeta if self.plantilla_tarjeta else (
            '<!-- Tarjeta de Producto: {SKU} -->\n'
            '<div class="product-card" onclick="window.open(\'{LINK}\',\'_blank\')">\n'
            '  <div class="product-image-container multi-image-hover">\n'
            '    <div class="product-brand-overlay"><img src="{LOGO}" alt="Logo {MARCA}"></div>\n'
            '    <img src="{IMG1}" alt="{SKU} - {MARCA} - Vista 1" class="product-img active">\n'
            '    <img src="{IMG2}" alt="{SKU} - {MARCA} - Vista 2" class="product-img">\n'
            '    <img src="{IMG3}" alt="{SKU} - {MARCA} - Vista 3" class="product-img">\n'
            '  </div>\n'
            '  <div class="product-info">\n'
            '    <span class="product-brand">{MARCA}</span>\n'
            '    <h2 class="product-name">{SKU}</h2>\n'
            '    <p class="product-price">\n'
            '      <span class="old-price">{OLD_PRICE}</span>\n'
            '      <span class="new-price">{NEW_PRICE}</span>\n'
            '    </p>\n'
            '  </div>\n'
            '</div>'
        )
        link_redireccion = self.entry_link_tarjeta.get().strip() or self.producto_actual.get("Link_Producto", "")
        if not self.plantilla_tarjeta:
            tarjeta_html = plantilla_tarjeta.format(
                SKU=self.producto_actual.get("Valor(es) del atributo 1", ""),
                MARCA=self.producto_actual.get("Valor(es) del atributo 2", ""),
                LOGO=logo,
                IMG1=imagenes[0],
                IMG2=imagenes[1],
                IMG3=imagenes[2],
                OLD_PRICE=self.producto_actual.get("Precio normal", ""),
                NEW_PRICE=self.producto_actual.get("precio con descuento", ""),
                LINK=link_redireccion
            )
            tarjeta_html = tarjeta_html.replace('<!-- Tarjeta de Producto: {SKU} -->', f'<!-- Tarjeta de Producto: {self.producto_actual.get("Valor(es) del atributo 1", "")} -->')
        else:
            tarjeta_html = generar_tarjeta_catalogo(
                self.producto_actual,
                imagenes,
                logo,
                link_redireccion,
                self.producto_actual.get("Precio normal", ""),
                self.producto_actual.get("precio con descuento", ""),
                self.producto_actual.get("Porcentajede descuento", ""),
                self.plantilla_tarjeta
            )
            tarjeta_html = re.sub(r'<!-- Tarjeta de Producto: [^>]+-->', f'<!-- Tarjeta de Producto: {self.producto_actual.get("Valor(es) del atributo 1", "")} -->', tarjeta_html)
        self.tarjeta_html_actual = tarjeta_html
        self.txt_tarjeta.delete("1.0", tk.END)
        self.txt_tarjeta.insert("1.0", self.tarjeta_html_actual)
        self.btn_copiar_tarjeta.config(state="normal")
        self.btn_insertar_tarjeta.config(state="normal")

    def copiar_tarjeta(self):
        if self.tarjeta_html_actual:
            pyperclip.copy(self.tarjeta_html_actual)
            messagebox.showinfo("Copiado", "Código de la tarjeta copiado al portapapeles.")

    def insertar_en_catalogo(self):
        if not self.catalogo_path:
            messagebox.showerror("Error", "Selecciona el archivo de catálogo.")
            return
        if not self.tarjeta_html_actual:
            messagebox.showerror("Error", "Genera primero la tarjeta individual.")
            return
        with open(self.catalogo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        nuevo_contenido = contenido.replace('</main>', f'{self.tarjeta_html_actual}\n</main>')
        with open(self.catalogo_path, 'w', encoding='utf-8') as f:
            f.write(nuevo_contenido)
        messagebox.showinfo("Éxito", "Tarjeta añadida correctamente al catálogo.")

    def sync_images_to_tab2(self, event=None):
        self.img1_2.delete(0, tk.END)
        self.img2_2.delete(0, tk.END)
        self.img3_2.delete(0, tk.END)
        self.img1_2.insert(0, self.img1.get())
        self.img2_2.insert(0, self.img2.get())
        self.img3_2.insert(0, self.img3.get())

    def sync_images_to_tab1(self, event=None):
        self.img1.delete(0, tk.END)
        self.img2.delete(0, tk.END)
        self.img3.delete(0, tk.END)
        self.img1.insert(0, self.img1_2.get())
        self.img2.insert(0, self.img2_2.get())
        self.img3.insert(0, self.img3_2.get())

    def update_tab2_fields(self, event=None):
        # Cuando se cambia a la pestaña 2, actualiza los campos con el producto seleccionado
        if self.notebook.index(self.notebook.select()) == 1 and self.producto_actual is not None:
            row = self.producto_actual
            self.lbl_marca.config(text=f"Marca: {row.get('Valor(es) del atributo 2', '')}")
            self.lbl_sku.config(text=f"SKU: {row.get('Valor(es) del atributo 1', '')}")
            self.lbl_precio_normal.config(text=f"Precio normal: {row.get('Precio normal', '')}")
            self.lbl_precio_desc.config(text=f"Precio con descuento: {row.get('precio con descuento', '')}")
            self.lbl_descuento.config(text=f"% Descuento: {row.get('Porcentajede descuento', '')}")
            self.img1_2.delete(0, tk.END)
            self.img2_2.delete(0, tk.END)
            self.img3_2.delete(0, tk.END)
            self.img1_2.insert(0, self.img1.get())
            self.img2_2.insert(0, self.img2.get())
            self.img3_2.insert(0, self.img3.get())
    
    # --- Métodos para Generación Masiva de Tarjetas ---
    
    def buscar_plantilla_tarjeta_masiva(self):
        """Busca archivo de plantilla de tarjeta para generación masiva"""
        filename = filedialog.askopenfilename(
            title="Seleccionar plantilla de tarjeta HTML",
            filetypes=[("Archivos HTML", "*.html"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.entry_plantilla_tarjeta_masiva.delete(0, tk.END)
            self.entry_plantilla_tarjeta_masiva.insert(0, filename)
    
    def buscar_catalogo_masivo(self):
        """Busca archivo de catálogo para inserción masiva"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de catálogo HTML",
            filetypes=[("Archivos HTML", "*.html"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.entry_catalogo_masivo.delete(0, tk.END)
            self.entry_catalogo_masivo.insert(0, filename)
    
    def seleccionar_todos_tarjetas(self):
        """Selecciona todos los productos en la pestaña de tarjetas"""
        if not hasattr(self, 'tree_tarjetas') or not self.df is not None:
            return
        
        self.productos_seleccionados_tarjetas.clear()
        for item in self.tree_tarjetas.get_children():
            self.productos_seleccionados_tarjetas.add(item)
            # Marcar visualmente como seleccionado
            self.tree_tarjetas.set(item, 'Seleccionado', '✓')
        
        self.actualizar_contador_seleccionados_tarjetas()
    
    def deseleccionar_todos_tarjetas(self):
        """Deselecciona todos los productos en la pestaña de tarjetas"""
        if not hasattr(self, 'tree_tarjetas'):
            return
        
        self.productos_seleccionados_tarjetas.clear()
        for item in self.tree_tarjetas.get_children():
            self.tree_tarjetas.set(item, 'Seleccionado', '')
        
        self.actualizar_contador_seleccionados_tarjetas()
    
    def seleccionar_marcados_tarjetas(self):
        """Selecciona solo los productos marcados como OK (verde) en la pestaña de tarjetas"""
        if not hasattr(self, 'tree_tarjetas'):
            return
        
        self.productos_seleccionados_tarjetas.clear()
        for item in self.tree_tarjetas.get_children():
            # Verificar si está marcado como verde en el historial
            sku = self.tree_tarjetas.set(item, 'Valor(es) del atributo 1')
            estado = self.estado_filas.get(sku, 'normal')
            
            if estado == 'verde':
                self.productos_seleccionados_tarjetas.add(item)
                self.tree_tarjetas.set(item, 'Seleccionado', '✓')
            else:
                self.tree_tarjetas.set(item, 'Seleccionado', '')
        
        self.actualizar_contador_seleccionados_tarjetas()
    
    def actualizar_contador_seleccionados_tarjetas(self):
        """Actualiza el contador de productos seleccionados en la pestaña de tarjetas"""
        count = len(self.productos_seleccionados_tarjetas)
        self.lbl_seleccionados_tarjetas.config(text=f"Seleccionados: {count}")
    
    def on_treeview_tarjetas_click(self, event):
        """Maneja clics en el TreeView de tarjetas"""
        region = self.tree_tarjetas.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree_tarjetas.identify_row(event.y)
            column = self.tree_tarjetas.identify_column(event.x)
            
            # Si se hace clic en la columna de selección
            if column == '#1':  # Primera columna (Seleccionado)
                if item in self.productos_seleccionados_tarjetas:
                    self.productos_seleccionados_tarjetas.remove(item)
                    self.tree_tarjetas.set(item, 'Seleccionado', '')
                else:
                    self.productos_seleccionados_tarjetas.add(item)
                    self.tree_tarjetas.set(item, 'Seleccionado', '✓')
                
                self.actualizar_contador_seleccionados_tarjetas()
    
    def on_treeview_tarjetas_double_click(self, event):
        """Maneja doble clic en el TreeView de tarjetas"""
        pass  # Implementar si es necesario
    
    def on_treeview_tarjetas_right_click(self, event):
        """Maneja clic derecho en el TreeView de tarjetas"""
        item = self.tree_tarjetas.identify_row(event.y)
        if item:
            self.tree_tarjetas.selection_set(item)
            self.menu_contextual_tarjetas.post(event.x_root, event.y_root)
    
    def menu_marcar_estado_tarjetas(self, estado):
        """Marca el estado de una fila en el TreeView de tarjetas"""
        selection = self.tree_tarjetas.selection()
        if not selection:
            return
        
        for item in selection:
            sku = self.tree_tarjetas.set(item, 'Valor(es) del atributo 1')
            self.set_estado_fila_tarjetas(sku, estado)
            self.update_checkbox_and_color_tarjetas(item)
        
        self.guardar_historial_estado()
    
    def set_estado_fila_tarjetas(self, sku, estado):
        """Establece el estado de una fila en la pestaña de tarjetas"""
        if estado == 'normal':
            if sku in self.estado_filas:
                del self.estado_filas[sku]
        else:
            self.estado_filas[sku] = estado
    
    def update_checkbox_and_color_tarjetas(self, rowid):
        """Actualiza el color de fondo de una fila en el TreeView de tarjetas"""
        sku = self.tree_tarjetas.set(rowid, 'Valor(es) del atributo 1')
        estado = self.estado_filas.get(sku, 'normal')
        
        # Definir colores para cada estado
        colores = {
            'verde': '#d4edda',    # Verde claro
            'amarillo': '#fff3cd', # Amarillo claro
            'rojo': '#f8d7da',     # Rojo claro
            'morado': '#e2d9f3',   # Morado claro
            'normal': '#ffffff'    # Blanco
        }
        
        color = colores.get(estado, '#ffffff')
        
        # Aplicar color a todas las columnas de la fila
        for col in self.tree_tarjetas['columns']:
            self.tree_tarjetas.set(rowid, col, self.tree_tarjetas.set(rowid, col))
        
        # Configurar tags para colores
        tag_name = f"estado_{estado}"
        self.tree_tarjetas.tag_configure(tag_name, background=color)
        
        # Aplicar tag a la fila
        current_tags = list(self.tree_tarjetas.item(rowid, 'tags'))
        # Remover tags de estado anteriores
        current_tags = [tag for tag in current_tags if not tag.startswith('estado_')]
        current_tags.append(tag_name)
        self.tree_tarjetas.item(rowid, tags=current_tags)
    
    def reiniciar_historial_tarjetas(self):
        """Reinicia el historial de estados en la pestaña de tarjetas"""
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres reiniciar el historial de estados?"):
            # Limpiar estados
            self.estado_filas.clear()
            self.tarjetas_generadas.clear()
            
            # Actualizar TreeView
            if hasattr(self, 'tree_tarjetas'):
                for item in self.tree_tarjetas.get_children():
                    self.update_checkbox_and_color_tarjetas(item)
            
            # Guardar cambios
            self.guardar_historial_estado()
            
            messagebox.showinfo("Éxito", "Historial reiniciado correctamente.")
    
    def configurar_columnas_tarjetas(self):
        """Configura las columnas del TreeView de tarjetas basándose en el CSV cargado"""
        if self.df is None:
            return
        
        # Limpiar TreeView
        for item in self.tree_tarjetas.get_children():
            self.tree_tarjetas.delete(item)
        
        # Configurar columnas
        columnas = ['Seleccionado'] + list(self.df.columns)
        self.tree_tarjetas['columns'] = columnas
        
        # Configurar encabezados y anchos
        anchos_columnas = {
            'Seleccionado': 80,
            'Valor(es) del atributo 1': 120,  # SKU
            'Valor(es) del atributo 2': 150,  # Marca
            'Precio normal': 100,
            'precio con descuento': 120,
            'Porcentajede descuento': 100
        }
        
        for col in columnas:
            ancho = anchos_columnas.get(col, 150)
            self.tree_tarjetas.heading(col, text=col, anchor='w')
            self.tree_tarjetas.column(col, width=ancho, anchor='w')
        
        # Llenar con datos
        for index, row in self.df.iterrows():
            valores = [''] + [str(row.get(col, '')) for col in self.df.columns]
            item_id = self.tree_tarjetas.insert('', 'end', values=valores)
            
            # Aplicar color basado en el historial
            self.update_checkbox_and_color_tarjetas(item_id)
    
    def sincronizar_datos_tarjetas(self):
        """Sincroniza los datos del CSV con el TreeView de tarjetas"""
        if self.df is not None:
            self.configurar_columnas_tarjetas()
    
    def generar_tarjetas_masivo(self):
        """Genera tarjetas masivamente para los productos seleccionados"""
        if not self.productos_seleccionados_tarjetas:
            messagebox.showwarning("Advertencia", "No hay productos seleccionados.")
            return
        
        plantilla_path = self.entry_plantilla_tarjeta_masiva.get().strip()
        if not plantilla_path or not os.path.exists(plantilla_path):
            messagebox.showerror("Error", "Selecciona una plantilla de tarjeta válida.")
            return
        
        if not self.logos_dict:
            messagebox.showwarning("Advertencia", "No se han cargado los logos de marcas. Algunas tarjetas podrían no tener logo.")
        
        # Ejecutar generación en hilo separado
        threading.Thread(target=self._generar_tarjetas_async, daemon=True).start()
    
    def _generar_tarjetas_async(self):
        """Genera tarjetas de forma asíncrona"""
        try:
            plantilla_path = self.entry_plantilla_tarjeta_masiva.get().strip()
            
            # Cargar plantilla
            plantilla_content = cargar_plantilla_html(plantilla_path)
            if not plantilla_content:
                return
            
            total_productos = len(self.productos_seleccionados_tarjetas)
            productos_procesados = 0
            
            self.progress_var_tarjetas.set(f"Generando tarjetas... 0/{total_productos}")
            
            for item_id in self.productos_seleccionados_tarjetas:
                try:
                    # Obtener datos del producto
                    valores = {}
                    for col in self.tree_tarjetas['columns']:
                        if col != 'Seleccionado':
                            valores[col] = self.tree_tarjetas.set(item_id, col)
                    
                    # Generar tarjeta
                    tarjeta_html = self._generar_tarjeta_individual(valores, plantilla_content)
                    
                    if tarjeta_html:
                        # Guardar tarjeta generada
                        sku = valores.get('Valor(es) del atributo 1', '')
                        self.tarjetas_generadas[sku] = tarjeta_html
                        
                        # Marcar como generado (morado)
                        self.set_estado_fila_tarjetas(sku, 'morado')
                        self.root.after(0, lambda item=item_id: self.update_checkbox_and_color_tarjetas(item))
                    
                    productos_procesados += 1
                    self.progress_var_tarjetas.set(f"Generando tarjetas... {productos_procesados}/{total_productos}")
                    
                except Exception as e:
                    print(f"Error procesando producto: {e}")
                    continue
            
            # Guardar historial
            self.guardar_historial_estado()
            
            self.progress_var_tarjetas.set(f"✅ Tarjetas generadas: {len(self.tarjetas_generadas)}")
            messagebox.showinfo("Éxito", f"Se generaron {len(self.tarjetas_generadas)} tarjetas correctamente.")
            
        except Exception as e:
            self.progress_var_tarjetas.set("❌ Error en la generación")
            messagebox.showerror("Error", f"Error durante la generación: {str(e)}")
    
    def _generar_tarjeta_individual(self, producto_data, plantilla_content):
        """Genera una tarjeta individual basada en los datos del producto"""
        try:
            # Extraer datos del producto
            sku = producto_data.get('Valor(es) del atributo 1', '')
            marca = producto_data.get('Valor(es) del atributo 2', '')
            precio_normal = producto_data.get('Precio normal', '')
            precio_descuento = producto_data.get('precio con descuento', '')
            porcentaje_desc = producto_data.get('Porcentajede descuento', '')
            
            # Construir URLs de imágenes
            imagenes = [
                producto_data.get('IMAGEN 1', ''),
                producto_data.get('IMAGEN 2', ''),
                producto_data.get('IMAGEN 3', '')
            ]
            
            # Buscar logo de la marca
            logo_marca = buscar_logo_marca(marca, self.logos_dict)
            
            # Buscar link de redirección específico para este SKU
            link_producto = self.links_redireccion.get(sku, f"#producto-{sku}")
            
            # Generar tarjeta usando la función existente
            row_dict = {
                'SKU': sku,
                'Marca': marca,
                'Valor(es) del atributo 1': sku,
                'Valor(es) del atributo 2': marca
            }
            
            # Usar la misma lógica que vista_previa_tarjeta
            if not plantilla_content or plantilla_content.strip() == '':
                # Usar plantilla por defecto si no hay plantilla cargada
                plantilla_tarjeta = (
                    '<!-- Tarjeta de Producto: {SKU} -->\n'
                    '<div class="product-card" onclick="window.open(\'{LINK}\',\'_blank\')"\n'
                    '  <div class="product-image-container multi-image-hover">\n'
                    '    <div class="product-brand-overlay"><img src="{LOGO}" alt="Logo {MARCA}"></div>\n'
                    '    <img src="{IMG1}" alt="{SKU} - {MARCA} - Vista 1" class="product-img active">\n'
                    '    <img src="{IMG2}" alt="{SKU} - {MARCA} - Vista 2" class="product-img">\n'
                    '    <img src="{IMG3}" alt="{SKU} - {MARCA} - Vista 3" class="product-img">\n'
                    '  </div>\n'
                    '  <div class="product-info">\n'
                    '    <span class="product-brand">{MARCA}</span>\n'
                    '    <h2 class="product-name">{SKU}</h2>\n'
                    '    <p class="product-price">\n'
                    '      <span class="old-price">{OLD_PRICE}</span>\n'
                    '      <span class="new-price">{NEW_PRICE}</span>\n'
                    '    </p>\n'
                    '  </div>\n'
                    '</div>'
                )
                tarjeta_html = plantilla_tarjeta.format(
                    SKU=sku,
                    MARCA=marca,
                    LOGO=logo_marca,
                    IMG1=imagenes[0] if len(imagenes) > 0 else '',
                    IMG2=imagenes[1] if len(imagenes) > 1 else '',
                    IMG3=imagenes[2] if len(imagenes) > 2 else '',
                    OLD_PRICE=precio_normal if precio_normal else '',
                    NEW_PRICE=precio_descuento if precio_descuento else '',
                    LINK=link_producto
                )
            else:
                # Usar plantilla cargada con generar_tarjeta_catalogo
                tarjeta_html = generar_tarjeta_catalogo(
                    row_dict,
                    imagenes,
                    logo_marca,
                    link_producto,
                    precio_normal,
                    precio_descuento,
                    porcentaje_desc,
                    plantilla_content
                )
            
            return tarjeta_html
            
        except Exception as e:
            print(f"Error generando tarjeta para {producto_data.get('Valor(es) del atributo 1', 'SKU desconocido')}: {e}")
            return None
    
    def cargar_logos_tarjetas(self):
        """Carga archivo de logos específico para la pestaña de tarjetas"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de logos",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.entry_logos_tarjetas.delete(0, tk.END)
            self.entry_logos_tarjetas.insert(0, filename)
            
            # Cargar logos usando la función existente
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Procesar líneas del archivo
                lineas = contenido.strip().split('\n')
                logos_cargados = 0
                
                for linea in lineas:
                    linea = linea.strip()
                    if linea and (':' in linea or '=' in linea):
                        try:
                            # Manejar tanto ':' como '=' como separadores
                            if ':' in linea:
                                marca, url = linea.split(':', 1)
                            else:
                                marca, url = linea.split('=', 1)
                            marca = marca.strip()
                            url = url.strip()
                            if marca and url:
                                self.logos_dict[marca] = url
                                logos_cargados += 1
                        except ValueError:
                            continue
                
                messagebox.showinfo("Éxito", f"Se cargaron {logos_cargados} logos de marcas.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar logos: {str(e)}")
    
    def cargar_links_redireccion(self):
        """Carga archivo de links de redirección"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de links de redirección",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.entry_links_redireccion.delete(0, tk.END)
            self.entry_links_redireccion.insert(0, filename)
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Procesar líneas del archivo
                lineas = contenido.strip().split('\n')
                links_cargados = 0
                
                for linea in lineas:
                    linea = linea.strip()
                    if linea and (':' in linea or '=' in linea):
                        try:
                            # Manejar tanto ':' como '=' como separadores
                            if ':' in linea:
                                sku, url = linea.split(':', 1)
                            else:
                                sku, url = linea.split('=', 1)
                            sku = sku.strip()
                            url = url.strip()
                            
                            # Remover prefijo 'Producto-' si existe
                            if sku.startswith('Producto-'):
                                sku = sku[9:]  # Remover 'Producto-'
                            
                            if sku and url:
                                self.links_redireccion[sku] = url
                                links_cargados += 1
                        except ValueError:
                            continue
                
                messagebox.showinfo("Éxito", f"Se cargaron {links_cargados} links de redirección.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar links: {str(e)}")
    
    def insertar_tarjetas_en_catalogo(self):
        """Inserta todas las tarjetas generadas en el catálogo"""
        if not self.tarjetas_generadas:
            messagebox.showwarning("Advertencia", "No hay tarjetas generadas para insertar.")
            return
        
        catalogo_path = self.entry_catalogo_masivo.get().strip()
        if not catalogo_path or not os.path.exists(catalogo_path):
            messagebox.showerror("Error", "Selecciona un archivo de catálogo válido.")
            return
        
        try:
            # Leer catálogo actual
            with open(catalogo_path, 'r', encoding='utf-8') as f:
                contenido_catalogo = f.read()
            
            # Preparar todas las tarjetas para insertar
            todas_las_tarjetas = '\n'.join(self.tarjetas_generadas.values())
            
            # Insertar antes del cierre de </main>
            nuevo_contenido = contenido_catalogo.replace('</main>', f'{todas_las_tarjetas}\n</main>')
            
            # Escribir catálogo actualizado
            with open(catalogo_path, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            
            messagebox.showinfo("Éxito", f"Se insertaron {len(self.tarjetas_generadas)} tarjetas en el catálogo correctamente.")
            
            # Limpiar tarjetas generadas después de insertar
            self.tarjetas_generadas.clear()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al insertar tarjetas en el catálogo: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = GeneradorCatalogoApp(root)
    root.mainloop()