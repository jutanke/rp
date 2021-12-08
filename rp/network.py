import zmq
import time
from threading import Thread
import rp.utils as utils


PORT = 1234


def server_function(socket):
    START_TIME = time.time()

    CURRENT_QUEUE = {}
    STAGING = {}

    while True:
        #  Wait for next request from client
        message = socket.recv_json()
        # print("Received request: ", message)
        if message["msg"] == "alive?":
            socket.send_json({"msg": "yes"})
        elif message["msg"] == "may_I?":
            NOW = time.time()
            server_alive_in_s = time.time() - START_TIME
            gpus = message["gpus"]
            cpu = message["cpu"]
            mem = message["mem"]
            unique_id = message["unique_id"]
            start_time = message["start_time"]
            if unique_id in CURRENT_QUEUE:
                CURRENT_QUEUE[unique_id]["last_touch"] = NOW
            else:
                CURRENT_QUEUE[unique_id] = {
                    "start_time": start_time,
                    "last_touch": NOW,
                    "cpu": cpu,
                    "gpus": gpus,
                    "mem": mem,
                }

            if server_alive_in_s < 10:
                # if the server is alive for less than
                # 10s we reject any request to make sure
                # that we get all waiting threads
                socket.send_json({"msg": "youmaynot"})
            else:
                # step 0: clean-up staging
                for key in STAGING:
                    placed_to_staging_in_s = NOW - STAGING[key]["placed_time"]
                    if placed_to_staging_in_s > 10:
                        del STAGING[key]

                # step 1: delete all entries that were not touched recently
                for key in CURRENT_QUEUE:
                    last_touched_in_s = NOW - CURRENT_QUEUE[key]["last_touch"]
                    if last_touched_in_s > 10:
                        del CURRENT_QUEUE[key]

                # step 2: get free resources
                free_cpu, free_mem, free_gpus = utils.get_free_resources()

                free_gpus = set(free_gpus)

                # step 3: add resource of staged processes
                for proc in STAGING.values():
                    free_cpu -= proc["cpu"]
                    free_mem -= proc["mem"]
                    for gpuid in proc["gpus"]:
                        if gpuid in free_gpus:
                            free_gpus.remove(gpuid)

                free_gpus = list(free_gpus)

                # step 4: sort all surviving entries by age
                you_may = False
                for _unique_id, resources in sorted(
                    CURRENT_QUEUE.items(), key=lambda e: e[1]["start_time"]
                ):
                    _cpu = resources["cpu"]
                    _mem = resources["mem"]
                    _gpus = resources["gpus"]

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

                    STAGING["unique_id"] = {
                        "placed_time": NOW,
                        "cpu": cpu,
                        "gpus": selected_gpus,
                        "mem": mem,
                    }

                    socket.send_json({"msg": "youmay", "gpus": selected_gpus})
                else:
                    socket.send_json({"msg": "youmaynot"})


def may_I_be_scheduled(start_time, gpus, mem, cpu, unique_id: str):
    """"""
    global PORT
    result = False
    try:
        print("may i?", start_time, gpus, mem, cpu)
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
            }
        )
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        if poller.poll(4000):  # 4s timeout in milliseconds
            message = socket.recv_json()

            result = message["msg"] == "youmay"
        else:
            result = False
    except:
        result = False

    print(" -->", result)
    return result


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


def make_me_server():
    global PORT
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:%s" % PORT)
    except:
        return False
    thread = Thread(target=server_function, args=(socket,))
    thread.start()
    return True