import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class SongHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self._last_run_ts = 0.0

    @staticmethod
    def _is_pro_path(path):
        return bool(path) and path.lower().endswith(".pro")

    @staticmethod
    def _is_print_pdf_path(path):
        if not path:
            return False
        normalized = path.replace("\\", "/").lower()
        return normalized.endswith(".pdf") and "/print_pdfs/" in normalized

    def _should_run_for_event(self, event):
        if event.is_directory:
            return False

        src_path = getattr(event, "src_path", "")
        dest_path = getattr(event, "dest_path", "")
        return (
            self._is_pro_path(src_path)
            or self._is_pro_path(dest_path)
            or self._is_print_pdf_path(src_path)
            or self._is_print_pdf_path(dest_path)
        )

    def _debounced_run_generator(self):
        now = time.time()
        if now - self._last_run_ts < 0.4:
            return
        self._last_run_ts = now
        self.run_generator()

    def on_modified(self, event):
        if self._should_run_for_event(event):
            self._debounced_run_generator()

    def on_created(self, event):
        if self._should_run_for_event(event):
            self._debounced_run_generator()

    def on_moved(self, event):
        if self._should_run_for_event(event):
            self._debounced_run_generator()

    # VS Code often saves using temp file writes and close events.
    def on_closed(self, event):
        if self._should_run_for_event(event):
            self._debounced_run_generator()

    def run_generator(self):
        print("Zjištěna změna v 'songs/'. Aktualizuji songs.json...")
        try:
            subprocess.run(
                ["python3", "generate_json.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                check=True,
            )
            print("songs.json aktualizován.")
        except subprocess.CalledProcessError as exc:
            print(f"Chyba při generování songs.json (exit {exc.returncode}).")


if __name__ == "__main__":
    songs_path = "songs/"
    print_pdfs_path = "print_pdfs/"
    event_handler = SongHandler()
    observer = Observer()
    observer.schedule(event_handler, songs_path, recursive=False)
    if os.path.isdir(print_pdfs_path):
        observer.schedule(event_handler, print_pdfs_path, recursive=False)

    print(f"Sleduji složky {songs_path} a {print_pdfs_path}... (Ukončíš pomocí Ctrl+C)")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()