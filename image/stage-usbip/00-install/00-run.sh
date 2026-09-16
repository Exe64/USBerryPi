#!/bin/bash -e
# files/usb-over-ip.deb is dropped in by CI (make deb)
# Not /tmp: on_chroot mounts a tmpfs over it, hiding the file
install -m 644 files/usb-over-ip.deb "${ROOTFS_DIR}/var/tmp/usb-over-ip.deb"
on_chroot << CHEOF
apt-get install -y /var/tmp/usb-over-ip.deb
rm /var/tmp/usb-over-ip.deb
CHEOF
