import asyncio
import aiofiles
import os
import aiohttp
import yaml
import logging
import zipfile
from cerberus import Validator
import pandas as pd
from src.api import thunderstore, nexusmods

logger = logging.getLogger(__name__)


class VapordMods:
    __CFG_FILENAME = 'vapordmods.yml'
    __MANIFESTS_FILENAME = 'vapordmods.manifests'
    __THUNDERSTORE_NAME = 'thunderstore'
    __NEXUSMODS_NAME = 'nexusmods'
    __WORKSHOP_NAME = 'workshop'

    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.manifests_filename = os.path.join(install_dir, self.__MANIFESTS_FILENAME)
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.cfg_data = {}
        self.mods_info = {}
        self.mods_status = {}

        asyncio.run(self.set_cfg_data())

        if self.cfg_data['config']['default_mods_dir']:
            self.default_mods_dir = self.cfg_data['config']['default_mods_dir']
        else:
            self.default_mods_dir = install_dir

        if not os.path.exists(self.cfg_filename):
            raise PermissionError(f"Cannot create or read '{self.cfg_filename}'.")

        if not (os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK)):
            raise PermissionError(f"'{self.cfg_filename}' is not a file or cannot be read.")
        elif os.path.exists(install_dir):
            asyncio.run(self.write_cfg_filename())

    async def write_cfg_filename(self):
        template = b'config:\n  default_mods_dir: \n\nmods:\n  - provider: \n    app: \n    mods: \n    version: \n' \
                   b'    \n  - provider:             \n    app:       \n    mods:              \n    version: \n'
        async with aiofiles.open(self.cfg_filename, 'wb') as cfg_file:
            await cfg_file.write(template)

    @staticmethod
    async def __load_yaml__(filename):
        if os.path.exists(filename):
            with aiofiles.open(filename, 'r') as file:
                return yaml.safe_load(await file.read())
        else:
            raise FileExistsError(filename)

    async def set_cfg_data(self):
        cfg_data = await self.__load_yaml__(self.cfg_filename)
        async with aiofiles.open('./src/schema', 'r') as schema:
            mods_validator = Validator(eval(await schema.read()))

        if not mods_validator.validate(cfg_data):
            raise KeyError(mods_validator.errors)
        self.cfg_data = cfg_data

    async def set_mods_info(self):
        if os.path.exists(self.manifests_filename):
            self.mods_info = await self.__load_yaml__(self.manifests_filename)

    def get_mods_info(self):
        return self.mods_info

    def get_mods_status(self):
        return self.mods_status

    async def refresh_mods_info(self, nmods_api_key: str = None, steam_api_key: str = None):
        try:
            suffixes = '_current'
            await self.set_cfg_data()
            await self.set_mods_info()

            df_cfg = pd.DataFrame.from_dict(self.cfg_data['mods'])
            for col in ['version', 'mods_dir']:
                if col not in df_cfg.columns:
                    df_cfg[col] = ''

            df_cfg.loc[((df_cfg['mods_dir'] == '') | (df_cfg['mods_dir'] is None)), 'mods_dir'] = self.default_mods_dir

            # Requests mods update
            mods_update = []
            apicall = None
            list_api_key = {self.__THUNDERSTORE_NAME: None, self.__NEXUSMODS_NAME: nmods_api_key, self.__WORKSHOP_NAME: steam_api_key}
            for idx, row in df_cfg.iterrows():
                apicall = getattr(globals()[row['provider']], row['provider'])()
                if await apicall.get_update(row['app'], row['mods'], row['mods_dir'], row['version'], list_api_key[row['provider']]) == 0:
                    mods_update.append(apicall.return_data())

            df_update = pd.DataFrame(mods_update)
            df_update['need_update'] = False

            if len(self.mods_info) > 0:
                df_current = pd.DataFrame(self.mods_info)
                df_status = df_update.merge(df_current, on=['provider', 'app', 'mods'], suffixes=(None, suffixes))
            else:
                df_status = df_update

            df_status['need_update'] = df_status['version'] != df_status[f'version{suffixes}']

            self.mods_status = df_status.filter(items=df_update.columns.to_list()).to_dict()
            return 0
        except Exception as er:
            logger.error(f"Error during update for mods: {er}")
            return 1

    @staticmethod
    def __extract_mods__(filename, destination):
        with zipfile.ZipFile(filename, 'r') as file:
            try:
                file.extractall(destination)
                return 0
            except Exception as er:
                logger.error(er)
                return 1

    async def __make_request__(self, session, row):
        try:
            resp = await session.request(method="GET", url=row['download_url'])

            if resp.status == 200:
                if not os.path.exists(row['mods_dir']):
                    os.makedirs(row['mods_dir'], exist_ok=True)

                filename = os.path.join(row['mods_dir'], resp.url.name)
                destination = os.path.join(row['mods_dir'], row['full_mods_name'])
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await asyncio.get_running_loop().run_in_executor(None, self.__extract_mods__, filename, destination) == 0:
                    os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if len(self.mods_status) == 0:
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
            return 1

        try:
            list_to_update = pd.DataFrame.from_dict(self.mods_status).query('need_update == True')
            if list_to_update is not None:
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for idx, rows in list_to_update.iterrows():
                        tasks.append(self.__make_request__(session, rows))

                    await asyncio.gather(*tasks)
                with open(self.manifests_filename, 'w') as manifest:
                    yaml.safe_dump(self.mods_status, manifest)
            return 0
        except Exception as er:
            logger.error(er)
            return 1
