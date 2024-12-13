import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import cv2
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import os
import io
from datetime import datetime

class SistemaRegistroEscolar:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Registro Escolar")
        
        # Configurar peso de filas y columnas para responsividad
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Obtener dimensiones de la pantalla
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Establecer tamaño inicial de la ventana (80% del tamaño de la pantalla)
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Configurar color de fondo principal
        self.root.configure(bg='#F5E6E8')  # Rosa pastel claro

        # Inicializar base de datos local
        self.inicializar_base_datos()

        # Variables de usuario
        self.usuario = tk.StringVar()
        self.contrasena = tk.StringVar()

        # Crear frames para transiciones
        self.frames = {}
        for F in (PaginaLogin, PaginaNiveles, PaginaRegistro, PaginaLectorQR, PaginaConsulta):
            frame = F(self.root, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.mostrar_frame(PaginaLogin)

    def mostrar_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()

    def cerrar_sesion(self):
        self.usuario.set("")
        self.contrasena.set("")
        self.mostrar_frame(PaginaLogin)

    def inicializar_base_datos(self):
        self.conexion = sqlite3.connect('registro_escolar.db')
        cursor = self.conexion.cursor()
    
        # Primero, eliminar la base de datos existente si existe
        cursor.execute("DROP TABLE IF EXISTS alumnos")
        cursor.execute("DROP TABLE IF EXISTS registro_entrada_salida")
    
        # Crear tabla de alumnos con la columna fecha_registro
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alumnos (
                id INTEGER PRIMARY KEY,
                matricula TEXT UNIQUE,
                nombre TEXT,
                edad INTEGER,
                nivel TEXT,
                grado TEXT,
                grupo TEXT,
                codigo_barras TEXT UNIQUE,
                fotografia BLOB,
                fecha_registro DATETIME
            )
        ''')
    
        # Crear tabla de registro de entrada/salida
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_entrada_salida (
                id INTEGER PRIMARY KEY,
                alumno_id INTEGER,
                fecha_hora DATETIME,
                tipo TEXT,
                FOREIGN KEY (alumno_id) REFERENCES alumnos(id)
            )
        ''')
    
        self.conexion.commit()
    
        # Crear índices para mejorar el rendimiento
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alumno_nivel 
            ON alumnos(nivel)
        ''')
    
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_alumno_grupo 
            ON alumnos(nivel, grado, grupo)
        ''')
    
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_registro_alumno 
            ON registro_entrada_salida(alumno_id)
        ''')
    
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_registro_fecha 
            ON registro_entrada_salida(fecha_hora)
        ''')
    
        # Crear vista para contar alumnos por grupo
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS view_alumnos_por_grupo AS
            SELECT nivel, grado, grupo, COUNT(*) as total_alumnos
            FROM alumnos
            GROUP BY nivel, grado, grupo
        ''')
    
        # Crear trigger para verificar límite de alumnos por grupo
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS check_grupo_limite
            BEFORE INSERT ON alumnos
            BEGIN
                SELECT CASE
                    WHEN (
                        SELECT COUNT(*)
                        FROM alumnos
                    WHERE nivel = NEW.nivel
                    AND grado = NEW.grado
                    AND grupo = NEW.grupo
                ) >= 45
                THEN RAISE(ABORT, 'El grupo ha alcanzado el límite máximo de 45 alumnos')
            END;
        END;
    ''')
    
        self.conexion.commit()

    def guardar_alumno(self, datos):
        cursor = self.conexion.cursor()
        cursor.execute('''
            INSERT INTO alumnos 
            (matricula, nombre, edad, nivel, grado, grupo, codigo_barras, fotografia, fecha_registro) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', datos)
        self.conexion.commit()

class PaginaLogin(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg='#F5E6E8')
        self.controller = controller
        
        # Hacer el frame responsivo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame central para el login
        login_frame = tk.Frame(self, bg='white', bd=10)
        login_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Título
        titulo = tk.Label(login_frame, 
                         text="Sistema de Registro Escolar",
                         font=("Arial", 24, "bold"),
                         bg='white',
                         fg='#6B4E71')  # Morado pastel
        titulo.pack(pady=20)

        # Campos de entrada
        tk.Label(login_frame, text="Usuario", bg='white', font=("Arial", 12)).pack()
        usuario_entry = tk.Entry(login_frame, 
                               textvariable=controller.usuario,
                               font=("Arial", 12))
        usuario_entry.pack(pady=5, padx=20)

        tk.Label(login_frame, text="Contraseña", bg='white', font=("Arial", 12)).pack()
        contrasena_entry = tk.Entry(login_frame,
                                  show="*",
                                  textvariable=controller.contrasena,
                                  font=("Arial", 12))
        contrasena_entry.pack(pady=5, padx=20)

        # Botón de login estilizado
        btn_login = tk.Button(login_frame,
                            text="Iniciar Sesión",
                            command=self.validar_login,
                            bg='#6B4E71',
                            fg='white',
                            font=("Arial", 12),
                            relief=tk.RAISED,
                            padx=20)
        btn_login.pack(pady=20)

    def validar_login(self):
        if self.controller.usuario.get() == "admin" and \
           self.controller.contrasena.get() == "escuela2024":
            self.controller.mostrar_frame(PaginaNiveles)
        else:
            messagebox.showerror("Error", "Credenciales incorrectas")

class PaginaNiveles(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg='#F5E6E8')
        self.controller = controller

        # Configurar grid responsivo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame principal
        main_frame = tk.Frame(self, bg='#F5E6E8')
        main_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Título
        tk.Label(main_frame,
                text="Seleccione Nivel Educativo",
                font=("Arial", 24, "bold"),
                bg='#F5E6E8',
                fg='#6B4E71').pack(pady=20)

        # Botones de nivel
        niveles = [
            ("Preescolar", "#FFE5D9"),  # Melocotón pastel
            ("Primaria", "#D4E6B5"),    # Verde pastel
            ("Secundaria", "#E3D7F4")   # Lavanda pastel
        ]

        for nivel, color in niveles:
            btn = tk.Button(main_frame,
                          text=nivel,
                          bg=color,
                          font=("Arial", 14),
                          command=lambda n=nivel: self.seleccionar_nivel(n),
                          width=20,
                          relief=tk.RAISED)
            btn.pack(pady=10)

        # Botones adicionales
        btn_qr = tk.Button(main_frame,
                         text="Lector QR",
                         command=lambda: controller.mostrar_frame(PaginaLectorQR),
                         bg='#B5C7D4',  # Azul pastel
                         font=("Arial", 14),
                         width=20)
        btn_qr.pack(pady=10)

        btn_consulta = tk.Button(main_frame,
                              text="Consultar Registros",
                              command=lambda: controller.mostrar_frame(PaginaConsulta),
                              bg='#D4B5C7',  # Rosa pastel
                              font=("Arial", 14),
                              width=20)
        btn_consulta.pack(pady=10)

        # Botón de cerrar sesión
        btn_cerrar = tk.Button(main_frame,
                             text="Cerrar Sesión",
                             command=controller.cerrar_sesion,
                             bg='#FFB5B5',  # Rojo pastel
                             font=("Arial", 14),
                             width=20)
        btn_cerrar.pack(pady=20)

    def seleccionar_nivel(self, nivel):
        self.controller.frames[PaginaRegistro].nivel_seleccionado = nivel
        self.controller.mostrar_frame(PaginaRegistro)

class PaginaRegistro(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg='#F5E6E8')
        self.controller = controller
        self.nivel_seleccionado = ""
        self.foto_path = None
        
        # Variables
        self.nivel_var = tk.StringVar()
        self.grado_var = tk.StringVar()
        self.grupo_var = tk.StringVar()
        self.nombre_var = tk.StringVar()
        self.edad_var = tk.StringVar()
        self.matricula_var = tk.StringVar()
        self.anio_var = tk.StringVar()
        
        # Configurar grid responsivo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame principal
        main_frame = tk.Frame(self, bg='#F5E6E8')
        main_frame.place(relx=0.5, rely=0.5, anchor='center')

        # Título
        self.titulo = tk.Label(main_frame,
                             text="Registro de Alumno",
                             font=("Arial", 24, "bold"),
                             bg='#F5E6E8',
                             fg='#6B4E71')
        self.titulo.pack(pady=20)

        # Frame de registro
        registro_frame = tk.Frame(main_frame, bg='white', padx=20, pady=20)
        registro_frame.pack(padx=20, pady=10)

       # Campos de registro
        tk.Label(registro_frame, text="Matrícula:", bg='white', font=("Arial", 12)).pack()
        tk.Entry(registro_frame, textvariable=self.matricula_var, font=("Arial", 12)).pack(pady=5)

        tk.Label(registro_frame, text="Nombre Completo:", bg='white', font=("Arial", 12)).pack()
        tk.Entry(registro_frame, textvariable=self.nombre_var, font=("Arial", 12)).pack(pady=5)

        tk.Label(registro_frame, text="Edad:", bg='white', font=("Arial", 12)).pack()
        tk.Entry(registro_frame, textvariable=self.edad_var, font=("Arial", 12)).pack(pady=5)

        
        # Combobox para año escolar
        tk.Label(registro_frame, text="Nivel Educativo:", bg='white', font=("Arial", 12)).pack()
        self.combo_nivel = ttk.Combobox(registro_frame, 
                                      textvariable=self.nivel_var,
                                      values=["Preescolar", "Primaria", "Secundaria"],
                                      state='readonly')
        self.combo_nivel.pack(pady=5)
        self.combo_nivel.bind('<<ComboboxSelected>>', self.actualizar_grados)

        # Combobox para grado
        tk.Label(registro_frame, text="Grado:", bg='white', font=("Arial", 12)).pack()
        self.combo_grado = ttk.Combobox(registro_frame, 
                               textvariable=self.grado_var,  # Cambiamos anio_var por grado_var
                               state='readonly')
        self.combo_grado.pack(pady=5)
        
        # Combobox para grupo
        tk.Label(registro_frame, text="Grupo:", bg='white', font=("Arial", 12)).pack()
        self.combo_grupo = ttk.Combobox(registro_frame, 
                                      textvariable=self.grupo_var,
                                      values=['A', 'B', 'C', 'D', 'E'],
                                      state='readonly')
        self.combo_grupo.pack(pady=5)

        # Frame para foto
        self.foto_label = tk.Label(registro_frame, bg='white', text="Sin foto seleccionada")
        self.foto_label.pack(pady=10)

        # Botones
        btn_foto = tk.Button(registro_frame,
                           text="Subir Foto",
                           command=self.subir_foto,
                           bg='#B5C7D4',
                           font=("Arial", 12))
        btn_foto.pack(pady=10)

        btn_guardar = tk.Button(registro_frame,
                              text="Guardar",
                              command=self.guardar_registro,
                              bg='#D4E6B5',
                              font=("Arial", 12))
        btn_guardar.pack(pady=10)

        btn_regresar = tk.Button(registro_frame,
                               text="Regresar",
                               command=lambda: controller.mostrar_frame(PaginaNiveles),
                               bg='#FFB5B5',
                               font=("Arial", 12))
        btn_regresar.pack(pady=10)

    def actualizar_grados(self, event=None):
        """Actualiza las opciones del combobox de grados según el nivel seleccionado"""
        grados = {
            "Preescolar": ["1er año", "2do año", "3er año"],
            "Primaria": ["1er año", "2do año", "3er año", "4to año", "5to año", "6to año"],
            "Secundaria": ["1er año", "2do año", "3er año"]
        }
        nivel_seleccionado = self.nivel_var.get()
        self.combo_grado['values'] = grados.get(nivel_seleccionado, [])
        if self.combo_grado['values']:
            self.combo_grado.current(0)
            self.grupo_var.set('A')  # Establecer grupo por defecto
            
    def verificar_cupo(self):
        cursor = self.controller.conexion.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM alumnos 
            WHERE nivel = ? AND grado = ? AND grupo = ?
        ''', (self.nivel_seleccionado, self.anio_var.get(), self.grupo_var.get()))
        
        cantidad_alumnos = cursor.fetchone()[0]
        return cantidad_alumnos < 45

    def subir_foto(self):
        self.foto_path = filedialog.askopenfilename(
            filetypes=[
                ("Archivos de imagen", 
                "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp")
            ]
        )
        
        if self.foto_path:
            # Verificar tamaño
            if os.path.getsize(self.foto_path) > 20 * 1024 * 1024:  # 20MB
                messagebox.showerror(
                    "Error", 
                    "La imagen excede el tamaño máximo permitido de 20MB"
                )
                self.foto_path = None
                return
                
            # Mostrar preview
            image = Image.open(self.foto_path)
            image.thumbnail((150, 150))  # Resize para preview
            photo = ImageTk.PhotoImage(image)
            self.foto_label.configure(image=photo, text="")
            self.foto_label.image = photo

    def guardar_registro(self):
        try:
            # Verificar campos
            if not all([self.matricula_var.get().strip(), 
                       self.nombre_var.get().strip(),
                       self.edad_var.get().strip(), 
                       self.nivel_var.get(),
                       self.grado_var.get(), 
                       self.grupo_var.get(), 
                       self.foto_path]):
                raise ValueError("Todos los campos son obligatorios")

            # Verificar matrícula única
            cursor = self.controller.conexion.cursor()
            cursor.execute('SELECT id FROM alumnos WHERE matricula = ?', 
                         (self.matricula_var.get(),))
            if cursor.fetchone():
                raise ValueError("La matrícula ya existe en el sistema")

            # Procesar imagen
            with open(self.foto_path, 'rb') as file:
                foto_binaria = file.read()

            # Generar código de barras único
            codigo_barras = f"{self.nivel_var.get()}_{self.grado_var.get()}_{self.matricula_var.get()}"

            # Guardar en base de datos
            self.controller.guardar_alumno((
                self.matricula_var.get(),
                self.nombre_var.get(),
                int(self.edad_var.get()),
                self.nivel_var.get(),
                self.grado_var.get(),
                self.grupo_var.get(),
                codigo_barras,
                foto_binaria,
                datetime.now()
            ))

            # Mostrar código QR
            self.mostrar_codigo_qr(codigo_barras)
            
            messagebox.showinfo("Éxito", "Alumno registrado correctamente")
            self.limpiar_campos()
            
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
            
    def mostrar_codigo_qr(self, codigo):
        # Crear una nueva ventana para mostrar el código QR
        qr_window = tk.Toplevel(self)
        qr_window.title("Código QR del Alumno")
        qr_window.geometry("400x500")
        qr_window.configure(bg='white')

        # Generar QR
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(codigo)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir para Tkinter
        qr_image = ImageTk.PhotoImage(qr_image)
        
        # Mostrar QR
        label_qr = tk.Label(qr_window, image=qr_image, bg='white')
        label_qr.image = qr_image
        label_qr.pack(pady=20)
        
        # Mostrar código
        tk.Label(qr_window, 
                text=f"Código: {codigo}",
                font=("Arial", 12),
                bg='white').pack(pady=10)
        
        # Botón para cerrar
        tk.Button(qr_window,
                 text="Cerrar",
                 command=qr_window.destroy,
                 bg='#FFB5B5',
                 font=("Arial", 12)).pack(pady=20)

    def limpiar_campos(self):
        self.nombre_var.set("")
        self.edad_var.set("")
        self.grado_var.set("")
        self.foto_path =self.foto_path = None
        self.foto_label.configure(image="", text="Sin foto seleccionada")
        self.foto_label.image = None

