import rp.utils as utils
import rp.console as console
from os.path import join, isdir
from time import time


def info(directory: str):
    print("\n")
    if utils.is_replik_project(directory):
        console.success("valid rp project <{directory}>\n")
        console.info("- - project information - - ")
        settings = utils.get_replik_settings(directory)
        cpu = settings["cpu"]
        gpus = settings["gpus"]
        memory = settings["memory"]
        docker_shm = settings["docker_shm"]
        console.write(
            f"resources:\n\t#cpu = {cpu}\n\t#gpus = {gpus}\n\t#mem = {memory}g\n\t#docker-shm = {docker_shm}"
        )
        console.write(f"\ndocker image tag: {settings['tag']}")

        paths = sorted(utils.get_paths_for_mapping(directory))

        console.write("\nmap the following paths into the container:")

        for path in paths:
            if "/" not in path:
                path = join(directory, path)
                last_entry = path.split("/")[-1]
                if isdir(path):
                    console.success(f"{path} -> /home/user/{last_entry} [path exists]")
                else:
                    console.fail(
                        f"{path} -> /home/user/{last_entry} [path does not exists]"
                    )

    else:
        console.warning("No valid rp project at this location")

    console.info("\n - - active processes - - ")

    NOW = time()
    used_cpus = 0
    mem_used = 1  # make sure that at least 1gb remains free!!
    for proc in utils.get_currently_running_docker_procs():
        console.write(f"{proc.docker_name} @{proc.image_name}")
        console.write(f"\tcpu = {proc.cpu}\n\tmem = {proc.mem}g\n\tshm={proc.shm_size}")
        console.write(f"\tgpus = {proc.gpu_devices}")

        used_cpus += proc.cpu
        mem_used += proc.mem

        elapsed_in_min = (NOW - proc.start_time) / 60
        if elapsed_in_min < 60:
            console.write(f"\telapsed = %02.2fmin" % elapsed_in_min)
        else:
            elapsed_in_h = elapsed_in_min / 60
            console.write(f"\telapsed = %02.2fh" % elapsed_in_h)
        console.write("- - - - - - - - - - - - -")
    console.info("\n - - global information - - ")

    total_cpus = utils.get_ncpu()
    console.write(f"cpu: {used_cpus}/{total_cpus}")
    total_mem, _ = utils.get_memory()
    console.write(f"total memory: {total_mem}g")
    available_mem = total_mem - mem_used
    console.write(f"available memory: {available_mem}g")
    console.write("gpus:")
    gpus = utils.get_gpus()
    for device_id in sorted(gpus.keys()):
        gpu = gpus[device_id]
        txt = f"\t{device_id} -> {gpu['name']}"
        if gpu["in_use"]:
            txt += " [in use]"
            console.warning(txt)
        else:
            txt += " [is free]"
            console.success(txt)

    print("\n")