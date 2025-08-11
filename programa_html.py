import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import pyperclip
import re

# ---------------- FUNCIONES AUXILIARES PARA HTML ----------------
def cargar_plantilla_html(path_default, path_usuario=None):
    path = path_usuario if path_usuario else path_default
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
    html = re.sub(r'<span class="product-brand">[^<]+</span>', f'<span class="product-brand">{row.get('Marca','')}</span>', html)
    html = re.sub(r'<h2 class="product-name">[^<]+</h2>', f'<h2 class="product-name">{row.get('SKU','')}</h2>', html)
    html = re.sub(r'<span class="old-price">[^<]*</span>', f'<span class="old-price">{old_price}</span>', html)
    html = re.sub(r'<span class="new-price">[^<]*</span>', f'<span class="new-price">{new_price}</span>', html)
    html = re.sub(r'<div class="discount-badge">[^<]*</div>', f'<div class="discount-badge">{descuento} de descuento</div>' if descuento else '', html)
    html = re.sub(r'<div class="product-brand-overlay"><img src="[^"]+" alt="[^"]+"></div>', f'<div class="product-brand-overlay"><img src="{logo_marca}" alt="Logo {row.get('Marca','')}"></div>', html)
    # Link de producto
    html = re.sub(r'onclick="window.open\([^)]+\)"', f'onclick="window.open(\'{link_producto}\',\'_blank\')"', html)
    return html

def generar_pagina_individual_desde_plantilla(row, imagenes, plantilla_path):
    html = cargar_plantilla_html('pagina_producto_VLE41684.html', plantilla_path)
    if html is None:
        return None
    # Reemplazo de imágenes principales y thumbnails
    html = re.sub(r'src="[^"]*CLOE-VLE.41684.-1_resultado-1.webp"', f'src="{imagenes[0]}"', html, count=2)
    html = re.sub(r'src="[^"]*CLOE-VLE.41684.-3_resultado-1.webp"', f'src="{imagenes[1]}"', html, count=1)
    html = re.sub(r'src="[^"]*CLOE-VLE.41684.-3_resultado-1.webp"', f'src="{imagenes[2]}"', html, count=1)
    # Reemplazo de textos principales
    html = re.sub(r'>CLOE<', f'>{row.get("Valor(es) del atributo 2", "")}<', html)
    html = re.sub(r'>VLE 41684<', f'>{row.get("Valor(es) del atributo 1", "")}<', html)
    html = html.replace('$3,600.00', row.get('Precio normal', ''))
    html = html.replace('$3,060.00', row.get('precio con descuento', ''))
    html = html.replace('-15%', row.get('Porcentajede descuento', ''))
    # Reemplazo de tabla de especificaciones
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">VLE 41684</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 1", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">CLOE</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 2", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Lente oftálmico</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 3", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Transparente</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 4", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Agatada</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 5", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Acetato</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 6", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Acetato con metal</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 7", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Sin clip</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 8", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Transparente</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 9", "")}</td>', html, count=1)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Mediano</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 10", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">puente anatomico</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 11", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">Lente, paño, estuche y líquido antirreflejante</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 12", "")}</td>', html)
    html = re.sub(r'<td class="py-3 px-4 text-gray-800">30 días de garantía contra defectos de fábrica.</td>', f'<td class="py-3 px-4 text-gray-800">{row.get("Valor(es) del atributo 13", "")}</td>', html)
    return html

