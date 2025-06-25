'''
Questo modulo fornisce un'interfaccia grafica per caricare file GeoTIFF e convertirli in formato JSON. \n
L'interfaccia consente di selezionare più file e li carica in un server postgreSQL dopo la conversione. \n
'''
import tkinter as tk
from tkinter import filedialog, messagebox
from geoTIFF_converter import convert_and_upload

def launch_gui():
    '''Lancia l'interfaccia grafica per il caricamento dei file GeoTIFF. \n'''
    def upload_files():
        '''Apre un dialogo per selezionare i file GeoTIFF, li carica e ne tenta la conversione. \n'''
        files = filedialog.askopenfilenames(filetypes=[("GeoTIFF files", "*.tif")])
        print(files)
        if not files:
            return
        try:
            for file in files:
                convert_and_upload(file, "postgresql+psycopg2://postgres:AndreasPostgres@localhost:5432/SWE")
            messagebox.showinfo("Successo", "File caricati con successo!")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    # Crea la finestra principale dell'interfaccia grafica
    root = tk.Tk()
    # Imposta il titolo della finestra
    root.title("SWE converter")
    # Imposta le dimensioni della finestra
    root.geometry("400x200")

    # Crea un pulsante per caricare i file GeoTIFF
    btn = tk.Button(root, text="Carica file GeoTIFF", command=upload_files)
    btn.pack(padx=20, pady=20)

    # Avvia il loop principale dell'interfaccia grafica
    root.mainloop()

# strumento di testing per l'interfaccia grafica
if __name__ == "__main__":
    # Lancia l'interfaccia grafica
    launch_gui()