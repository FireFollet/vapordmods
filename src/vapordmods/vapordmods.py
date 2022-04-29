import asyncio
import aiofiles
import os
import aiohttp
import yaml
import logging
import json
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
    __SWORKSHOP_NAME = 'sworkshop'

    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.manifests_filename = os.path.join(install_dir, self.__MANIFESTS_FILENAME)
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.mods_status: pd.DataFrame = pd.DataFrame()

        if os.path.exists(self.cfg_filename):
            if not (os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK)):
                raise PermissionError(f"'{self.cfg_filename}' is not a file or cannot be read.")
        elif os.path.exists(install_dir):
            with open(self.cfg_filename, 'w') as cfg_file:
                cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__NEXUSMODS_NAME +
                               ':\n\n  ' + self.__SWORKSHOP_NAME + ':\n')
        else:
            raise PermissionError(f"Cannot create or read '{self.cfg_filename}'.")

    async def load_cfg(self):
        if os.path.exists(self.cfg_filename):
            with open(self.cfg_filename, 'r') as cfg_file:
                return yaml.safe_load(cfg_file)
        else:
            raise FileExistsError(self.cfg_filename)

    async def refresh_mods_info(self, api_key: str = None):
        # load mods config
        try:
            cfg_data = await self.load_cfg()
        except yaml.YAMLError as er:
            logger.error(er)
            raise yaml.YAMLError(er)
        except FileExistsError as er:
            logger.error(er)
            raise FileExistsError(er)

        # load validation schema
        async with aiofiles.open('./src/schema.py', 'r') as schema:
            mods_validator = Validator(schema.read())

        # Validate the cfg file
        if not mods_validator.validate(cfg_data):
            raise KeyError(mods_validator.errors)

        df_cfg = pd.DataFrame.from_dict(cfg_data['mods'])
        if 'version' not in df_cfg.columns:
            df_cfg['version'] = None

        # Requests mods update
        mods_update = []

        req = None
        apicall = None
        for idx, row in df_cfg.iterrows():
            if row['provider'] == self.__THUNDERSTORE_NAME:
                apicall = thunderstore.thunderstore()
                req = await apicall.get_update(row['app'], row['mods'], row['version'])
                mods_update.append(req)
            elif row.provider == self.__NEXUSMODS_NAME:
                apicall = nexusmods.nexusmods()
                req = await apicall.get_update(row['app'], row['mods'], row['version'], api_key)
                mods_update.append(req)

        df_update = pd.DataFrame(mods_update)

        if os.path.exists(self.manifests_filename):
            with open(self.manifests_filename, 'r') as manifests:
                mods_current = json.load(manifests)

            df_current = pd.DataFrame(mods_current)
            df_status = df_update.join(df_current, ['provider', 'app', 'mods'], rsuffix='current_')
            if df_status['version'] != df_status['current_version']:
                df_status['need_update'] = True
            else:
                df_status['need_update'] = False
        else:
            df_status = df_update
            df_status['need_update'] = True

        self.mods_status = df_status

    @staticmethod
    def extract_mods(self, filename, destination):
        with zipfile.ZipFile(filename, 'r') as file:
            try:
                file.extractall(destination)
                return 0
            except Exception as er:
                logger.error(er)
                return 1

    async def make_request(self, session, row):
        try:
            resp = await session.request(method="GET", url=row['download_link'])

            if resp.status == 200:
                filename = os.path.join(row['mods_dir'], resp.url.name)
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await asyncio.get_running_loop().run_in_executor(None, self.extract_mods, filename, row['full_mods_name']) == 0:
                    os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if not self.mods_status:
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
            return 1

        list_to_update = self.mods_status.query('need_update == True')
        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, rows in pd.DataFrame(list_to_update).iterrows():
                tasks.append(self.make_request(session, rows))

            await asyncio.gather(*tasks)
