import zmq
import time
from threading import Thread
import rp.utils as utils
from random import randint


PORT = 1234


def server_function(socket, debug: bool):
    START_TIME = time.time()

    CURRENT_QUEUE = {}
    STAGING = {}
    KILLED = {}

    while True:
        #  Wait for next request from client
        message = socket.recv_json()

        if debug:
            print("[debug|server] reveive message:", message["msg"])

        if message["msg"] == "alive?":
            socket.send_json({"msg": "yes"})
        elif message["msg"] == "kill":
            pid = message["pid"]
            name = "rp%04d" % pid
            if debug:
                print(f"[debug|server] receive kill command for {name}")
            # JULIAN
            delete_unique_id = None
            for unique_id, entry in CURRENT_QUEUE.items():
                if entry["name"] == name:
                    delete_unique_id = unique_id
                    KILLED[name] = time.time()
                    if debug:
                        print("\tscheduled for killing")
            if delete_unique_id is None and debug:
                print("\tNOT in queue and NOT scheduled for killing")
            if delete_unique_id is not None:
                del CURRENT_QUEUE[delete_unique_id]
            socket.send_json({"msg": "yes"})
        elif message["msg"] == "nameme":
            container_names = set(utils.get_running_container_names_cached())
            for proc in CURRENT_QUEUE.values():
                container_names.add(proc["name"])

            # 10 tries should be enough!
            for _ in range(10):
                name = "rp%04d" % randint(0, 9999)
                if name not in container_names:
                    break

            socket.send_json({"msg": "you_have_been_named", "name": name})

        elif message["msg"] == "whoisqueued":
            if debug:
                print("[debug|server] send current queue #", len(CURRENT_QUEUE))
            socket.send_json({"msg": "queue", "queue": CURRENT_QUEUE})
            if debug:
                print("[debug|server] current queue has been sent!")
        elif message["msg"] == "may_I?":
            NOW = time.time()
            server_alive_in_s = NOW - START_TIME
            gpus = message["gpus"]
            cpu = message["cpu"]
            mem = message["mem"]
            script = message["script"]
            name = message["name"]
            docker_image = message["docker_image"]
            unique_id = message["unique_id"]
            start_time = message["start_time"]

            # clean-up the killed list
            removed_from_killed = []
            for name_to_be_killed, request_time in KILLED.items():
                elapsed_since_kill_req = NOW - request_time
                if elapsed_since_kill_req > 120:
                    if debug:
                        print(
                            f"[debug|server] waiting too long for kill... releasing {name}"
                        )
                    removed_from_killed.append(name_to_be_killed)
            for name_to_be_killed in removed_from_killed:
                del KILLED[name_to_be_killed]

            if name in KILLED:
                if debug:
                    print(
                        f"[debug|server] ->{name}, you may not as you have been killed"
                    )
                del KILLED[name]
                socket.send_json({"msg": "youhavebeenkilled"})
            else:
                if unique_id in CURRENT_QUEUE:
                    # to not overload the server we flat-out reject anyone
                    # that has run a request and was denied within the last
                    # 5s
                    elapsed_since_last_req = (
                        NOW - CURRENT_QUEUE[unique_id]["last_touch"]
                    )
                    if elapsed_since_last_req < 5:
                        socket.send_json({"msg": "youmaynot"})
                        continue

                    CURRENT_QUEUE[unique_id]["last_touch"] = NOW
                else:
                    CURRENT_QUEUE[unique_id] = {
                        "start_time": start_time,
                        "last_touch": NOW,
                        "cpu": cpu,
                        "gpus": gpus,
                        "mem": mem,
                        "name": name,
                        "script": script,
                        "docker_image": docker_image,
                    }

                if server_alive_in_s < 5:
                    # if the server is alive for less than
                    # 5s we reject any request to make sure
                    # that we get all waiting threads
                    socket.send_json({"msg": "youmaynot"})
                else:
                    # step 0: clean-up staging
                    if debug:
                        print("[debug|server] step 0: clean-up staging")
                        _start = time.time()
                    del_key_from_staging = []
                    for key in STAGING:
                        placed_to_staging_in_s = NOW - STAGING[key]["placed_time"]
                        if placed_to_staging_in_s > 10:
                            del_key_from_staging.append(key)
                    for key in del_key_from_staging:
                        del STAGING[key]

                    # step 1: delete all entries that were not touched recently
                    if debug:
                        print("\telapsed", time.time() - _start)
                        print(
                            "[debug|server] step 1: delete all entries that were not touched!"
                        )
                        _start = time.time()
                    del_key_from_current_queue = []
                    for key in CURRENT_QUEUE:
                        last_touched_in_s = NOW - CURRENT_QUEUE[key]["last_touch"]
                        if last_touched_in_s > 10:
                            del_key_from_current_queue.append(key)
                    for key in del_key_from_current_queue:
                        del CURRENT_QUEUE[key]

                    # step 2: get free resources
                    if debug:
                        print("\telapsed", time.time() - _start)
                        print("[debug|server] step 2: get free resources")
                        _start = time.time()
                    free_cpu, free_mem, free_gpus = utils.get_free_resources_cached(
                        debug=debug
                    )
                    free_gpus = set(free_gpus)

                    # step 3: add resource of staged processes
                    if debug:
                        print("\telapsed", time.time() - _start)
                        print("[debug|server] step 3: add resources of staged procs")
                        _start = time.time()
                    for proc in STAGING.values():
                        free_cpu -= proc["cpu"]
                        free_mem -= proc["mem"]
                        for gpuid in proc["gpus"]:
                            if gpuid in free_gpus:
                                free_gpus.remove(gpuid)

                    free_gpus = list(free_gpus)

                    # step 4: sort all surviving entries by age
                    if debug:
                        print("\telapsed", time.time() - _start)
                        print("[debug|server] step 4: sort all surviving entries")
                        _start = time.time()
                    you_may = False
                    for _unique_id, resources in sorted(
                        CURRENT_QUEUE.items(), key=lambda e: e[1]["start_time"]
                    ):
                        _cpu = resources["cpu"]
                        _mem = resources["mem"]
                        _gpus = resources["gpus"]

                        if debug:
                            print(
                                f"\t[debug|server] cpu fit? {free_cpu} vs {_cpu}",
                                free_cpu - _cpu,
                            )
                            print(
                                f"\t[debug|server] mem fit? {free_mem} vs {_mem}",
                                free_mem - _mem,
                            )
                            print(
                                f"\t[debug|server] gpu fit? {len(free_gpus)} vs {_gpus}",
                                len(free_gpus) - _gpus,
                            )

                        # do the resources fit?
                        if (
                            free_cpu - _cpu >= 0
                            and free_mem - _mem >= 0
                            and len(free_gpus) - _gpus >= 0
                        ):
                            if _unique_id == unique_id:
                                # we are the next in queue! Lets schedule!
                                you_may = True
                                break
                    if you_may:
                        selected_gpus = []
                        for _ in range(gpus):
                            selected_gpus.append(free_gpus.pop(0))

                        STAGING[unique_id] = {
                            "placed_time": NOW,
                            "cpu": cpu,
                            "gpus": selected_gpus,
                            "mem": mem,
                        }

                        del CURRENT_QUEUE[unique_id]

                        socket.send_json({"msg": "youmay", "gpus": selected_gpus})
                    else:
                        socket.send_json({"msg": "youmaynot"})
                    if debug:
                        print("\telapsed", time.time() - _start)


