from rp.console import write, fail, info, warning, success
import rp.utils as utils
import rp.network as network
from rp.build import build
from sys import exit
import time
import random
from os.path import isdir, join


from subprocess import call


def run(
    directory: str,
    cpu: int,
    gpu: int,
    mem: int,
    outfile_name: str,
    script: str,
    final_docker_exec_command: str,
    debug: bool,
):
    if not utils.is_replik_project(directory):
        fail(f"{directory} is not valid rp directory.. exiting")
        exit()

    settings = utils.get_replik_settings(directory)

    unique_run_id = utils.get_unique_id(settings)
    tag = settings["tag"]

    write("Building docker image...")
    warning("Do not Ctrl+C while docker image is being build!")
    time.sleep(1.0)

    build(directory, outfile_name=outfile_name, script=script)

    success("docker image successfully build!")

    docker_shm = settings["docker_shm"]

    if cpu == -1:
        cpu = settings["cpu"]
    if mem == -1:
        mem = settings["memory"]
    if gpu == -1:
        gpu = settings["gpus"]

    is_server = network.make_me_server(debug=debug)
    if is_server:
        info("I'm authority!")
    time.sleep(0.1)

    START_TIME = time.time()

    # get a name:
    am_i_named = False
    while not am_i_named:
        name = network.give_me_a_name()
        if name is not None:
            am_i_named = True

    write(f"waiting to be scheduled as <{name}>")

    may_I_be_scheduled = False
    while not may_I_be_scheduled:
        may_I_be_scheduled, gpu_device_ids = network.may_I_be_scheduled(
            START_TIME,
            gpus=gpu,
            cpu=cpu,
            mem=mem,
            unique_id=unique_run_id,
            name=name,
            docker_image=tag,
            script=script,
        )
        if may_I_be_scheduled:
            break

        random_wait_in_s = random.uniform(5.0, 30.0)
        time.sleep(random_wait_in_s)

        if not is_server:
            # the tcp port operates as lock
            # if we cannot become server there is another
            # authority and we obey to them!
            is_server = network.make_me_server(debug=debug)
            if is_server:
                info("I'm authority!")

    assert gpu == len(gpu_device_ids)

    docker_exec_command = "docker run"
    docker_exec_command += f' --privileged --shm-size="{docker_shm}" '
    docker_exec_command += f'--memory="{mem}g" '
    docker_exec_command += f'--cpus="{cpu}" '

    if gpu > 0:
        docker_exec_command += "--gpus '" + '"device='
        for i, gpuid in enumerate(gpu_device_ids):
            if i > 0:
                docker_exec_command += ","
            docker_exec_command += str(gpuid)
        docker_exec_command += '"' + "' "

    # mount volumes
    project_name = settings["name"]

    docker_exec_command += f"-v {directory}:/home/user/{project_name} "

    for path_host in utils.get_paths_for_mapping(directory):
        if "/" not in path_host:
            path_host = join(directory, path_host)
        last_entry = path_host.split("/")[-1]
        if not isdir(path_host):
            fail(f"source path does not exist - cannot map! <{path_host}>")
            exit()

        path_container = f"/home/user/{last_entry}"
        docker_exec_command += f"-v {path_host}:{path_container} "

    docker_exec_command += f"--name {name} "
    docker_exec_command += f"--rm -it {tag} " + final_docker_exec_command

    info("scheduled!")
    call(docker_exec_command, shell=True)