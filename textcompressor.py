#!/usr/bin/env python3
import os
import sys
import base64
import configparser
import math

# Constant for the maximum number of lines per file
MAX_LINES_PER_FILE = 4000

# Introduction section for the archive (to be inserted at the beginning of the compressed file)
INTRODUCTION = """=== INTRODUCTION ===
This file represents the entire structure of a software project. It has been generated automatically and contains:
- The entire directory and file hierarchy.
- Text files included in full.
- (Binary files are compressed only if the 'compress_binary' option is enabled.)
The markers used are:
  • <<<PROJECT_ARCHIVE_START>>>: start of the archive.
  • <<<DIR: [relative_path] >>>: indicates a directory.
  • <<<FILE_START: [relative_path] >>> and <<<FILE_END>>>: delimit a file in text mode.
The file follows this schema to allow an AI or automatic parsing tools to understand and, if necessary, reconstruct the original project structure.
=====================
"""

# Markers for the archive format
MARKER_PROJECT_START = "<<<PROJECT_ARCHIVE_START>>>"
MARKER_PROJECT_END = "<<<PROJECT_ARCHIVE_END>>>"
MARKER_DIR_PREFIX = "<<<DIR:"

# Markers for text files
MARKER_FILE_START_PREFIX = "<<<FILE_START:"
MARKER_FILE_END = "<<<FILE_END>>>"

# Markers for binary files (used only if compress_binary is True)
MARKER_FILE_BINARY_START_PREFIX = "<<<FILE_BINARY_START:"
MARKER_FILE_BINARY_END = "<<<FILE_BINARY_END>>>"

