from rp.console import write, fail, info, warning, success
import rp.utils as utils
import os
from os.path import join, isfile, isdir
from os import makedirs
import json
from sys import exit


def init(directory: str, cpu: int, gpu: int, mem: int):

    if cpu == -1:
        cpu = 1
    if gpu == -1:
        gpu = 0
    if mem == -1:
        mem = 3

    write("\n[rp]")

    if utils.is_replik_project(directory):
        fail(f"Directory already contains a <rp> project!")
        exit()

    project_name = directory.split("/")[-1].lower()
    info(f"initialize at {directory}")

    # create folders
    cache_dir = join(directory, ".cache")
    output_dir = join(directory, "output")
    if not isdir(cache_dir):
        makedirs(cache_dir)
    if not isdir(output_dir):
        makedirs(output_dir)

    username = utils.get_username()
    info(f"project name: {project_name}")
    info(f"user: {username}")

    print("\n")

    rp_info = {
        "name": project_name,
        "username": username,
        "tag": f"{username}/rp_{project_name}",
        "docker_shm": "64g",
        "memory": mem,
        "cpu": cpu,
        "gpus": gpu,
        "rp_version": utils.VERSION,
        "stdout_to_file": False,
    }

    os.makedirs(utils.get_local_replik_dir(directory))
    os.makedirs(join(utils.get_local_replik_dir(directory), "logs"))
    docker_dir = join(directory, "docker")
    os.makedirs(docker_dir)

    # handle .gitignore
    gitignore_file = join(directory, ".gitignore")
    with open(gitignore_file, "a+") as f:
        f.write("output/\n")
        f.write(".cache/\n")
        f.write(".replik_paths.json\n")

    with open(utils.get_paths_fname(directory), "w") as f:
        json.dump(["output", ".cache"], f, indent=4, sort_keys=True)

    with open(join(docker_dir, "hook_post_useradd"), "w") as f:
        f.write("# add Dockerfile RUN's that are executed after the user is set\n")
        f.write('RUN echo "after-user hook"\n')

    with open(join(docker_dir, "hook_pre_useradd"), "w") as f:
        f.write("# add Dockerfile RUN's that are executed before the user is set\n")
        f.write('RUN echo "pre-user hook"\n')

    with open(join(docker_dir, "bashhook.sh"), "w") as f:
        f.write('if [[ -z "${BASHHOOKEXEC}" ]]; then\n')
        f.write('\techo "bashhook"\n')
        f.write("\texport BASHHOOKEXEC=1\n")
        f.write("fi\n")

    with open(join(docker_dir, ".dockerignore"), "w") as f:
        f.write("*.sh\n")
        f.write("data/\n")

    with open(join(docker_dir, "Dockerfile"), "w") as f:
        f.write("FROM nvidia/cuda:11.3.1-cudnn8-runtime-ubuntu20.04\n\n")
        f.write("ENV DEBIAN_FRONTEND noninteractive\n")
        f.write("ENV PATH /opt/miniconda3/bin:$PATH\n")
        f.write("ENV CPLUS_INCLUDE_PATH /opt/miniconda3/include\n\n")

        f.write("RUN apt-get update && apt-get install -y apt-file && apt upgrade -y\n")
        f.write(
            "RUN apt install -y build-essential curl git cmake pkg-config checkinstall\n\n"
        )
        f.write(
            "RUN curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh\n"
        )
        f.write("RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/miniconda3\n")
        f.write("RUN conda update -y -n base -c defaults conda\n")
        f.write("RUN conda install -y pip\n")

    with open(join(directory, "demo.sh"), "w") as f:
        f.write('echo "rp-demo"')

    with open(utils.replik_root_file(directory), "w") as f:
        json.dump(rp_info, f, indent=4, sort_keys=True)
