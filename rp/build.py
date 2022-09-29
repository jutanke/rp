import os
from os.path import join
import rp.utils as utils
import rp.console as console
from shutil import copyfile, copytree, move
from sys import exit
from subprocess import call
import subprocess


def build(directory: str, outfile_name: str, script: str):
    utils.handle_broken_project(directory)
    dockerdir = utils.get_dockerdir(directory)

    tmp_dockerdir = utils.get_tempdockerdir(directory)

    copytree(dockerdir, tmp_dockerdir)

    dockerdir = tmp_dockerdir

    dockerfile = join(dockerdir, "Dockerfile")
    dockerfile_bkp = join(dockerdir, "Dockerfile.bkp")
    hook_pre_useradd = join(dockerdir, "hook_pre_useradd")
    hook_post_useradd = join(dockerdir, "hook_post_useradd")

    info = utils.get_replik_settings(directory)

    tag = info["tag"]
    project_name = info["name"]
    docker_mem = info["docker_shm"]
    stdout_to_file = info["stdout_to_file"]

    if len(outfile_name) > 0 or stdout_to_file:
        if utils.check_if_string_contains_forbidden_symbols(outfile_name):
            console.fail(f"outfile contains forbidden symbols {outfile_name}")
            exit()
        outfile_name = utils.get_stdout_file_in_container(directory, outfile_name)
        console.info(f"write all output to <{outfile_name}>")
        stdout_to_file = True

    # -- BUILD DOCKERFILE
    # this part is SUUUPER brittle so continue with care!
    move(dockerfile, dockerfile_bkp)

    with open(dockerfile, "w") as D:
        with open(dockerfile_bkp) as D_base:
            for line in D_base:
                D.write(line)
        D.write("\n")
        with open(hook_pre_useradd) as hook:
            for line in hook:
                D.write(line)
        D.write("\n")

        # add user
        uid = os.getuid()
        D.write(f'RUN adduser --disabled-password --gecos "" -u {uid} user')
        D.write("\nUSER user\n")

        with open(hook_post_useradd) as hook:
            for line in hook:
                D.write(line)

        # add the script call
        D.write("\n")

        pipe = ""
        if stdout_to_file:
            pipe = f" &>{outfile_name}"

        D.write(
            'RUN echo "'
            + f"source /home/user/{project_name}/docker/bashhook.sh\\n"
            + f'cd /home/user/{project_name} && bash {script}{pipe}"'
            + " >> /home/user/run.sh"
        )

        # add startup bash hook:
        # THIS IS ONLY RELEVANT WHEN ```rp enter```
        D.write("\n")
        D.write(
            f'RUN echo "/bin/bash /home/user/{project_name}/docker/bashhook.sh" >> /home/user/.bashrc'
        )

    r = call(f"cd {dockerdir} && docker build --tag='{tag}' .", shell=True)

    # move(dockerfile_bkp, dockerfile)
    if r != 0:
        console.fail("building failed\n")
        exit(0)