def get_base_path():
    """
    Returns the directory where the executable or the current script is located.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def should_include_file(filename, white_list, black_list):
    """
    Determines whether to include a file based on filter lists.
    If the white list is not empty, the file is included only if its extension (in lowercase) is present.
    If the white list is empty but a black list is provided, the file is excluded if its extension is present.
    Otherwise, the file is included.
    """
    ext = os.path.splitext(filename)[1].lower()  # extension includes the dot, e.g., ".py"
    if white_list:
        if ext not in [w.lower() for w in white_list]:
            return False
    if black_list:
        if ext in [b.lower() for b in black_list]:
            return False
    return True

def write_lines_to_files(output_file, lines):
    """
    Writes the list of lines to one or more files.
    If the total number of lines is less than or equal to MAX_LINES_PER_FILE, writes to output_file.
    Otherwise, splits the content into parts:
      e.g., if output_file is "text-compressed-project.txt",
      it generates "text-compressed-project_part1.txt", "text-compressed-project_part2.txt", etc.
    Before writing, if the file already exists, it is removed to ensure overwriting.
    Also, truncate(0) is called immediately after opening the file to force clearing previous content.
    """
    total_lines = len(lines)
    
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except Exception as e:
            print(f"Warning: Unable to delete {output_file}: {e}", file=sys.stderr)
    
    if total_lines <= MAX_LINES_PER_FILE:
        with open(output_file, "w", encoding="utf-8") as f:
            f.truncate(0)
            f.write("".join(lines))
        print(f"Compression complete. Archive saved in: {output_file}")
    else:
        parts = math.ceil(total_lines / MAX_LINES_PER_FILE)
        base, ext = os.path.splitext(output_file)
        for part in range(parts):
            part_filename = f"{base}_part{part+1}{ext}"
            if os.path.exists(part_filename):
                try:
                    os.remove(part_filename)
                except Exception as e:
                    print(f"Warning: Unable to delete {part_filename}: {e}", file=sys.stderr)
            start = part * MAX_LINES_PER_FILE
            end = start + MAX_LINES_PER_FILE
            with open(part_filename, "w", encoding="utf-8") as f:
                f.truncate(0)
                f.write("".join(lines[start:end]))
            print(f"Part {part+1} saved in: {part_filename}")
        print(f"Compression complete. Total parts generated: {parts}")

def compress_project(input_dir, output_file, white_list=None, black_list=None, compress_binary=False):
    """
    Recursively scans the input directory and builds the content as a list of lines.
    Applies the white list/black list filters (if provided) and excludes entire directories present in the black list.
    If a file cannot be read in text mode:
      - If compress_binary is True, it is compressed in binary mode (base64).
      - If compress_binary is False (default), the file is ignored.
    At the end, if the total number of lines exceeds MAX_LINES_PER_FILE, the result is split into multiple files.
    """
    if white_list is None:
        white_list = []
    if black_list is None:
        black_list = []

    output_lines = []
    output_lines.append(INTRODUCTION + "\n")
    output_lines.append(MARKER_PROJECT_START + "\n")
    
    for root, dirs, files in os.walk(input_dir):
        # Exclude entire directories if their name is present in the black list (case-insensitive)
        dirs[:] = [d for d in dirs if d.lower() not in [b.lower() for b in black_list]]
        
        rel_dir = os.path.relpath(root, input_dir)
        if rel_dir == ".":
            rel_dir = ""
        output_lines.append(f"{MARKER_DIR_PREFIX} {rel_dir} >>>\n")
        
        for file in files:
            if not should_include_file(file, white_list, black_list):
                continue
            file_path = os.path.join(root, file)
            rel_file_path = os.path.join(rel_dir, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                output_lines.append(f"{MARKER_FILE_START_PREFIX} {rel_file_path} >>>\n")
                output_lines.append(content + "\n")
                output_lines.append(MARKER_FILE_END + "\n")
            except Exception as e:
                if compress_binary:
                    try:
                        with open(file_path, "rb") as f:
                            binary_content = f.read()
                        encoded = base64.b64encode(binary_content).decode('ascii')
                        output_lines.append(f"{MARKER_FILE_BINARY_START_PREFIX} {rel_file_path} >>>\n")
                        output_lines.append(encoded + "\n")
                        output_lines.append(MARKER_FILE_BINARY_END + "\n")
                    except Exception as e2:
                        print(f"Error reading file {file_path} in binary mode: {e2}", file=sys.stderr)
                else:
                    print(f"File {file_path} is not in text format and binary compression is disabled. It will be skipped.", file=sys.stderr)
    output_lines.append(MARKER_PROJECT_END + "\n")
    write_lines_to_files(output_file, output_lines)

def combine_multipart_archive(input_file):
    """
    If the specified file does not exist, tries to combine multipart files (with _partN suffix).
    Returns a list of lines resulting from the combination, or None if no file is found.
    """
    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            return f.readlines()
    else:
        base, ext = os.path.splitext(input_file)
        part = 1
        combined_lines = []
        while True:
            part_filename = f"{base}_part{part}{ext}"
            if os.path.exists(part_filename):
                with open(part_filename, "r", encoding="utf-8") as f:
                    combined_lines.extend(f.readlines())
                part += 1
            else:
                break
        if combined_lines:
            return combined_lines
        else:
            return None

def decompress_project(input_file, output_dir):
    """
    Reads the archive file (or multipart files) and reconstructs the original structure.
    Handles files stored in text mode.
    """
    lines = combine_multipart_archive(input_file)
    if lines is None:
        print(f"Archive file not found: {input_file}", file=sys.stderr)
        return

    start_index = 0
    for idx, line in enumerate(lines):
        if line.strip() == MARKER_PROJECT_START:
            start_index = idx
            break

    if start_index == 0:
        print("The archive file does not have a valid format.", file=sys.stderr)
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
        else:
            i += 1
    print(f"Decompression complete. Project restored in: {output_dir}")

def create_default_config(config_file):
    """
    Creates a default .ini configuration file with comments and examples.
    The file will be created with the name text-compressor-config.ini.
    """
    default_config = """; Configuration for text-compressor
; ============================================
; This configuration file (text-compressor-config.ini) allows you to specify parameters for
; compressing and decompressing the project.
;
; [Paths]
; compress_folder =
;    Specifies the path of the directory to compress.
;    If left blank, the directory where the executable is located will be used.
;
; decompress_folder =
;    Specifies the path of the directory where the archive will be decompressed.
;    If left blank, the current directory will be used.
;
; output_archive =
;    Specifies the full path of the output file for compression.
;    If left blank, a file named "text-compressed-project.txt" will be created in the compression directory.
;
; input_archive =
;    Specifies the full path of the archive file to decompress.
;    If left blank, "text-compressed-project.txt" in the compression directory will be used.
;
; [Filters]
; white_list =
;    List of extensions to include (if provided, only these files will be compressed).
;    Example: .py, .txt, .md
;
; black_list =
;    List of extensions and/or folder names to exclude.
;    Example: .git, .exe, .pyc, .dll, build
;    If a folder name is present in black_list, that folder will be excluded from compression.
;
; compress_binary =
;    Specifies whether to compress binary files (by converting them to base64).
;    Set to True to compress binary files, or False to ignore them.
;    Default is False.
;
; If both lists are empty, all files will be compressed.
; ============================================
[Paths]
compress_folder =
decompress_folder =
output_archive =
input_archive =

