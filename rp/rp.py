import click
import multiprocessing

multiprocessing.freeze_support()
import subprocess
from rp.console import fail

from rp.utils import VERSION
from rp.init import init
from rp.run import run
import os


@click.command()
@click.argument("tool")
@click.option("--script", default="demo.sh")
@click.option("--cpu", default=-1)
@click.option("--gpu", default=-1)
@click.option("--mem", default=-1)
def rp(tool, script, cpu, gpu, mem):
    path = os.getcwd()

    if tool == "init":
        init(path, cpu=cpu, gpu=gpu, mem=mem)
    elif tool == "run":
        run(path, cpu=cpu, gpu=gpu, mem=mem)
    elif tool == "schedule":
        pass
    else:
        fail(f"tool <{tool}> not found")


if __name__ == "__main__":
    rp()