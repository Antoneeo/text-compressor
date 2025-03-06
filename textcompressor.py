#!/usr/bin/env python3
import os
import sys
import base64
import configparser

# Sezione introduttiva per l'archivio (da inserire all'inizio del file compresso)
INTRODUCTION = """=== INTRODUZIONE ===
Questo file rappresenta l'intera struttura di un progetto software. È stato generato automaticamente e contiene:
- L'intera gerarchia di directory e file.
- File di testo inseriti integralmente.
- File binari convertiti in base64, contrassegnati da marker specifici.
I marker utilizzati sono:
  • <<<PROJECT_ARCHIVE_START>>>: inizio dell'archivio.
  • <<<DIR: [percorso_relativo] >>>: indica una directory.
  • <<<FILE_START: [percorso_relativo] >>> e <<<FILE_END>>>: delimitano un file in modalità testo.
  • <<<FILE_BINARY_START: [percorso_relativo] >>> e <<<FILE_BINARY_END>>>: delimitano un file in modalità binaria (base64).
Il file segue questo schema per permettere a un'AI o a strumenti di parsing automatici di comprendere e, se necessario, ricostruire la struttura originale del progetto.
=====================
"""

# Marker per il formato dell'archivio
MARKER_PROJECT_START = "<<<PROJECT_ARCHIVE_START>>>"
MARKER_PROJECT_END = "<<<PROJECT_ARCHIVE_END>>>"
MARKER_DIR_PREFIX = "<<<DIR:"

# Marker per file in modalità testo
MARKER_FILE_START_PREFIX = "<<<FILE_START:"
MARKER_FILE_END = "<<<FILE_END>>>"

# Marker per file in modalità binaria (base64)
MARKER_FILE_BINARY_START_PREFIX = "<<<FILE_BINARY_START:"
MARKER_FILE_BINARY_END = "<<<FILE_BINARY_END>>>"

