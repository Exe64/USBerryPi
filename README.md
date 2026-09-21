# USBerryPi

![USBerryPi](docs/banner.jpg)

Turns a Raspberry Pi (Pi 1 to Pi 5), or any Debian or Ubuntu machine, into a network USB device server:

- **USB/IP** (tcp/3240): every plugged-in device is shared automatically, except hubs, exclusions, and what the machine itself runs on: mounted disks, swap and network interfaces (shown as `système`), so a USB boot disk or USB Ethernet adapter is never pulled away.
- **ser2net**: selected serial ports (Zigbee dongle, TIC module…) are exposed over TCP and never shared over USB/IP.
- **Web UI** (port 80): devices with the client-side commands to attach them, connected clients, ser2net, exclusions, services, logs, reboot, one-click updates.

## Installation

### Option 1: ready-to-flash image (Raspberry Pi)

From the [releases](../../releases):

| Image | Models |
|---|---|
| `usb-over-ip-armhf.img.xz` | Pi 1, 2, 3, 4, 5 |
| `usb-over-ip-arm64.img.xz` | Pi 3, 4, 5 (64-bit) |

Flash with **Raspberry Pi Imager** ("Use custom"). Without customisation, the image boots with DHCP on Ethernet and the system user is created on the console at first boot.

Imager 2.0 greys out the customisation step for custom images: it only offers it for images declared in a manifest. To get user, SSH and Wi-Fi settings back, point Imager at the manifest published with each release -- App Options -> Content Repository -> Use custom URL:

```
https://github.com/Exe64/USBerryPi/releases/latest/download/usberrypi.rpi-imager-manifest
```

Both images then show up in the OS list, customisation included, and Imager downloads and verifies the latest release itself. To flash an image already on disk, save [the manifest](docs/usberrypi.rpi-imager-manifest) locally as `os_list_local.rpi-imager-manifest`, replace the `url` with `file:///absolute/path/to/usb-over-ip-arm64.img.xz`, drop the `extract_*` and `image_download_size` fields, and double-click it.

Then open http://usbip.local (or the Pi's IP). On first access, the UI asks you to choose a password.

### Option 2: package on an existing system

Raspberry Pi OS, Debian 12+ or Ubuntu 22.04+, any architecture: Raspberry Pi, x86 mini PC or thin client, other ARM board, VM with USB passthrough.

```sh
sudo modprobe usbip_host        # the kernel must provide USB/IP
sudo apt install ./usb-over-ip_<version>_all.deb
```

Debian and Raspberry Pi OS kernels include USB/IP. On Ubuntu the module is in `linux-modules-extra`, which comes with the standard `linux-image-generic` kernel but not with the `virtual` kernel of cloud and minimal images (`sudo apt install linux-modules-extra-$(uname -r)`); the `usbip` tools come from `linux-tools-generic`, pulled in by the package. Vendor kernels (Armbian…) sometimes leave USB/IP out: if `modprobe usbip_host` fails, the board can't be used as a server.

Then open http://<hostname>.local (or the machine's IP). On first access, the UI asks you to choose a password.

Installations made with the legacy `install_server` / `install_ser2net` scripts are migrated automatically: exclusion list, ser2net ports, and replacement of the old `usbipd` service.

## Client side

A shared device is used by one client at a time; once attached, it behaves like a local USB device (a USB key shows up as a drive). The bus ID (`1-1.2`) is the first column of the device list in the UI.

Linux (`usbip` comes with `linux-tools` / `usbip` packages):

```sh
sudo modprobe vhci-hcd
usbip list -r usbip.local
sudo usbip attach -r usbip.local -b 1-1.2
sudo usbip port                 # attached devices
sudo usbip detach -p 00         # release it for other clients
```

Windows 10 1903+ / 11: install [usbip-win2](https://github.com/vadimgrn/usbip-win2) (signed drivers), then in an administrator prompt:

```bat
usbip list -r usbip.local
usbip attach -r usbip.local -b 1-1.2
usbip detach -p 1               :: port number printed by attach
```

For ser2net, e.g. in Home Assistant: `socket://usbip.local:6638`.

## Files

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

When a newer release exists, the UI offers to install it: the machine downloads the `.deb` from this repository's GitHub releases over HTTPS and installs it as root (no package signature beyond that). It needs Internet access for it; the services restart, which disconnects USB/IP and ser2net clients.

## Development

```sh
make test                    # unit tests (Python 3, no dependencies)
make deb VERSION=1.0.0       # requires dpkg-deb
rsvg-convert -w 128 -h 128 docs/logo.svg -o docs/icon.png   # Imager icon, after editing the logo
```

Release a version: `git tag v1.0.0 && git push --tags`. GitHub Actions builds the `.deb`, then both images with [pi-gen](https://github.com/RPi-Distro/pi-gen) (stage `image/stage-usbip`), and attaches them to the release.
