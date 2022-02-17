import click
import multiprocessing

multiprocessing.freeze_support()
import subprocess
from rp.console import fail

from rp.utils import VERSION
from rp.init import init
from rp.kill import kill
from rp.run import run
from rp.info import info
import os


@click.command()
@click.argument("tool")
@click.option("--script", default="demo.sh")
@click.option("--cpu", default=-1)
@click.option("--gpu", default=-1)
@click.option("--mem", default=-1)
@click.option("--pid", default=-1)
@click.option("--outfile_name", default="")
@click.option("--debug", is_flag=True)
def rp(tool, script, cpu, gpu, mem, pid, outfile_name, debug):
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
        )
    elif tool == "enter":
        run(
            path,
            cpu=cpu,
            gpu=gpu,
            mem=mem,
            outfile_name=outfile_name,
            script=script,
            final_docker_exec_command="/bin/bash",
            debug=debug,
        )
    elif tool == "info":
        info(path, debug=debug)
    elif tool == "kill":
        kill(pid)
    else:
        fail(f"tool <{tool}> not found")


if __name__ == "__main__":
    rp()