import rp.utils as utils
import rp.console as console
import rp.network as network
from os.path import join, isdir
from time import time, sleep


def info(directory: str, debug: bool):
    print("\n")
    if debug:
        print("[debug] rp info")
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

    console.info("\n - - queued processes - - ")
    if debug:
        print("[debug|info] try to make me server...")
    is_server = network.make_me_server(debug=debug)  # just in case
    if debug:
        print(f"[debug|info] are we server: {is_server}")
    if is_server:
        sleep(0.5)

    if debug:
        print("[debug|info] ask who is queued...")
    do_we_know_queue = False
    while not do_we_know_queue:
        do_we_know_queue, queue = network.whoisqueued()
        if debug:
            print(f"[debug|info] we got a response.. do we know? {do_we_know_queue}")

    NOW = time()

    if len(queue) > 0:
        for proc in sorted(queue.values(), key=lambda x: x["start_time"]):
            elapsed_in_min = (NOW - proc["start_time"]) / 60
            console.write(f"{proc['name']} @{proc['docker_image']}")
            console.write(proc["script"])
            console.write(f"waiting for %02.2fmin" % elapsed_in_min)
            console.write("- - - - - - - - - - - - -")

    console.info("\n - - active processes - - ")

    used_cpus = 0
    mem_used = 1  # make sure that at least 1gb remains free!!
    for proc in utils.get_currently_running_docker_procs(debug):
        console.write(f"{proc.docker_name} @{proc.image_name}")
        console.write(f"\tcpu = {proc.cpu}\n\tmem = {proc.mem}g")
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
    console.write(f"cpu: {total_cpus-used_cpus}/{total_cpus}")
    total_mem, _ = utils.get_memory()
    available_mem = total_mem - mem_used
    console.write(f"memory: {available_mem}g/{total_mem}g")
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
