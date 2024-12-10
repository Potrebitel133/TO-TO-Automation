import sys
from UI import loading , utils

def run():
    try:
        if utils.is_already_running():
            print("Application is already running.")
            sys.exit(1)
        loading.launch_main()
    finally:
        utils.release_lock()
    
if __name__ == "__main__":
    run()