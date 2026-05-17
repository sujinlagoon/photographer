import time

from backend.app.core.config import settings

from backend.app.services.sync_service import (
    FolderWatcher
)


def start_folder_watcher():

    watcher = FolderWatcher(
        settings.WATCH_FOLDER
    )

    watcher.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        watcher.stop()