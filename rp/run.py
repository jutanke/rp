from rp.console import write, fail, info, warning, success
import rp.utils as utils
import rp.network as network
from sys import exit
import time
import random


def run(directory: str, cpu: int, gpu: int, mem: int):
    if not utils.is_replik_project(directory):
        fail(f"{directory} is not valid rp directory.. exiting")
        exit()

    settings = utils.get_replik_settings(directory)

    unique_run_id = utils.get_unique_id(settings)

    write("Building docker image...")
    warning("Do not Ctrl+C while docker image is being build!")

    success("docker image successfully build!")

    if cpu == -1:
        cpu = settings["cpu"]
    if mem == -1:
        mem = settings["memory"]
    if gpu == -1:
        gpu = settings["gpus"]

    print("cpu", cpu, gpu, mem)
    print("settings", settings)

    print("unique_run_id", unique_run_id)

    # gpus = utils.get_gpus()

    # print("gpus", gpus)

    is_alive = network.is_server_alive()
    print("is_alive(1)", is_alive)

    is_server = network.make_me_server()
    if is_server:
        info("I'm authority!")

    time.sleep(0.1)

    START_TIME = time.time()

    while not network.may_I_be_scheduled(
        START_TIME, gpus=gpu, cpu=cpu, mem=mem, unique_id=unique_run_id
    ):
        random_wait_in_s = random.uniform(1.5, 3.5)
        time.sleep(random_wait_in_s)

        if not is_server:
            # the tcp port operates as lock
            # if we cannot become server there is another
            # authority and we obey to them!
            is_server = network.make_me_server()
            if is_server:
                info("I'm authority!")

    # print("is_server", is_server)

    print("EXEC")
    time.sleep(1000)

    # is_alive = network.is_server_alive()
    # print("is_alive(2)", is_alive)
