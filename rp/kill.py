import rp.console as console
import rp.utils as utils
import rp.network as network


def kill(pid: int, debug=False):
    if pid == -1:
        console.fail("to kill a container you need to pass a pid:")
        console.write("\t$ rp kill --pid=1  # to kill container 1")
    else:
        container_name = "rp%04d" % pid
        running_container_names = set(utils.get_running_container_names())

        if container_name in running_container_names:
            rr = utils.kill_container(container_name)
            if rr == 0:
                console.success(f"{container_name} killed!")
        else:
            network.kill(pid, debug=debug)
