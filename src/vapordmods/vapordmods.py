import os
import requests
import yaml
import logging
import json


class vapordmods:
    __THUNDERSTORE_API_URL_LATEST = "https://thunderstore.io/api/experimental/package/{}/{}/"
    __THUNDERSTORE_API_URL_VERSION = "https://thunderstore.io/api/experimental/package/{}/{}/{}"
    __CFG_FILENAME = 'vapordmods.yml'
    __MANIFESTS_DIR = 'vapordmods_manifests'
    __THUNDERSTORE_NAME = 'thunderstore'
    __STEAMWORKSHOP_NAME = 'steamworkshop'

    def __init__(self, install_dir: str):
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.cfg_data = None
        self.thunderstore_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__THUNDERSTORE_NAME)
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
            cfg_file.write('mods:\n  ' + self.__THUNDERSTORE_NAME + ':\n\n  ' + self.__STEAMWORKSHOP_NAME + ':\n')
            cfg_file.close()
        else:
            raise FileNotFoundError("Cannot create or read '{}'.".format(self.cfg_filename))

        list_mods = {self.thunderstore_dir, self.steamworkshop_dir}

        for mod in list_mods:
            if not os.path.exists(mod):
                os.makedirs(mod)

    def reloadcfg(self):
        f = open(self.cfg_filename, "r")
        self.cfg_data = yaml.safe_load(f)
        f.close()

    def thunderstoreapi(self, namespace, name, version=None):
        if not version:
            r = requests.get(self.__THUNDERSTORE_API_URL_LATEST.format(namespace, name))
        else:
            r = requests.get(self.__THUNDERSTORE_API_URL_VERSION.format(namespace, name, version))
        if r.status_code == 200:
            return r.json()
        else:
            return None

    def buildupdateinfofromthunderstore(self):
        if self.cfg_data['mods'][self.__THUNDERSTORE_NAME]:
            depotdata = {}
            for namespace in self.cfg_data['mods'][self.__THUNDERSTORE_NAME]:
                for name, value in namespace:
                    currentmanifest = None
                    filename = os.path.join(self.thunderstore_dir, namespace + '_' + name + '.json')
                    if os.path.exists(filename):
                        f = open(filename, 'r')
                        currentmanifest = json.load(f)
                        f.close()

                    if value and currentmanifest:
                        if value == currentmanifest['latest']['version_number']:
                            data = {'currentversion': value, 'latestversion': 'current_match_requirement',
                                    'needupdate': False, 'newmanifest': None}
                            if namespace not in depotdata[self.__THUNDERSTORE_NAME]:
                                depotdata[self.__THUNDERSTORE_NAME][namespace] = {name: data}
                            else:
                                depotdata[self.__THUNDERSTORE_NAME][namespace][name] = data
                    else:
                        r = self.thunderstoreapi(namespace, name, value)
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

    def buildupdateinfofromsteam(self):
        pass

    def getmodinfo(self):
        if self.cfg_data['mods']:
            modstatus = {self.__THUNDERSTORE_NAME: {}, self.__STEAMWORKSHOP_NAME: {}}

            return modstatus
        else:
            raise ValueError("Erreur a faire")
