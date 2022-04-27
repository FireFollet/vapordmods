import asyncio
import os


class SteamCMD:

    def __init__(self, steamcmd_exec):
        if os.path.exists(steamcmd_exec):
            if os.access(steamcmd_exec, os.X_OK):
                if os.path.basename(steamcmd_exec).lower().startswith('steamcmd'):
                    self.steamcmd_exec = steamcmd_exec
                else:
                    raise Exception(f"The file {steamcmd_exec} doesn't seems to be a steamcmd execution file.")
            else:
                raise PermissionError(f"The current user cannot execute the file {steamcmd_exec}.")
        else:
            raise FileNotFoundError(f"The file {steamcmd_exec} is not found.")

    async def execute_cmd(self, args: list):
        proc = await asyncio.create_subprocess_exec(self.steamcmd_exec, *args)
        await proc.wait()
        return proc.returncode

    async def update_workshop_mods(self, username: str, password: str, app_id: str, published_file_id, steam_guard_code: str = None):
        args = [
            '+login',
            username,
            password,
            'workshop_download_item',
            app_id,
            published_file_id,
            '+quit'
        ]

        if steam_guard_code:
            args.insert(3, steam_guard_code)

        return await self.execute_cmd(args)
