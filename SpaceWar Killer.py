import os
import string
import threading
import queue
import time
import msvcrt
import sys
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# ===== Global Settings =====
settings = {
    "multithreaded": True,
    "max_threads": 4,
}

results = []
results_lock = threading.Lock()
print_lock = threading.Lock()
RECYCLE_BIN_NAMES = {"$recycle.bin", "recycler"}

spinner_cycle = ['|', '/', '-', '\\']

# ===== Colored ASCII Banner =====
ASCII_BANNER = (
    Fore.RED
    + r"""
 ________  ________  ________  ________  _______   ___       __   ________  ________          ___  __    ___  ___       ___       _______   ________     
|\   ____\|\   __  \|\   __  \|\   ____\|\  ___ \ |\  \     |\  \|\   __  \|\   __  \        |\  \|\  \ |\  \|\  \     |\  \     |\  ___ \ |\   __  \    
\ \  \___|\ \  \|\  \ \  \|\  \ \  \___|\ \   __/|\ \  \    \ \  \ \  \|\  \ \  \|\  \       \ \  \/  /|\ \  \ \  \    \ \  \    \ \   __/|\ \  \|\  \   
 \ \_____  \ \   ____\ \   __  \ \  \    \ \  \_|/_\ \  \  __\ \  \ \   __  \ \   _  _\       \ \   ___  \ \  \ \  \    \ \  \    \ \  \_|/_\ \   _  _\  
  \|____|\  \ \  \___|\ \  \ \  \ \  \____\ \  \_|\ \ \  \|\__\_\  \ \  \ \  \ \  \\  \|       \ \  \\ \  \ \  \ \  \____\ \  \____\ \  \_|\ \ \  \\  \| 
    ____\_\  \ \__\    \ \__\ \__\ \_______\ \_______\ \____________\ \__\ \__\ \__\\ _\        \ \__\\ \__\ \__\ \_______\ \_______\ \_______\ \__\\ _\ 
   |\_________\|__|     \|__|\|__|\|_______|\|_______|\|____________|\|__|\|__|\|__|\|__|        \|__| \|__|\|__|\|_______|\|_______|\|_______|\|__|\|__|
    """
    + Fore.MAGENTA
    + r"""                                             By Swan :)                                                                                            
                                                                                                                                                         
                                                                                                                                                          """
    + Style.RESET_ALL
)


# ===== Utilities =====

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def update_fake_app_id(ini_path, new_id):
    try:
        lines = []
        with open(ini_path, 'r', errors='ignore') as f:
            for line in f:
                if line.strip().lower().startswith("fakeappid="):
                    lines.append(f"FakeAppId={new_id}\n")
                else:
                    lines.append(line)
        with open(ini_path, 'w', errors='ignore') as f:
            f.writelines(lines)
        safe_print(
            Fore.GREEN
            + f"\nUpdated FakeAppId in:\n  {ini_path}\n  -> {new_id}"
            + Style.RESET_ALL
        )
    except Exception as e:
        safe_print(Fore.RED + f"Error updating FakeAppId in {ini_path}: {e}" + Style.RESET_ALL)


def process_ini_file(ini_file):
    try:
        real_id = None
        with open(ini_file, "r", errors="ignore") as f:
            for line in f:
                if line.strip().lower().startswith("realappid="):
                    real_id = line.strip().split("=", 1)[1]
                    break
        if real_id:
            with results_lock:
                results.append({"path": ini_file, "realappid": real_id})
    except Exception as e:
        safe_print(Fore.RED + f"Error reading INI file {ini_file}: {e}" + Style.RESET_ALL)


# ===== Scanning =====


def scan_path(path, progress_callback=None):
    folder_count = 0
    try:
        for root, dirs, files in os.walk(path):
            # Skip recycle bin folders
            dirs[:] = [d for d in dirs if d.lower() not in RECYCLE_BIN_NAMES]

            folder_count += 1
            if progress_callback and folder_count % 10 == 0:
                progress_callback(root)

            for file in files:
                if file.lower().startswith("onlinefix") and file.lower().endswith(".ini"):
                    process_ini_file(os.path.join(root, file))

    except Exception as e:
        safe_print(Fore.RED + f"\nError scanning path {path}: {e}" + Style.RESET_ALL)


def worker_thread(q, progress_callback=None):
    while True:
        try:
            path = q.get_nowait()
        except queue.Empty:
            return
        scan_path(path, progress_callback)
        q.task_done()


def threaded_scan(paths, max_threads=4, progress_callback=None):
    q = queue.Queue()
    for p in paths:
        q.put(p)

    threads = []
    for _ in range(min(max_threads, len(paths))):
        t = threading.Thread(target=worker_thread, args=(q, progress_callback))
        t.daemon = True
        t.start()
        threads.append(t)

    q.join()


