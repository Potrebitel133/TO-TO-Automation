#!/usr/bin/env python
import sys
from UI import loading , utils

def run():
    lock = utils.LockFileManager()
    try:
        if lock.is_already_running():
            print("Application is already running.")
            sys.exit(1)
        loading.launch_main()
    finally:
        lock.release_lock()
    
if __name__ == "__main__":
    run()