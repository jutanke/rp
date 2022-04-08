import click
import multiprocessing
from sys import exit

multiprocessing.freeze_support()
import subprocess
from rp.console import fail

from rp.utils import VERSION
from rp.init import init
from rp.kill import kill
from rp.run import run
from rp.info import info
from rp.freeze import freeze
import os


@click.command()
@click.argument("tool")
@click.option("--script", default="demo.sh")
@click.option("--cpu", default=-1)
@click.option("--gpu", default=-1)
@click.option("--mem", default=-1)
@click.option("--pid", default=-1)
@click.option("--outfile_name", default="")
@click.option("--detach", is_flag=False)
@click.option("--debug", is_flag=True)
def rp(tool, script, cpu, gpu, mem, pid, outfile_name, debug, detach):
    path = os.getcwd()

    if tool == "init":
        init(path, cpu=cpu, gpu=gpu, mem=mem)
    elif tool == "run":
        run(
            path,
            cpu=cpu,
            gpu=gpu,
            mem=mem,
            outfile_name=outfile_name,
            script=script,
            final_docker_exec_command="/bin/bash /home/user/run.sh",
            debug=debug,
            detach=detach,
        )
    elif tool == "enter":
        if detach:
            fail("Cannot `enter` while `--detach=True`. Exiting...")
            exit()
        run(
            path,
            cpu=cpu,
            gpu=gpu,
            mem=mem,
            outfile_name=outfile_name,
            script=script,
            final_docker_exec_command="/bin/bash",
            debug=debug,
            detach=False,
        )
    elif tool == "info":
        info(path, debug=debug)
    elif tool == "freeze":
        freeze(path, debug=debug)
    elif tool == "kill":
        kill(pid)
    else:
        fail(f"tool <{tool}> not found")


if __name__ == "__main__":
    rp()
