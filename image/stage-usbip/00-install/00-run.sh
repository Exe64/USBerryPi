#!/bin/bash -e
# files/usb-over-ip.deb is dropped in by CI (make deb)
install -m 644 files/usb-over-ip.deb "${ROOTFS_DIR}/tmp/usb-over-ip.deb"
on_chroot << CHEOF
apt-get install -y /tmp/usb-over-ip.deb
rm /tmp/usb-over-ip.deb
CHEOF
