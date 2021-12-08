import pwd
import os
import json
from os.path import join, isfile
from typing import Dict
from datetime import datetime
from time import time

import multiprocessing
import subprocess

import psutil
from collections import namedtuple
from typing import List

RunningProcess = namedtuple(
    "RunningProcess",
    [
        "cpu",
        "mem",
        "shm_size",
        "gpu_devices",
        "image_name",
        "docker_name",
        "start_time",
    ],
)

VERSION = "0.0.1"
FORBIDDEN_CHARACTERS = [
    " ",
    "%",
    "^",
    "&",
    "/",
    "\\",
    ".",
    "?",
    "$",
    "#",
    "'",
    '"',
    "!",
    ",",
    ".",
    ":",
    ";",
    "*",
    "(",
    ")",
    "[",
    "]",
    "-",
    "+",
    "=",
    "{",
    "}",
]


def check_if_string_contains_forbidden_symbols(txt: str) -> bool:
    global FORBIDDEN_CHARACTERS
    for c in FORBIDDEN_CHARACTERS:
        if c in txt:
            return True
    return False


def get_username():
    """"""
    return pwd.getpwuid(os.getuid()).pw_gecos.lower().replace(" ", "_")


def get_local_replik_dir(directory: str) -> str:
    return join(directory, ".rp")


def get_paths_fname(directory: str):
    """
    ["/path/to/file1", "/path/to/file2", ...]
    """
    return join(directory, ".rp/paths.json")


def get_dockerdir(directory: str) -> str:
    return join(directory, "docker")


def replik_root_file(directory: str) -> str:
    """
    {root}/.rp
    """
    return join(directory, ".rp/info.json")


def is_replik_project(directory: str) -> bool:
    """"""
    return isfile(replik_root_file(directory))


def get_replik_settings(directory: str) -> Dict:
    """"""
    if not is_replik_project(directory):
        console.fail(f"Directory {directory} is no rp project")
        exit(0)  # exit program
    replik_fname = replik_root_file(directory)
    with open(replik_fname, "r") as f:
        return json.load(f)


def get_ncpu():
    return multiprocessing.cpu_count()


def get_memory():
    mem = psutil.virtual_memory()
    total = mem.total / (1024.0 ** 3)
    available = mem.available / (1024.0 ** 3) * 0.95
    return int(total), int(available)


def get_paths_for_mapping(directory):
    assert is_replik_project(directory=directory)
    fname = get_paths_fname(directory)
    with open(fname, "r") as f:
        return json.load(f)


def get_running_container_names():
    """
    get the names of all currently running containers
    """
    return [
        f.replace('"', "")
        for f in (
            subprocess.run(
                ["docker", "ps", "--format", '"{{.Names}}"'], stdout=subprocess.PIPE
            )
            .stdout.decode("utf-8")
            .lower()
            .split("\n")
        )
        if len(f) > 0
    ]


def get_currently_running_docker_procs() -> List[RunningProcess]:
    running_processes = []
    for container_name in get_running_container_names():
        dev = subprocess.run(
            [
                "docker",
                "inspect",
                "--format='{{json .HostConfig}}'",
                container_name,
            ],
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")[1:-2]

        image_name = subprocess.run(
            [
                "docker",
                "inspect",
                "--format='{{json .Config.Image}}'",
                container_name,
            ],
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")[2:-3]

        start_time = subprocess.run(
            [
                "docker",
                "inspect",
                "--format='{{json .State.StartedAt}}'",
                container_name,
            ],
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")[1:-2]
        start_time = start_time.replace('"', "").replace("T", " ")
        end_pt = start_time.find(
            "."
        )  # the nanosec confuse the converter and they don't matter anyways
        start_time = start_time[:end_pt]
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp()

        container = json.loads(dev)

        cpu = container["NanoCpus"] / 1000000000
        shm_size = container["ShmSize"] / (1024 ** 3)
        mem = container["Memory"] / (1024 ** 3)

        gpu_device_ids = container["DeviceRequests"][0]["DeviceIDs"]

        device_ids = []
        if gpu_device_ids is not None:
            for did in gpu_device_ids:
                device_ids.append(int(did))

        running_processes.append(
            RunningProcess(
                cpu=cpu,
                mem=mem,
                shm_size=shm_size,
                gpu_devices=device_ids,
                docker_name=container_name,
                image_name=image_name,
                start_time=start_time,
            )
        )
    return list(sorted(running_processes, key=lambda p: p.start_time))


def get_gpus():
    GPU_WHITELIST = [
        "GeForce RTX 2080 Ti",
        "GeForce RTX 3090",
        "GeForce GTX 1080 Ti",
        "TITAN RTX",
    ]

    gpu_uid_to_device_id = {}
    gpus = {}  # device_id -> {}
    for device_id, query in enumerate(
        [
            f
            for f in subprocess.run(
                ["nvidia-smi", "--query-gpu=gpu_name,gpu_uuid", "--format=csv"],
                stdout=subprocess.PIPE,
            )
            .stdout.decode("utf-8")
            .split("\n")
            if len(f) > 0 and not f.startswith("name")
        ]
    ):
        query = query.split(", ")
        name = query[0]
        uuid = query[1]
        gpu_uid_to_device_id[uuid] = device_id
        gpus[device_id] = {"name": name, "in_use": False, "by": None, "uuid": uuid}

    for container_name in get_running_container_names():
        dev = subprocess.run(
            [
                "docker",
                "inspect",
                "--format='{{json .HostConfig.DeviceRequests}}'",
                container_name,
            ],
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")

        if dev == "null":
            pass  # no GPU for this container!
        else:
            dev = str(dev)[1:-2]
            dev = json.loads(dev)

            if dev[0]["DeviceIDs"] is not None:
                device_ids = [int(d) for d in dev[0]["DeviceIDs"]]
                for device_id in device_ids:
                    gpus[device_id]["in_use"] = True

    # check for 'rogue' processes on GPUs
    procs = (
        subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid", "--format=csv"],
            stdout=subprocess.PIPE,
        )
        .stdout.decode("utf-8")
        .split("\n")
    )
    procs = [p for p in procs if len(p) > 0 and not p.startswith("pid")]
    for query in procs:
        query = procs[i].split(", ")
        assert len(query) == 2
        pid = query[0]
        gpu_uuid = query[1]
        device_id = gpu_uid_to_device_id[gpu_uuid]
        gpus[device_id]["in_use"] = True

    return gpus
