import aiohttp

__NEXUSMODS_API_URL_FILES = "https://api.nexusmods.com/v1/games/{}/mods/{}/files.json"
__NEXUSMODS_API_URL_DOWNLOAD_LINK = "https://api.nexusmods.com/v1/games/{}/mods/{}/files/{}/download_link.json"


async def get_update(game_domain_name: str, mod_id: str, version: str = None, api_key: str = None) -> dict:
    request = __NEXUSMODS_API_URL_FILES.format(game_domain_name, mod_id)
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }

    async with aiohttp.request('GET', request, headers=headers) as resp:
        if resp.status == 200:
            j = await resp.json()

            if not version:
                filedata = j['files'][len(j['files']) - 1]
            else:
                filedata = [i for i in j['files'] if i['version'] == version]
                if len(filedata) == 0:
                    return {'status': resp.status, 'data': "The version '{}' was not found in the game domain '{}' for the mod '{}'.".format(version, game_domain_name, mod_id)}
                else:
                    filedata = filedata[0]

            req_dl = __NEXUSMODS_API_URL_DOWNLOAD_LINK.format(game_domain_name, mod_id, str(filedata['file_id']))
            async with aiohttp.request('GET', req_dl, headers=headers) as resp_dl:
                if resp_dl.status == 200:
                    dl = await resp_dl.json()
                    data = {'app': game_domain_name, 'mods': mod_id, 'version': filedata['version'], 'dependencies': 'n/a',
                            'download_url': dl[0]['URI'], 'manifest': j}
                    return {'status': resp.status, 'data': data}
                else:
                    return {'status': resp.status, 'data': resp.reason}
        else:
            return {'status': resp.status, 'data': resp.reason}