def get_all_drives():
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:/"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


# ===== Spinner =====


def spinner(message, stop_event, current_folder_container):
    idx = 0
    while not stop_event.is_set():
        folder_display = current_folder_container[0]
        display_msg = (
            f"\r{Fore.YELLOW}{message} {spinner_cycle[idx % len(spinner_cycle)]} "
            + f"{Fore.CYAN}Scanning: {folder_display[:60]}"
            + Style.RESET_ALL
        )
        print(display_msg.ljust(80), end="", flush=True)
        idx += 1
        time.sleep(0.15)
    print("\r" + " " * 80 + "\r", end="", flush=True)


# ===== Results Display & Editing =====


def update_all_fake_app_ids(new_id):
    safe_print(Fore.GREEN + f"\nUpdating all FakeAppId values to {new_id}..." + Style.RESET_ALL)
    with results_lock:
        for entry in results:
            update_fake_app_id(entry["path"], new_id)
    safe_print(Fore.GREEN + "All FakeAppId values updated.\n" + Style.RESET_ALL)


def display_results():
    if not results:
        print(Fore.RED + "\nNo OnlineFix.ini files found." + Style.RESET_ALL)
        input("Press Enter to return to menu...")
        return

    index = 0
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(Fore.CYAN + "Found OnlineFix.ini files:\n" + Style.RESET_ALL)
        with results_lock:
            subset = results[index : index + 9]
            for i, r in enumerate(subset, start=index + 1):
                print(
                    Fore.YELLOW
                    + f"{i}. "
                    + Fore.WHITE
                    + f"{r['path']} | RealAppId: {r['realappid']}"
                    + Style.RESET_ALL
                )

        print()
        print(
            Fore.LIGHTBLACK_EX
            + "[Arrow Keys] Navigate | [Q] Quit listing | [Number] Edit FakeAppId"
            + Style.RESET_ALL
        )
        print(
            Fore.LIGHTBLACK_EX
            + "Type 'all' to change FakeAppId for ALL listed files.\n"
            + Style.RESET_ALL
        )
        print(
            Fore.MAGENTA
            + 'For some reason OnlineFix/SteamworksFix only lets you use free game\'s app ID, so make sure to only use free ones like "1625450" which is Muck.'
            + Style.RESET_ALL
        )

        key = msvcrt.getch()
        if key == b"H":  # Up arrow
            index = max(0, index - 9)
        elif key == b"P":  # Down arrow
            with results_lock:
                if index + 9 < len(results):
                    index += 9
        elif key in (b"q", b"Q"):
            break
        elif key.isdigit():
            num = int(key.decode())
            edit_index = index + num - 1
            with results_lock:
                if 0 <= edit_index < len(results):
                    new_id = input(
                        Fore.GREEN
                        + f"Enter new FakeAppId for {results[edit_index]['path']}: "
                        + Style.RESET_ALL
                    ).strip()
                    if new_id:
                        update_fake_app_id(results[edit_index]["path"], new_id)
        else:
            os.system("cls" if os.name == "nt" else "clear")
            command = input(
                Fore.GREEN
                + "Enter command (number to edit, 'all' to change all, 'q' to quit): "
                + Style.RESET_ALL
            ).strip().lower()
            if command == "q":
                break
            elif command == "all":
                new_id = input(
                    Fore.GREEN
                    + "Enter new FakeAppId to set for ALL listed files: "
                    + Style.RESET_ALL
                ).strip()
                if new_id:
                    update_all_fake_app_ids(new_id)
            elif command.isdigit():
                num = int(command)
                edit_index = index + num - 1
                with results_lock:
                    if 0 <= edit_index < len(results):
                        new_id = input(
                            Fore.GREEN
                            + f"Enter new FakeAppId for {results[edit_index]['path']}: "
                            + Style.RESET_ALL
                        ).strip()
                        if new_id:
                            update_fake_app_id(results[edit_index]["path"], new_id)
            else:
                print(Fore.RED + "Invalid command. Press any key to continue." + Style.RESET_ALL)
                msvcrt.getch()


# ===== Menus =====


