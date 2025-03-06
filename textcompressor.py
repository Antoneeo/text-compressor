#!/usr/bin/env python3
import os
import sys
import base64

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
    Restituisce la directory in cui si trova l'eseguibile.
    Se l'applicazione è compilata (es. con PyInstaller), usa sys.executable;
    altrimenti, usa __file__.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def compress_project(input_dir, output_file):
    """
    Scansiona ricorsivamente la directory di input e scrive il contenuto in un file di archivio.
    Se il file di output esiste già, chiede conferma per la sovrascrittura.
    Per ogni file si tenta prima la lettura in modalità testo; in caso di errore, si legge in modalità binaria,
    si codifica in base64 e si usa un marker specifico.
    """
    if os.path.exists(output_file):
        overwrite = input(f"Il file '{output_file}' esiste già. Vuoi sovrascriverlo? [y/N]: ")
        if overwrite.lower() != 'y':
            print("Operazione annullata.")
            return

    with open(output_file, "w", encoding="utf-8") as out:
        out.write(MARKER_PROJECT_START + "\n")
        
        for root, dirs, files in os.walk(input_dir):
            rel_dir = os.path.relpath(root, input_dir)
            if rel_dir == ".":
                rel_dir = ""
            # Scrive il marker della directory
            dir_marker = f"{MARKER_DIR_PREFIX} {rel_dir} >>>"
            out.write(dir_marker + "\n")
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_file_path = os.path.join(rel_dir, file)
                # Prova a leggere il file in modalità testo
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_marker = f"{MARKER_FILE_START_PREFIX} {rel_file_path} >>>"
                    out.write(file_marker + "\n")
                    out.write(content + "\n")
                    out.write(MARKER_FILE_END + "\n")
                except Exception as e:
                    # Se non si riesce a leggere come testo, proviamo in modalità binaria
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

    if not lines or lines[0].strip() != MARKER_PROJECT_START:
        print("Il file di archivio non ha un formato valido.", file=sys.stderr)
        return

    i = 1
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
            i += 1  # Salta il marker di fine file
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
            i += 1  # Salta il marker di fine file binario
        else:
            i += 1
    print(f"Decompressione completata. Progetto ripristinato in: {output_dir}")

def main():
    base_path = get_base_path()
    
    print("Scegli l'operazione da eseguire:")
    print("1) Comprimere il progetto")
    print("2) Decomprimere un archivio")
    choice = input("Inserisci la tua scelta (1/2): ").strip()
    
    if choice == "1":
        input_dir = base_path
        output_file = os.path.join(base_path, "text-compressed-project.txt")
        print(f"Compressore: verrà utilizzata la directory: {input_dir}")
        print(f"Archivio di output: {output_file}")
        compress_project(input_dir, output_file)
    elif choice == "2":
        default_archive = os.path.join(base_path, "text-compressed-project.txt")
        archive = input(f"Inserisci il percorso del file di archivio da decomprimere (default: {default_archive}): ").strip()
        if archive == "":
            archive = default_archive
        default_output_dir = os.path.join(base_path, "decompressed_project")
        output_dir = input(f"Inserisci il percorso della directory di destinazione (default: {default_output_dir}): ").strip()
        if output_dir == "":
            output_dir = default_output_dir
        decompress_project(archive, output_dir)
    else:
        print("Scelta non valida. Uscita.")

if __name__ == "__main__":
    main()
