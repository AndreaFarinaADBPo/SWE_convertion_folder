'''
Questo modulo fornisce un'interfaccia grafica per caricare file GeoTIFF e convertirli in formato JSON. \n
L'interfaccia consente di selezionare più file e li carica in un server postgreSQL dopo la conversione. \n
'''
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from geoTIFF_converter import convert_and_upload

def launch_gui():
    '''Lancia l'interfaccia grafica per il caricamento e la conversione dei file GeoTIFF.'''
    selected_files = []

    # Funzione per selezionare i file GeoTIFF e aggiungerli alla lista dei file selezionati.
    def select_files():
        '''Apre un dialogo per selezionare i file GeoTIFF e li aggiunge alla lista dei file selezionati.'''
        # Apre un dialogo per selezionare i file GeoTIFF
        files = filedialog.askopenfilenames(filetypes=[("GeoTIFF files", "*.tif")])
        # Mette i file selezionati nella lista dei file
        if files:
            # Ripulisce la lista dei file selezionati
            selected_files.clear()
            # Aggiunge i file selezionati alla lista
            selected_files.extend(files)
            # Aggiorna la Listbox con i file selezionati
            file_listbox.delete(0, tk.END)
            # Inserisce i file selezionati nella Listbox
            for file in selected_files:
                file_listbox.insert(tk.END, file)

    # Funzione per mostrare una finestra di avanzamento durante la conversione dei file.
    def show_progress_window():
        '''Crea una finestra di avanzamento per mostrare lo stato della conversione dei file.'''
        progress_win = tk.Toplevel(root)
        progress_win.title("Avanzamento conversione")
        progress_win.geometry("400x150")
        progress_win.resizable(False, False)

        progress_label = tk.Label(progress_win, text="Inizio conversione...", anchor="w")
        progress_label.pack(fill="x", padx=20, pady=(20, 5))

        progress_bar = ttk.Progressbar(progress_win, length=350, mode='determinate', maximum=len(selected_files))
        progress_bar.pack(padx=20, pady=10)

        return progress_win, progress_label, progress_bar

    # Funzione per convertire e caricare i file selezionati nel database PostgreSQL.
    def convert_and_upload_files():
        '''Converte e carica i file GeoTIFF selezionati nel database PostgreSQL.'''
        # Mostra un messaggio di avviso se non sono stati selezionati file
        if not selected_files:
            messagebox.showwarning("Attenzione", "Nessun file selezionato.")
            return
        # Ottieni i parametri dalla box
        user = entry_user.get()
        password = entry_password.get()
        host = entry_host.get()
        port = entry_port.get()
        dbname = entry_dbname.get()
        db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        
        # Disabilita i controlli durante la conversione
        btn_select.config(state="disabled")
        btn_convert.config(state="disabled")
        entry_user.config(state="disabled")
        entry_password.config(state="disabled")
        entry_host.config(state="disabled")
        entry_port.config(state="disabled")
        entry_dbname.config(state="disabled")

        progress_win, progress_label, progress_bar = show_progress_window()

        # Funzione per eseguire la conversione e il caricamento dei file in un thread separato.
        def worker():
            '''Esegue la conversione e il caricamento dei file in un thread separato.'''
            success = True
            
            # Inizializza la barra di avanzamento
            for idx, file in enumerate(selected_files, 1):
                # Funzione per aggiornare l'interfaccia grafica con lo stato corrente della conversione
                def update_gui():
                    '''Aggiorna l'interfaccia grafica con lo stato corrente della conversione.'''
                    progress_label.config(text=f"Sto convertendo: {file.split('/')[-1]} ({idx}/{len(selected_files)})")
                    progress_bar['value'] = idx - 1
                # Aggiorna l'interfaccia grafica
                root.after(0, update_gui)
                
                # Tenta di convertire e caricare il file
                try:
                    # Chiama la funzione di conversione e caricamento
                    convert_and_upload(file, db_url)
                # Se la conversione e il caricamento hanno successo, aggiorna la barra di avanzamento e interrompe il ciclo
                except Exception as e:
                    success = False
                    # Funzione per mostrare un messaggio di errore nell'interfaccia grafica
                    def show_error():
                        '''Mostra un messaggio di errore nell'interfaccia grafica.'''
                        progress_label.config(text=f"Errore su {file.split('/')[-1]}: {e}")
                        progress_bar['value'] = idx
                        messagebox.showerror("Errore", f"Errore su {file}:\n{e}")
                    # Mostra l'errore nell'interfaccia grafica
                    root.after(0, show_error)
                    break
            
            # Funzione per aggiornare l'interfaccia grafica al termine della conversione
            def finish():
                '''Aggiorna l'interfaccia grafica al termine della conversione.'''
                progress_bar['value'] = len(selected_files)
                if success:
                    progress_label.config(text="Conversione completata con successo!")
                    messagebox.showinfo("Successo", "Tutti i file sono stati caricati con successo!")
                btn_select.config(state="normal")
                btn_convert.config(state="normal")
                entry_user.config(state="normal")
                entry_password.config(state="normal")
                entry_host.config(state="normal")
                entry_port.config(state="normal")
                entry_dbname.config(state="normal")
                progress_win.after(1500, progress_win.destroy)
            # Chiude la finestra di avanzamento dopo un breve ritardo
            root.after(0, finish)

        # Avvia il thread per la conversione e il caricamento dei file
        threading.Thread(target=worker, daemon=True).start()

    root = tk.Tk()
    root.title("SWE converter")
    root.geometry("700x450")

    # Pulsante per selezionare i file
    btn_select = tk.Button(root, text="Seleziona file GeoTIFF", command=select_files)
    btn_select.pack(padx=20, pady=10)

    # Lista dei file selezionati
    file_listbox = tk.Listbox(root, width=80, height=10)
    file_listbox.pack(padx=20, pady=10)

    # Frame per i parametri di connessione (in basso a sinistra)
    conn_frame = tk.LabelFrame(root, text="Parametri connessione DB")
    conn_frame.place(relx=0.0, rely=1.0, anchor='sw', x=20, y=-20)

    tk.Label(conn_frame, text="User:").grid(row=0, column=0, sticky='e')
    entry_user = tk.Entry(conn_frame, width=12)
    entry_user.grid(row=0, column=1)

    tk.Label(conn_frame, text="Password:").grid(row=1, column=0, sticky='e')
    entry_password = tk.Entry(conn_frame, width=12, show="*")
    entry_password.grid(row=1, column=1)

    tk.Label(conn_frame, text="Host:").grid(row=2, column=0, sticky='e')
    entry_host = tk.Entry(conn_frame, width=12)
    entry_host.grid(row=2, column=1)
    entry_host.insert(0, "localhost")

    tk.Label(conn_frame, text="Port:").grid(row=3, column=0, sticky='e')
    entry_port = tk.Entry(conn_frame, width=12)
    entry_port.grid(row=3, column=1)
    entry_port.insert(0, "5432")

    tk.Label(conn_frame, text="DB Name:").grid(row=4, column=0, sticky='e')
    entry_dbname = tk.Entry(conn_frame, width=12)
    entry_dbname.grid(row=4, column=1)

    # Pulsante per convertire e caricare i file
    btn_convert = tk.Button(root, text="Convert and upload", command=convert_and_upload_files)
    btn_convert.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-20)  # 20px dal bordo destro e dal fondo

    root.mainloop()

# strumento di testing per l'interfaccia grafica
if __name__ == "__main__":
    # Lancia l'interfaccia grafica
    launch_gui()