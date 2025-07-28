import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
import os
from geoTIFF_converter import convert_and_upload


class SWEConverterGUI(tk.Tk):
    '''Classe per l'interfaccia grafica del convertitore SWE.'''
    # Metodo di inizializzazione della classe SWEConverterGUI
    def __init__(self):
        '''Inizializza della classe SWEConverterGUI.'''
        super().__init__()
        self.title("SWE Converter")
        self.geometry("700x500")
        self.selected_files = []
        self.queue = queue.Queue()
        self._create_widgets()

    # Metodo per creare i widget dell'interfaccia grafica
    def _create_widgets(self):
        '''Crea i widget dell'interfaccia grafica.'''
        # Pulsante per selezionare i file GeoTIFF
        self.btn_select = tk.Button(self, text="Seleziona file GeoTIFF", command=self.select_files)
        self.btn_select.pack(padx=20, pady=10)

        # Lista dei file selezionati
        self.file_listbox = tk.Listbox(self, width=80, height=10)
        self.file_listbox.pack(padx=20, pady=10)

        # Frame per i parametri di connessione al database
        conn_frame = tk.LabelFrame(self, text="Parametri connessione DB")
        conn_frame.place(relx=0.0, rely=1.0, anchor='sw', x=20, y=-20)

        tk.Label(conn_frame, text="User:").grid(row=0, column=0, sticky='e')
        self.entry_user = tk.Entry(conn_frame, width=20)
        self.entry_user.grid(row=0, column=1)

        tk.Label(conn_frame, text="Password:").grid(row=1, column=0, sticky='e')
        self.entry_password = tk.Entry(conn_frame, width=20, show="*")
        self.entry_password.grid(row=1, column=1)

        tk.Label(conn_frame, text="Host:").grid(row=2, column=0, sticky='e')
        self.entry_host = tk.Entry(conn_frame, width=20)
        self.entry_host.grid(row=2, column=1)
        
        tk.Label(conn_frame, text="Port:").grid(row=3, column=0, sticky='e')
        self.entry_port = tk.Entry(conn_frame, width=20)
        self.entry_port.grid(row=3, column=1)
        self.entry_port.insert(0, "5432")

        tk.Label(conn_frame, text="DB Name:").grid(row=4, column=0, sticky='e')
        self.entry_dbname = tk.Entry(conn_frame, width=20)
        self.entry_dbname.grid(row=4, column=1)

        # Pulsante per convertire e caricare i file
        self.btn_convert = tk.Button(self, text="Convert and upload", command=self.convert_and_upload_files)
        self.btn_convert.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-20)

    # Metodo per selezionare i file GeoTIFF
    def select_files(self):
        '''Apre un dialogo per selezionare i file GeoTIFF e li aggiunge alla lista dei file selezionati.'''
        files = filedialog.askopenfilenames(filetypes=[("GeoTIFF files", "*.tif")])
        if files:
            self.selected_files.clear()
            self.selected_files.extend(files)
            self.file_listbox.delete(0, tk.END)
            for file in self.selected_files:
                self.file_listbox.insert(tk.END, file)
    
    # Metodo per convertire e caricare i file selezionati nel database PostgreSQL
    def convert_and_upload_files(self):
        '''Converte e carica i file GeoTIFF selezionati nel database PostgreSQL.'''
        if not self.selected_files:
            messagebox.showwarning("Attenzione", "Nessun file selezionato.")
            return
        
        user = self.entry_user.get()
        password = self.entry_password.get()
        host = self.entry_host.get()
        port = self.entry_port.get()
        dbname = self.entry_dbname.get()
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

        # Disabilita i controlli durante la conversione
        self.btn_select.config(state="disabled")
        self.btn_convert.config(state="disabled")
        self.entry_user.config(state="disabled")
        self.entry_password.config(state="disabled")
        self.entry_host.config(state="disabled")
        self.entry_port.config(state="disabled")
        self.entry_dbname.config(state="disabled")

        # Mostra una finestra di avanzamento
        self.progress_win, self.progress_label, self.progress_bar, self.log_text = self.show_progress_window()
        threading.Thread(
            target=self._worker_thread,
            args=(db_url,),
            daemon=True
        ).start()
        self.after(100, self._process_queue)
    
    # Metodo per mostrare una finestra di avanzamento
    def show_progress_window(self):
        '''Crea una finestra con tab Progress e Log.'''
        progress_win = tk.Toplevel(self)
        progress_win.title("Avanzamento conversione")
        progress_win.geometry("500x300")
        notebook = ttk.Notebook(progress_win)
        notebook.pack(fill="both", expand=True)

        # Tab Progresso
        progress_tab = tk.Frame(notebook)
        notebook.add(progress_tab, text="Progresso")
        progress_label = tk.Label(progress_tab, text="Inizio conversione...", anchor="w")
        progress_label.pack(fill="x", padx=20, pady=(20, 5))
        progress_bar = ttk.Progressbar(progress_tab, maximum=len(self.selected_files) , length=450, mode='determinate')
        progress_bar.pack(padx=20, pady=(0, 20))

        # Tab Log
        log_tab = tk.Frame(notebook)
        notebook.add(log_tab, text="Log dettagliato")
        log = tk.Text(log_tab, wrap="word", state="disabled")
        log.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(log.master, command=log.yview)
        log['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side="right", fill="y")

        # Ritorna gli elementi della finestra di avanzamento
        return progress_win, progress_label, progress_bar, log
    
    # Metodo per eseguire la conversione e il caricamento in un thread separato
    def _worker_thread(self, db_url):
        '''Esegue la conversione e il caricamento dei file in un thread separato.'''
        success = True
        for idx, file in enumerate(self.selected_files, start=1):
            self.queue.put(("update", file, idx))
            try:
                convert_and_upload(file, db_url)
                self.queue.put(("log", f"Completato: {file}"))
            except Exception as e:
                success = False
                self.queue.put(("error", file, str(e)))
                break
        self.queue.put(("done", success))

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
                    self.progress_label.config(text=f"Sto convertendo: {os.path.basename(file)} ({idx}/{len(self.selected_files)})")
                    self.progress_bar['value'] = idx - 1
                # Caso log, aggiunge il messaggio al log
                elif kind == "log":
                    _, text = msg
                    self._append_log(text)
                # Caso error, mostra un messaggio di errore
                elif kind == "error":
                    _, file, err = msg
                    self.progress_bar['value'] = self.progress_bar['maximum']
                    self._append_log(f"Errore su {file}: {err}")
                    messagebox.showerror("Errore", f"Errore su {file}:\n{err}")
                # Caso done, aggiorna la barra di progresso e mostra un messaggio di successo o errore  
                elif kind == "done":
                    _, success = msg
                    self.progress_bar['value'] = self.progress_bar['maximum']
                    if success:
                        self._append_log("Conversione completata con successo!")
                        messagebox.showinfo("Successo", "Tutti i file sono stati caricati con successo!")
                    self.progress_win.after(1500, self.progress_win.destroy)
                    # riabilita widget...
                    self.btn_select.config(state="normal")
                    self.btn_convert.config(state="normal")
                    self.entry_user.config(state="normal")
                    self.entry_password.config(state="normal")
                    self.entry_host.config(state="normal")
                    self.entry_port.config(state="normal")
                    self.entry_dbname.config(state="normal")
        except queue.Empty:
            pass
        else:
            pass
        finally:
            if self.progress_win.winfo_exists():
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