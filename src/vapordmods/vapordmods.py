import asyncio
import aiofiles
import os
import aiohttp
import yaml
import logging
import json
import zipfile
from src.api import thunderstore, nexusmods

logger = logging.getLogger(__name__)


class VapordMods:
    __CFG_FILENAME = 'vapordmods.yml'
    __MANIFESTS_DIR = 'vapordmods_manifests'
    __THUNDERSTORE_NAME = 'thunderstore'
    __NEXUSMODS_NAME = 'nexusmods'
    __SWORKSHOP_NAME = 'sworkshop'

    def __init__(self, server_dir: str, mods_dir: str = None):
        self.server_dir = server_dir
        self.mods_dir = mods_dir
        self.cfg_filename = os.path.join(server_dir, self.__CFG_FILENAME)
        self.cfg_data = None
        self.mods_info = None
        self.thunderstore_dir = os.path.join(server_dir, self.__MANIFESTS_DIR, self.__THUNDERSTORE_NAME)
        self.nexusmods_dir = os.path.join(server_dir, self.__MANIFESTS_DIR, self.__NEXUSMODS_NAME)
        self.mods_manifest_dir = {
            self.__THUNDERSTORE_NAME: self.thunderstore_dir,
            self.__NEXUSMODS_NAME: self.nexusmods_dir
        }

        if os.path.exists(self.cfg_filename):
            if os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK):
                self.reload_cfg()
            else:
                raise PermissionError(f"'{self.cfg_filename}' is not a file or cannot be read.")
        elif os.path.exists(server_dir):
            with open(self.cfg_filename, 'w') as cfg_file:
                cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__NEXUSMODS_NAME +
                               ':\n\n  ' + self.__SWORKSHOP_NAME + ':\n')
        else:
            raise PermissionError(f"Cannot create or read '{self.cfg_filename}'.")

        list_mods = {self.thunderstore_dir, self.nexusmods_dir, self.__SWORKSHOP_NAME }

        for mod in list_mods:
            if not os.path.exists(mod):
                os.makedirs(mod)

    def reload_cfg(self):
        if os.path.exists(self.cfg_filename):
            with open(self.cfg_filename, 'r') as cfg_file:
                self.cfg_data = yaml.safe_load(cfg_file)

    async def refresh_mods_info(self, api_key: str = None):
        if self.cfg_data['mods']:
            modstatus = {self.__THUNDERSTORE_NAME: {}, self.__NEXUSMODS_NAME: {}}
            for provider in self.cfg_data['mods']:
                if provider not in (self.__THUNDERSTORE_NAME, self.__NEXUSMODS_NAME):
                    break
                if not self.cfg_data['mods'][provider]:
                    break

                for app in self.cfg_data['mods'][provider]:
                    if app is None:
                        break
                    for mod in self.cfg_data['mods'][provider][app]:
                        if mod is None:
                            break

                        if type(mod) == str:
                            modname = mod
                            modversion = None
                        else:
                            list_mod = list(mod.items())[0]
                            modname = list_mod[0]
                            modversion = list_mod[1]

                        currentmanifest = None
                        filename = os.path.join(self.thunderstore_dir, app + '_' + modname + '.json')
                        if os.path.exists(filename):
                            f = open(filename, 'r')
                            currentmanifest = json.load(f)
                            f.close()

                        data = None
                        if modversion and currentmanifest:
                            if currentmanifest['latest']:
                                installed_version = currentmanifest['latest']['version_number']
                            else:
                                installed_version = currentmanifest['version_number']
                            if modversion == installed_version:
                                data = {'currentversion': modversion, 'latestversion': 'current_match_requirement',
                                        'needupdate': False, 'download_link': 'not_required',
                                        'mods_dir': 'not_required', 'newmanifest': None}
                        else:
                            params = {}
                            req = None
                            apicall = None
                            if provider == self.__THUNDERSTORE_NAME:
                                apicall = thunderstore.thunderstore()
                                req = await apicall.get_update(app, modname, modversion)
                            elif provider == self.__NEXUSMODS_NAME:
                                apicall = nexusmods.nexusmods()
                                req = await apicall.get_update(app, modname, modversion, api_key)

                            if req == 0:
                                r = apicall.return_data()
                                latestversion = r['version']
                                download_link = None
                                if currentmanifest:
                                    currentversion = currentmanifest['version']
                                    if currentmanifest['version'] == r['version']:
                                        needupdate = False
                                        newmanifest = None
                                    else:
                                        needupdate = True
                                        newmanifest = r['manifest']
                                else:
                                    currentversion = 'not_installed'
                                    needupdate = True
                                    newmanifest = r['manifest']

                                data = {'currentversion': currentversion, 'latestversion': latestversion,
                                        'needupdate': needupdate, 'download_link': r['download_url'],
                                        'mods_dir': self.mods_dir[provider], 'newmanifest': newmanifest}

                        if app not in modstatus[provider]:
                            modstatus[provider][app] = {modname: data}
                        else:
                            modstatus[provider][app][modname] = data
                self.mods_info = modstatus
        else:
            logger.error(f"No mods information in the file {self.cfg_filename} or the config is not loaded. Please execute the methode 'reload_cfg'.")

    def extract_mods(self, filename, mods_name):
        filename = os.path.join(self.mods_dir, filename)
        with zipfile.ZipFile(filename, 'r') as file:
            try:
                destination = os.path.join(self.mods_dir, mods_name)
                file.extractall(destination)
                return 0
            except Exception as er:
                logger.error(er)
                return 1

    async def make_request(self, session, mods_name, update_manifest):
        try:
            resp = await session.request(method="GET", url=update_manifest['download_link'])

            if resp.status == 200:
                filename = os.path.join(update_manifest['mods_dir'], resp.url.name)
                async with aiofiles.open(filename, 'wb') as f:
                    await f.write(await resp.read())

                if await asyncio.get_running_loop().run_in_executor(None, self.extract_mods, resp.url.name, mods_name) == 0:
                    async with aiofiles.open(update_manifest['namespace'] + '-' + update_manifest['name'], 'w') as file_manifest:
                        await file_manifest.write(json.dumps(update_manifest, indent=4))
                    os.remove(filename)
            else:
                logger.error(f"Error with the request: {resp.status} {resp.text()}")

        except Exception as er:
            logger.error(er)

    async def update_mods(self):
        if type(self.mods_info) == dict:
            if len(self.mods_info) > 0:
                async with aiohttp.ClientSession() as session:
                    for provider in self.mods_info:
                        tasks = []
                        for provider_k, provider_v in self.mods_info.items():
                            for app_k, app_v in provider_v.items():
                                for mods_k, mods_v in app_v.items():
                                    if mods_v['needupdate']:
                                        tasks.append(self.make_request(session, mods_k, mods_v))

                        if len(tasks) > 0:
                            await asyncio.gather(*tasks)
        else:
            logger.error(f"No mods information. Please execute the method 'refresh_mods_info'.")
