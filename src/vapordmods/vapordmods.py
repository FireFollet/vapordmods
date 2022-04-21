import os
import yaml
import logging
import json
from src.api import thunderstore


class vapordmods:
    __CFG_FILENAME = 'vapordmods.yml'
    __MANIFESTS_DIR = 'vapordmods_manifests'
    __THUNDERSTORE_NAME = 'thunderstore'
    __NEXUSMODS_NAME = 'nexusmods'
    __STEAMWORKSHOP_NAME = 'steamworkshop'

    def __init__(self, install_dir: str):
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.cfg_data = None
        self.thunderstore_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__THUNDERSTORE_NAME)
        self.thunderstore_mods = []
        self.nexusmods_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__NEXUSMODS_NAME)
        self.thunderstore_mods = []
        self.steamworkshop_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__STEAMWORKSHOP_NAME)
        self.steamworkshop_mods = []

        if os.path.exists(self.cfg_filename):
            if os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK):
                self.reloadcfg()
            else:
                raise PermissionError("'{}' is not a file or cannot be read.".format(self.cfg_filename))
        elif os.path.exists(install_dir):
            cfg_file = open(self.cfg_filename, 'w')
            cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__NEXUSMODS_NAME +
                           ':\n\n  ' + self.__STEAMWORKSHOP_NAME + ':\n')
            cfg_file.close()
        else:
            raise FileNotFoundError("Cannot create or read '{}'.".format(self.cfg_filename))

        list_mods = {self.thunderstore_dir, self.nexusmods_dir, self.steamworkshop_dir}

        for mod in list_mods:
            if not os.path.exists(mod):
                os.makedirs(mod)

    async def reloadcfg(self):
        f = open(self.cfg_filename, "r")
        self.cfg_data = yaml.safe_load(f)
        f.close()

    async def getmodinfo(self):
        if self.cfg_data['mods']:
            modstatus = {self.__THUNDERSTORE_NAME: {}, self.__NEXUSMODS_NAME: {}, self.__STEAMWORKSHOP_NAME: {}}
            for provider in self.cfg_data['mods']:
                for app in self.cfg_data['mods'][provider]:
                    for mods, value in app:
                        currentmanifest = None
                        filename = os.path.join(self.thunderstore_dir, app + '_' + mods + '.json')
                        if os.path.exists(filename):
                            f = open(filename, 'r')
                            currentmanifest = json.load(f)
                            f.close()

                        if value and currentmanifest:
                            if value == currentmanifest['latest']['version_number']:
                                data = {'currentversion': value, 'latestversion': 'current_match_requirement',
                                        'needupdate': False, 'newmanifest': None}
                                if app not in modstatus[self.__THUNDERSTORE_NAME]:
                                    modstatus[self.__THUNDERSTORE_NAME][app] = {mods: data}
                                else:
                                    modstatus[self.__THUNDERSTORE_NAME][app][mods] = data
                        else:
                            r = await locals()[provider].get_update(app, mods, value)
                            if r:
                                with r.json() as manifest:
                                    latestversion = manifest['latest']['version_number']
                                    if currentmanifest:
                                        currentversion = currentmanifest['latest']['version_number']
                                        if currentmanifest['latest']['version_number'] == manifest['latest']['version_number']:
                                            needupdate = False
                                            newmanifest = None
                                        else:
                                            needupdate = True
                                            newmanifest = manifest
                                    else:
                                        currentversion = 'not_installed'
                                        needupdate = True
                                        newmanifest = manifest
                            else:
                                logging.error("Impossible de trouver l'info pour ...")
                return modstatus
        else:
            raise ValueError("Erreur a faire")
