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
    __SWORKSHOP_NAME = 'sworkshop'

    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.manifests_filename = os.path.join(install_dir, self.__MANIFESTS_FILENAME)
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self._cfg_data = {}
        self._mods_info = {}
        self._mods_status = {}

        asyncio.run(self.set_cfg_data())

        if self._cfg_data['config']['default_mods_dir']:
            self.default_mods_dir = self._cfg_data['config']['default_mods_dir']
        else:
            self.default_mods_dir = install_dir

        if os.path.exists(self.cfg_filename):
            if not (os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK)):
                raise PermissionError(f"'{self.cfg_filename}' is not a file or cannot be read.")
        elif os.path.exists(install_dir):
            with open(self.cfg_filename, 'w') as cfg_file:
                cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__NEXUSMODS_NAME +
                               ':\n\n  ' + self.__SWORKSHOP_NAME + ':\n')
        else:
            raise PermissionError(f"Cannot create or read '{self.cfg_filename}'.")

    @property
    def cfg_data(self):
        return self._cfg_data

    @cfg_data.setter
    def cfg_data(self, value):
        self._cfg_data = value

    @property
    def mods_status(self):
        return self._mods_status

    @mods_status.setter
    def mods_status(self, value):
        self._mods_status = value

    @staticmethod
    def __load_yaml(filename):
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                return yaml.safe_load(file)
        else:
            raise FileExistsError(filename)

    async def set_cfg_data(self):
        cfg_data = self.__load_yaml(self.cfg_filename)
        async with aiofiles.open('./src/schema', 'r') as schema:
            mods_validator = Validator(eval(await schema.read()))

        if not mods_validator.validate(cfg_data):
            raise KeyError(mods_validator.errors)
        self._cfg_data = cfg_data

    @property
    def mods_info(self):
        return self._mods_info

    @mods_info.setter
    def mods_info(self, value):
        self._mods_info = value

    def set_mods_info(self):
        if os.path.exists(self.manifests_filename):
            self._mods_info = self.__load_yaml(self.manifests_filename)

    async def refresh_mods_info(self, api_key: str = None):
        try:
            suffixes = '_current'
            await self.set_cfg_data()
            self.set_mods_info()

            df_cfg = pd.DataFrame.from_dict(self.cfg_data['mods'])
            for col in ['version', 'mods_dir']:
                if col not in df_cfg.columns:
                    df_cfg[col] = ''

            df_cfg.loc[((df_cfg['mods_dir'] == '') | (df_cfg['mods_dir'] is None)), 'mods_dir'] = self.default_mods_dir

            # Requests mods update
            mods_update = []
            apicall = None
            for idx, row in df_cfg.query(f"provider in ['{self.__THUNDERSTORE_NAME}', '{self.__NEXUSMODS_NAME}']").iterrows():
                apicall = getattr(globals()[row['provider']], row['provider'])()
                await apicall.get_update(row['app'], row['mods'], row['mods_dir'], row['version'], api_key)
                mods_update.append(apicall.return_data())

            df_update = pd.DataFrame(mods_update)
            df_update['need_update'] = False

            if len(self._mods_info) > 0:
                df_current = pd.DataFrame(self._mods_info)
                df_status = df_update.merge(df_current, on=['provider', 'app', 'mods'], suffixes=(None, suffixes))
            else:
                df_status = df_update

            df_status['need_update'] = df_status['version'] != df_status[f'version{suffixes}']

            self._mods_status = df_status.filter(items=df_update.columns.to_list()).to_dict()
            return 0
        except Exception as er:
            logger.error(f"Error during update for mods: {er}")
            return 1

    @staticmethod
    def __extract_mods(filename, destination):
        with zipfile.ZipFile(filename, 'r') as file:
            try:
                file.extractall(destination)
                return 0
            except Exception as er:
                logger.error(er)
                return 1

    async def __make_request(self, session, row):
        try:
            resp = await session.request(method="GET", url=row['download_url'])

            if resp.status == 200:
                if not os.path.exists(row['mods_dir']):
                    os.makedirs(row['mods_dir'], exist_ok=True)

                filename = os.path.join(row['mods_dir'], resp.url.name)
                destination = os.path.join(row['mods_dir'], row['full_mods_name'])
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await asyncio.get_running_loop().run_in_executor(None, self.__extract_mods, filename, destination) == 0:
                    os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if len(self._mods_status) == 0:
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
            return 1

        try:
            list_to_update = pd.DataFrame.from_dict(self._mods_status).query('need_update == True')
            if list_to_update is not None:
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for idx, rows in list_to_update.iterrows():
                        tasks.append(self.__make_request(session, rows))

                    await asyncio.gather(*tasks)
                with open(self.manifests_filename, 'w') as manifest:
                    yaml.safe_dump(self._mods_status, manifest)
            return 0
        except Exception as er:
            logger.error(er)
            return 1