[Filters]
white_list =
black_list = .git, .exe, .pyc, .dll, build
compress_binary = False
"""
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(default_config)
    print(f"Configuration file created: {config_file}")

def read_config(config_file):
    """
    Reads the configuration file in .ini format and returns:
    compress_folder, decompress_folder, output_archive, input_archive, white_list, black_list, compress_binary.
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
    compress_binary = config.getboolean('Filters', 'compress_binary', fallback=False)
    if config.has_section('Filters'):
        white_list = config.get('Filters', 'white_list', fallback='').split(',')
        white_list = [w.strip() for w in white_list if w.strip()]
        black_list = config.get('Filters', 'black_list', fallback='').split(',')
        black_list = [b.strip() for b in black_list if b.strip()]
    return compress_folder, decompress_folder, output_archive, input_archive, white_list, black_list, compress_binary

def main():
    base_path = get_base_path()
    print("Choose configuration mode:")
    print("1) Interactive mode")
    print("2) Use configuration file (.ini)")
    mode_choice = input("Enter your choice (1/2): ").strip()
    
    if mode_choice == "1":
        # Interactive mode: compress_binary is set to False by default
        input_dir = input(f"Enter the directory to compress (default: {base_path}): ").strip()
        if input_dir == "":
            input_dir = base_path
        default_output_archive = os.path.join(input_dir, "text-compressed-project.txt")
        output_file = input(f"Enter the full path of the output file (default: {default_output_archive}): ").strip()
        if output_file == "":
            output_file = default_output_archive
        white_list_str = input("Enter the white list (extensions separated by commas, default: empty → all files): ").strip()
        white_list = [x.strip() for x in white_list_str.split(',')] if white_list_str else []
        black_list_str = input("Enter the black list (extensions or folder names separated by commas, default: .git, .exe, .pyc, .dll, build): ").strip()
        if black_list_str == "":
            black_list = [".git", ".exe", ".pyc", ".dll", "build"]
        else:
            black_list = [x.strip() for x in black_list_str.split(',')]
        compress_binary = False  # By default, in interactive mode binary files are not compressed.
        
        print("Choose the operation to perform:")
        print("1) Compress the project")
        print("2) Decompress an archive")
        choice = input("Enter your choice (1/2): ").strip()
        if choice == "1":
            print(f"Compression: the directory to compress is: {input_dir}")
            print(f"Output archive: {output_file}")
            compress_project(input_dir, output_file, white_list, black_list, compress_binary)
        elif choice == "2":
            default_archive = os.path.join(input_dir, "text-compressed-project.txt")
            archive = input(f"Enter the path of the archive file to decompress (default: {default_archive}): ").strip()
            if archive == "":
                archive = default_archive
            output_dir = input(f"Enter the destination directory (default: {base_path}): ").strip()
            if output_dir == "":
                output_dir = base_path
            decompress_project(archive, output_dir)
        else:
            print("Invalid choice. Exiting.")
    
    elif mode_choice == "2":
        default_config = os.path.join(base_path, "text-compressor-config.ini")
        config_path = input(f"Enter the path of the configuration file (default: {default_config}): ").strip()
        if config_path == "":
            config_path = default_config
        if not os.path.exists(config_path):
            print(f"The configuration file {config_path} does not exist. A default configuration file will be created.")
            create_default_config(config_path)
        try:
            compress_folder, decompress_folder, output_archive, input_archive, white_list, black_list, compress_binary = read_config(config_path)
        except Exception as e:
            print(f"Error reading configuration file: {e}")
            return
        
        print("Choose the operation to perform:")
        print("1) Compress the project")
        print("2) Decompress an archive")
        choice = input("Enter your choice (1/2): ").strip()
        if choice == "1":
            print(f"Compression: the directory to compress is: {compress_folder}")
            print(f"Output archive: {output_archive}")
            compress_project(compress_folder, output_archive, white_list, black_list, compress_binary)
        elif choice == "2":
            print(f"Decompression: the archive to decompress is: {input_archive}")
            print(f"The project will be restored in: {decompress_folder}")
            decompress_project(input_archive, decompress_folder)
        else:
            print("Invalid choice. Exiting.")
    else:
        print("Invalid mode. Exiting.")

if __name__ == "__main__":
    main()