class PaginaLectorQR(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg='#F5E6E8')
        self.controller = controller
        
        # Configurar grid responsivo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Frame izquierdo para cámara y botón de regresar
        left_frame = tk.Frame(self, bg='#F5E6E8')
        left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Frame para video
        video_frame = tk.Frame(left_frame, bg='white', relief=tk.GROOVE, bd=2)
        video_frame.pack(fill='both', expand=True)
        
        # Label para video
        self.video_label = tk.Label(video_frame, bg='black')
        self.video_label.pack(padx=10, pady=10)

        # Botón de regresar debajo de la cámara
        btn_regresar = tk.Button(left_frame,
                               text="← Regresar al Menú Principal",
                               command=lambda: self.cerrar_camara(controller),
                               bg='#FFB5B5',
                               font=("Arial", 12),
                               padx=20,
                               pady=10)
        btn_regresar.pack(pady=20)

        # Frame derecho para el tablero 3x3
        right_frame = tk.Frame(self, bg='#F5E6E8')
        right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        # Título del tablero
        tk.Label(right_frame,
                text="Control de Entrada/Salida",
                font=("Arial", 20, "bold"),
                bg='#F5E6E8',
                fg='#6B4E71').pack(pady=(0,20))

        # Frame para el tablero 3x3
        tablero_frame = tk.Frame(right_frame, bg='white', relief=tk.GROOVE, bd=2)
        tablero_frame.pack(fill='both', expand=True, padx=10)

        # Crear tablero 3x3
        self.casillas = []
        for i in range(3):
            fila = []
            frame_fila = tk.Frame(tablero_frame, bg='white')
            frame_fila.pack(fill='x', expand=True, pady=5)
            
            for j in range(3):
                # Frame para cada casilla
                casilla_frame = tk.Frame(frame_fila,
                                       bg='#E3D7F4',
                                       width=200,
                                       height=150,
                                       relief=tk.RAISED,
                                       bd=2)
                casilla_frame.pack(side=tk.LEFT, padx=5, expand=True)
                casilla_frame.pack_propagate(False)
                
                # Label para info del alumno
                info_label = tk.Label(casilla_frame,
                                    text="Espacio Disponible",
                                    bg='#E3D7F4',
                                    font=("Arial", 10),
                                    wraplength=180)
                info_label.pack(expand=True)
                
                # Botón de retiro
                btn_retiro = tk.Button(casilla_frame,
                                     text="Retirar Alumno",
                                     command=lambda x=i, y=j: self.retirar_alumno(x, y),
                                     state='disabled',
                                     bg='#FFB5B5')
                btn_retiro.pack(pady=5)
                
                fila.append({
                    'frame': casilla_frame,
                    'label': info_label,
                    'boton': btn_retiro,
                    'ocupado': False,
                    'alumno_id': None
                })
            self.casillas.append(fila)

        # Iniciar captura de video
        self.captura = cv2.VideoCapture(0)
        self.actualizar_video()

    def actualizar_video(self):
        if hasattr(self, 'captura') and self.captura.isOpened():
            ret, frame = self.captura.read()
            if ret:
                # Redimensionar el frame para que tenga un tamaño razonable
                frame = cv2.resize(frame, (480, 360))  # Ajusta estos valores según necesites
                
                # Buscar códigos QR/Barras
                codigos = decode(frame)
                for codigo in codigos:
                    datos = codigo.data.decode('utf-8')
                    self.procesar_codigo(datos)

                # Convertir frame para Tkinter
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            
            self.video_label.after(10, self.actualizar_video)
            
    def cerrar_camara(self, controller):
        if hasattr(self, 'captura'):
            self.captura.release()
            cv2.destroyAllWindows()  # Cerrar todas las ventanas de OpenCV
        self.video_label.config(image='')  # Limpiar el label de video
        controller.mostrar_frame(PaginaNiveles)  # Regresar al menú principal

