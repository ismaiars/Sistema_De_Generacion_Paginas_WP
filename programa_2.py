import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import pyperclip
import re
import json

# ---------------- FUNCIONES AUXILIARES PARA HTML ----------------
def cargar_plantilla_html(path):
    if not os.path.exists(path):
        messagebox.showerror("Error", f"No se encontró la plantilla base '{os.path.basename(path)}'.")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def buscar_logo_marca(marca, logos_dict):
    # Normaliza la marca quitando espacios, minúsculas y caracteres especiales
    clave = str(marca).strip().lower().replace(' ', '').replace('-', '').replace('_', '')
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
    # Reemplazo en <img> (todas las apariciones, no solo una)
    html = re.sub(r'src="[^"]*RB2398-1_resultado\.webp"', f'src="{img1}"', html)
    html = re.sub(r'src="[^"]*RB2398-2_resultado\.webp"', f'src="{img2}"', html)
    html = re.sub(r'src="[^"]*RB2398-3_resultado\.webp"', f'src="{img3}"', html)
    # Reemplazo en miniaturas (puede haber más de una aparición por imagen)
    html = re.sub(r'src="[^"]*1_resultado\.webp"', f'src="{img1}"', html)
    html = re.sub(r'src="[^"]*2_resultado\.webp"', f'src="{img2}"', html)
    html = re.sub(r'src="[^"]*3_resultado\.webp"', f'src="{img3}"', html)
    # Reemplazo en el script JS (array imageSources, siempre 3, solo links del CSV/campos, o vacío)
    img1_js = f'"{img1}"'
    img2_js = f'"{img2}"'
    img3_js = f'"{img3}"'
    html = re.sub(r'const imageSources = \[[^\]]*\];', f'const imageSources = [{img1_js}, {img2_js}, {img3_js}];', html)

    # --- Reemplazo de textos principales (marca, modelo, precios, descuento) ---
    html = re.sub(r'<h1[^>]*id="product-brand"[^>]*>[^<]*</h1>', f'<h1 id="product-brand" class="text-4xl md:text-5xl font-bold text-orange-500 uppercase">{row.get("Valor(es) del atributo 2", "")}</h1>', html)
    html = re.sub(r'<p[^>]*id="product-model"[^>]*>[^<]*</p>', f'<p id="product-model" class="text-xl text-gray-400 mb-4">{row.get("Valor(es) del atributo 1", "")}</p>', html)
    html = re.sub(r'<span class="text-2xl text-gray-400 line-through mr-2">[^<]*</span>', f'<span class="text-2xl text-gray-400 line-through mr-2">{row.get("Precio normal", "")}</span>', html)
    html = re.sub(r'<span class="inline-block bg-red-100 text-red-600 text-lg font-bold px-2 py-1 rounded align-middle mr-2">[^<]*</span>', f'<span class="inline-block bg-red-100 text-red-600 text-lg font-bold px-2 py-1 rounded align-middle mr-2">{row.get("Porcentajede descuento", "")}</span>', html)
    html = re.sub(r'<span class="text-5xl font-extrabold text-black">[^<]*</span>', f'<span class="text-5xl font-extrabold text-black">{row.get("precio con descuento", "")}</span>', html)

    # --- Reemplazo de tabla de especificaciones ---
    # Mapeo de campos: (ajusta si tus columnas cambian)
    tabla_map = [
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700 w-1/3">SKU</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 1", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Marca</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 2", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Tipo</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 3", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Color</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 4", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Forma</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 5", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Material</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 6", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Varillas</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 7", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Clip</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 8", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Color de Mica</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 9", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Medida</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 10", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Puente</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 11", "")}</td></tr>'),
        (r'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr><td class="py-3 px-4 font-semibold text-gray-700">Accesorios</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 12", "")}</td></tr>'),
        (r'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">[^<]*</td></tr>', f'<tr class="bg-gray-50"><td class="py-3 px-4 font-semibold text-gray-700">Garantía</td><td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 13", "")}</td></tr>'),
    ]
    for patron, reemplazo in tabla_map:
        html = re.sub(patron, reemplazo, html)

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
        self.cargar_historial_estado()

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
        
        self.notebook = ttk.Notebook(root, style='Modern.TNotebook')
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Pestaña 1: Página individual ---
        self.tab1 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab1, text="  Página Individual  ")
        # --- Pestaña 2: Tarjeta individual y catálogo ---
        self.tab2 = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(self.tab2, text="  Catálogo y Tarjetas  ")

        # --- Pestaña 1 ---
        # Header con título
        header1 = tk.Frame(self.tab1, bg="#ffffff", height=60)
        header1.pack(fill="x", padx=20, pady=(20, 10))
        header1.pack_propagate(False)
        title1 = tk.Label(header1, text="Generación de Páginas Individuales", 
                         font=('Segoe UI', 16, 'bold'), fg="#212529", bg="#ffffff")
        title1.pack(side="left", pady=15)
        
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
        self.xscroll = tk.Scrollbar(self.tree_frame, orient='horizontal')
        self.xscroll.pack(side='bottom', fill='x')
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
        
        # Configurar efectos hover para botones
        self._setup_button_hover_effects()

        # Sincronización de imágenes y datos entre pestañas
        self.img1.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img2.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img3.bind('<KeyRelease>', self.sync_images_to_tab2)
        self.img1_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.img2_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.img3_2.bind('<KeyRelease>', self.sync_images_to_tab1)
        self.notebook.bind('<<NotebookTabChanged>>', self.update_tab2_fields)
    
    def _setup_button_hover_effects(self):
        """Configura efectos hover para los botones"""
        buttons_config = [
            (self.btn_cargar, "#007bff", "#0056b3"),
            (self.btn_reiniciar_historial, "#dc3545", "#c82333"),
            (self.btn_buscar_plantilla_ind, "#f8f9fa", "#e9ecef"),
            (self.btn_pagina_individual, "#28a745", "#1e7e34"),
            (self.btn_buscar_catalogo, "#f8f9fa", "#e9ecef"),
            (self.btn_cargar_logos, "#007bff", "#0056b3"),
            (self.btn_generar_tarjeta, "#007bff", "#0056b3"),
            (self.btn_copiar_tarjeta, "#6c757d", "#545b62"),
            (self.btn_insertar_tarjeta, "#28a745", "#1e7e34")
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
            
            # Restablecer estados visuales en el TreeView si existe
            if self.tree:
                for item in self.tree.get_children():
                    self.set_estado_fila(item, 'normal')
                    self.checked_rows[item] = False
            
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
        if path.endswith('.csv'):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                marca = str(row.iloc[0]).strip().lower().replace(' ', '').replace('-', '').replace('_', '')
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
                    self.logos_dict[marca.strip().lower().replace(' ', '').replace('-', '').replace('_', '')] = logo.strip()
        messagebox.showinfo("Éxito", "Archivo de logos cargado correctamente.")

    def cargar_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if not path:
            return
        if path.endswith('.xlsx'):
            self.df = pd.read_excel(path)
        else:
            self.df = pd.read_csv(path)
        self.campos_csv = list(self.df.columns)
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
                                height=10, xscrollcommand=self.xscroll.set, style='Modern.Treeview')
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
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_producto)
        self.tree.bind("<Button-1>", self.on_treeview_click)
        self.xscroll.config(command=self.tree.xview)
        self.tree.delete(*self.tree.get_children())
        self.checked_rows = {}
        for idx, (_, row) in enumerate(self.df.iterrows()):
            iid = str(idx)
            self.checked_rows[iid] = False
            values = [str(idx + 1), "", *[row.get(col, "") for col in self.campos_csv]]
            self.tree.insert("", "end", iid=iid, values=values)
        # Restaurar colores/estados desde historial
        for rowid, estado in self.estado_filas.items():
            self.set_estado_fila(rowid, estado)
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
        self.estado_filas[rowid] = estado
        self.guardar_historial_estado()

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
        # Cambiar color de fondo
        if checked:
            self.set_estado_fila(rowid, 'verde')
            self.estado_filas[rowid] = 'verde'
            self.guardar_historial_estado()
        else:
            self.set_estado_fila(rowid, 'normal')
            self.estado_filas[rowid] = 'normal'
            self.guardar_historial_estado()

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
        faltan = [i for i, img in enumerate(imagenes, 1) if not img or str(img).lower() == 'nan']
        if faltan:
            msg = "Faltan los siguientes links: " + ", ".join([f"Imagen {i}" for i in faltan]) + ". Puedes continuar, pero revisa que la tarjeta tenga todos los recursos."
            messagebox.showwarning("Advertencia", msg)
        marca = self.producto_actual.get("Valor(es) del atributo 2", "").strip().lower().replace(' ', '').replace('-', '').replace('_', '')
        logo = buscar_logo_marca(marca, self.logos_dict)
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

if __name__ == "__main__":
    root = tk.Tk()
    app = GeneradorCatalogoApp(root)
    root.mainloop()
