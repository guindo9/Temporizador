import tkinter as tk
from tkinter.font import Font
from time import sleep
from threading import Thread, Event
import os
import pygame
from tkinter import messagebox
import sys
import configparser

# --- Constants ---
RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
MAIN_DIR = os.path.dirname(os.path.abspath(sys.executable))
ICON_DIR = os.path.join(RUTA_SCRIPT, "icono")
ICON = os.path.join(ICON_DIR, "icon_89.ico")
ALARMA = os.path.join(ICON_DIR, "beep_beep.wav")
CONFIG_FILE = os.path.join(MAIN_DIR, "config.ini")
INSTRUCTIONS_FILE = os.path.join(MAIN_DIR, "instrucciones.txt")

# Timer Thresholds
WARNING_THRESHOLD_SECONDS_RED = 29
WARNING_THRESHOLD_SECONDS_ORANGE = 59

# Minimum Window Sizes
MIN_WIDTH = 260
MIN_HEIGHT = 95

class Timer(tk.Frame):
    """
    A customizable desktop timer application with advanced window controls and
    color customization via an INI file.
    """
    def __init__(self, parent):
        self.root = parent

        # --- Load Configuration ---
        self.config_settings = self._load_config()
        self.colors = self.config_settings['colors']
        self.alarm_repeat_count = self.config_settings['alarm_repeat_count']
        
        tk.Frame.__init__(self, parent, bg=self.colors['bg_dark'])
        
        self.active = False
        self.kill = False
        self.playing = False
        self.show_title = True
        self.siempre_en_primer_plano = True

        # --- Timer Variables ---
        self.start_hours = tk.StringVar(value="0")
        self.start_minutes = tk.StringVar(value="0")
        self.start_seconds = tk.StringVar(value="0")
        
        self.start_hours.trace("w", lambda name, index, mode, var=self.start_hours: self._validate_time_input(var, 99))
        self.start_minutes.trace("w", lambda name, index, mode, var=self.start_minutes: self._validate_time_input(var, 59))
        self.start_seconds.trace("w", lambda name, index, mode, var=self.start_seconds: self._validate_time_input(var, 59))

        self.hours_left = 0
        self.minutes_left = 0
        self.seconds_left = 0
        self.time_remaining = "00:00:00"
        self.clock = None

        # --- UI Elements Creation ---
        self._create_widgets()
        self._pack_initial_widgets()

        # --- Threading and Event Handling ---
        self.update_event = Event()
        self.thread = Thread(target=self._update_timer_loop, daemon=True)
        self.thread.start()

        # --- Window Event Bindings ---
        self.resize_delay = None
        self.last_height = 1
        self.last_width = 1 # Initialize last_width
        self.root.bind("<Configure>", self._on_window_resize)
        self.root.bind("<Control-Up>", self._adjust_transparency)
        self.root.bind("<Control-Down>", self._adjust_transparency)
        self.root.bind("<Control-t>", self._toggle_title_bar)
        self.root.bind("<Control-T>", self._toggle_title_bar)
        self.root.bind("<Control-f>", self._toggle_always_on_top)
        self.root.bind("<Control-F>", self._toggle_always_on_top)
        
        self.root.bind("<Button-1>", self._start_move)
        self.root.bind("<B1-Motion>", self._do_move)
        
        self.root.bind("<ButtonPress-3>", self._start_resize)
        self.root.bind("<B3-Motion>", self._do_resize)
        self.root.bind("<ButtonRelease-3>", self._stop_resize)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Initialize pygame mixer once
        try:
            pygame.mixer.init()
        except pygame.error as e:
            messagebox.showerror("Error de Audio", f"No se pudo inicializar Pygame Mixer: {e}\nLa alarma podría no funcionar.")
            self.alarm_enabled = False
        else:
            self.alarm_enabled = True
            if not os.path.exists(ALARMA):
                messagebox.showwarning("Advertencia", f"No se encontró el archivo de alarma: {ALARMA}\nLa alarma podría no funcionar.")
                self.alarm_enabled = False

        self.root.update_idletasks()
        self._update_text_size()
        self._create_instructions_file()

    def _load_config(self):
        """Loads configuration from config.ini or creates a default."""
        config = configparser.ConfigParser()
        
        # Default color settings
        default_colors = {
            'bg_dark': "#2e2e2e",
            'bg_lighter': "#363636",
            'button_color': "#006f9c",
            'button_active_color': "#185973",
            'spinbox_text_color': "#006f9c",
            'clock_color_normal': "white",
            'clock_color_orange': "orange",
            'clock_color_red': "red"
        }
        
        # Default general settings
        default_settings = {
            'alarm_repeat_count': str(30) # Stored as string, convert to int later
        }

        # Combine for initial config object if file doesn't exist
        full_config = configparser.ConfigParser()
        full_config['Colors'] = default_colors
        full_config['Settings'] = default_settings

        if os.path.exists(CONFIG_FILE):
            try:
                config.read(CONFIG_FILE)
                # Overwrite defaults with values from file
                if 'Colors' in config:
                    for key in default_colors:
                        default_colors[key] = config['Colors'].get(key, default_colors[key])
                if 'Settings' in config:
                    for key in default_settings:
                        default_settings[key] = config['Settings'].get(key, default_settings[key])
            except Exception as e:
                messagebox.showwarning("Error de Configuración", f"Error al leer config.ini: {e}. Usando valores por defecto.")
        else:
            # Create default config file if it doesn't exist
            try:
                with open(CONFIG_FILE, 'w') as f:
                    full_config.write(f)
            except Exception as e:
                messagebox.showwarning("Error de Archivo", f"No se pudo crear config.ini: {e}. Continuará sin archivo de configuración.")
        
        # Return parsed settings
        return {
            'colors': default_colors,
            'alarm_repeat_count': int(default_settings['alarm_repeat_count'])
        }

    def _create_instructions_file(self):
        """Creates the instructions.txt file if it doesn't exist."""
        if not os.path.exists(INSTRUCTIONS_FILE):
            try:
                with open(INSTRUCTIONS_FILE, 'w', encoding='utf-8') as f:
                    f.write("""
###################################################
#            INSTRUCCIONES DE USO                 #
#          Temporizador Personalizable            #
###################################################

¡Bienvenido al Temporizador Personalizable!

Este programa es un temporizador de cuenta regresiva que puedes ajustar a tus necesidades.

---

1.  FUNCIONAMIENTO BÁSICO

    * AJUSTAR TIEMPO:
        * Al iniciar, verás tres campos (Horas, Minutos, Segundos). Usa las flechas arriba/abajo o escribe directamente los números para establecer el tiempo deseado.
        * El sistema validará automáticamente que los valores sean números y estén dentro de rangos lógicos (0-99 para horas, 0-59 para minutos/segundos).

    * INICIAR:
        * Haz clic en el botón "Iniciar" para comenzar la cuenta regresiva.
        * La ventana cambiará a un modo compacto sin barra de título, mostrando solo el tiempo.

    * PAUSAR / REANUDAR:
        * Una vez iniciado, haz doble clic en el reloj (donde se muestra el tiempo) para revelar los botones "Pausar" y "Cancelar".
        * Haz clic en "Pausar" para detener temporalmente la cuenta. El botón cambiará a "Reanudar".
        * Haz clic en "Reanudar" para continuar la cuenta.
        * Haz doble clic en el reloj nuevamente para ocultar los botones si no los necesitas a la vista.

    * CANCELAR:
        * Haz clic en "Cancelar" para detener el temporizador y regresar a la pantalla de configuración inicial. Se te pedirá confirmación.

    * FIN DEL TEMPORIZADOR (ALARMA):
        * Cuando el tiempo llega a cero, el reloj se pondrá en rojo y sonará una alarma.
        * Aparecerá un botón "Detener". Haz clic en él para silenciar la alarma y reiniciar la interfaz.

---

2.  CONFIGURACIÓN DE COLORES (config.ini)

    Puedes personalizar los colores de la interfaz editando el archivo `config.ini`.

    * ¿DÓNDE ENCONTRARLO?
        * El archivo `config.ini` se crea automáticamente en el mismo directorio donde se encuentra el ejecutable del programa.

    * ¿CÓMO EDITARLO?
        * Abre `config.ini` con cualquier editor de texto (Bloc de notas, Notepad++, VS Code, etc.).
        * Verás una sección `[Colors]` con una lista de nombres de colores y sus valores (códigos hexadecimales como `#RRGGBB` o nombres de colores en inglés como "red", "blue", "white").
        * Ejemplo: `bg_dark = #2e2e2e`

    * SECCIÓN [Colors]:
        * Aquí encontrarás una lista de nombres de colores y sus valores (códigos hexadecimales como `#RRGGBB` o nombres de colores en inglés como "red", "blue", "white").
        * Ejemplo: `bg_dark = #2e2e2e`
        * `bg_dark`: Fondo principal de la ventana y los campos de número.
        * `bg_lighter`: Fondo de los recuadros de "Horas", "Minutos", "Segundos".
        * `button_color`: Color de fondo de los botones "Iniciar", "Cancelar", "Pausar", "Detener".
        * `button_active_color`: Color de fondo de los botones cuando pasas el ratón por encima (estado activo).
        * `spinbox_text_color`: Color de los números en los campos de Horas/Minutos/Segundos.
        * `clock_color_normal`: Color del texto del reloj cuando hay mucho tiempo restante.
        * `clock_color_orange`: Color del texto del reloj cuando el tiempo restante es menor a un umbral (por defecto, menos de 1 minuto).
        * `clock_color_red`: Color del texto del reloj cuando el tiempo restante es muy bajo (por defecto, menos de 30 segundos) y cuando la alarma está sonando.

    * SECCIÓN [Settings]:
        * `alarm_repeat_count`: Número de veces que la alarma sonará cuando el temporizador llegue a cero. Por defecto es `30`. Puedes cambiar este número a tu gusto.

    * IMPORTANTE:
        * Después de realizar cambios en `config.ini`, **debes cerrar y volver a abrir el programa** para que los nuevos valores surtan efecto.
        * Asegúrate de que los valores de color sean válidos (códigos hexadecimales de 6 dígitos o nombres de colores web).
        * Asegúrate de que los valores de la sección `[Settings]` sean números enteros válidos. Un valor inválido puede causar errores.

---

3.  TECLAS RÁPIDAS (ACCESOS DIRECTOS)

    Puedes controlar la ventana y el temporizador con las siguientes combinaciones de teclas:

    * CONTROL + FLECHA ARRIBA: Aumenta la transparencia de la ventana (se vuelve más opaca).
    * CONTROL + FLECHA ABAJO: Disminuye la transparencia de la ventana (se vuelve más transparente).
    * CONTROL + T: (Alternar) Muestra u oculta la barra de título de la ventana.
    * CONTROL + F: (Alternar) Activa o desactiva la función "Siempre en primer plano" (la ventana se mantendrá siempre visible sobre otras).

    * ARRASTRAR VENTANA:
        * Haz clic y arrastra con el **botón izquierdo del ratón** en cualquier parte de la ventana para moverla.

    * REDIMENSIONAR VENTANA:
        * Haz clic y arrastra con el **botón derecho del ratón** en una de las esquinas de la ventana para cambiar su tamaño.

---

¡Disfruta de tu temporizador!
""")
            except Exception as e:
                messagebox.showwarning("Error de Archivo", f"No se pudo crear instrucciones.txt: {e}")

    def _create_widgets(self):
        """Creates all the Tkinter widgets for the application."""
        self.spinbox_frame = tk.Frame(self, bg=self.colors['bg_dark'])
        
        self.hours_frame = tk.LabelFrame(self.spinbox_frame, text="Horas:", fg="white", bg=self.colors['bg_lighter'])
        self.hours_select = tk.Spinbox(self.hours_frame, from_=0, to=99, width=2, textvariable=self.start_hours, 
                                       font=Font(family='Helvetica', size=34, weight='bold'),
                                       bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'], justify='center', wrap=True)
        
        self.minutes_frame = tk.LabelFrame(self.spinbox_frame, text="Minutos:", fg="white", bg=self.colors['bg_lighter'])
        self.minutes_select = tk.Spinbox(self.minutes_frame, from_=0, to=59, textvariable=self.start_minutes,
                                         font=Font(family='Helvetica', size=34, weight='bold'),
                                         width=2, bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'], justify='center', wrap=True)
        
        self.seconds_frame = tk.LabelFrame(self.spinbox_frame, text="Segundos:", fg="white", bg=self.colors['bg_lighter'])
        self.seconds_select = tk.Spinbox(self.seconds_frame, from_=0, to=59, textvariable=self.start_seconds,
                                         font=Font(family='Helvetica', size=34, weight='bold'),
                                         width=2, bg=self.colors['bg_dark'], fg=self.colors['spinbox_text_color'], justify='center', wrap=True)

        self.button_frame = tk.Frame(self, bg=self.colors['bg_dark'])
        self.active_button = tk.Button(self.button_frame, text="Iniciar", command=self.start, 
                                       bg=self.colors['button_color'], fg="white", relief="raised", anchor="center", 
                                       activebackground=self.colors['button_active_color'])
        self.stop_button = tk.Button(self.button_frame, text="Cancelar", command=self.stop, 
                                     bg=self.colors['button_color'], fg="white", relief="raised", anchor="center", 
                                     activebackground=self.colors['button_active_color'])
        self.pause_button = tk.Button(self.button_frame, text="  Pausar   ", command=self.pause, 
                                      bg=self.colors['button_color'], fg="white", relief="raised", anchor="center", 
                                      activebackground=self.colors['button_active_color'])
        
        self.clock = tk.Label(self, text=self.time_remaining, font=Font(family='Helvetica', size=36, weight='bold'), bg=self.colors['bg_dark'], fg=self.colors['clock_color_normal'])
        self.clock.bind("<Double-Button-1>", self._toggle_buttons_visibility)

    def _pack_initial_widgets(self):
        """Packs the initial widgets for the timer setup phase."""
        self.spinbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=5)
        self.hours_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=2, pady=2)
        self.minutes_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=2, pady=2)
        self.seconds_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=2, pady=2)
        self.hours_select.pack(fill=tk.BOTH, expand=4)
        self.minutes_select.pack(fill=tk.BOTH, expand=4)
        self.seconds_select.pack(fill=tk.BOTH, expand=4)

        self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        self.active_button.pack(fill=tk.BOTH, expand=1)

    def _validate_time_input(self, var, max_val):
        """
        Validates spinbox input to ensure it's numeric and within bounds.
        """
        current_val = var.get()
        cleaned_val = "".join(filter(str.isdigit, current_val))
        
        if not cleaned_val:
            var.set("0")
            return

        try:
            num_val = int(cleaned_val)
            if num_val > max_val:
                var.set(str(max_val))
            elif num_val < 0:
                var.set("0")
            else:
                var.set(str(num_val))
        except ValueError:
            var.set("0")

    def _update_timer_loop(self):
        """
        Runs in a separate thread to update the timer countdown.
        """
        while not self.kill:
            self.update_event.wait()
            
            if self.active and self.clock is not None:
                if self.hours_left + self.minutes_left + self.seconds_left > 0:
                    self._update_clock_display()
                    sleep(1)
                    if self.seconds_left > 0:
                        self.seconds_left -= 1
                    elif self.minutes_left > 0:
                        self.seconds_left = 59
                        self.minutes_left -= 1
                    elif self.hours_left > 0:
                        self.minutes_left = 59
                        self.hours_left -= 1
                else:
                    self._timer_end()
            else:
                sleep(0.1)

    def _update_clock_display(self):
        """
        Updates the clock display and changes its color based on remaining time.
        """
        if self.clock:
            hours = f"{self.hours_left:02}"
            minutes = f"{self.minutes_left:02}"
            seconds = f"{self.seconds_left:02}"
            self.time_remaining = f"{hours}:{minutes}:{seconds}"
            self.clock.config(text=self.time_remaining)

            total_seconds = self.hours_left * 3600 + self.minutes_left * 60 + self.seconds_left
            if total_seconds <= WARNING_THRESHOLD_SECONDS_RED:
                self.clock.config(fg=self.colors['clock_color_red'])
            elif total_seconds <= WARNING_THRESHOLD_SECONDS_ORANGE:
                self.clock.config(fg=self.colors['clock_color_orange'])
            else:
                self.clock.config(fg=self.colors['clock_color_normal'])

    def _timer_end(self):
        """
        Handles the actions when the timer reaches zero (plays alarm, changes UI).
        """
        self.active = False
        self.time_remaining = "00:00:00"
        self.clock.config(text=self.time_remaining, fg=self.colors['clock_color_red'])
        
        self.playing = True
        
        self.clock.unbind("<Double-Button-1>")

        self.pause_button.pack_forget()
        self.stop_button.pack_forget()
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        self.active_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.active_button.config(text="Detener", command=self._stop_alarm)

        if self.alarm_enabled:
            pygame.mixer.music.load(ALARMA)
            for _ in range(self.alarm_repeat_count):
                if not self.playing:
                    break
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and self.playing:
                    sleep(0.1)

        self._reset_interface()

    def _stop_alarm(self):
        """
        Stops the alarm sound and resets the interface.
        """
        self.playing = False
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self._reset_interface()

    def _reset_interface(self):
        """Resets the UI to its initial state for setting a new timer."""
        if self.clock.winfo_ismapped():
            self.clock.pack_forget()
        
        self.spinbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=5)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        self.active_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.pause_button.pack_forget()
        self.stop_button.pack_forget()
        
        self.active_button.config(text="Iniciar", command=self.start, 
                                  bg=self.colors['button_color'], fg="white", relief="raised", anchor="center")
        
        self.start_hours.set("0")
        self.start_minutes.set("0")
        self.start_seconds.set("0")
        self.clock.config(fg=self.colors['clock_color_normal'])

        self.clock.bind("<Double-Button-1>", self._toggle_buttons_visibility)
        
        self.root.overrideredirect(False)
        self.root.attributes("-alpha", 1.0)
        self.show_title = True
        self.siempre_en_primer_plano = True
        self.root.wm_attributes("-topmost", 1)

        self.root.update_idletasks()
        self._update_text_size()

    def _toggle_buttons_visibility(self, event=None):
        """
        Toggles the visibility of pause/stop buttons and adjusts clock display.
        """
        if self.active and not self.playing:
            if self.pause_button.winfo_ismapped():
                self.pause_button.pack_forget()
                self.stop_button.pack_forget()
                self.button_frame.pack_forget()
                self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
            else:
                self.button_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
                self.stop_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
                self.pause_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
                self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=3)

    def start(self):
        """
        Initiates the timer countdown. Validates input and changes UI state.
        """
        try:
            hours = int(self.start_hours.get())
            minutes = int(self.start_minutes.get())
            seconds = int(self.start_seconds.get())
        except ValueError:
            messagebox.showerror("Error de Entrada", "Por favor, ingrese solo números válidos en los campos de tiempo.")
            return

        if hours == 0 and minutes == 0 and seconds == 0:
            return

        self.hours_left = hours
        self.minutes_left = minutes
        self.seconds_left = seconds
        
        self.spinbox_frame.pack_forget()
        self.active_button.pack_forget()
        self.button_frame.pack_forget()
        
        self.clock.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.pause_button.config(text="  Pausar   ", command=self.pause)

        self.root.overrideredirect(True)
        self._update_text_size()

        self.active = True
        self.update_event.set()

    def pause(self):
        """Pauses the timer countdown."""
        if self.active:
            self.active = False
            self.update_event.clear()
            self.pause_button.config(text="Reanudar", command=self.resume)

    def resume(self):
        """Resumes the timer countdown."""
        if not self.active:
            self.active = True
            self.update_event.set()
            self.pause_button.config(text="  Pausar   ", command=self.pause)
            self._toggle_buttons_visibility()

    def stop(self):
        """Stops the timer and asks for confirmation."""
        response = messagebox.askyesno("Confirmación", "¿Estás seguro de que deseas cancelar el temporizador?")
        if response:
            self.active = False
            self.playing = False
            self.update_event.clear()
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self._reset_interface()

    def _on_closing(self):
        """Handles the graceful shutdown of the application."""
        self.kill = True
        self.update_event.set()
        
        if self.thread.is_alive():
            self.thread.join(timeout=1)
        
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        self.root.destroy()

    # --- Window Control Functions ---

    def _toggle_always_on_top(self, event=None):
        """Toggles the 'always on top' attribute of the window."""
        self.siempre_en_primer_plano = not self.siempre_en_primer_plano
        self.root.wm_attributes("-topmost", 1 if self.siempre_en_primer_plano else 0)
        
    def _toggle_title_bar(self, event=None):
        """Toggles the visibility of the window's title bar."""
        self.show_title = not self.show_title
        self.root.overrideredirect(not self.show_title)

    def _adjust_transparency(self, event):
        """Adjusts the window's transparency."""
        current_alpha = self.root.attributes("-alpha")
        step = 0.05
        if event.keysym == "Up":
            self.root.attributes("-alpha", min(current_alpha + step, 1.0))
        elif event.keysym == "Down":
            self.root.attributes("-alpha", max(current_alpha - step, 0.2))

    def _start_move(self, event):
        """Records initial mouse position for window dragging."""
        self.x_offset = event.x_root
        self.y_offset = event.y_root

    def _do_move(self, event):
        """Moves the window based on mouse drag."""
        x = self.root.winfo_x() + (event.x_root - self.x_offset)
        y = self.root.winfo_y() + (event.y_root - self.y_offset)
        self.root.geometry(f"+{x}+{y}")
        self.x_offset = event.x_root
        self.y_offset = event.y_root

    def _on_window_resize(self, event):
        """Debounces window resize events to update text size efficiently."""
        if self.resize_delay:
            self.root.after_cancel(self.resize_delay)
        self.resize_delay = self.root.after(50, self._update_text_size)

    def _update_text_size(self, event=None):
        """
        Updates the font sizes of various widgets based on the current window height.
        """
        current_height = self.root.winfo_height()
        current_width = self.root.winfo_width()

        if ((abs(current_height - self.last_height) < 5 and self.last_height != 1 and current_height != 0) and 
            (abs(current_width - self.last_width) < 5 and self.last_width != 1 and current_width != 0)):
            return
        
        font_size_buttons = max(10, min(53, int(current_height / 14)))
        font_size_spin = max(28, min(220, int(current_height / 7)))
        font_size_text = max(10, min(50, int(current_height / 23)))
        
        button_font = Font(family='Helvetica', size=font_size_buttons, weight='bold')
        text_font = Font(family='Helvetica', size=font_size_text)
        spin_font = Font(family='Helvetica', size=font_size_spin, weight='bold')

        self.active_button.config(font=button_font)
        self.stop_button.config(font=button_font)
        self.pause_button.config(font=button_font)

        self.hours_frame.config(font=text_font)
        self.minutes_frame.config(font=text_font)
        self.seconds_frame.config(font=text_font)

        self.hours_select.config(font=spin_font)
        self.minutes_select.config(font=spin_font)
        self.seconds_select.config(font=spin_font)
       
        if self.clock is not None:
            font_size_clock = max(47, int(current_height / 4))
            self.clock.config(font=Font(family='Helvetica', size=font_size_clock, weight='bold'))
        
        self.last_height = current_height
        self.last_width = current_width

    def _start_resize(self, event):
        """
        Records the initial position and determines the corner for resizing.
        """
        margin = 25
        self.start_x = event.x_root
        self.start_y = event.y_root

        self.win_x = self.root.winfo_x()
        self.win_y = self.root.winfo_y()
        self.win_width = self.root.winfo_width()
        self.win_height = self.root.winfo_height()

        self.resize_corner = None
        if event.x <= margin and event.y <= margin:
            self.resize_corner = "top_left"
        elif event.x >= self.win_width - margin and event.y <= margin:
            self.resize_corner = "top_right"
        elif event.x <= margin and event.y >= self.win_height - margin:
            self.resize_corner = "bottom_left"
        elif event.x >= self.win_width - margin and event.y >= self.win_height - margin:
            self.resize_corner = "bottom_right"

    def _do_resize(self, event):
        """
        Performs the window resizing based on the detected corner.
        """
        if not self.resize_corner:
            return

        dx = event.x_root - self.start_x
        dy = event.y_root - self.start_y

        new_width = self.win_width
        new_height = self.win_height
        new_x = self.win_x
        new_y = self.win_y

        if self.resize_corner == "bottom_right":
            new_width = max(self.win_width + dx, MIN_WIDTH)
            new_height = max(self.win_height + dy, MIN_HEIGHT)
        elif self.resize_corner == "top_left":
            new_width = max(self.win_width - dx, MIN_WIDTH)
            new_height = max(self.win_height - dy, MIN_HEIGHT)
            new_x = self.win_x + (self.win_width - new_width)
            new_y = self.win_y + (self.win_height - new_height)
        elif self.resize_corner == "top_right":
            new_width = max(self.win_width + dx, MIN_WIDTH)
            new_height = max(self.win_height - dy, MIN_HEIGHT)
            new_y = self.win_y + (self.win_height - new_height)
        elif self.resize_corner == "bottom_left":
            new_width = max(self.win_width - dx, MIN_WIDTH)
            new_height = max(self.win_height + dy, MIN_HEIGHT)
            new_x = self.win_x + (self.win_width - new_width)

        self.root.geometry(f"{new_width}x{new_height}+{int(new_x)}+{int(new_y)}")

    def _stop_resize(self, event):
        """Finalizes the resizing process."""
        self.resize_corner = None

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("285x112")
    root.minsize(MIN_WIDTH, MIN_HEIGHT)
    root.attributes("-topmost", True)
    
    # Temporarily create an instance to load colors for the root window
    temp_timer_instance = Timer(root)
    root.configure(bg=temp_timer_instance.colors['bg_dark'])
    
    root.title("Temporizador")
    
    if os.path.exists(ICON):
        root.iconbitmap(ICON)
    else:
        messagebox.showwarning("Advertencia", f"No se encontró el archivo de icono: {ICON}")
    
    # Re-instantiate the Timer with the now correctly configured root
    timer = Timer(root)
    timer.pack(fill=tk.BOTH, expand=1)
    
    root.mainloop()