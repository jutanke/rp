import rp.utils as utils
import rp.network as network
import rp.console as console
import time

console.info("~ ~ start rp server ~ ~")

am_I_server = network.make_me_server()

console.write("waiting to become authority...")
while not am_I_server:
    time.sleep(1)
    am_I_server = network.make_me_server()

console.info("~> I became authority! Now I will run forever!")

# never stop..
while True:
    time.sleep(9999999)