import rp.utils as utils
from os.path import join
import rp.console as console
from subprocess import call


def freeze(directory: str, debug: bool):
    """
    Freezes the docker image so that it can be easily
    shared without worring about libraries etc becoming
    unavailable
    """
    info = utils.get_replik_settings(directory)
    tag = info["tag"]

    fname = utils.get_frozen_image_path(directory)

    r = call(f"docker image save -o={fname} {tag}")
    if r != 0:
        console.fail("freezing failed\n")
        exit(0)
