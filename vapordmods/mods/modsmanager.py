import steam.monkey
steam.monkey.patch_minimal()
import asyncio
import aiofiles
import aiofiles.os
import os
import aiohttp
import yaml
import logging
import zipfile
import pandas as pd
from cerberus import Validator
from pathlib import Path
from vapordmods.api import worhshop, thunderstore, nexusmods
from vapordmods.mods.schema import schema
from vapordmods.tools.steamcmd import SteamManager


logger = logging.getLogger(__name__)


class ModsManager:
    _CFG_FILENAME = 'vapordmods.yml'
    _MANIFESTS_FILENAME = 'vapordmods.manifests'
    _THUNDERSTORE_NAME = 'thunderstore'
    _NEXUSMODS_NAME = 'nexusmods'
    _WORKSHOP_NAME = 'workshop'

    def __init__(self, install_dir: str,
                 web_api_key: str = None,
                 steam_username: str = None,
                 steam_password: str = None,
                 steam_guard: str = None,
                 two_factor_code: str = None):
        self.install_dir = install_dir
        self.web_api_key = web_api_key
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.steam_guard = steam_guard
        self.two_factor_code = two_factor_code
        self.manifests_filename = os.path.join(install_dir, self._MANIFESTS_FILENAME)
        self.cfg_filename = os.path.join(install_dir, self._CFG_FILENAME)
        self.cfg_data = {}
        self.mods_info = {}
        self.mods_status = {}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        if not os.path.exists(self.install_dir):
            raise NotADirectoryError(f"The installdir {self.install_dir} doesn't exist.")

        if not os.path.exists(self.cfg_filename) and not os.access(self.install_dir, os.W_OK):
            raise PermissionError(f"Cannot write to the folder {self.install_dir }.")

        if not os.path.exists(self.cfg_filename):
            loop.run_until_complete(self.write_cfg_filename())

    async def write_cfg_filename(self):
        template = b'config:\n  default_mods_dir: \n\nmods:\n  - provider: \n    app: \n    mods: \n    version: \n' \
                   b'    \n  - provider:             \n    app:       \n    mods:              \n    version: \n'
        async with aiofiles.open(self.cfg_filename, 'wb') as cfg_file:
            await cfg_file.write(template)

    @staticmethod
    async def __load_yaml(filename):
        if os.path.exists(filename):
            async with aiofiles.open(filename, 'r') as file:
                return yaml.safe_load(await file.read())
        else:
            raise FileExistsError(filename)

    async def load_cfg_data(self):
        cfg_data = await self.__load_yaml(self.cfg_filename)
        mods_validator = Validator(schema)

        if not mods_validator.validate(cfg_data):
            raise KeyError(mods_validator.errors)
        self.cfg_data = cfg_data

        if self.cfg_data['config']['default_mods_dir']:
            self.default_mods_dir = self.cfg_data['config']['default_mods_dir']
        else:
            self.default_mods_dir = self.install_dir

    async def load_mods_info(self):
        if os.path.exists(self.manifests_filename):
            self.mods_info = await self.__load_yaml(self.manifests_filename)

    def get_mods_info(self):
        return self.mods_info

    def get_mods_status(self):
        return self.mods_status

    async def refresh_mods_info(self, nmods_api_key: str = None, steam_api_key: str = None):
        try:
            suffixes = '_current'
            await self.load_cfg_data()
            self.mods_info = {}
            await self.load_mods_info()

            df_cfg = pd.DataFrame.from_dict(self.cfg_data['mods'])
            for col in ['version', 'mods_dir']:
                if col not in df_cfg.columns:
                    df_cfg[col] = ''

            df_cfg.loc[((df_cfg['mods_dir'] == '') | (df_cfg['mods_dir'] is None)), 'mods_dir'] = self.default_mods_dir
            df_cfg = df_cfg.fillna('')

            # Requests mods update
            mods_update = []
            apicall = None
            list_api_key = {self._THUNDERSTORE_NAME: None, self._NEXUSMODS_NAME: nmods_api_key, self._WORKSHOP_NAME: steam_api_key}
            for idx, row in df_cfg.iterrows():
                apicall = getattr(globals()[row['provider']], row['provider'])()
                if await apicall.get_update(row['app'], row['mods'], row['mods_dir'], row['version'], list_api_key[row['provider']]) == 0:
                    mods_update.append(apicall.return_data())

            df_update = pd.DataFrame(mods_update)
            df_update['need_update'] = False

            if len(self.mods_info) > 0:
                df_current = pd.DataFrame(self.mods_info)
                df_status = df_update.merge(df_current, on=['provider', 'app', 'mods'], suffixes=(None, suffixes))
                df_status['need_update'] = df_status['version'] != df_status[f'version{suffixes}']
            else:
                df_status = df_update
                df_status['need_update'] = True

            self.mods_status = df_status.filter(items=df_update.columns.to_list()).to_dict()
            return 1
        except Exception as er:
            logger.error(f"Error during update for mods: {er}")
            return 0

    @staticmethod
    async def __extract_mods(filename, destination):
        with zipfile.ZipFile(filename, 'r') as file:
            try:
                file.extractall(destination)
                return 1
            except Exception as er:
                logger.error(er)
                return 0

    async def __make_request(self, session, row):
        try:
            resp = await session.request(method="GET", url=row['download_url'])

            if resp.status == 200:
                if not await aiofiles.os.path.exists(row['mods_dir']):
                    await aiofiles.os.makedirs(row['mods_dir'], exist_ok=True)

                filename = os.path.join(row['mods_dir'], resp.url.name)
                destination = os.path.join(row['mods_dir'], row['full_mods_name'])
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await self.__extract_mods(filename, destination) == 1:
                    await aiofiles.os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if len(self.mods_status) == 0:
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
            return 0

        try:
            list_to_update = pd.DataFrame.from_dict(self.mods_status).query(f"need_update == True & provider in "
                                                                            f"['{self._THUNDERSTORE_NAME}',"
                                                                            f"'{self._NEXUSMODS_NAME}']")
            if not list_to_update.empty:
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for idx, row in list_to_update.iterrows():
                        tasks.append(self.__make_request(session, row))

                    await asyncio.gather(*tasks)

            list_to_update_workshop = pd.DataFrame.from_dict(self.mods_status).query(f"need_update == True & "
                                                                                     f"provider == '{self._WORKSHOP_NAME}'")
            if not list_to_update_workshop.empty:
                steam_update = SteamManager(web_api_key=self.web_api_key,
                                            username=self.steam_username,
                                            password=self.steam_password,
                                            steam_guard_code=self.steam_guard,
                                            two_factor_code=self.two_factor_code
                                            )
                for idx, row in list_to_update_workshop.iterrows():
                    result = await steam_update.update_worksop_mod(row['app'], row['mods'])
                    if result == 1 and result(1):
                        Path(result(1)).symlink_to(os.path.join(row['mods_dir'], row['title']))
                    elif result == 1:
                        logger.error(f"The symlink for the APP_ID {row['app']} and published_file_id {row['mods']} was note created.")
                    else:
                        logger.error(result(1))

            with open(self.manifests_filename, 'w') as manifest:
                yaml.safe_dump(self.mods_status, manifest)

            return 1
        except Exception as er:
            logger.error(er)
            return 0
