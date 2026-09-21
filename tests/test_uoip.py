import json, os, sys, tempfile, threading, unittest, urllib.error, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "package", "usr", "lib", "usb-over-ip"))
import uoip


def mkdev(root, busid, vid, pid, serial="", cls="00", tty=None):
    """Mimics sysfs: real directories under devices/, symlinks in bus/usb/devices/."""
    d, links = f"{root}/devices/{busid}", f"{root}/bus/usb/devices"
    os.makedirs(d)
    os.makedirs(links, exist_ok=True)
    os.symlink(d, f"{links}/{busid}")
    for k, v in {"idVendor": vid, "idProduct": pid, "bDeviceClass": cls, "product": "Dongle", "serial": serial}.items():
        if v:
            with open(f"{d}/{k}", "w") as f:
                f.write(v + "\n")
    if tty:
        os.makedirs(f"{d}/{busid}:1.0/{tty}")
        os.symlink(f"{d}/{busid}:1.0", f"{links}/{busid}:1.0")
        os.makedirs(f"{root}/class/tty/{tty}")
        os.symlink(f"{d}/{busid}:1.0/{tty}", f"{root}/class/tty/{tty}/device")


class Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        uoip.SYS, uoip.ETC = f"{self.tmp.name}/sys", f"{self.tmp.name}/etc"
        mkdev(uoip.SYS, "1-1", "0424", "9514", cls="09")
        mkdev(uoip.SYS, "1-1.1", "0424", "ec00")
        mkdev(uoip.SYS, "1-1.2", "10c4", "EA60", serial="ABC", tty="ttyUSB0")
        mkdev(uoip.SYS, "1-1.10", "046d", "c52b")
        os.makedirs(f"{uoip.SYS}/bus/usb/devices/usb1")
        uoip.init()

    def tearDown(self):
        self.tmp.cleanup()

    def blocked(self):
        exclude, serial = uoip.load_exclude(), uoip.load_serial()
        return {d["busid"]: uoip.blocked(d, exclude, serial) for d in uoip.devices()}

    def test_devices_and_blocking(self):
        self.assertEqual(list(self.blocked()), ["1-1", "1-1.1", "1-1.2", "1-1.10"])  # numeric sort, usb1 skipped
        self.assertEqual(self.blocked(), {"1-1": "hub", "1-1.1": "exclu", "1-1.2": "", "1-1.10": ""})
        self.assertEqual(uoip.device("1-1.2")["ttys"], ["ttyUSB0"])

    def test_serial_blocks_its_usb_device(self):
        uoip.save_serial([{"name": "zigbee", "tty": "/dev/ttyUSB0", "port": 6638, "baud": 115200, "format": "n81"}])
        self.assertEqual(uoip.load_serial()[0]["usb"], "10c4:ea60:abc")
        self.assertEqual(self.blocked()["1-1.2"], "ser2net")
        yaml = open(f"{uoip.ETC}/ser2net.yaml").read()
        self.assertIn("connection: &zigbee\n  accepter: tcp,6638\n", yaml)
        self.assertIn("connector: serialdev,/dev/ttyUSB0,115200n81,local,nobreak", yaml)

    def test_ser2net_yaml_without_ports(self):
        # ser2net exits on an empty YAML document: with no port the file must still hold a mapping
        body = [l for l in uoip.ser2net_yaml([]).splitlines() if l and not l.startswith(("%", "---", "#"))]
        self.assertEqual(body[0].split("#")[0].strip(), "{}")

    def test_serial_validation(self):
        ok = {"name": "tic", "tty": "/dev/serial/by-id/usb-FTDI_x-if00-port0", "port": 6639, "baud": 1200, "format": "e71"}
        for bad in ({"name": "a b"}, {"tty": "/etc/passwd"}, {"tty": "/dev/ttyUSB0,9600"}, {"port": 3240},
                    {"port": "6639"}, {"port": 80}, {"baud": 1234}, {"format": "x81"}):
            with self.assertRaises(ValueError, msg=bad):
                uoip.save_serial([{**ok, **bad}])
        with self.assertRaises(ValueError):
            uoip.save_serial([ok, {**ok, "name": "tic2"}])  # duplicate port
        uoip.save_serial([ok])

    def test_migration_from_old_scripts(self):
        old = f"{self.tmp.name}/ser2net.yaml"
        open(old, "w").write("%YAML 1.1\n---\nconnection: &tic\n  accepter: tcp,6639\n  enable: on\n  options:\n"
                             "    kickolduser: true\n  connector: serialdev,/dev/ttyUSB0,1200e71,local\n")
        os.remove(f"{uoip.ETC}/serial.json")
        src = uoip.read
        uoip.read = lambda p, d="": src(old if p == "/etc/ser2net.yaml" else p, d)
        try:
            uoip.init()
        finally:
            uoip.read = src
        self.assertEqual([(s["name"], s["port"], s["baud"], s["format"]) for s in uoip.load_serial()], [("tic", 6639, 1200, "e71")])

    def test_exclude_validation(self):
        uoip.save_exclude(["10c4:ea60:abc", "046d:c52b"])
        self.assertEqual(self.blocked()["1-1.10"], "exclu")
        with self.assertRaises(ValueError):
            uoip.save_exclude(["nope"])

    def test_peers(self):
        proc = f"{self.tmp.name}/proc"
        os.makedirs(proc)
        head = "  sl  local_address rem_address   st\n"
        open(f"{proc}/tcp", "w").write(head + "   0: 0A00000A:0CA8 6401A8C0:D431 01 0\n   1: 00000000:0CA8 00000000:0000 0A 0\n")
        open(f"{proc}/tcp6", "w").write(head + "   0: 00000000000000000000000000000000:0CA8 0000000000000000FFFF00006501A8C0:9C40 01 0\n")
        self.assertEqual(uoip.peers(3240, proc), ["192.168.1.100", "192.168.1.101"])

    def test_web_auth_and_csrf(self):
        srv = uoip.ThreadingHTTPServer(("127.0.0.1", 0), uoip.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def call(path, body=None, ctype="application/json", auth=None):
            req = urllib.request.Request(base + path, None if body is None else json.dumps(body).encode(),
                                         {"Content-Type": ctype, **({"Authorization": auth} if auth else {})})
            try:
                with urllib.request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        self.assertEqual(call("/api/state"), (200, {"setup": True}))
        self.assertEqual(call("/api/exclude", {"entries": []})[0], 403)
        self.assertEqual(call("/api/password", {"password": "motdepasse"}, "text/plain")[0], 415)
        self.assertEqual(call("/api/password", {"password": "court"})[0], 400)
        self.assertEqual(call("/api/password", {"password": "motdepasse"}), (200, {"ok": True}))
        self.assertEqual(call("/api/state")[0], 401)
        good = "Basic " + __import__("base64").b64encode(b"admin:motdepasse").decode()
        status, st = call("/api/state", auth=good)
        self.assertEqual((status, [d["busid"] for d in st["devices"]]), (200, ["1-1", "1-1.1", "1-1.2", "1-1.10"]))
        self.assertEqual(call("/api/device", {"busid": "../../x", "action": "bind"}, auth=good)[0], 400)
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    unittest.main()
