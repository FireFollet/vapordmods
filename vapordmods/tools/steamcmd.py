import logging
import subprocess
import os
import re
import asyncio
from builtins import staticmethod


class SteamCMD:

    def __init__(self, steamcmd_exec):
        self.steamcmd_running = False

        if os.path.exists(steamcmd_exec):
            if os.access(steamcmd_exec, os.X_OK):
                if os.path.basename(steamcmd_exec).lower().startswith('tools'):
                    self.steamcmd_exec = steamcmd_exec
                else:
                    raise FileNotFoundError(f"The file '{steamcmd_exec}' doesn't seems to be a tools execution file.")
            else:
                raise PermissionError(f"The current user cannot execute the file '{steamcmd_exec}'.")
        else:
            raise FileNotFoundError(f"The file '{steamcmd_exec}' is not found.")

    @staticmethod
    def __execute_process(args: list, timeout: int = 180):
        proc = subprocess.run(args, capture_output=True, timeout=timeout)
        return proc

    def build_base_args(self, username: str, password: str,  steam_guard_code: str = None):
        args = [
            self.steamcmd_exec,
            '+login',
        ]

        if username.lower() in ['', 'anonymous']:
            args.append('anonymous')
        else:
            args.append(username)
            args.append(password)

        if steam_guard_code:
            args.append(steam_guard_code)

        return args

    async def execute_steamcmd(self, steam_args: list):
        if self.steamcmd_running:
            logging.info(f"Cannot execute the function 'update_workshop_mods' beacause tools is already running.")
            return 1

        try:
            self.steamcmd_running = True
            result = await asyncio.get_running_loop().run_in_executor(None, self.__execute_process, steam_args)
        finally:
            self.steamcmd_running = False

        return result

    async def update_workshop_mods(self, username: str, password: str, app_id: str, published_file_id: str, steam_guard_code: str = None):
        args = self.build_base_args(username, password, steam_guard_code)

        args.append('+workshop_download_item')
        args.append(app_id)
        args.append(published_file_id)
        args.append('+quit')

        result = await self.execute_steamcmd(args)

        if result.returncode == 0:
            regex = re.search('Success. Downloaded item.*"(.*)"', result.stdout.decode())
            if regex:
                return 0, regex.groups()[0]
            else:
                return 0, ''
        else:
            return result.returncode, result.stderr.decode()
