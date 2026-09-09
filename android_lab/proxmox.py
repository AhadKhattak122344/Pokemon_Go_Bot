"""Plan, inspect, and provision a single-node Proxmox Android test fleet.

Python 3.11+, standard library only. `plan` never connects to a host. `preflight`
only reads. `deploy` explicitly clones a prepared template and starts the clones;
it does not install Android or establish app compatibility.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
import uuid


class FleetError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise FleetError(message)


def integer(value, label, low, high):
    require(type(value) is int and low <= value <= high,
            f"{label} must be an integer from {low} to {high}")


def object_response(value, label):
    require(isinstance(value, dict), f"Malformed {label}: expected an object")
    return value


def list_response(value, label):
    require(isinstance(value, list) and all(isinstance(item, dict) for item in value),
            f"Malformed {label}: expected a list of objects")
    return value


def byte_count(value, label):
    require(type(value) is int and value >= 0, f"Malformed {label}: expected non-negative bytes")
    return value


def validate_config(config):
    require(isinstance(config, dict), "Configuration must be a JSON object")
    required = {"host", "node", "template_vmid", "storage", "bridge", "cores",
                "memory_mib", "namespace_uuid", "instances"}
    optional = {"reserve_memory_mib", "reserve_storage_gib", "task_timeout_s",
                "poll_interval_s", "ca_file"}
    require(required <= config.keys(), f"Missing settings: {sorted(required - config.keys())}")
    require(config.keys() <= required | optional, "Unknown configuration setting")
    c = dict(config)
    c.setdefault("reserve_memory_mib", 4096)
    c.setdefault("reserve_storage_gib", 20)
    c.setdefault("task_timeout_s", 1800)
    c.setdefault("poll_interval_s", 2)
    require(isinstance(c["host"], str), "host must be an HTTPS URL")
    try:
        host = urlsplit(c["host"])
        valid_port = host.port is None or 1 <= host.port <= 65535
    except ValueError as exc:
        raise FleetError("Invalid host URL") from exc
    require(host.scheme == "https" and host.hostname and valid_port
            and not host.username and not host.password and not host.query
            and not host.fragment and host.path in ("", "/", "/api2/json")
            and not re.search(r"\s", c["host"]),
            "host must be https://HOST:8006 without credentials, query, or extra path")
    c["host"] = f"https://{host.netloc}"
    for key in ("node", "storage", "bridge"):
        require(isinstance(c[key], str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", c[key]),
                f"Invalid {key}")
    for key, low, high in (("template_vmid", 100, 999999999), ("cores", 1, 256),
                           ("memory_mib", 1024, 1048576), ("reserve_memory_mib", 0, 1048576),
                           ("reserve_storage_gib", 0, 1048576), ("task_timeout_s", 1, 86400),
                           ("poll_interval_s", 1, 10)):
        integer(c[key], key, low, high)
    try:
        c["namespace_uuid"] = str(uuid.UUID(c["namespace_uuid"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise FleetError("namespace_uuid must be a UUID; generate one per fleet") from exc
    require(isinstance(c["instances"], list) and 1 <= len(c["instances"]) <= 100,
            "instances must contain 1 to 100 entries")
    ids, names = {c["template_vmid"]}, set()
    for item in c["instances"]:
        require(isinstance(item, dict) and set(item) == {"vmid", "name"},
                "Each instance needs exactly vmid and name")
        integer(item["vmid"], "instance vmid", 100, 999999999)
        require(item["vmid"] not in ids, "Duplicate VMID or VMID equals template")
        require(isinstance(item["name"], str) and len(item["name"]) <= 63
                and re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]|[a-zA-Z]", item["name"]),
                "Instance names must be valid single-label hostnames")
        require(item["name"].lower() not in names, "Duplicate instance name")
        ids.add(item["vmid"])
        names.add(item["name"].lower())
    if "ca_file" in c:
        require(isinstance(c["ca_file"], str) and c["ca_file"], "ca_file must be a path")
    return c


def make_plan(config):
    c = validate_config(config)
    instances = []
    namespace = uuid.UUID(c["namespace_uuid"])
    for item in c["instances"]:
        identity = uuid.uuid5(namespace, f"vm:{item['vmid']}")
        # Locally administered, unicast; VM identity, not Android attestation.
        mac = ":".join(f"{byte:02X}" for byte in bytes([0x02]) + identity.bytes[:5])
        instances.append({**item, "mac": mac, "smbios_uuid": str(identity)})
    require(len({i["mac"] for i in instances}) == len(instances), "Generated MAC collision")
    return {"status": "planned_offline", "host": c["host"], "node": c["node"],
            "template_vmid": c["template_vmid"], "storage": c["storage"],
            "bridge": c["bridge"], "cores_each": c["cores"],
            "memory_mib_each": c["memory_mib"], "instances": instances,
            "total_vcpus": c["cores"] * len(instances),
            "total_memory_mib": c["memory_mib"] * len(instances),
            "android_readiness": "unverified", "disk_policy": "full clone; inherit template disks"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FleetError("API redirect rejected; use the direct Proxmox HTTPS endpoint")


class ProxmoxClient:
    def __init__(self, config, token_id, token_secret):
        require(isinstance(token_id, str) and re.fullmatch(r"[^\s=!]+@[^\s=!]+![^\s=!]+", token_id),
                "Set PVE_TOKEN_ID to USER@REALM!TOKENID")
        require(isinstance(token_secret, str) and token_secret and not re.search(r"\s", token_secret),
                "Set PVE_TOKEN_SECRET to the API token value")
        self.base = config["host"] + "/api2/json"
        self.authorization = f"PVEAPIToken={token_id}={token_secret}"
        context = ssl.create_default_context(cafile=config.get("ca_file"))
        self.opener = build_opener(HTTPSHandler(context=context), NoRedirect())

    def request(self, method, path, data=None):
        encoded = urlencode(data).encode() if data is not None else None
        req = Request(self.base + path, data=encoded, method=method,
                      headers={"Authorization": self.authorization,
                               "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with self.opener.open(req, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as exc:
            # Don't echo bodies/headers that could contain credentials.
            raise FleetError(f"Proxmox {method} {path} returned HTTP {exc.code}; check task/host logs and ACLs") from None
        except (URLError, TimeoutError, OSError) as exc:
            raise FleetError(f"Proxmox {method} {path} connection failed ({type(exc).__name__}); check DNS/TLS/network. "
                             "A timed-out write may still be running; inspect Proxmox before retrying.") from None
        except (ValueError, UnicodeError):
            raise FleetError("Proxmox returned invalid JSON") from None
        require(isinstance(payload, dict) and "data" in payload, "Malformed Proxmox API response")
        return payload["data"]

    def wait_task(self, node, upid, timeout_s, poll_s):
        require(isinstance(upid, str) and upid.startswith("UPID:"), "Expected Proxmox task UPID")
        deadline = time.monotonic() + timeout_s
        while True:
            status = self.request("GET", f"/nodes/{node}/tasks/{quote(upid, safe='')}/status")
            require(isinstance(status, dict), "Malformed task status")
            if status.get("status") == "stopped":
                if str(status.get("exitstatus", "")).startswith("WARNINGS:"):
                    raise FleetError(f"Task completed with warnings: {upid}; review the task log before continuing")
                require(status.get("exitstatus") == "OK", f"Task failed: {upid}; inspect Proxmox task log")
                return
            require(status.get("status") == "running", f"Unknown state for task {upid}")
            remaining = deadline - time.monotonic()
            require(remaining > 0, f"Task timed out: {upid}; it may still be running. Inspect before retrying")
            time.sleep(min(poll_s, remaining))


def disk_bytes(template):
    total = 0
    for key, value in template.items():
        if not re.fullmatch(r"(?:scsi|sata|virtio|ide)\d+|efidisk0|tpmstate0", key):
            continue
        if "media=cdrom" in str(value) or str(value).startswith("none"):
            continue
        require(not str(value).startswith("/"), "Passthrough disks require manual deployment")
        size = re.search(r"(?:^|,)size=(\d+(?:\.\d+)?)([KMGT]?)B?(?:,|$)", str(value))
        require(size is not None, f"Template {key} lacks a known disk size")
        total += math.ceil(float(size[1]) * 1024 ** (" KMGT".index(size[2]) if size[2] else 0))
    require(total > 0, "Template has no sized virtual disks")
    return total


def preflight(client, config, plan):
    c = config
    base = f"/nodes/{c['node']}"
    version = object_response(client.request("GET", "/version"), "version")
    resources = list_response(client.request("GET", "/cluster/resources?type=vm"), "cluster VM inventory")
    for vm in resources:
        integer(vm.get("vmid"), "inventory VMID", 100, 999999999)
        require(isinstance(vm.get("name", ""), str), "Malformed inventory VM name")
    existing = {v["vmid"] for v in resources}
    require(not existing.intersection(i["vmid"] for i in plan["instances"]),
            "A target VMID already exists; no existing VM will be overwritten or adopted")
    names = {v.get("name", "").lower() for v in resources}
    require(not names.intersection(i["name"].lower() for i in plan["instances"]),
            "A target VM name already exists")
    source = next((v for v in resources if v.get("vmid") == c["template_vmid"]), None)
    require(source and source.get("node") == c["node"] and source.get("type") == "qemu",
            "Template must be a visible QEMU VM on the configured node")
    template = object_response(client.request("GET", f"{base}/qemu/{c['template_vmid']}/config"), "template config")
    state = object_response(client.request("GET", f"{base}/qemu/{c['template_vmid']}/status/current"), "template state")
    require(template.get("template") == 1, "Source VM must already be converted to a template")
    require(state.get("status") == "stopped" and not template.get("lock"), "Template must be stopped and unlocked")
    require("net0" in template and not any(re.fullmatch(r"net[1-9]\d*", k) for k in template),
            "Automation supports a template with exactly one NIC (net0)")
    require(not any(re.fullmatch(r"(?:hostpci|usb|virtiofs|parallel|numa)\d+", k) for k in template)
            and not any(re.fullmatch(r"serial\d+", k) and v != "socket" for k, v in template.items())
            and not any(template.get(k) for k in ("args", "hookscript", "vcpus")),
            "Templates with passthrough/shared devices, hooks, custom topology, or QEMU args need manual review")
    require(not any("cloudinit" in str(v) for k, v in template.items()
                    if re.fullmatch(r"(?:ide|scsi|sata|virtio)\d+", k)),
            "Cloud-init drives are not supported by this Android clone workflow")
    require(isinstance(template["net0"], str), "Malformed template net0")
    for item in plan["instances"]:
        network_config(template["net0"], c["bridge"], item["mac"])
    networks = list_response(client.request("GET", f"{base}/network"), "node network inventory")
    require(any(n.get("iface") == c["bridge"] and n.get("type") in ("bridge", "OVSBridge")
                and n.get("active") == 1 for n in networks), "Configured bridge is missing or inactive")
    storage = object_response(client.request("GET", f"{base}/storage/{c['storage']}/status"), "storage status")
    require(isinstance(storage.get("content"), str), "Malformed storage content types")
    require(storage.get("active") == 1 and storage.get("enabled") == 1
            and "images" in storage.get("content", "").split(","),
            "Target storage must be active, enabled, and support disk images")
    required_disk = disk_bytes(template) * len(plan["instances"]) + c["reserve_storage_gib"] * 1024**3
    require(byte_count(storage.get("avail"), "storage availability") >= required_disk,
            "Insufficient free storage for full clones plus reserve")
    node = object_response(client.request("GET", f"{base}/status"), "node status")
    memory = object_response(node.get("memory"), "node memory")
    required_memory = (plan["total_memory_mib"] + c["reserve_memory_mib"]) * 1024**2
    require(byte_count(memory.get("available", memory.get("free")), "available memory") >= required_memory,
            "Insufficient available node RAM for all clones plus reserve")
    source_mac = template["net0"].split(",")[0].split("=")[-1].upper()
    require(source_mac not in {i["mac"] for i in plan["instances"]}, "Clone MAC collides with template")
    return {"status": "preflight_passed_android_unverified", "version": version,
            "required_storage_bytes_including_reserve": required_disk,
            "required_memory_bytes_including_reserve": required_memory,
            "template_config": template,
            "note": "Read checks do not prove clone/config/start write permissions or Android compatibility."}


def network_config(template_net, bridge, mac):
    parts = template_net.split(",")
    model = parts[0].split("=")[0]
    require(model in {"virtio", "e1000", "e1000e", "rtl8139", "vmxnet3", "ne2k_pci", "pcnet", "i82551", "i82557b", "i82559er"},
            "Unknown template NIC model")
    # Preserve VLAN, firewall, MTU, queues, rate, etc. Only MAC/bridge change.
    other = [p for p in parts[1:] if not p.startswith(("bridge=", "macaddr="))]
    require("link_down=1" not in other, "Template NIC link is disabled")
    return ",".join([f"{model}={mac}", f"bridge={bridge}", *other])


def deploy(client, config, plan, record):
    checked = preflight(client, config, plan)
    c = config
    base = f"/nodes/{c['node']}/qemu"
    # Validate every generated network setting before the first write.
    nets = {i["vmid"]: network_config(checked["template_config"]["net0"], c["bridge"], i["mac"])
            for i in plan["instances"]}
    for item in plan["instances"]:
        vmid = item["vmid"]
        for stage, method, path, data in (
            ("clone", "POST", f"{base}/{c['template_vmid']}/clone",
             {"newid": vmid, "name": item["name"], "full": 1, "storage": c["storage"]}),
            ("configure", "PUT", f"{base}/{vmid}/config",
             {"net0": nets[vmid], "smbios1": f"uuid={item['smbios_uuid']}",
              "cores": c["cores"], "sockets": 1, "memory": c["memory_mib"], "balloon": 0,
              "onboot": 0, "description": "Android test fleet; Android/app readiness must be verified separately."}),
            ("start", "POST", f"{base}/{vmid}/status/start", {}),
        ):
            # Persist intent before a request whose response could time out.
            record({"vmid": vmid, "stage": stage, "status": "requesting"})
            result = client.request(method, path, data)
            if stage != "configure" or result is not None:
                require(isinstance(result, str) and result.startswith("UPID:"), "Expected task UPID after write")
                record({"vmid": vmid, "stage": stage, "status": "running", "upid": result})
                client.wait_task(c["node"], result, c["task_timeout_s"], c["poll_interval_s"])
            record({"vmid": vmid, "stage": stage, "status": "complete"})
        state = object_response(client.request("GET", f"{base}/{vmid}/status/current"), "clone state")
        require(state.get("status") == "running", f"VM {vmid} did not reach running state")
        record({"vmid": vmid, "stage": "provisioned", "status": "android_unverified"})


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "preflight", "deploy"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = {"status": "in_progress", "events": []}
    output_created = False
    try:
        require(args.action != "deploy" or args.out is not None, "deploy requires --out for its task journal")
        if args.out:
            require(args.out.resolve() != args.config.resolve(), "Report must not overwrite configuration")
            require(not args.out.exists(), "Report already exists; use a new --out path to preserve evidence")
        config = validate_config(json.loads(args.config.read_text(encoding="utf-8-sig")))
        if config.get("ca_file"):
            config["ca_file"] = str((args.config.parent / config["ca_file"]).resolve())
        plan = make_plan(config)
        report["plan"] = plan
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Reserve a fresh journal atomically; don't race another invocation.
            with args.out.open("x", encoding="utf-8") as output:
                output_created = True
                output.write(json.dumps(report, indent=2) + "\n")
        def record(event):
            report["events"].append(event)
            if args.out:
                write_report(args.out, report)
        if args.action == "plan":
            report["status"] = "planned_offline"
        else:
            client = ProxmoxClient(config, os.environ.get("PVE_TOKEN_ID"), os.environ.get("PVE_TOKEN_SECRET"))
            if args.action == "preflight":
                result = preflight(client, config, plan)
                result.pop("template_config")
                report.update(result)
            else:
                deploy(client, config, plan, record)
                report["status"] = "provisioned_android_unverified"
        if args.out:
            write_report(args.out, report)
        print(json.dumps(report, indent=2))
        return 0
    except (FleetError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        # Only update an output this run successfully created.
        if output_created:
            try:
                write_report(args.out, report)
            except OSError:
                report["journal_error"] = "Could not update the journal; the last recorded remote operation may still be running."
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