def get_base_path():
    """
    Restituisce la directory in cui si trova l'eseguibile o lo script corrente.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def should_include_file(filename, white_list, black_list):
    """
    Determina se includere un file in base alle liste di filtro.
    Se la white list è non vuota, viene incluso solo se l'estensione del file (in minuscolo) è presente.
    Se invece la white list è vuota ma è presente una black list, viene escluso se l'estensione è presente nella black list.
    Altrimenti, il file viene incluso.
    """
    ext = os.path.splitext(filename)[1].lower()  # include il punto, es: ".py"
    if white_list:
        if ext not in [w.lower() for w in white_list]:
            return False
    if black_list:
        if ext in [b.lower() for b in black_list]:
            return False
    return True

def compress_project(input_dir, output_file, white_list=None, black_list=None):
    """
    Scansiona ricorsivamente la directory di input e scrive il contenuto in un file di archivio.
    Se il file di output esiste già, chiede conferma per la sovrascrittura.
    Per ogni file si tenta la lettura in modalità testo (UTF-8); in caso di errore, si legge in modalità binaria,
    si codifica in base64 e si usa un marker specifico.
    Applica i filtri white list/black list, se forniti.
    """
    if white_list is None:
        white_list = []
    if black_list is None:
        black_list = []

    if os.path.exists(output_file):
        overwrite = input(f"Il file '{output_file}' esiste già. Vuoi sovrascriverlo? [y/N]: ")
        if overwrite.lower() != 'y':
            print("Operazione annullata.")
            return

    with open(output_file, "w", encoding="utf-8") as out:
        # Scrive la sezione introduttiva
        out.write(INTRODUCTION + "\n")
        # Scrive il marker d'inizio archivio
        out.write(MARKER_PROJECT_START + "\n")
        
        for root, dirs, files in os.walk(input_dir):
            rel_dir = os.path.relpath(root, input_dir)
            if rel_dir == ".":
                rel_dir = ""
            # Scrive il marker della directory
            dir_marker = f"{MARKER_DIR_PREFIX} {rel_dir} >>>"
            out.write(dir_marker + "\n")
            
            for file in files:
                if not should_include_file(file, white_list, black_list):
                    continue
                file_path = os.path.join(root, file)
                rel_file_path = os.path.join(rel_dir, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_marker = f"{MARKER_FILE_START_PREFIX} {rel_file_path} >>>"
                    out.write(file_marker + "\n")
                    out.write(content + "\n")
                    out.write(MARKER_FILE_END + "\n")
                except Exception as e:
                    try:
                        with open(file_path, "rb") as f:
                            binary_content = f.read()
                        encoded = base64.b64encode(binary_content).decode('ascii')
                        file_marker = f"{MARKER_FILE_BINARY_START_PREFIX} {rel_file_path} >>>"
                        out.write(file_marker + "\n")
                        out.write(encoded + "\n")
                        out.write(MARKER_FILE_BINARY_END + "\n")
                    except Exception as e2:
                        print(f"Errore nella lettura del file {file_path} in modalità binaria: {e2}", file=sys.stderr)
        out.write(MARKER_PROJECT_END + "\n")
    print(f"Compressione completata. Archivio salvato in: {output_file}")

def decompress_project(input_file, output_dir):
    """
    Legge il file di archivio e ricostruisce la struttura originale.
    Gestisce sia i file memorizzati in modalità testo sia quelli in modalità binaria (base64).
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Errore nell'apertura del file di archivio: {e}", file=sys.stderr)
        return

    start_index = 0
    for idx, line in enumerate(lines):
        if line.strip() == MARKER_PROJECT_START:
            start_index = idx
            break

    if start_index == 0:
        print("Il file di archivio non ha un formato valido.", file=sys.stderr)
        return

    i = start_index + 1
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if line == MARKER_PROJECT_END:
            break
        if line.startswith(MARKER_DIR_PREFIX):
            dir_path = line[len(MARKER_DIR_PREFIX):].strip(" >")
            full_dir = os.path.join(output_dir, dir_path)
            os.makedirs(full_dir, exist_ok=True)
            i += 1
        elif line.startswith(MARKER_FILE_START_PREFIX):
            rel_file_path = line[len(MARKER_FILE_START_PREFIX):].strip(" >")
            full_file_path = os.path.join(output_dir, rel_file_path)
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
            i += 1
            content_lines = []
            while i < len(lines) and lines[i].strip() != MARKER_FILE_END:
                content_lines.append(lines[i])
                i += 1
            with open(full_file_path, "w", encoding="utf-8") as out_file:
                out_file.write("".join(content_lines))
            i += 1
        elif line.startswith(MARKER_FILE_BINARY_START_PREFIX):
            rel_file_path = line[len(MARKER_FILE_BINARY_START_PREFIX):].strip(" >")
            full_file_path = os.path.join(output_dir, rel_file_path)
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
            i += 1
            encoded_lines = []
            while i < len(lines) and lines[i].strip() != MARKER_FILE_BINARY_END:
                encoded_lines.append(lines[i])
                i += 1
            encoded = "".join(encoded_lines)
            try:
                decoded = base64.b64decode(encoded)
            except Exception as e:
                print(f"Errore nel decodificare il contenuto binario del file {rel_file_path}: {e}", file=sys.stderr)
                decoded = b""
            with open(full_file_path, "wb") as out_file:
                out_file.write(decoded)
            i += 1
        else:
            i += 1
    print(f"Decompressione completata. Progetto ripristinato in: {output_dir}")

def create_default_config(config_file):
    """
    Crea un file di configurazione .ini di default con commenti ed esempi.
    """
    default_config = """; Configurazione per text-compressor
; ---------------------------------------
; Sezione Paths:
; compress_folder: specifica il percorso della directory da comprimere.
;    Se lasciato vuoto, verrà utilizzata la directory corrente.
; decompress_folder: specifica il percorso della directory dove decomprimere.
;    Se lasciato vuoto, verrà utilizzata la directory corrente.
; output_archive: specifica il percorso completo del file di output per la compressione.
;    Se lasciato vuoto, verrà creato 'text-compressed-project.txt' nella directory di compressione.
; input_archive: specifica il percorso completo del file di archivio da decomprimere.
;    Se lasciato vuoto, verrà usato 'text-compressed-project.txt' nella directory di compressione.

[Paths]
compress_folder =
decompress_folder =
output_archive =
input_archive =

; ---------------------------------------
; Sezione Filters:
; white_list: elenco delle estensioni da includere (se presente, solo questi file saranno compressi).
;    Esempio: .py, .txt, .md
; black_list: elenco delle estensioni da escludere.
;    Esempio: .exe, .bin
; Se entrambe le liste sono vuote, verranno presi tutti i file.

[Filters]
white_list =
black_list =
"""
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(default_config)
    print(f"File di configurazione creato: {config_file}")

