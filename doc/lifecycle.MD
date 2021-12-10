# Life Cycle of an rp project

An `rp` project has the following folder structure:

* `/home/{user}/my_project`
  * `/docker`
    * `Dockerfile`: base Dockerfile. Only change fundamental things such as the base image in here
    * `bashhook.sh`: script that is being called when the container starts. If possible do NOT use this to install libraries or to compile code as this will be executed at every run!
    * `hook_pre_useradd`: **Add your `RUN` docker commands into this file!** The `RUN`s in this file will be executed BEFORE the user is changed to the local user
    * `hook_post_useradd`: similar to `hook_pre_useradd`, however, the `RUN`s will be executed as local user rather than `root`. **Only use this if you know what you are doing!**
  * `/.rp`
    * `info.json`
    * `paths.json`: list of paths that should be added to the container. The paths must be **absolute** paths! A path will be mapped into the container as follows: `/home/user/{last_folder_name}`
  * `/.cache`
  * `/output`

which is created by calling ```rp init``` in ```/home/{user}/my_project```.

When running a ```rp``` container you use
```
rp run --script=your_script.sh
```
where ```your_script.sh``` is located in your project root: ```/home/{user}/my_project/your_script.sh```. 

When running a script the ```rp``` goes through the following life cycle:

## STEP 1 build the docker image

**IMPORTANT**: do NOT ```Ctrl+C``` while the docker image is being build!

### STEP 1.1 Create the build-Dockerfile:
The actual Dockerfile that is being used to build the image is a concatenation of:

* (1) ```docker/Dockerfile```: all RUNs are executed as *root*
* (2) ```docker/hook_pre_useradd```: all RUNs are executed as *root*
* (3) replace the root docker user with your user (name that user *user*)
* (4) ```docker/hook_post_useradd```: all RUNs are executed as *user* 

### STEP 1.2 ```docker build```
The actual image is being build. **IMPORTANT**: No volume from ```.rp/paths.json``` has been mapped yet and neither has the project!

If the build finished successfully you will see
```
docker image successfully build!
```

## STEP 2 ```docker run```

### STEP 2.1 build the run command to create the container
Once the image is build ```rp``` will wait to be scheduled. Once the process is being scheduled ```rp``` will create the container given the previously generated image.
Now all paths are being mapped:
* ```/home/user/{my_project}``` (note: ```rp``` makes the project name lower-case!)
* ```/home/user/{folder_name}``` for all paths in ```.rp/paths.json```

### STEP 2.2 execute the container
* execute the ```docker/bashhooks.sh```.
* execute the specified script ```/home/user/{my_project}/your_script.sh```