class PaginaConsulta(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg='#F5E6E8')
        self.controller = controller
        
        # Variables
        self.nivel_var = tk.StringVar()
        self.anio_var = tk.StringVar()
        self.grupo_var = tk.StringVar()

        # Configurar grid responsivo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame principal
        main_frame = tk.Frame(self, bg='#F5E6E8')
        main_frame.place(relx=0.5, rely=0.5, anchor='center')
        
        # Título
        tk.Label(main_frame,
                text="Consulta de Registros",
                font=("Arial", 24, "bold"),
                bg='#F5E6E8',
                fg='#6B4E71').pack(pady=20)

        # Añadir el botón de regresar
        btn_regresar = tk.Button(main_frame,
                                text="← Regresar",
                                command=lambda: controller.mostrar_frame(PaginaNiveles),
                                bg='#FFB5B5',
                                font=("Arial", 12),
                                padx=10,
                                pady=5)
        btn_regresar.pack(pady=10)
        
        # Frame de filtros
        filtros_frame = tk.Frame(main_frame, bg='white')
        filtros_frame.pack(fill='x', padx=20, pady=10)
        
         # Combobox para nivel
        tk.Label(filtros_frame, text="Nivel:", bg='white').pack(side=tk.LEFT, padx=5)
        self.combo_nivel = ttk.Combobox(filtros_frame, 
                                      textvariable=self.nivel_var,
                                      values=["Preescolar", "Primaria", "Secundaria"],
                                      state='readonly')
        self.combo_nivel.pack(side=tk.LEFT, padx=5)
        self.combo_nivel.bind('<<ComboboxSelected>>', self.actualizar_años)

        # Combobox para año escolar
        tk.Label(filtros_frame, text="Año:", bg='white').pack(side=tk.LEFT, padx=5)
        self.combo_año = ttk.Combobox(filtros_frame, 
                                    textvariable=self.anio_var,
                                    state='readonly')
        self.combo_año.pack(side=tk.LEFT, padx=5)

        # Combobox para grupo
        tk.Label(filtros_frame, text="Grupo:", bg='white').pack(side=tk.LEFT, padx=5)
        self.combo_grupo = ttk.Combobox(filtros_frame, 
                                      textvariable=self.grupo_var,
                                      values=['A', 'B', 'C', 'D', 'E'],
                                      state='readonly')
        self.combo_grupo.pack(side=tk.LEFT, padx=5)

        # Frame de búsqueda
        busqueda_frame = tk.Frame(main_frame, bg='white')
        busqueda_frame.pack(fill='x', padx=20, pady=10)

        
        # Configurar TreeView
        self.tree = ttk.Treeview(main_frame, 
                                columns=("Matrícula", "Nombre", "Edad", "Grupo","Fecha registro"))
        self.tree.heading("Matrícula", text="Matrícula")
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Edad", text="Edad")
        self.tree.heading("Grupo", text="Grupo")
        self.tree.heading("Fecha registro", text="Fecha registro")
        self.tree.pack(pady=20, padx=20, fill='both', expand=True)
        
         # Añadir botón de búsqueda
        self.btn_buscar = tk.Button(filtros_frame,
                                  text="Buscar",
                                  command=self.buscar_registros,
                                  bg='#D4E6B5',
                                  font=("Arial", 12))
        self.btn_buscar.pack(side=tk.LEFT, padx=20)

    def buscar_registros(self):
        # Limpiar tabla actual
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Validar que se haya seleccionado al menos el nivel
        if not self.nivel_var.get():
            messagebox.showwarning("Advertencia", "Por favor seleccione al menos el nivel educativo")
            return

        # Construir consulta SQL
        consulta = '''
            SELECT matricula, nombre, edad, nivel, grado, grupo, fecha_registro
            FROM alumnos
            WHERE nivel = ?
        '''
        parametros = [self.nivel_var.get()]

        if self.anio_var.get():
            consulta += " AND grado = ?"
            parametros.append(self.anio_var.get())
        
        if self.grupo_var.get():
            consulta += " AND grupo = ?"
            parametros.append(self.grupo_var.get())

        consulta += " ORDER BY nombre"

        # Ejecutar consulta
        cursor = self.controller.conexion.cursor()
        cursor.execute(consulta, parametros)
        resultados = cursor.fetchall()
        
        # Mostrar resultados
        if resultados:
            for resultado in resultados:
                self.tree.insert("", "end", values=resultado)
        else:
            messagebox.showinfo("Información", "No se encontraron registros")
        
    def actualizar_años(self, event=None):
        grados = {
            "Preescolar": ["1er año", "2do año", "3er año"],
            "Primaria": ["1er año", "2do año", "3er año", "4to año", "5to año", "6to año"],
            "Secundaria": ["1er año", "2do año", "3er año"]
        }
        self.combo_año['values'] = grados.get(self.nivel_var.get(), [])
        if self.combo_año['values']:
            self.combo_año.current(0)

        

    def buscar_registros(self):
        # Limpiar tabla actual
        for item in self.tree.get_children():
            self.tree.delete(item)

       # Construir consulta SQL
        consulta = '''
            SELECT matricula, nombre, edad, grupo
            FROM alumnos
            WHERE nivel = ? AND grado = ? AND grupo = ?
        '''
        
        cursor = self.controller.conexion.cursor()
        cursor.execute(consulta, (
            self.nivel_var.get(),
            self.anio_var.get(),
            self.grupo_var.get()
        ))
        
        resultados = cursor.fetchall()
        for resultado in resultados:
            self.tree.insert("", "end", values=resultado)
            
        parametros = []

        if self.busqueda_nombre.get():
            consulta += " AND a.nombre LIKE ?"
            parametros.append(f"%{self.busqueda_nombre.get()}%")

        if self.combo_nivel.get() != "Todos":
            consulta += " AND a.nivel = ?"
            parametros.append(self.combo_nivel.get())

        # Ejecutar consulta
        cursor = self.controller.conexion.cursor()
        cursor.execute(consulta, parametros)
        resultados = cursor.fetchall()

        # Mostrar resultados
        for resultado in resultados:
            ultima_entrada = resultado[4] if resultado[4] else "Sin registro"
            self.tree.insert("", "end", values=resultado[:4] + (ultima_entrada,))

if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaRegistroEscolar(root)
    root.mainloop()