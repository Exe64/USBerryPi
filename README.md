# USBerryPi

![USBerryPi](docs/banner.jpg)

Turns a Raspberry Pi (Pi 1 to Pi 5) into a network USB device server:

- **USB/IP** (tcp/3240): every plugged-in device is shared automatically, except hubs and exclusions.
- **ser2net**: selected serial ports (Zigbee dongle, TIC module…) are exposed over TCP and never shared over USB/IP.
- **Web UI** (port 80): devices, connected clients, ser2net, exclusions, services, logs, reboot.

## Installation

### Option 1: ready-to-flash image

From the [releases](../../releases):

| Image | Models |
|---|---|
| `usb-over-ip-armhf.img.xz` | Pi 1, 2, 3, 4, 5 |
| `usb-over-ip-arm64.img.xz` | Pi 3, 4, 5 (64-bit) |

Flash with **Raspberry Pi Imager** ("Use custom"). Without customisation, the image boots with DHCP on Ethernet and the system user is created on the console at first boot.

Imager 2.0 greys out the customisation step for custom images: it only offers it for images declared in a manifest. To get user, SSH and Wi-Fi settings back, point Imager at this repository's manifest instead of picking the file by hand -- App Options -> Content Repository -> Use custom URL:

```
https://raw.githubusercontent.com/Exe64/USBerryPi/main/docs/usberrypi.rpi-imager-manifest
```

Both images then show up in the OS list, customisation included, and Imager downloads the latest release itself. To flash an image already on disk, save [the manifest](docs/usberrypi.rpi-imager-manifest) locally as `os_list_local.rpi-imager-manifest`, replace the `url` with `file:///absolute/path/to/usb-over-ip-arm64.img.xz` and double-click it.

Then open http://usbip.local (or the Pi's IP). On first access, the UI asks you to choose a password.

### Option 2: package on an existing Raspberry Pi OS

```sh
sudo apt install ./usb-over-ip_<version>_all.deb
```

Installations made with the legacy `install_server` / `install_ser2net` scripts are migrated automatically: exclusion list, ser2net ports, and replacement of the old `usbipd` service.

## Client side

```sh
sudo modprobe vhci-hcd
usbip list -r usbip.local
sudo usbip attach -r usbip.local -b 1-1.2
```

For ser2net, e.g. in Home Assistant: `socket://usbip.local:6638`.

## Files on the Pi

| Path | Purpose |
|---|---|
| `/etc/usb-over-ip/exclude` | `vid:pid` or `vid:pid:serial` never shared |
| `/etc/usb-over-ip/serial.json` | ser2net ports (source of truth, edited by the UI) |
| `/etc/usb-over-ip/ser2net.yaml` | generated ser2net configuration |
| `/etc/usb-over-ip/password` | UI password (PBKDF2); delete it to reset |
| `/usr/lib/usb-over-ip/uoip.py` | autobind, ser2net generation and web server (Python stdlib) |

Services: `usb-over-ip` (usbipd), `usb-over-ip-web`, `ser2net`.

## Security

The UI runs as root, protected by an HTTP Basic password without TLS. It is meant for a trusted local network: do not expose it to the Internet. Until a password is set, the first visitor gets to choose it. USB/IP itself has no authentication at all.

## Development

```sh
make test                    # unit tests (Python 3, no dependencies)
make deb VERSION=1.0.0       # requires dpkg-deb
```

Release a version: `git tag v1.0.0 && git push --tags`. GitHub Actions builds the `.deb`, then both images with [pi-gen](https://github.com/RPi-Distro/pi-gen) (stage `image/stage-usbip`), and attaches them to the release.