def may_I_be_scheduled(
    start_time,
    gpus,
    mem,
    cpu,
    unique_id: str,
    name: str,
    docker_image: str,
    script: str,
):
    """"""
    global PORT
    result = False
    youhavebeenkilled = False
    gpu_devices = []
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect("tcp://localhost:%s" % PORT)
        socket.send_json(
            {
                "msg": "may_I?",
                "gpus": gpus,
                "mem": mem,
                "cpu": cpu,
                "unique_id": unique_id,
                "start_time": start_time,
                "docker_image": docker_image,
                "name": name,
                "script": script,
            }
        )
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(4000):  # 4s timeout in milliseconds
            message = socket.recv_json()
            result = message["msg"] == "youmay"
            if result:
                gpu_devices = message["gpus"]
            else:
                youhavebeenkilled = message["msg"] == "youhavebeenkilled"
        else:
            result = False
    except:
        result = False

    return result, gpu_devices, youhavebeenkilled


def kill(pid: int, debug=False):
    """"""
    global PORT
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect("tcp://localhost:%s" % PORT)
        socket.send_json({"msg": "kill", "pid": pid})

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(1000):  # 1s timeout in milliseconds
            message = socket.recv_json()
        else:
            pass

        socket.close()
        context.term()
    except:
        pass


def give_me_a_name():
    global PORT
    name = None
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect("tcp://localhost:%s" % PORT)
        socket.send_json({"msg": "nameme"})
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(1000):  # 1s timeout in milliseconds
            message = socket.recv_json()

        if message["msg"] == "you_have_been_named":
            name = message["name"]

        socket.close()
        context.term()
    except:
        pass
    return name


def whoisqueued():
    global PORT
    result = False
    queue = {}
    try:
        # !possible edge-case!
        # if a new server is spawn it might be that not
        # all queued processes have made contact yet!
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect("tcp://localhost:%s" % PORT)
        socket.send_json({"msg": "whoisqueued"})
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(60000):  # 60s timeout in milliseconds
            message = socket.recv_json()
        else:
            result = False
        if message["msg"] == "queue":
            result = True
            queue = message["queue"]
        else:
            result = False
        socket.close()
        context.term()
    except:
        result = False
    return result, queue


def is_server_alive():
    global PORT
    result = False
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect("tcp://localhost:%s" % PORT)
        socket.send_json({"msg": "alive?"})
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(1000):  # 1s timeout in milliseconds
            message = socket.recv_json()
        else:
            result = False
        if message["msg"] == "yes":
            result = True
        else:
            result = False
        socket.close()
        context.term()
    except:
        result = False
    return result


def make_me_server(debug: bool):
    global PORT
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:%s" % PORT)
    except:
        return False
    thread = Thread(
        target=server_function,
        args=(
            socket,
            debug,
        ),
    )
    thread.daemon = True  # kill when main-thread dies
    thread.start()
    return True