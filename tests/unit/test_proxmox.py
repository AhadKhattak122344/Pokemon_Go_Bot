"""Offline regression tests; never connect to Proxmox or alter a VM."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from android_lab import proxmox as fleet
EXAMPLE = Path(__file__).parents[2] / "config/proxmox.example.json"


def config():
    return fleet.validate_config(json.loads(EXAMPLE.read_text()))


class FakeClient:
    def __init__(self):
        self.calls = []
        self.waits = []
        self.clone_done = False
        self.started = False
        self.fail_wait = False
        self.overrides = {}

    def request(self, method, path, data=None):
        self.calls.append((method, path, data))
        if (method, path) in self.overrides:
            return self.overrides[method, path]
        responses = {
            "/version": {"version": "test-only"},
            "/cluster/resources?type=vm": [{"vmid": 9000, "node": "pve", "type": "qemu", "name": "template"}],
            "/nodes/pve/qemu/9000/config": {"template": 1,
                "net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr0,firewall=1,tag=42,mtu=1450",
                "sata0": "local-lvm:base-9000-disk-0,size=64G", "ide2": "none,media=cdrom",
                "efidisk0": "local-lvm:base-9000-disk-1,size=4M"},
            "/nodes/pve/qemu/9000/status/current": {"status": "stopped"},
            "/nodes/pve/network": [{"iface": "vmbr0", "type": "bridge", "active": 1}],
            "/nodes/pve/storage/local-lvm/status": {"active": 1, "enabled": 1,
                                                    "content": "images,rootdir", "avail": 200 * 1024**3},
            "/nodes/pve/status": {"memory": {"free": 16 * 1024**3}},
            "/nodes/pve/qemu/10001/status/current": {"status": "running"},
        }
        if method == "GET":
            return copy.deepcopy(responses[path])
        if path.endswith("/clone"):
            return "UPID:pve:clone"
        if method == "PUT":
            if not self.clone_done:
                raise AssertionError("Configured before clone completed")
            return None
        if path.endswith("/start"):
            self.started = True
            return "UPID:pve:start"
        raise AssertionError((method, path))

    def wait_task(self, node, upid, timeout, poll):
        self.waits.append(upid)
        if self.fail_wait:
            raise fleet.FleetError("Mock clone failure")
        if upid.endswith("clone"):
            self.clone_done = True


class PlanningTests(unittest.TestCase):
    def test_stable_unique_locally_administered_ids(self):
        c = config()
        c["instances"].append({"vmid": 10002, "name": "android-2"})
        plan = fleet.make_plan(c)
        self.assertEqual(plan, fleet.make_plan(c))
        self.assertEqual(len({v["mac"] for v in plan["instances"]}), 2)
        self.assertEqual(plan["total_memory_mib"], 16384)
        self.assertEqual(plan["android_readiness"], "unverified")
        for vm in plan["instances"]:
            self.assertEqual(int(vm["mac"][:2], 16) & 3, 2)

    def test_configuration_errors(self):
        for key, value in (("host", "http://example.com"), ("host", "https://secret@host"),
                           ("host", "https://host/evil"), ("host", "https://host:invalid"),
                           ("cores", True), ("memory_mib", 0), ("task_timeout_s", -1),
                           ("namespace_uuid", "bad"), ("instances", []), ("node", "pve/../x")):
            with self.subTest(key=key, value=value):
                c = config()
                c[key] = value
                with self.assertRaises(fleet.FleetError):
                    fleet.make_plan(c)

    def test_duplicate_ids_and_names(self):
        for item in ({"vmid": 9000, "name": "android-2"},
                     {"vmid": 10001, "name": "android-2"},
                     {"vmid": 10002, "name": "ANDROID-1"}):
            c = config()
            c["instances"].append(item)
            with self.assertRaises(fleet.FleetError):
                fleet.make_plan(c)

    def test_plan_is_offline_and_does_not_need_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fleet, "ProxmoxClient") as client:
            out = Path(tmp) / "plan.json"
            with patch("sys.stdout", new_callable=io.StringIO):
                code = fleet.main(["plan", "--config", str(EXAMPLE), "--out", str(out)])
            self.assertEqual(code, 0)
            client.assert_not_called()
            self.assertEqual(json.loads(out.read_text())["status"], "planned_offline")

    def test_existing_reports_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            out.write_text("keep me")
            with patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(fleet.main(["plan", "--config", str(EXAMPLE), "--out", str(out)]), 1)
            self.assertEqual(out.read_text(), "keep me")


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.c = config()
        self.plan = fleet.make_plan(self.c)
        self.client = FakeClient()

    def test_preflight_only_reads_and_counts_all_template_disks(self):
        result = fleet.preflight(self.client, self.c, self.plan)
        self.assertEqual(result["required_storage_bytes_including_reserve"],
                         84 * 1024**3 + 4 * 1024**2)
        self.assertTrue(all(method == "GET" for method, _, _ in self.client.calls))

    def test_failures_block_all_writes(self):
        cases = [
            ("/nodes/pve/qemu/9000/config", {"template": 0}),
            ("/nodes/pve/qemu/9000/status/current", {"status": "running"}),
            ("/nodes/pve/network", [{"iface": "vmbr0", "type": "bridge", "active": 0}]),
            ("/nodes/pve/storage/local-lvm/status", {"enabled": 1, "active": 1, "content": "iso", "avail": 10**15}),
            ("/nodes/pve/storage/local-lvm/status", {"enabled": 1, "active": 1, "content": "images", "avail": 0}),
            ("/nodes/pve/status", {"memory": {"free": 0}}),
            ("/cluster/resources?type=vm", [{"vmid": 10001}]),
        ]
        for path, response in cases:
            with self.subTest(path=path, response=response):
                client = FakeClient()
                client.overrides["GET", path] = response
                with self.assertRaises(fleet.FleetError):
                    fleet.deploy(client, self.c, self.plan, lambda _: None)
                self.assertTrue(all(method == "GET" for method, _, _ in client.calls))

    def test_disk_sizing_rejects_unknown_sizes(self):
        with self.assertRaises(fleet.FleetError):
            fleet.disk_bytes({"sata0": "storage:disk"})
        with self.assertRaises(fleet.FleetError):
            fleet.disk_bytes({"sata0": "/dev/sda,size=64G"})
        self.assertEqual(fleet.disk_bytes({"sata0": "storage:disk,size=1.5T"}), int(1.5 * 1024**4))

    def test_malformed_api_data_fails_cleanly_before_writes(self):
        cases = [("/version", None), ("/cluster/resources?type=vm", [None]),
                 ("/nodes/pve/qemu/9000/config", None), ("/nodes/pve/network", {}),
                 ("/nodes/pve/storage/local-lvm/status", {"content": None}),
                 ("/nodes/pve/status", {"memory": {"free": "unknown"}})]
        for path, value in cases:
            with self.subTest(path=path):
                client = FakeClient()
                client.overrides["GET", path] = value
                with self.assertRaises(fleet.FleetError):
                    fleet.deploy(client, self.c, self.plan, lambda _: None)
                self.assertTrue(all(method == "GET" for method, _, _ in client.calls))

    def test_inherited_host_resources_and_unusable_nics_are_rejected(self):
        path = "/nodes/pve/qemu/9000/config"
        for key, value in (("hookscript", "local:snippets/hook.pl"), ("virtiofs0", "shared"),
                           ("parallel0", "/dev/parport0"), ("serial0", "/dev/ttyS0"),
                           ("numa0", "cpus=0-1"), ("net0", "virtio=AA:BB:CC:DD:EE:FF,link_down=1"),
                           ("net0", "unknown=AA:BB:CC:DD:EE:FF")):
            with self.subTest(key=key):
                client = FakeClient()
                template = client.request("GET", path)
                template[key] = value
                client.overrides["GET", path] = template
                with self.assertRaises(fleet.FleetError):
                    fleet.preflight(client, self.c, self.plan)


class DeployTests(unittest.TestCase):
    def test_clone_wait_configure_start_wait_order_and_network_preserved(self):
        c = config()
        client = FakeClient()
        events = []
        plan = fleet.make_plan(c)
        fleet.deploy(client, c, plan, events.append)
        writes = [(m, p, d) for m, p, d in client.calls if m != "GET"]
        self.assertEqual([(m, p.rsplit("/", 1)[-1]) for m, p, _ in writes],
                         [("POST", "clone"), ("PUT", "config"), ("POST", "start")])
        self.assertEqual(client.waits, ["UPID:pve:clone", "UPID:pve:start"])
        self.assertEqual(writes[0][2]["full"], 1)
        self.assertIn("firewall=1,tag=42,mtu=1450", writes[1][2]["net0"])
        self.assertIn(plan["instances"][0]["mac"], writes[1][2]["net0"])
        self.assertEqual(writes[1][2]["onboot"], 0)
        self.assertEqual(events[-1]["status"], "android_unverified")

    def test_failed_clone_never_configures_or_starts(self):
        client = FakeClient()
        client.fail_wait = True
        events = []
        with self.assertRaises(fleet.FleetError):
            fleet.deploy(client, config(), fleet.make_plan(config()), events.append)
        self.assertFalse(client.started)
        self.assertEqual(len([1 for m, _, _ in client.calls if m != "GET"]), 1)
        self.assertEqual(events[-1]["upid"], "UPID:pve:clone")

    def test_failure_journal_retains_task_for_recovery(self):
        client = FakeClient()
        client.fail_wait = True
        with tempfile.TemporaryDirectory() as tmp, patch.object(fleet, "ProxmoxClient", return_value=client):
            out = Path(tmp) / "deploy.json"
            with patch("sys.stderr", new_callable=io.StringIO):
                code = fleet.main(["deploy", "--config", str(EXAMPLE), "--out", str(out)])
            report = json.loads(out.read_text())
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["events"][-1]["upid"], "UPID:pve:clone")

    def test_journal_failure_stops_remote_writes_and_reports_on_stderr(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp, patch.object(fleet, "ProxmoxClient", return_value=client), patch.object(fleet, "write_report", side_effect=OSError("disk full")):
            out = Path(tmp) / "deploy.json"
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                code = fleet.main(["deploy", "--config", str(EXAMPLE), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertIn("journal_error", json.loads(stderr.getvalue()))
            self.assertTrue(all(method == "GET" for method, _, _ in client.calls))


class TransportTests(unittest.TestCase):
    def make_client(self):
        return fleet.ProxmoxClient(config(), "fleet@pve!qa", "test-secret")

    def test_token_header_and_url_encoded_body(self):
        client = self.make_client()
        with patch.object(client.opener, "open") as call:
            call.return_value.__enter__.return_value = io.StringIO('{"data": "UPID:pve:test"}')
            self.assertEqual(client.request("POST", "/example", {"name": "a b"}), "UPID:pve:test")
        req = call.call_args.args[0]
        self.assertEqual(req.get_header("Authorization"), "PVEAPIToken=fleet@pve!qa=test-secret")
        self.assertEqual(req.data, b"name=a+b")
        self.assertEqual(call.call_args.kwargs["timeout"], 30)

    def test_http_errors_do_not_echo_secrets_or_retry(self):
        client = self.make_client()
        with patch.object(client.opener, "open", side_effect=HTTPError("x", 403, "test-secret", {}, None)) as call:
            with self.assertRaises(fleet.FleetError) as exc:
                client.request("POST", "/example", {})
            self.assertNotIn("test-secret", str(exc.exception))
            self.assertEqual(call.call_count, 1)

    def test_redirects_never_forward_token(self):
        with self.assertRaises(fleet.FleetError):
            fleet.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere")

    def test_waits_for_completed_task_and_checks_exitstatus(self):
        client = self.make_client()
        with patch.object(client, "request", side_effect=[{"status": "running"}, {"status": "stopped", "exitstatus": "OK"}]) as call, patch.object(fleet.time, "sleep"):
            client.wait_task("pve", "UPID:pve:test", 10, 1)
            self.assertEqual(call.call_count, 2)
            self.assertIn("UPID%3Apve%3Atest", call.call_args.args[1])
        for status in ({"status": "stopped", "exitstatus": "ERROR"}, {"status": "stopped"}):
            with patch.object(client, "request", return_value=status):
                with self.assertRaises(fleet.FleetError):
                    client.wait_task("pve", "UPID:pve:test", 10, 1)

    def test_task_timeout_does_not_start_another_task(self):
        client = self.make_client()
        with patch.object(client, "request", return_value={"status": "running"}) as call, patch.object(fleet.time, "monotonic", side_effect=[0, 11]):
            with self.assertRaisesRegex(fleet.FleetError, "may still be running"):
                client.wait_task("pve", "UPID:pve:test", 10, 1)
            self.assertEqual(call.call_count, 1)

    def test_task_warnings_require_review(self):
        client = self.make_client()
        with patch.object(client, "request", return_value={"status": "stopped", "exitstatus": "WARNINGS: 1"}):
            with self.assertRaisesRegex(fleet.FleetError, "completed with warnings"):
                client.wait_task("pve", "UPID:pve:test", 10, 1)


if __name__ == "__main__":
    unittest.main()
