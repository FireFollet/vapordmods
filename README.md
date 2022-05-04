<p align="left">
    <a href="https://sonarcloud.io/project/information?id=FireFollet_vapordmods" alt="sqale_rating">
        <img src="https://sonarcloud.io/api/project_badges/measure?project=FireFollet_vapordmods&metric=sqale_rating" /></a>
    <a href="https://sonarcloud.io/project/information?id=FireFollet_vapordmods" alt="reliability_rating">
        <img src="https://sonarcloud.io/api/project_badges/measure?project=FireFollet_vapordmods&metric=reliability_rating" /></a>
    <a href="https://sonarcloud.io/project/information?id=FireFollet_vapordmods" alt="security_rating">
        <img src="https://sonarcloud.io/api/project_badges/measure?project=FireFollet_vapordmods&metric=security_rating" /></a>
</p>

# Disclaimers
This project is a way to learn and improve my knowledge of Python. The code and how it's implemented is far from perfect.

Keep in mind that this module is new and bugs are possibles

# Features
This module allows to update mods (**Thunderstore**, **Nexusmods** and **Steam Workshop**) automatically. You configure the file **vapordmods.yml** with the mods, the version and the folder you want.

Everytime the code run, a comparaison is made with the **vapordmods.manifest** file to compare the version of the installed mods with the latest version if no specific version is identified. 

If an update is required, or it's not installed, the mod is downloaded and installed int the directory you have specified.

The mods are not removed automatically and you need to remove the mods manually.

- Management of [Thunderstore](https://thunderstore.io/) mods
- Management of [Nexusmods](https://www.nexusmods.com/) mods
  - You need to be premium to use this feature. You cannot have the download link without it.
- Management of [Steam Workshop](https://steamcommunity.com/workshop/) mods
  - You can only update to the latest version at the moment.

# Install

# Examples

## Configuration files
```
config:
  default_mods_dir: /opt/mods/`

mods:
  - provider: thunderstore
    app: ishid4
    mods: BetterArchery
    version: 1.7.5
    
  - provider: thunderstore
    app: OdinPlus
    mods: OdinsTraps
    version:
    
  - provider: thunderstore
    app: OdinPlus
    mods: ShrinkMe
    version: 
  
  - provider: workshop
    app: 896660
    mods: 1025487
```


## Codes
