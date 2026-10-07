#!/bin/python3

import os
from pathlib import Path
import pathlib
import hashlib
import shutil
from sys import argv
from sys import stdout

dbg = False
verb = False

# =========================================================================
# Архитектура работы:
# 1. Берём текущую директорию
# 2. Создаём карту этой директории
# 3. Берём образцовую директорию
# 4. Создаём карту этой директории
# 5. Показываем карту будущего переноса
# 6. Показываем файлы, которые хз как и куда девать (их нет в ориге или они изменены)
# 7. Начинаем перенос
# 8. Учёт: Checksum -> Name -> size -> homefolder
# 9. Файлы, которые девать некуда - записываем в Syncmover_unknown/...
# 10.Выводим логи по тому, что вообще случилось
# 11.
# 
# 
# 
# 
# =========================================================================

def create_file_map(directory):
    dirs = []
    files = []

    path = Path(directory)

    if not path.exists() or not path.is_dir():
        _log_error(f"[ERR] Dir '{directory}' not found")
        return dirs, files
    
    for i in path.rglob('*'):
        if i.is_file():
            dirs.append(str(i.parent))
            files.append(i.name)
    return dirs, files

def print_tree(folders, files, rootpath):
    global dbg
    if dbg: print(
        "Entered print_tree...\n"
        f"folders : {folders}\n"
        f"files   : {files}\n"
        f"rootpath: {rootpath}"
    )

    if len(folders) != len(files):
        _log_error("[ERR] Count of files not equal to count of folders")
        return
    
    root = os.path.normpath(rootpath)

    tree = {}
    files_at = {}
    tree[()] = set()

    for folder, file in zip(folders, files):
        try:
            rel = os.path.relpath(folder, root)
        except ValueError:
            continue
        
        if rel == '.':
            parts = ()
        else:
            parts = rel.replace('\\','/')
            parts = tuple(p for p in rel.split('/') if p and p != '.')
        
        if any(p == '..' for p in parts):
            continue

        for i in range(len(parts)):
            parent = parts[:i]
            child = parts[:i+1]
            if parent not in tree:
                tree[parent] = set()
            tree[parent].add(child)
        
        if parts not in files_at:
            files_at[parts] = set()
        files_at[parts].add(file)

    def print_node(node, prefix="", is_last=True, is_root=False):
        global dbg
        global verb
        # Определение иконки
        if node == ():
            name = os.path.basename(root) or root
            icon = "📁 "
        else:
            name = node[-1]
            icon = "📁 " if node in tree else ""
        
        # Формирование префикса для текущей строки
        if is_root and (dbg or verb):
            print(f"{icon}{name}")
        else:
            marker = "└── " if is_last else "├── "
            print(f"{prefix}{marker}{icon}{name}")
        
        children_folders = sorted(tree.get(node, ()))
        children_files = sorted(files_at.get(node, ()))
        total = len(children_folders) + len(children_files)
        next_prefix = "" if is_root else (prefix + ("    " if is_last else "│   "))
        
        idx = 0
        for child in children_folders:
            idx += 1
            print_node(child, next_prefix, idx == total, False)
        
        for f in children_files:
            idx += 1
            marker = "└── " if is_last else "├── "
            # Если у узла есть потомки, уходим в рекурсию
            if node:
                full_rel = "/".join(node) + "/" + f
            else:
                full_rel = f
            print(f"{next_prefix}{marker} {full_rel}")
    if dbg == True or verb == True:
        print_node(())

def get_sha256(file_path: pathlib.Path) -> str:
    hashsh = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            hashsh.update(byte_block)
    return hashsh.hexdigest()

def _log_error(msg: str) -> None:
    global dbg
    if dbg:
        print("\n",msg)
def _log_skip (msg: str) -> None:
    global dbg
    if dbg:
        print("\n",msg)

def precheck(source, dest, files, file_mirror, dirmir):
    global dbg
    chk = True
    file = source / files
    mirfile = dirmir / file_mirror
    if dbg: print("f:",file, "||m:", mirfile)
    # Check does files are equal
    if not files == file_mirror:
        _log_error("[ERR] Files has different names")
        chk = False

    # Check existing of first file
    if not file.exists():
        _log_error("[ERR] Beginning file not found")
        chk = False
    if not file.is_file():
        _log_error("[ERR] This is not file")
        chk = False

    # Check existing of mirroring file
    if not mirfile.exists():
        _log_error("[ERR] Mirroring file not found")
        chk = False
    if not mirfile.is_file():
        _log_error("[ERR] Mirroring file is not file")

    # Try to get size of file
    sz = None; sz2 = None
    try:
        sz = file.stat().st_size
    except OSError:
        _log_error(f"[ERR] Can't get size of {file}")
        chk = False
    try:
        sz2 = mirfile.stat().st_size
    except OSError:
        _log_error(f"[ERR] Can't get size of {mirfile}")
        chk = False
    if sz != sz2 or sz == None or sz2 == None:
        _log_error("[ERR] Files sizes are not equal")
        chk = False
    
    # Check existing of source directory
    if not source.is_dir():
        _log_error(f"[ERR] Home directory not exist: {source}")
        chk = False
    # Check existing of mirroring directory
    if not dirmir.is_dir():
        _log_error(f"[ERR] Mirroring directory not exist: {dirmir}")
        chk = False
        
    # Check existing of dest directory
    if not dest.is_dir():
        chk = False
        _log_error(f"[ERR] Destination dir not exist: {dest}")

    return chk

