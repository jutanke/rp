import pwd
import os
import json
from os.path import join, isfile
from typing import Dict
from datetime import datetime

import multiprocessing
import subprocess


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


def get_gpus():
    GPU_WHITELIST = [
        "GeForce RTX 2080 Ti",
        "GeForce RTX 3090",
        "GeForce GTX 1080 Ti",
        "TITAN RTX",
    ]

    gpus = {}  # gpu-id -> {}
    for gpuid, name in enumerate(
        [
            f
            for f in subprocess.run(
                ["nvidia-smi", "--query-gpu=gpu_name", "--format=csv"],
                stdout=subprocess.PIPE,
            )
            .stdout.decode("utf-8")
            .split("\n")
            if len(f) > 0 and f != "name"
        ]
    ):
        # print(f"{gpuid} _. {name}", len(name))
        gpus[gpuid] = {"name": name, "in_use": False, "by": None}

    for container_name in get_running_container_names():

        dev = subprocess.run(
            ["docker",
            "inspect",
            "--format='{{json .HostConfig.DeviceRequests}}'",
            container_name]
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")

        print("~~", dev)