def read_config(config_file):
    """
    Legge il file di configurazione in formato .ini e restituisce:
      - compress_folder: directory da comprimere (default → cartella locale)
      - decompress_folder: directory dove decomprimere (default → cartella locale)
      - output_archive: percorso del file di output per compressione (default → 'text-compressed-project.txt' nella cartella di compressione)
      - input_archive: percorso del file di archivio da decomprimere (default → 'text-compressed-project.txt' nella cartella di compressione)
      - white_list e black_list: liste di filtro (se non presenti, liste vuote)
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    compress_folder = config.get('Paths', 'compress_folder', fallback='').strip()
    decompress_folder = config.get('Paths', 'decompress_folder', fallback='').strip()
    if compress_folder == "":
        compress_folder = get_base_path()
    if decompress_folder == "":
        decompress_folder = get_base_path()
    output_archive = config.get('Paths', 'output_archive', fallback='').strip()
    if output_archive == "":
        output_archive = os.path.join(compress_folder, "text-compressed-project.txt")
    input_archive = config.get('Paths', 'input_archive', fallback='').strip()
    if input_archive == "":
        input_archive = os.path.join(compress_folder, "text-compressed-project.txt")
    white_list = []
    black_list = []
    if config.has_section('Filters'):
        white_list = config.get('Filters', 'white_list', fallback='').split(',')
        white_list = [w.strip() for w in white_list if w.strip()]
        black_list = config.get('Filters', 'black_list', fallback='').split(',')
        black_list = [b.strip() for b in black_list if b.strip()]
    return compress_folder, decompress_folder, output_archive, input_archive, white_list, black_list

def main():
    base_path = get_base_path()
    print("Scegli la modalità di configurazione:")
    print("1) Modalità interattiva")
    print("2) Utilizza file di configurazione (.ini)")
    mode_choice = input("Inserisci la tua scelta (1/2): ").strip()
    
    if mode_choice == "1":
        # Modalità interattiva
        input_dir = input(f"Inserisci il percorso della directory da comprimere (default: {base_path}): ").strip()
        if input_dir == "":
            input_dir = base_path
        default_output_archive = os.path.join(input_dir, "text-compressed-project.txt")
        output_file = input(f"Inserisci il percorso completo del file di output (default: {default_output_archive}): ").strip()
        if output_file == "":
            output_file = default_output_archive
        white_list_str = input("Inserisci la white list (estensioni separate da virgola, default: vuota → tutti i file): ").strip()
        white_list = [x.strip() for x in white_list_str.split(',')] if white_list_str else []
        black_list_str = input("Inserisci la black list (estensioni separate da virgola, default: vuota): ").strip()
        black_list = [x.strip() for x in black_list_str.split(',')] if black_list_str else []
        
        print("Scegli l'operazione da eseguire:")
        print("1) Comprimere il progetto")
        print("2) Decomprimere un archivio")
        choice = input("Inserisci la tua scelta (1/2): ").strip()
        if choice == "1":
            print(f"Compressione: verrà compressa la directory: {input_dir}")
            print(f"Archivio di output: {output_file}")
            compress_project(input_dir, output_file, white_list, black_list)
        elif choice == "2":
            default_archive = os.path.join(input_dir, "text-compressed-project.txt")
            archive = input(f"Inserisci il percorso del file di archivio da decomprimere (default: {default_archive}): ").strip()
            if archive == "":
                archive = default_archive
            output_dir = input(f"Inserisci il percorso della directory di destinazione (default: {base_path}): ").strip()
            if output_dir == "":
                output_dir = base_path
            decompress_project(archive, output_dir)
        else:
            print("Scelta non valida. Uscita.")
    
    elif mode_choice == "2":
        default_config = os.path.join(base_path, "config.ini")
        config_path = input(f"Inserisci il percorso del file di configurazione (default: {default_config}): ").strip()
        if config_path == "":
            config_path = default_config
        if not os.path.exists(config_path):
            print(f"Il file di configurazione {config_path} non esiste. Verrà creato un file di configurazione di default.")
            create_default_config(config_path)
        try:
            compress_folder, decompress_folder, output_archive, input_archive, white_list, black_list = read_config(config_path)
        except Exception as e:
            print(f"Errore nella lettura del file di configurazione: {e}")
            return
        
        print("Scegli l'operazione da eseguire:")
        print("1) Comprimere il progetto")
        print("2) Decomprimere un archivio")
        choice = input("Inserisci la tua scelta (1/2): ").strip()
        if choice == "1":
            print(f"Compressione: verrà compressa la directory: {compress_folder}")
            print(f"Archivio di output: {output_archive}")
            compress_project(compress_folder, output_archive, white_list, black_list)
        elif choice == "2":
            print(f"Decompressione: verrà decompresso l'archivio: {input_archive}")
            print(f"Il progetto verrà ripristinato nella directory: {decompress_folder}")
            decompress_project(input_archive, decompress_folder)
        else:
            print("Scelta non valida. Uscita.")
    else:
        print("Modalità non valida. Uscita.")

if __name__ == "__main__":
    main()
