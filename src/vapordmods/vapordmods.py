import os
import requests
import yaml
import logging
import json


class vapordmods:
    __API_URL_LATEST = "https://thunderstore.io/api/experimental/package/{}/{}/"
    __API_URL_VERSION = "https://thunderstore.io/api/experimental/package/{}/{}/{}"
    __CFG_FILENAME = 'vapord_mods.yml'
    __MANIFESTS_DIR = 'vapord_manifests'
    __MANIFESTS_TMODS_DIR = 'tmods'
    __MANIFESTS_NMODS_DIR = 'nmods'
    __MANIFESTS_SWORKSHOP_DIR = 'sworkshop'

    def __init__(self, install_dir: str):
        self.cfg_filename = os.path.join(install_dir, self.__CFG_FILENAME)
        self.cfg_data = None
        self.tmods_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__MANIFESTS_TMODS_DIR)
        self.tmods_mods = []
        self.tmods_manifests = []
        self.nmods_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__MANIFESTS_NMODS_DIR)
        self.nmods_mods = []
        self.nmods_manifests = []
        self.sworkshop_dir = os.path.join(install_dir, self.__MANIFESTS_DIR, self.__MANIFESTS_SWORKSHOP_DIR)
        self.sworkshop_mods = []
        self.sworkshop_manifests = []

        if os.path.exists(self.cfg_filename):
            if os.path.isfile(self.cfg_filename) and os.access(self.cfg_filename, os.R_OK):
                self.reloadcfg()
            else:
                raise PermissionError("'{}' is not a file or cannot be read.".format(self.cfg_filename))
        elif os.path.exists(install_dir):
            cfg_file = open(self.cfg_filename, 'w')
            cfg_file.write('mods:\n  tmods:\n\n  nmods:\n\n  sworkshop:\n')
            cfg_file.close()
        else:
            raise FileNotFoundError("Cannot create or read '{}'.".format(self.cfg_filename))

        list_mods = {self.tmods_dir, self.nmods_dir, self.sworkshop_dir}

        for mod in list_mods:
            if not os.path.exists(mod):
                os.makedirs(mod)

    def reloadcfg(self):
        f = open(self.cfg_filename, "r")
        self.cfg_data = yaml.safe_load(f)
        f.close()

    def tmodapi(self, namespace, name, version=None):
        if not version:
            r = requests.get(self.__API_URL_LATEST.format(namespace, name))
        else:
            r = requests.get(self.__API_URL_VERSION.format(namespace, name, version))
        if r.status_code == 200:
            return r.json()
        else:
            return None

    def getmodinfo(self):
        if self.cfg_data['mods']:
            modstatus = {'tmods': {}, 'nmods': {}, 'sworkshop': {}}
            # tmods
            if self.cfg_data['mods']['tmods']:
                for namespace in self.cfg_data['mods']['tmods']:
                    for name, value in namespace:
                        currentmanifest = None
                        filename = os.path.join(self.tmods_dir, namespace + '_' + name + '.json')
                        if os.path.exists(filename):
                            f = open(filename, 'r')
                            currentmanifest = json.load(f)
                            f.close()

                        if value and currentmanifest:
                            if value == currentmanifest['latest']['version_number']:
                                data = {'currentversion': value, 'latestversion': 'current_match_requirement', 'needupdate': False, 'newmanifest': None}
                                if namespace not in modstatus['tmods']:
                                    modstatus['tmods'][namespace] = {name: data}
                                else:
                                    modstatus['tmods'][namespace][name] = data
                        else:
                            r = self.tmodapi(namespace, name, value)
                            if r:
                                latestversion = r['latest']['version_number']
                                if currentmanifest:
                                    currentversion = currentmanifest['latest']['version_number']
                                    if currentmanifest['latest']['version_number'] == r['latest']['version_number']:
                                        needupdate = False
                                        newmanifest = None
                                    else:
                                        needupdate = True
                                        newmanifest = r
                                else:
                                    currentversion = 'not_installed'
                                    needupdate = True
                                    newmanifest = r
                            else:
                                logging.error("Impossible de trouver l'info pour ...")
            return modstatus
