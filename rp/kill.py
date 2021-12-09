import rp.console as console


def kill(pid: int):
    if pid == -1:
        console.fail("to kill a container you need to pass a pid:")
        console.write("\t$ rp kill --pid=1  # to kill container 1")
    else:
        container_name = "rp%04" % pid

    console.fail("Not implemented yet!!")