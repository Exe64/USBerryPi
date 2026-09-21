VERSION ?= 0.0.0
DEB := build/usb-over-ip_$(VERSION)_all.deb

.PHONY: deb test clean
deb: $(DEB)

$(DEB): $(shell find package -type f)
	# -L: banner.jpg is a symlink to docs/banner.jpg, the package needs the file itself
	rm -rf build/root && mkdir -p build && cp -rL package build/root
	find build/root -name __pycache__ -prune -exec rm -rf {} +
	sed -i 's/@VERSION@/$(VERSION)/' build/root/DEBIAN/control build/root/usr/lib/usb-over-ip/uoip.py
	chmod -R u=rwX,go=rX build/root && chmod 755 build/root/DEBIAN/p* build/root/usr/lib/usb-over-ip/uoip.py
	dpkg-deb --root-owner-group -Zxz --build build/root $@

test:
	python3 -m unittest discover -s tests -v

clean:
	rm -rf build
