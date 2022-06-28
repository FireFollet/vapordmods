from steam.monkey import patch_minimal

patch_minimal()

import shutil
import tempfile
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
    _GITHUB_NAME = 'github'

    def __init__(self, install_dir: str, client: SteamManager = None):
        self.default_mods_dir = None
        self.install_dir = install_dir
        self.client = client
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
            raise PermissionError(f"Cannot write to the folder {self.install_dir}.")

        if not os.path.exists(self.cfg_filename):
            loop.run_until_complete(self.write_cfg_filename())

    async def write_cfg_filename(self):
        template = b'config:\n  default_mods_dir: \n\nmods:\n  - provider: \n    app: \n    mods: \n    version: \n' \
                   b'    \n  - provider:             \n    app:       \n    mods:              \n    version: \n'
        async with aiofiles.open(self.cfg_filename, 'wb') as cfg_file:
            await cfg_file.write(template)

    @staticmethod
    async def __load_yaml(filename):
        if await aiofiles.os.path.exists(filename):
            async with aiofiles.open(filename, 'r') as file:
                return yaml.safe_load(await file.read())
        else:
            raise FileExistsError(filename)

    async def load_cfg_data(self):
        cfg_data = await self.__load_yaml(self.cfg_filename)
        mods_validator = Validator(schema)

        try:
            if not mods_validator.validate(cfg_data):
                logger.error(mods_validator.errors)
                return False
        except Exception as er:
            logger.error(er)
            return False

        self.cfg_data = cfg_data
        self.default_mods_dir = cfg_data['config']['default_mods_dir'] or self.install_dir
        return True

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

            df_cfg = df_cfg.fillna('')
            df_cfg.loc[((df_cfg['mods_dir'] == '') | (df_cfg['mods_dir'] is None)), 'mods_dir'] = self.default_mods_dir

            # Requests mods update
            mods_update = []
            apicall = None
            list_api_key = {self._THUNDERSTORE_NAME: None, self._NEXUSMODS_NAME: nmods_api_key,
                            self._WORKSHOP_NAME: steam_api_key, self._GITHUB_NAME: None}
            for idx, row in df_cfg.iterrows():
                apicall = getattr(globals()[row['provider']], row['provider'])()
                if row['provider'] in (self._THUNDERSTORE_NAME, self._NEXUSMODS_NAME, self._WORKSHOP_NAME):
                    params = {
                        'namepsace': row['app'],
                        'name': row['mods'],
                        'mods_dir': row['mods_dir'],
                        'version': row['version'],
                        'api_key': list_api_key[row['provider']]
                    }
                else:
                    params = {
                        'owner': row['app'],
                        'repo': row['mods'],
                        'mods_dir': row['mods_dir'],
                        'version': row['version'],
                        'filename': row['filename']
                    }

                if await apicall.get_update(**params) == 0:
                    mods_update.append(apicall.return_data())

            df_update = pd.DataFrame(mods_update)
            df_update['need_update'] = False

            if len(self.mods_info):
                df_current = pd.DataFrame(self.mods_info)
                df_status = df_update.merge(df_current, on=['provider', 'app', 'mods'], suffixes=(None, suffixes))
                df_status['need_update'] = df_status['version'] != df_status[f'version{suffixes}']
            else:
                df_status = df_update
                df_status['need_update'] = True

            self.mods_status = df_status.to_dict('records')
            return 1
        except Exception as er:
            logger.error(f"Error during update for mods: {er}")
            return 0

    @staticmethod
    async def __extract_mods(filename, destination, row):
        with zipfile.ZipFile(filename, 'r') as file:
            temp_dir = os.path.join(tempfile.gettempdir(), 'vapord_temp')
            try:
                if row['provider'].lower() == 'thunderstore' and 'bepinexpack' in row['full_mods_name'].lower():
                    benpinex = 'BepInEx'
                    file_list = [x for x in file.namelist() if benpinex in x]
                    benpinex_dir = file_list[0][0:file_list[0].index(os.sep)]
                    temp_dir_bepinex = os.path.join(temp_dir, benpinex_dir)
                    file.extractall(temp_dir, file_list)
                    cp_dir = temp_dir_bepinex
                else:
                    file.extractall(temp_dir)
                    cp_dir = temp_dir

                shutil.copytree(cp_dir, row['mods_dir'], dirs_exist_ok=True)

                return 1
            except Exception as er:
                logger.error(er)
                return 0
            finally:
                if await aiofiles.os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

    async def __make_request(self, session, row):
        try:
            resp = await session.request(method="GET", url=row['download_url'])

            if resp.status == 200:
                await aiofiles.os.makedirs(row['mods_dir'], exist_ok=True)

                filename = os.path.join(row['mods_dir'], resp.url.name)
                destination = os.path.join(row['mods_dir'], row['full_mods_name'])
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await self.__extract_mods(filename, destination, row):
                    await aiofiles.os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if not len(self.mods_status):
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
            return 0

        try:
            list_to_update = [x for x in self.mods_status if x['need_update'] and x['provider'] in
                              [self._THUNDERSTORE_NAME, self._NEXUSMODS_NAME, self._GITHUB_NAME]]

            if len(list_to_update):
                async with aiohttp.ClientSession() as session:
                    tasks = [self.__make_request(session, i) for i in list_to_update]

                    await asyncio.gather(*tasks)

            list_to_update_workshop = [x for x in self.mods_status if
                                       x['need_update'] == 'True' and x['provider'] == self._WORKSHOP_NAME]
            if len(list_to_update_workshop):
                for i in list_to_update_workshop:
                    result = await self.client.update_worksop_mod(i['app'], i['mods'])
                    if result == 1 and result(1):
                        Path(result(1)).symlink_to(os.path.join(i['mods_dir'], i['title']))
                    elif result == 1:
                        logger.error(
                            f"The symlink for the APP_ID {i['app']} and published_file_id {i['mods']} was note created.")
                    else:
                        logger.error(result(1))

            with open(self.manifests_filename, 'w') as manifest:
                yaml.safe_dump(self.mods_status, manifest)

            return 1
        except Exception as er:
            logger.error(er)
            return 0
