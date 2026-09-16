# USBerryPi

Transforme un Raspberry Pi (Pi 1 à Pi 5) en serveur de périphériques USB en réseau :

- **USB/IP** (tcp/3240) : tout périphérique branché est partagé automatiquement, sauf hubs et exclusions.
- **ser2net** : les ports série choisis (dongle Zigbee, module TIC…) sont exposés en TCP et jamais partagés en USB/IP.
- **Interface web** (port 80) : périphériques, clients connectés, ser2net, exclusions, services, journaux, redémarrage.

## Installation

### Option 1 : image prête à flasher

Dans les [releases](../../releases) :

| Image | Modèles |
|---|---|
| `usb-over-ip-armhf.img.xz` | Pi 1, 2, 3, 4, 5 |
| `usb-over-ip-arm64.img.xz` | Pi 3, 4, 5 (64 bits) |

Flasher avec **Raspberry Pi Imager** (« Use custom ») et renseigner les réglages de personnalisation : utilisateur, SSH, Wi-Fi. Sans personnalisation, l'image démarre en DHCP sur Ethernet ; l'utilisateur système est créé au premier démarrage sur la console.

Ouvrir ensuite http://usbip.local (ou l'IP du Pi). Au premier accès, l'interface demande de choisir son mot de passe.

### Option 2 : paquet sur un Raspberry Pi OS existant

```sh
sudo apt install ./usb-over-ip_<version>_all.deb
```

Les installations faites avec les anciens scripts `install_server` / `install_ser2net` sont migrées automatiquement : liste d'exclusion, ports ser2net et remplacement de l'ancien service `usbipd`.

## Côté client

```sh
sudo modprobe vhci-hcd
usbip list -r usbip.local
sudo usbip attach -r usbip.local -b 1-1.2
```

Pour ser2net, dans Home Assistant par exemple : `socket://usbip.local:6638`.

## Fichiers sur le Pi

| Chemin | Rôle |
|---|---|
| `/etc/usb-over-ip/exclude` | `vid:pid` ou `vid:pid:série` jamais partagés |
| `/etc/usb-over-ip/serial.json` | ports ser2net (source de vérité, éditée par l'UI) |
| `/etc/usb-over-ip/ser2net.yaml` | configuration ser2net générée |
| `/etc/usb-over-ip/password` | mot de passe de l'UI (PBKDF2) ; le supprimer le réinitialise |
| `/usr/lib/usb-over-ip/uoip.py` | autobind, génération ser2net et serveur web (Python stdlib) |

Services : `usb-over-ip` (usbipd), `usb-over-ip-web`, `ser2net`.

## Sécurité

L'interface tourne en root, protégée par un mot de passe en HTTP Basic sans TLS. Elle est prévue pour un réseau local de confiance : ne pas l'exposer sur Internet. Tant qu'aucun mot de passe n'est défini, le premier visiteur le choisit. USB/IP lui-même n'a aucune authentification.

## Développement

```sh
make test                    # tests unitaires (Python 3, sans dépendance)
make deb VERSION=1.0.0       # nécessite dpkg-deb
```

Publier une version : `git tag v1.0.0 && git push --tags`. GitHub Actions construit le `.deb`, puis les deux images avec [pi-gen](https://github.com/RPi-Distro/pi-gen) (stage `image/stage-usbip`), et les attache à la release.