# ---------------- GUI PRINCIPAL ----------------
class GeneradorCatalogoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Productos para Catálogo")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 700)
        self.df = None
        self.producto_actual = None
        self.catalogo_path = ''
        self.campos_csv = []
        self.plantilla_ind_path = ''
        self.plantilla_tarjeta = ''
        self.logos_dict = {}

        # Frame superior
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=5, pady=5)

        self.btn_cargar = tk.Button(top_frame, text="Cargar CSV", command=self.cargar_csv)
        self.btn_cargar.pack(side="right", padx=5)

        # Plantilla individual
        tk.Label(top_frame, text="Plantilla página individual:").pack(side="left", padx=5)
        self.entry_plantilla_ind = tk.Entry(top_frame, width=40)
        self.entry_plantilla_ind.pack(side="left")
        self.btn_buscar_plantilla_ind = tk.Button(top_frame, text="Buscar plantilla", command=self.buscar_plantilla_ind)
        self.btn_buscar_plantilla_ind.pack(side="left", padx=2)

        # Logos marcas
        tk.Label(top_frame, text="Archivo de logos de marcas:").pack(side="left", padx=5)
        self.entry_logos = tk.Entry(top_frame, width=40)
        self.entry_logos.pack(side="left")
        self.btn_cargar_logos = tk.Button(top_frame, text="Cargar logos", command=self.cargar_logos)
        self.btn_cargar_logos.pack(side="left", padx=2)

        # Tabla de productos con scroll horizontal
        self.tree = None
        self.tree_frame = tk.Frame(root)
        self.tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.xscroll = tk.Scrollbar(self.tree_frame, orient='horizontal')
        self.xscroll.pack(side='bottom', fill='x')

        # Frame de edición de imágenes
        edit_frame = tk.LabelFrame(root, text="Imágenes para el Producto Seleccionado")
        edit_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(edit_frame, text="Imagen 1:").grid(row=0, column=0, sticky="w")
        self.img1 = tk.Entry(edit_frame, width=60)
        self.img1.grid(row=0, column=1, padx=5)
        tk.Label(edit_frame, text="Imagen 2:").grid(row=0, column=2, sticky="w")
        self.img2 = tk.Entry(edit_frame, width=60)
        self.img2.grid(row=0, column=3, padx=5)
        tk.Label(edit_frame, text="Imagen 3:").grid(row=1, column=0, sticky="w")
        self.img3 = tk.Entry(edit_frame, width=60)
        self.img3.grid(row=1, column=1, padx=5)

        # Botón para generar página individual
        self.btn_pagina_individual = tk.Button(edit_frame, text="Generar y descargar página individual", command=self.crear_pagina_individual)
        self.btn_pagina_individual.grid(row=2, column=0, columnspan=4, pady=10)

        # Frame para tarjeta individual y catálogo
        tarjeta_frame = tk.LabelFrame(root, text="Tarjeta Individual para Catálogo")
        tarjeta_frame.pack(fill="x", padx=5, pady=5)
        # Buscar catálogo primero
        catalogo_row = tk.Frame(tarjeta_frame)
        catalogo_row.pack(fill="x", pady=2)
        self.entry_catalogo = tk.Entry(catalogo_row, width=40)
        self.entry_catalogo.pack(side="left", padx=5)
        self.btn_buscar_catalogo = tk.Button(catalogo_row, text="Buscar catálogo", command=self.buscar_catalogo)
        self.btn_buscar_catalogo.pack(side="left", padx=2)
        # Link de redirección
        link_row = tk.Frame(tarjeta_frame)
        link_row.pack(fill="x", pady=2)
        tk.Label(link_row, text="Link de redirección:").pack(side="left", padx=5)
        self.entry_link_tarjeta = tk.Entry(link_row, width=60)
        self.entry_link_tarjeta.pack(side="left", padx=5)
        # Botones de acción
        btns_row = tk.Frame(tarjeta_frame)
        btns_row.pack(fill="x", pady=2)
        self.btn_generar_tarjeta = tk.Button(btns_row, text="Generar tarjeta individual", command=self.vista_previa_tarjeta)
        self.btn_generar_tarjeta.pack(side="left", padx=5, pady=5)
        self.btn_copiar_tarjeta = tk.Button(btns_row, text="Copiar código de tarjeta", command=self.copiar_tarjeta, state="disabled")
        self.btn_copiar_tarjeta.pack(side="left", padx=5, pady=5)
        self.btn_insertar_tarjeta = tk.Button(btns_row, text="Agregar tarjeta al catálogo", command=self.insertar_en_catalogo, state="disabled")
        self.btn_insertar_tarjeta.pack(side="left", padx=5, pady=5)
        # Scrollbars para la previsualización
        self.txt_tarjeta_frame = tk.Frame(tarjeta_frame)
        self.txt_tarjeta_frame.pack(fill="x", padx=5, pady=5, expand=True)
        self.txt_tarjeta_scroll_y = tk.Scrollbar(self.txt_tarjeta_frame, orient="vertical")
        self.txt_tarjeta_scroll_y.pack(side="right", fill="y")
        self.txt_tarjeta_scroll_x = tk.Scrollbar(self.txt_tarjeta_frame, orient="horizontal")
        self.txt_tarjeta_scroll_x.pack(side="bottom", fill="x")
        self.txt_tarjeta = tk.Text(self.txt_tarjeta_frame, height=18, wrap="none", yscrollcommand=self.txt_tarjeta_scroll_y.set, xscrollcommand=self.txt_tarjeta_scroll_x.set)
        self.txt_tarjeta.pack(fill="both", expand=True)
        self.txt_tarjeta_scroll_y.config(command=self.txt_tarjeta.yview)
        self.txt_tarjeta_scroll_x.config(command=self.txt_tarjeta.xview)

        self.tarjeta_html_actual = ''
        self.plantilla_tarjeta = ''

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
        self.tree = ttk.Treeview(self.tree_frame, columns=self.campos_csv, show="headings", height=10, xscrollcommand=self.xscroll.set)
        for col in self.campos_csv:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_producto)
        self.xscroll.config(command=self.tree.xview)
        self.tree.delete(*self.tree.get_children())
        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=[row.get(col, "") for col in self.campos_csv])
        # Cargar plantilla de tarjeta del catálogo (primera tarjeta encontrada)
        self.cargar_plantilla_tarjeta_catalogo()

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
        # Autollenar campos de imágenes
        self.img1.delete(0, tk.END)
        self.img2.delete(0, tk.END)
        self.img3.delete(0, tk.END)
        self.img1.insert(0, row.get("IMAGEN 1", ""))
        self.img2.insert(0, row.get("IMAGEN 2", ""))
        self.img3.insert(0, row.get("IMAGEN 3", ""))

    def crear_pagina_individual(self):
        if self.producto_actual is None:
            messagebox.showwarning("Advertencia", "Selecciona un producto de la tabla.")
            return
        imagenes = [self.img1.get(), self.img2.get(), self.img3.get()]
        faltan = [i for i, img in enumerate(imagenes, 1) if not img or str(img).lower() == 'nan']
        if faltan:
            msg = "Faltan los siguientes links: " + ", ".join([f"Imagen {i}" for i in faltan]) + ". Puedes continuar, pero revisa que la página tenga todos los recursos."
            messagebox.showwarning("Advertencia", msg)
        html = generar_pagina_individual_desde_plantilla(self.producto_actual, imagenes, self.plantilla_ind_path)
        if html is None:
            return
        nombre_archivo = f"{self.producto_actual.get('SKU','producto')}.html"
        save_path = filedialog.asksaveasfilename(defaultextension=".html", initialfile=nombre_archivo, filetypes=[("HTML Files", "*.html")])
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)
            messagebox.showinfo("Éxito", f"Página individual creada: {os.path.basename(save_path)}")

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

if __name__ == "__main__":
    root = tk.Tk()
    app = GeneradorCatalogoApp(root)
    root.mainloop()