def aftercheck(final_file, src_file_name, src_size, src_hash):
    global dbg
    if dbg: print("Enterint aftercheck module")
    
    chk = True
    if not final_file.is_file():
        _log_error(f"[ERR] File missing at destination: {final_file}")
        chk = False
    
    if final_file.name != src_file_name:
        _log_error(f"[ERR] Name mismatch: {final_file.name} != {src_file_name}")
        chk = False

    if final_file.stat().st_size != src_size:
        _log_error(
            f"[ERR] Size mismatch: {final_file}"
            f"expected {src_size}, got {final_file.stat().st_size}"            
        )
        chk = False

    try:
        dest_hash = get_sha256(final_file)
    except OSError as exc:
        _log_error(f"[ERR] Cant get destination {final_file}")
        chk = False
    
    if dest_hash != src_hash:
        _log_error(f"[ERR] Hashes not equal: src {src_hash} | dest {dest_hash}")
        chk = False
    return chk

def progress_bar(now, total, length=30):
    global verb
    global dbg
    percent = (now / total) * 100
    filled = int(length * now // total)
    bar = '█' * filled + '-' * (length - filled)
    if dbg:
        stdout.write(f'\033[s\n\r\033[K[{bar}] {round(percent*100)/100}%\n\033[u')
    elif verb:
        stdout.write(f'\r[{bar}] {round(percent*100)/100}%\n\033[F')
    stdout.flush()

def move(source_dirs, mirr_dirs, source_files, mirr_files, dest, mirror_src):
    global dbg
    global verb
    """
    Попарный перенос:
      - (source_dirs[i], source_files[i])  — источник
      - (mirr_dirs[j], mirr_files[j]) — зеркало
      - dest -- Конечная папка переноса
      - связь между ними по ИМЕНИ: src_files[i] == mirror_files[j]

    dest_file = dest_dir / <имя зеркальной директории j> / src_files[i]

    Сообщаем отдельно:
      • если для src_files[i] НЕ нашлось ни одного mirror_files[j]
        — «некуда перемещать»;
      • если для mirror_files[j] НЕ нашлось ни одного src_files[i]
        — «в конечном адресе есть файл, которого нет в исходной».
    """
    if verb:
        print("Entered Move")
    if dbg:
        print("Entered MOVE")
        print(f"first Source dir: {str(source_dirs[0])}")
        print(f"first Mirror dir: {str(mirr_dirs[0])}")
        print(f"destination root: {str(dest)}")
        print()
    
    dest = Path(dest)
    if not dest.is_dir():
        _log_error(f"[ERR] Directory not exists: {dest}")
        try:
            _log_skip(f"[SKIP] Trying to create directory")
            dest.mkdir(parents=True, exist_ok=True)
        except:
            _log_error("[ERR] Error due creating directory")
            return
        if not dest.is_dir():
            _log_error("[ERR] Destination dir not exist")
            return

    if dbg or verb: print("Check does lengths equal...")
    if len(source_dirs) != len(source_files):
        _log_error("[ERR] Count of source directories adresses are not equal with count of source files")
        return
    if len(mirr_dirs) != len(mirr_files):
        _log_error("[ERR] Count of mirror directories adresses are not equal with count of mirror files")
        return

    if dbg or verb: print("Creating mirror map...")
    mirror_index: dict[str, list[int]] = {}
    for j, name in enumerate(mirr_files):
        mirror_index.setdefault(name, []).append(j)
    if dbg: print(f"Mirror_indexes: {mirror_index}\n")

    # Использованные записи зеркал
    used_mirrors = set()
    used_sources = set()

    #mirrors_set = set(mirr_files)

    if dbg or verb: print("[MAIN]\tEnter source dir loop...")
    # i - число, source_directory - директория
    for i, source_directory in enumerate(source_dirs):
        progress_bar(i, len(source_dirs))
        source = Path(source_dirs[i])
        file = source_files[i]
        src_addr = source / file
        
        if dbg:
            print(
                f"\033[K  i          = {i}\n"
                f"  source_dir = {source_directory}\n"
                f"  file       = {file}\n"
                f"  merged     = {src_addr}\n"
            )

        # Индекс файла в словаре зеркал
        candidate = mirror_index.get(file)
        if not candidate:
            _log_skip(
                f"[SKIP] No mirroring destination for {source_directory}" 
                f"(source: {src_addr})"
            )
            continue
        if dbg:
            print(f"  index = {candidate[0]}, src_file = {file}\n")
        # moved - status of move of file
        moved = False
        for j in candidate:
            dirmir = Path(mirr_dirs[j])
            file_mirror = mirr_files[j]
            relative_path = dirmir.relative_to(mirror_src)

            destination_dir = dest / relative_path
            final_file = destination_dir / file
            

            if not destination_dir.is_dir():
                _log_error(f"[ERR] Directory not exists: {destination_dir}")
                try:
                    _log_skip(f"[SKIP] Trying to create directory")
                    destination_dir.mkdir(parents=True, exist_ok=True)
                except:
                    _log_error("[ERR] Error due creating directory")
                    return
                if not destination_dir.is_dir():
                    _log_error("[ERR] Destination dir still not exist\nUNKNOWN ERROR")
                    return


            if dbg:
                print(
                    f"  j = {j}\n"
                    f"  relat...path ={relative_path}\n"
                    f"  dest..._dir  = {destination_dir}\n"
                    f"  mirror_dir   = {dirmir}\n"
                    f"  file_mirr    = {file_mirror}\n"
                    f"  destination  = {destination_dir}\n"
                    f"  final_file   = {final_file}\n"
                )
            '''
            if verb: print(
                f"  source file: {src_addr}"
                f"  mirror file: {file_mirror}"
                f"  final  file: {final_file}"
                )
            '''
            if dbg: print("Entering Precheck module...")
            # Предварительная проверка
            # source           - Папка с файлом
            # destination_dir  - Конечная папка
            # file             - Файл источника
            # file_mirror      - Файл зеркала
            # dirmir           - Папка зеркала
            if not precheck(source, destination_dir, file, file_mirror, dirmir):
                continue
            if dbg: print("Precheck passed successfully")

            # Скип в случае нахождения совпадения
            if final_file.exists():
                _log_skip(f"[SKIP] Destination has unknown file: {final_file}")
                continue

            # Смотрим файл до переноса
            try:
                src_size = src_addr.stat().st_size
                src_hash = get_sha256(src_addr)
                if dbg: print(f"source: {src_size}, hash: {src_hash}")
                mir_size = (dirmir / file_mirror).stat().st_size
                mir_hash = get_sha256(dirmir / file_mirror)
                if dbg: print(f"mirror: {mir_size}, hash: {mir_hash}")

                if src_size != mir_size:
                    _log_skip(f"[SKIP] size are not same: {src_size} || {mir_size}")
                if src_hash != mir_hash:
                    _log_skip(f"[SKIP] hash are not equal: {src_hash} || {mir_hash}")

            except OSError as exc:
                _log_error(f"[ERR] Cant read source {src_addr}: {exc}")
                continue
            
            #
            #
            #
            #
            # Перенос файла
            try:
                c = 0
                #print("POTENTIONALLY FILE IS MOVED")
                shutil.move(str(src_addr), str(final_file))
            except (OSError, shutil.Error) as exc:
                _log_error(f"[ERR] Move failed: {src_addr} -> {final_file} | {exc}")
                continue
            
            #
            #
            # final_file - Конечный адрес файла
            # file       - Имя файла, который переносился
            # src_size   - Размер исходного файла
            # src_hash   - Хэш исходного файла
            # AFTERCHECK - проверяет корректность файла после переноса
            
            if not aftercheck(final_file, file, src_size, src_hash):
                _log_skp(f"[SKIP] Some of final data not complain")
            

            if dbg or verb: print(f"{i+1}   {src_addr} ---> {final_file}")
            used_mirrors.add(j)
            used_sources.add(i)
            moved = True
            break
        
        if not moved and candidate:
            _log_skip(f"[SKIP] No valid destination for {source_directory}")
        
    progress_bar(len(source_dirs), len(source_dirs))
    
    # Список файлов, которые не были найдены в зеркале
    print(f"\nDestination has file not found in source (if next is empty, everything is okay): ")
    for j, file_mirror in enumerate(mirr_files):
        if j in used_mirrors:
            continue
        if file_mirror not in set(source_files):
            print(f"- {Path(mirr_dirs[j]) / file_mirror}")

    print(f"\nSource files has not been moved (if next is empty, everything is okay):")
    # Список файлов, которые не были перемещены из источника
    for j, file_source in enumerate(source_files):
        if j in used_sources:
            continue
        if file_source not in set(mirr_files):
            print(f"- {Path(source_dirs[i]) / file_source}")

    print("Move is finished")
    return





def main(args):
    global dbg
    global verb
    chk = False
    # Comandlette 
    if '-h' in args:
        print(
            "Usage: python3 syncmover.py /source /mirror /destination\n"
            "Usage: python3 syncmover.py /mirror /destination\n"
            "Usage: python3 syncmover.py -d /source /mirror /destination\n"
            "Usage: python3 syncmover.py -d /mirror /destination\n"
            "Example: python3 syncmover.py -d /media/usb /home/user1 /home/user2/Downloads\n"
            "                                   home       mirror         destination     \n"

            "\nScript works using standard libraries of python and do not require to install anything instead of python\n"
            "-h - help      . Print this menu\n"
            "-d - debug mode. Print most of possible data\n"
            "-v - verbose   . Print some of additive data (less than debug)\n"
            "Priority: -h > -d > -v\n"
            )
        return
    if ['-d'] in args or dbg:
        for i in range(len(args)):
            print(f"args[{i}] = {args[i]}")
    if '-d' in args or dbg:
        for i in range(len(args)):
            print(f"args[{i}] = {args[i]}")
    #if ['-v'] and ['-d'] in args:
    #    args.remove("-v")
    #if '-v' and '-d' in args:
    #    args.remove('-v')

    # Чек аргументов
    if len(args) < 3:
        print("Usage: python3 syncmover.py /source /mirror /destination")
        print("Usage: python3 syncmover.py /mirror /destination    (source = ./)")
        print("Usage: python3 syncmover.py -d /source /mirror /destination")
        print("Usage: python3 syncmover.py -d /mirror /destination    (source = ./)")
        return
    if len(args) == 3:
        home_directory = os.getcwd()
        mirror_directory = args[1]
        dest_directory = args[2]
    if len(args) == 4:
        if args[1] == '-d' or args[1] == '-v' or args[1] == ['-d'] or args[1] == ['-v']:
            if args[1] == '-d' or args[1] == ['-d']: dbg = True
            if args[1] == '-v' or args[1] == ['-v']: verb = True
            home_directory = os.getcwd()
            mirror_directory = args[2]
            dest_directory = args[3]    
        elif '-d' in args:
            print("Usage: python3 syncmover.py -d /source /mirror /destination")
            print("Usage: python3 syncmover.py -d /mirror /destination")
            return
        else:
            home_directory = args[1]
            mirror_directory = args[2]
            dest_directory = args[3]
            
    if len(args) == 5:
        if '-d' in args:
            dbg = True
        if '-v' in args:
            verb = True
        home_directory = args[2]
        mirror_directory = args[3]
        dest_directory = args[4]
    for i in args:
        try:
            if i != "-d":
                Path(i)
        except (TypeError, ValueError):
            print(f"Unknown format: {i}")
            return

    if dbg or chk or verb:
        print(
            f"  Home  : {home_directory}\n"
            f"  Mirror: {mirror_directory}\n"
            f"  Dest  : {dest_directory}\n"
            )
        if chk:
            print("Script is ready to normal run")
            return
    print(f"Debug = {dbg}, Verbose = {verb}")

    # Текущая директория
    #home_directory = os.getcwd()
    # Директория, с которой берём слепок
    #mirror_directory = "/media/bland/Shared/Uni/test/"
    # Директория, куда всё складываем
    # Analysis
    #dest_directory = "/home/bland/Downloads/test-dest"
    if dbg or verb:
        print(f"Exploring home folder:\n{home_directory}")
    directories, files = create_file_map(home_directory)
    if dbg or verb:
        print(f"Files found: {len(files)}")
        print_tree(directories, files, str(home_directory))

    # Analysis of mirroring directory
    if dbg or verb:
        print(f"Exploring mirror directory:\n{mirror_directory}")
    mirror_dirs, mirr_files = create_file_map(mirror_directory)
    if dbg or verb:
        print(f"Files found: {len(mirr_files)}")
        print_tree(mirror_dirs, mirr_files, str(mirror_directory))

    
    if dbg:
        print("\nSources")
        for i in range(len(directories)):
            print(f"{i} dir  {directories[i]} {files[i]}")
        print("\nMirrors")
        for i in range(len(mirror_dirs)):
            print(f"{i} mdir {mirror_dirs[i]}, {mirr_files[i]}")

    # MOVE
    move(directories, mirror_dirs, files, mirr_files, dest_directory, mirror_directory)
    

    


if __name__ == "__main__":
    main(argv)
