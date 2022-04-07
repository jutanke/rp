import pwd
import os
import json
from os.path import join, isfile
from typing import Dict
from datetime import datetime
from time import time
import random

import multiprocessing
import subprocess

import psutil
from collections import namedtuple
from typing import List
from shutil import copyfile, move
import rp.console as console

from sys import exit


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

VERSION = "0.0.2"
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


CACHE = {}


def handle_broken_project(directory):
    if is_broken_project(directory):
        console.warning(
            "\nThis repo seems to be broken (interrupt during docker build)"
        )
        fname_bkp = join(directory, "docker/Dockerfile.bkp")
        fname_broken = join(directory, "docker/Dockerfile")
        move(fname_bkp, fname_broken)
        console.success("\tprobably fixed!\n")


def is_broken_project(directory: str) -> bool:
    """"""
    return isfile(join(directory, "docker/Dockerfile.bkp"))


def get_running_container_names_cached(cached_s=0.5):
    global CACHE
    key = "get_running_container_names"
    now = time()
    recalc = True
    if key in CACHE:
        last_time = CACHE[key]["last_time"]
        elapsed_in_s = now - last_time
        if elapsed_in_s < cached_s:
            recalc = False
    if recalc:
        names = get_running_container_names()
        CACHE[key] = {"last_time": now, "names": names}
    else:
        names = CACHE[key]["names"]
    return names


def get_stdout_file_in_container(directory: str, outfile_name: str = "") -> str:
    settings = get_replik_settings(directory)
    project_name = settings["name"]
    now = datetime.now()
    dt_string = now.strftime("%Y%m%d_%H%M%S")
    if len(outfile_name) == 0:
        return f"/home/user/{project_name}/.rp/logs/stdout_{dt_string}.log"
    else:
        return f"/home/user/{project_name}/.rp/logs/{outfile_name}_{dt_string}.log"


def get_free_resources_cached(cached_s=2.0, debug=False):
    """get resources is expensive! Query only once in a short time!"""
    global CACHE
    key = "get_free_resources"
    now = time()
    recalc = True
    if key in CACHE:
        last_time = CACHE[key]["last_time"]
        elapsed_in_s = now - last_time
        if elapsed_in_s < cached_s:
            recalc = False
    if recalc:
        if debug:
            print("[debug|get_free_resources_cached] recalc!")
        free_cpu, free_mem, free_gpus = get_free_resources(debug)
        CACHE[key] = {
            "last_time": now,
            "free_cpu": free_cpu,
            "free_mem": free_mem,
            "free_gpus": free_gpus,
        }
    else:
        if debug:
            print("[debug|get_free_resources_cached] cached!")
        free_cpu = CACHE[key]["free_cpu"]
        free_mem = CACHE[key]["free_mem"]
        free_gpus = CACHE[key]["free_gpus"]

    return free_cpu, free_mem, free_gpus


def get_free_resources(debug: bool):
    free_cpu = get_ncpu()
    free_mem, _ = get_memory()
    for proc in get_currently_running_docker_procs(debug=debug):
        free_cpu -= proc.cpu
        free_mem -= proc.mem

    free_gpus = get_free_gpu_device_ids()

    return free_cpu, free_mem, free_gpus


def get_unique_id(settings):
    """
    unique id for this run
    """
    rand = random.uniform(0.1, 2.5)
    txt = f"{settings['tag']}_{time()}_{rand}"
    return txt


def get_frozen_image_path(directory: str) -> str:
    """
    Path to the frozen image
    """
    info = utils.get_replik_settings(directory)
    project_name = info["name"]
    return join(get_dockerdir(directory), f"frozen_{project_name}_image.tar")


def get_dockerdir(directory: str) -> str:
    return join(directory, "docker")


def get_tempdockerdir(directory: str) -> str:
    unique_name = f"{time()}"
    path = join(directory, f".cache/rp/docker/{unique_name}")
    return path


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
    get the names of all currently running rp containers
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
        if len(f) > 0 and f.replace('"', "").startswith("rp")
    ]


def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(
        now_timestamp
    )
    return utc_datetime + offset


def get_currently_running_docker_procs(debug: bool) -> List[RunningProcess]:
    running_processes = []
    for container_name in get_running_container_names():
        if debug:
            print(
                f"[debug|get_currently_running_docker_procs] try to check container {container_name}"
            )
            _start = time()
        try:
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
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            start_time = datetime_from_utc_to_local(start_time).timestamp()

            container = json.loads(dev)

            cpu = container["NanoCpus"] / 1000000000
            shm_size = container["ShmSize"] / (1024 ** 3)
            mem = container["Memory"] / (1024 ** 3)

            if container["DeviceRequests"] is None:
                gpu_device_ids = None
            else:
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
            if debug:
                print(
                    f"[debug|get_currently_running_docker_procs] add running proc {container_name}"
                )
                print(f"\tcpu:{cpu} mem:{mem}, gpus:{device_ids}")
                print("\telapsed", time() - _start)
        except:
            print(
                f"[debug|get_currently_running_docker_procs] failed to load {container_name}"
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

        if dev == "null" or dev == "'null'" or dev is None:
            pass  # no GPU for this container!
        else:
            try:
                dev = str(dev)[1:-2]
                dev = json.loads(dev)
                if (
                    dev is not None
                    and dev[0] is not None
                    and dev[0]["DeviceIDs"] is not None
                ):
                    device_ids = [int(d) for d in dev[0]["DeviceIDs"]]
                    for device_id in device_ids:
                        gpus[device_id]["in_use"] = True
            except json.decoder.JSONDecodeError:
                print("-------------------------------")
                console.fail("[get_gpus] crashed json decoder:")
                print(f"container: {container_name}")
                print("failed string:")
                print(dev)
                print("-------------------------------")

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
        query = query.split(", ")
        assert len(query) == 2
        pid = query[0]
        gpu_uuid = query[1]
        device_id = gpu_uid_to_device_id[gpu_uuid]
        gpus[device_id]["in_use"] = True

    return gpus


def get_free_gpu_device_ids():
    gpus = get_gpus()
    free_device_ids = []
    for device_id in gpus.keys():
        if not gpus[device_id]["in_use"]:
            free_device_ids.append(device_id)
    return free_device_ids