def scan_menu():
    results.clear()

    print(Fore.CYAN + "\nChoose scan mode:" + Style.RESET_ALL)
    print("1. Look in one drive only (Unstable, SSD recommended)")
    print("2. Look in all drives (slowest)")
    print( Fore.YELLOW + "3. Look in one specific folder (fastest and most stable)")
    print("4. Look in specific folders on multiple drives (best if games are organized)\n" + Style.RESET_ALL)

    choice = input(Fore.GREEN + "Enter choice (1-4): " + Style.RESET_ALL).strip()

    paths = []
    if choice == "1":
        drive = input(Fore.GREEN + "Enter drive letter (e.g., D:/): " + Style.RESET_ALL).strip()
        if os.path.exists(drive):
            paths.append(drive)
        else:
            print(Fore.RED + f"Drive {drive} does not exist." + Style.RESET_ALL)
            input("Press Enter to return to menu.")
            return

    elif choice == "2":
        paths = get_all_drives()
        if not paths:
            print(Fore.RED + "No drives found." + Style.RESET_ALL)
            input("Press Enter to return to menu.")
            return

    elif choice == "3":
        folder = input(Fore.GREEN + "Enter folder path: " + Style.RESET_ALL).strip()
        if os.path.exists(folder):
            print(
                Fore.YELLOW
                + "\n⚠️ FASTEST OPTION — Make sure all games are in this folder or its subfolders!\n"
                + Style.RESET_ALL
            )
            paths.append(folder)
        else:
            print(Fore.RED + f"Folder {folder} does not exist." + Style.RESET_ALL)
            input("Press Enter to return to menu.")
            return

    elif choice == "4":
        folders_input = input(
            Fore.GREEN + "Enter folder paths separated by commas: " + Style.RESET_ALL
        ).strip()
        folders = [f.strip() for f in folders_input.split(",")]
        valid_folders = []
        for f in folders:
            if os.path.exists(f):
                valid_folders.append(f)
            else:
                print(Fore.RED + f"Folder {f} does not exist and will be skipped." + Style.RESET_ALL)
        if not valid_folders:
            print(Fore.RED + "No valid folders found." + Style.RESET_ALL)
            input("Press Enter to return to menu.")
            return
        paths = valid_folders

    else:
        print(Fore.RED + "Invalid choice." + Style.RESET_ALL)
        input("Press Enter to return to menu.")
        return

    stop_spinner = threading.Event()
    current_folder = [""]

    def progress_cb(folder):
        current_folder[0] = folder

    spinner_thread = threading.Thread(
        target=spinner, args=("Scanning folders...", stop_spinner, current_folder)
    )
    spinner_thread.start()

    if settings["multithreaded"]:
        threaded_scan(paths, max_threads=settings["max_threads"], progress_callback=progress_cb)
    else:
        for p in paths:
            scan_path(p, progress_callback=progress_cb)

    stop_spinner.set()
    spinner_thread.join()
    safe_print(Fore.GREEN + "\nScan complete.\n" + Style.RESET_ALL)

    display_results()


def settings_menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(ASCII_BANNER)
        print(Fore.CYAN + "Settings:\n" + Style.RESET_ALL)
        print(
            Fore.YELLOW
            + f"1. Multithreaded Scanning: {'ON' if settings['multithreaded'] else 'OFF'}"
        )
        print(F"2. Max Threads: {settings['max_threads']}" + Style.RESET_ALL)
        print("\n[Enter number to toggle or change] | [B] Back to menu")

        choice = input(Fore.GREEN + "Choice: " + Style.RESET_ALL).strip().lower()
        if choice == "1":
            settings["multithreaded"] = not settings["multithreaded"]
        elif choice == "2":
            val = input(Fore.GREEN + "Enter max number of threads (1-16): " + Style.RESET_ALL).strip()
            if val.isdigit():
                v = int(val)
                if 1 <= v <= 16:
                    settings["max_threads"] = v
                else:
                    print(Fore.RED + "Value out of range." + Style.RESET_ALL)
                    input("Press Enter to continue.")
            else:
                print(Fore.RED + "Invalid number." + Style.RESET_ALL)
                input("Press Enter to continue.")
        elif choice == "b":
            break
        else:
            print(Fore.RED + "Invalid choice." + Style.RESET_ALL)
            input("Press Enter to continue.")


def main_menu():
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(ASCII_BANNER)
        print(Fore.YELLOW + "1. Start Scan")
        print("2. Settings")
        print("3. Exit" + Style.RESET_ALL)
        print()
        print(
            Fore.LIGHTBLACK_EX
            + "If any bugs arise, please post them here:"
            + Style.RESET_ALL
        )
        print(Fore.LIGHTBLACK_EX + "https://github.com/Swanikins/SpaceWar-Killer\n" + Style.RESET_ALL)

        choice = input(Fore.GREEN + "Enter choice: " + Style.RESET_ALL).strip()
        if choice == "1":
            scan_menu()
        elif choice == "2":
            settings_menu()
        elif choice == "3":
            print(Fore.CYAN + "Goodbye!" + Style.RESET_ALL)
            sys.exit(0)
        else:
            print(Fore.RED + "Invalid choice." + Style.RESET_ALL)
            input("Press Enter to continue.")


if __name__ == "__main__":
    main_menu()
