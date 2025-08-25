import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import logging
import queue
import os
from geoTIFF_converter import convert_and_upload, GuiLogHandler

status_label_idle_text = "In attesa..."

# Classe per l'interfaccia grafica del convertitore SWE
class SWEConverterGUI(tk.Tk):
    '''Classe per l'interfaccia grafica del convertitore SWE.'''
    # Metodo di inizializzazione della classe SWEConverterGUI
    def __init__(self):
        '''Inizializza della classe SWEConverterGUI.'''
        # Inizializza la finestra principale
        super().__init__()
        self.title("SWE Converter")
        self.geometry("700x500")
        # Inizializza variabili e coda per la gestione dei thread
        self.selected_files = []
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        # Configura il gestore di log per l'interfaccia grafica
        gui_handler = GuiLogHandler(self.queue)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)  # o DEBUG se vuoi più dettagli
        # Crea i widget dell'interfaccia grafica
        self._create_widgets()

    # Metodo per creare le tab
    def _create_widgets(self):
        '''Crea le tab che conterranno i widget dell'interfaccia grafica.'''
        # Crea un notebook per le tab
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        # TAB 1 - Parametri
        param_frame = ttk.Frame(notebook)
        notebook.add(param_frame, text="Parametri")
        self._populate_param_tab(param_frame)
        # TAB 2 - Log
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log")
        self._populate_log_tab(log_frame)
        # Crea i widget a fondo della finestra
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        self._populate_bottom_frame(bottom_frame)

    # Metodo per popolare la tab dei parametri
    def _populate_param_tab(self, frame: ttk.Frame):
        '''Popola la tab dei parametri con i widget necessari.'''
        # Frame per i parametri di connessione al database
        conn_frame = tk.LabelFrame(frame, text="Parametri connessione DB")
        conn_frame.pack(fill="x", padx=20, pady=(20, 10))
        # Crea il campo dello User
        tk.Label(conn_frame, text="User:").grid(row=0, column=0, sticky='e')
        self.entry_user = tk.Entry(conn_frame, width=20)
        self.entry_user.grid(row=0, column=1)
        # Crea il campo della password
        tk.Label(conn_frame, text="Password:").grid(row=1, column=0, sticky='e')
        self.entry_password = tk.Entry(conn_frame, width=20, show="*")
        self.entry_password.grid(row=1, column=1)
        # Crea il campo dell'host
        tk.Label(conn_frame, text="Host:").grid(row=2, column=0, sticky='e')
        self.entry_host = tk.Entry(conn_frame, width=20)
        self.entry_host.grid(row=2, column=1)
        # Crea il campo della porta con valore predefinito 5432
        tk.Label(conn_frame, text="Port:").grid(row=3, column=0, sticky='e')
        self.entry_port = tk.Entry(conn_frame, width=20)
        self.entry_port.grid(row=3, column=1)
        self.entry_port.insert(0, "5432")
        # Crea il campo del nome del database
        tk.Label(conn_frame, text="DB Name:").grid(row=4, column=0, sticky='e')
        self.entry_dbname = tk.Entry(conn_frame, width=20)
        self.entry_dbname.grid(row=4, column=1)

        # Frame per selezione dei file
        file_frame = tk.LabelFrame(frame, text="Selezione file GeoTIFF")
        file_frame.pack(fill="both", expand=True, padx=20, pady=10)
        # Riga contenente la entry e il bottone "..."
        file_select_row = tk.Frame(file_frame)
        file_select_row.pack(fill="x", padx=10, pady=(10, 5))
        # Entry per mostrare i file selezionati (non modificabile)
        self.selected_files_var = tk.StringVar()
        self.entry_selected_files = tk.Entry(file_select_row, textvariable=self.selected_files_var, state="readonly")
        self.entry_selected_files.pack(side="left", fill="x", expand=True)
        # Pulsante "..."
        self.btn_select = tk.Button(file_select_row, text="...", width=3, command=self.select_files)
        self.btn_select.pack(side="left", padx=(5, 0))
        # Listbox per mostrare i file selezionati
        listbox_container = tk.Frame(file_frame)
        listbox_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.file_listbox = tk.Listbox(listbox_container, height=5)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(listbox_container, command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

    # Metodo per popolare la tab dei log
    def _populate_log_tab(self, frame: ttk.Frame):
        '''Popola la tab dei log con i widget necessari.'''
        # Crea un contenitore per il log + scrollbar
        log_container = ttk.Frame(frame)
        log_container.pack(fill="both", expand=True, padx=10, pady=10)
        # Crea un Text widget per il log
        self.log_text = tk.Text(log_container, wrap="word", state="disabled", height=15)
        self.log_text.pack(fill="both", expand=True, padx=0, pady=0)
        # Aggiunge uno scrollbar al Text widget
        scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text['yscrollcommand'] = scrollbar.set

    # Metodo per creare i widget a fondo della finestra
    def _populate_bottom_frame(self, frame: ttk.Frame):
        '''Crea i widget a fondo della finestra principale.'''
        # Riga 1: Etichetta di stato
        self.status_label = tk.Label(frame, text=status_label_idle_text, anchor="w")
        self.status_label.pack(fill="x", pady=(0, 5))
        # Riga 2: ProgressBar + Pulsante affiancati
        progress_button_frame = ttk.Frame(frame)
        progress_button_frame.pack(fill="x", padx=5)
        # Progress bar a sinistra che si espande
        self.progress_bar = ttk.Progressbar(progress_button_frame, mode='determinate')
        self.progress_bar.pack(side="left", fill="x", expand=True, pady=(0, 5))
        # Pulsante per interrompere la conversione
        self.btn_stop = tk.Button(progress_button_frame, text="Interrompi", command=self.quit)
        self.btn_stop.pack(side="right", padx=(10, 0), pady=(0, 5))
        # Disabilita il pulsante di stop inizialmente
        self.btn_stop.config(state="disabled")
        # Pulsante per convertire e caricare i file
        self.btn_convert = tk.Button(frame, text="Converti e upload", command=self.convert_and_upload_files)
        self.btn_convert.pack(side="right", padx=(10, 0), pady=(0, 5))

    # Metodo per selezionare i file GeoTIFF
    def select_files(self):
        '''Apre un dialogo per selezionare i file GeoTIFF e li aggiunge alla lista dei file selezionati.'''
        files = filedialog.askopenfilenames(filetypes=[("GeoTIFF files", "*.tif *.tiff")])
        if files:
            self.file_list = list(files)  # Salva la lista di file
            self.file_listbox.delete(0, tk.END)
            for f in self.file_list:
                self.file_listbox.insert(tk.END, f)
            # Mostra il numero di file o il primo file selezionato
            self.selected_files_var.set(f"{len(files)} file selezionati")
            # Reset barra di avanzamento e stato
            self.progress_bar["value"] = 0
            self.status_label.config(text=status_label_idle_text)
    
    # Metodo per convertire e caricare i file selezionati nel database PostgreSQL
    def convert_and_upload_files(self):
        '''Converte e carica i file GeoTIFF selezionati nel database PostgreSQL.'''
        # Controlla se sono stati selezionati file
        if not self.file_list:
            messagebox.showwarning("Attenzione", "Nessun file selezionato.")
            return
        
        # Estrae i parametri di connessione dal form
        user = self.entry_user.get()
        password = self.entry_password.get()
        host = self.entry_host.get()
        port = self.entry_port.get()
        dbname = self.entry_dbname.get()
        # Controlla se tutti i campi di connessione sono stati compilati
        if not all([user, password, host, port, dbname]):
            messagebox.showwarning("Attenzione", "Compila tutti i campi di connessione.")
            return
        # Crea l'URL di connessione al database PostgreSQL
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

        # Da valore alla progress bar
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(self.file_list)
        # Disabilita i widget durante la conversione
        self.btn_convert.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_select.config(state="disabled")
        self._toggle_db_fields("disabled")
        self.stop_event.clear()
        self._append_log("Avvio conversione...\n")

        # Crea un thread per eseguire la conversione e il caricamento
        threading.Thread(target=self._worker_thread, args=(db_url,), daemon=True).start()
        self.after(100, self._process_queue)
    
    # Metodo per abilitare/disabilitare i campi del database
    def _toggle_db_fields(self, state):
        self.entry_user.config(state=state)
        self.entry_password.config(state=state)
        self.entry_host.config(state=state)
        self.entry_port.config(state=state)
        self.entry_dbname.config(state=state)
    
    # Metodo per interrompere il processo di conversione
    def _stop_processing(self):
        self.stop_event.set()
        self._append_log("Interruzione richiesta dall'utente.")
    
    # Metodo per eseguire la conversione e il caricamento in un thread separato
    def _worker_thread(self, db_url):
        '''Esegue la conversione e il caricamento dei file in un thread separato.'''
        success = True
        failed_files = []
        for idx, file in enumerate(self.file_list, start=1):
            if self.stop_event.is_set():
                self.queue.put(("log", "Elaborazione interrotta."))
                success = False
                break
            self.queue.put(("update", file, idx))
            try:
                convert_and_upload(file, db_url)
                self.queue.put(("log", f"Completato: {file}"))
            except Exception as e:
                success = False
                failed_files.append(file)
                self.queue.put(("error", file, str(e)))
                # Continua con il prossimo file in caso di errore
                continue
        self.queue.put(("done", success, failed_files))

    # Metodo per processare la coda degli eventi
    def _process_queue(self):
        '''Processa gli eventi nella coda e aggiorna l'interfaccia grafica.'''
        try:
            while True:
                # Ottiene il messaggio dalla coda
                msg = self.queue.get_nowait()
                kind = msg[0]
                # Caso update, aggiorna la barra di progresso e l'etichetta
                if kind == "update":
                    _, file, idx = msg
                    self.progress_bar["value"] = idx
                    filename = os.path.basename(file)
                    self.status_label.config(text=f"Elaborazione file {idx}/{len(self.file_list)}: {filename}")
                    self._append_log(f"Elaborazione file {idx}: {os.path.basename(file)}")
                # Caso log, aggiunge il messaggio al log
                elif kind == "log":
                    _, text = msg
                    self._append_log(text)
                # Caso error, mostra un messaggio di errore
                elif kind == "error":
                    _, file, err = msg
                    self._append_log(f"Errore su {file}: {err}")
                    messagebox.showerror("Errore", f"Errore su {file}:\n{err}")
                # Caso done, aggiorna la barra di progresso e mostra un messaggio di successo o errore  
                elif kind == "done":
                    if len(msg) == 3:
                        _, success, failed_files = msg
                    else:
                        _, success = msg
                        failed_files = []
                    self.btn_convert.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    self.btn_select.config(state="normal")
                    self._toggle_db_fields("normal")
                    if success and not failed_files:
                        self._append_log("Conversione completata con successo")
                        self.status_label.config(text="Conversione completata con successo")
                    elif success and failed_files:
                        self._append_log(f"Conversione completata con errori su {len(failed_files)} file.")
                        for f in failed_files:
                            self._append_log(f" - {f}")
                        self.status_label.config(text=f"Conversione completata con errori su {len(failed_files)} file.")
                        messagebox.showwarning("Attenzione", f"Conversione completata con errori su {len(failed_files)} file.")
                    else:
                        self.status_label.config(text="Conversione interrotta o fallita.")
        except queue.Empty:
            pass
        finally:
            if not self.stop_event.is_set():
                self.after(100, self._process_queue)

    # Metodo per aggiungere un messaggio al log
    def _append_log(self, text):
        '''Aggiunge un messaggio al log della finestra di avanzamento.'''
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")


if __name__ == "__main__":
    app = SWEConverterGUI()
    app.mainloop()