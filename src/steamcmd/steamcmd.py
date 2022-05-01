import subprocess
import os
import re
from builtins import staticmethod
#

class SteamCMD:

    def __init__(self, steamcmd_exec):
        if os.path.exists(steamcmd_exec):
            if os.access(steamcmd_exec, os.X_OK):
                if os.path.basename(steamcmd_exec).lower().startswith('steamcmd'):
                    self.steamcmd_exec = steamcmd_exec
                else:
                    raise FileNotFoundError(f"The file '{steamcmd_exec}' doesn't seems to be a steamcmd execution file.")
            else:
                raise PermissionError(f"The current user cannot execute the file '{steamcmd_exec}'.")
        else:
            raise FileNotFoundError(f"The file '{steamcmd_exec}' is not found.")

    @staticmethod
    def execute_cmd(args: list, timeout: int = 180):
        proc = subprocess.run(args, capture_output=True, timeout=timeout)
        return proc

    def update_workshop_mods(self, username: str, password: str, app_id: str, published_file_id, steam_guard_code: str = None):
        args = [
            self.steamcmd_exec,
            '+login',
            username,
            password,
            '+workshop_download_item',
            app_id,
            published_file_id,
            '+quit'
        ]

        if steam_guard_code:
            args.insert(3, steam_guard_code)

        result = self.execute_cmd(args)
        if result.returncode == 0:
            regex = re.search('Success. Downloaded item.*"(.*)"', result.stdout.decode())
            if regex:
                return 0, regex.groups()[0]
            else:
                return 0, ''
        else:
            return result.returncode, result.stderr.decode()
