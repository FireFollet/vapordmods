import os
import yaml
import logging
import json
from src.api import thunderstore, nexusmods


class vapordmods:
    __CFG_FILENAME = 'vapordmods.yml'
    __MANIFESTS_DIR = 'vapordmods_manifests'
    __THUNDERSTORE_NAME = 'thunderstore'
    __NEXUSMODS_NAME = 'nexusmods'

    def __init__(self, install_dir: str):
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.cfg_data = None
        self.mods_info = None
        self.thunderstore_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__THUNDERSTORE_NAME)
        self.nexusmods_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__NEXUSMODS_NAME)

        if os.path.exists(self.cfg_filename):
            if os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK):
                self.reload_cfg()
            else:
                raise PermissionError("'{}' is not a file or cannot be read.".format(self.cfg_filename))
        elif os.path.exists(install_dir):
            cfg_file = open(self.cfg_filename, 'w')
            cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__NEXUSMODS_NAME + ':\n')
            cfg_file.close()
        else:
            raise FileNotFoundError("Cannot create or read '{}'.".format(self.cfg_filename))

        list_mods = {self.thunderstore_dir, self.nexusmods_dir}

        for mod in list_mods:
            if not os.path.exists(mod):
                os.makedirs(mod)

    def reload_cfg(self):
        f = open(self.cfg_filename, "r")
        self.cfg_data = yaml.safe_load(f)
        f.close()

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
                                        'needupdate': False, 'download_link': 'not_required', 'newmanifest': None}
                        else:
                            r = await globals()[provider].get_update(app, modname, modversion, api_key)
                            if r:
                                latestversion = r['data']['version']
                                download_link = None
                                if currentmanifest:
                                    currentversion = currentmanifest['version']
                                    if currentmanifest['version'] == r['data']['version']:
                                        needupdate = False
                                        download_link = 'not_required'
                                        newmanifest = None
                                    else:
                                        needupdate = True
                                        ddownload_link = r['data']['download_url']
                                        newmanifest = r['data']['manifest']
                                else:
                                    currentversion = 'not_installed'
                                    needupdate = True
                                    download_link = r['data']['download_url']
                                    newmanifest = r['data']['manifest']

                                data = {'currentversion': currentversion, 'latestversion': latestversion,
                                        'needupdate': needupdate, 'download_link': download_link, 'newmanifest': newmanifest}
                            else:
                                logging.error("Impossible de trouver l'info pour ...")

                        if app not in modstatus[provider]:
                            modstatus[provider][app] = {modname: data}
                        else:
                            modstatus[provider][app][modname] = data
                self.mods_info = modstatus
        else:
            raise ValueError("Erreur a faire")

    async def update_mods(self):
        pass
