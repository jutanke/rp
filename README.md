# rp

Serverless queing tool for GPU-servers based on docker.

## Getting started

Assuming we have a folder `/home/{user}/my_project` which we want to convert into an `rp` project:
We simply 
```
cd /home/{user}/my_project
```
and then
```
rp init
```
This will create the following file structure:
* `/home/{user}/my_project`
  * `/docker`
    * `Dockerfile`: base Dockerfile. **Add your RUN docker commands into this file!**
    * `bashhook.sh`: script that is being called when the container starts. If possible do NOT use this to install libraries or to compile code as this will be executed at every run!
    * `hook_pre_useradd`: the `RUN`s in this file will be executed BEFORE the user is changed to the local user
    * `hook_post_useradd`: similar to `hook_pre_useradd`, however, the `RUN`s will be executed as local user rather than `root`. **Only use this if you know what you are doing!**
  * `/.rp`
    * `info.json`
    * `paths.json`: list of paths that should be added to the container. The paths must be **absolute** paths! A path will be mapped into the container as follows: `/home/user/{last_folder_name}`
  * `/.cache`
  * `/output`

```javascript
/* .rp/info.json 
In this file you can set the default hardware parameters such as
how many CPU cores should be used and how much memory (in GB) should
be utilized. Docker will enforce those limitations so you may run OOM
even though the host still has plenty!
*/
{
    "cpu": 4,
    "docker_shm": "64g",
    "gpus": 1,
    "memory": 8,
    "name": "demo",
    "rp_version": "0.0.1",
    "stdout_to_file": false,
    "tag": "julian_tanke/rp_demo",
    "username": "julian_tanke"
}
```

After you created your Dockerfile to your liking you can run scripts within the container.
Lets create a script `/home/{user}/my_project/hello.sh`:
```bash
# hello.sh
echo "Hello $1"
```
which we can execute within the container:
```
rp run --script="hello.sh funny-name"
```

Once you see the message
```
docker image successfully build!
```
you can savely `Ctrl+C` whenever you like.

If you have a long-running task you should run ```rp run ...``` from within `tmux` or `screen` as the process will otherwise be killed when exiting the terminal! Alternatively, you can run the process in detached mode via ```rp run --detach=True ...```. Note that you will not receive any console prints while detached.

You can specify different hardware constraints to the `run` command:
```rp run --cpu=x --gpu=x --mem=x ...```

By default the output is directly printed to the terminal. However, you may also pipe it into a text file as follows:
```
rp run --outfile_name="myrun" --script="xxxx"
```
This will create a file `/home/{user}/my_project/.rp/logs/myrun_{datetime}.log`.

To **kill** a run you can either `Ctrl+C` the terminal or you can simply `docker kill` the respective container. Note that the container name is being printed to terminal as:
```waiting to be scheduled as <{containe name}>```.
Each container is named using 4 random integers ```xxxx```. You can also kill a process (even when it is just being queued!) via ```rp```:
```bash
rp kill pid=xxxx
```

## How to debug your container
You can get a bash into your container by simply:
```
rp enter
```
Note that this will operate just like ```rp run``` so you might have to wait to be scheduled. 
**Important**: Please do NOT leave a bash open if you are not using it as it will block the resources until freed!
Note that you can change the resource requirements on the fly similar to ```rp run```:
```
rp enter --cpu=1 --mem=4 --gpu=0
```
