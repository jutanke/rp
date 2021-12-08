from rp.console import write, fail, info, warning, success
import rp.utils as utils
import rp.network as network
from sys import exit


def run(directory: str, cpu: int, gpu: int, mem: int):
    if not utils.is_replik_project(directory):
        fail(f"{directory} is not valid rp directory.. exiting")
        exit()

    settings = utils.get_replik_settings(directory)

    if cpu == -1:
        cpu = settings["cpu"]
    if mem == -1:
        mem = settings["memory"]
    if gpu == -1:
        gpu = settings["gpus"]

    print("cpu", cpu, gpu, mem)
    print("settings", settings)

    gpus = utils.get_gpus()

    print("gpus", gpus)
