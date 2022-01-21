# I do not want ```rp``` to infest my code!

```rp``` creates quite a set of files/folders that you might not want to have inside your repository or ```rp``` folders might conflict with structures within your repository.

There is an easy fix: simply initialize ```rp``` one level above your repository.
Assuming that your work repository is located at
```
/home/{your_user}/my_project
```
create a new folder
```
/home/{your_user}/my_project_rp
```
and move ```/home/{your_user}/my_project``` inside this project (do NOT symlink!)
so that your repo is now located at:
```
/home/{your_user}/my_project_rp/my_project
```
Now you can go to 
```
/home/{your_user}/my_project_rp
```
and initialize ```rp```:
```
/home/{your_user}/my_project_rp$ rp init
```

To run a script from your project you can now simply
```
/home/{your_user}/my_project_rp$ rp run --script="my_project/run.sh"
```
However, your current working dir will NOT be ```my_project/``` but rather the dummy ```rp``` wrapper directory.
To fix this you simply create a script ```/home/{your_user}/my_project_rp/run.sh``` with the following line:
```bash
cd my_project && bash run.sh $@
```

Now you can call
```
/home/{your_user}/my_project_rp$ rp run --script="run.sh"
```
which will in turn call your script inside ```my_project``` with the correct working dir. We add ```$@``` so that all parameters which are passed to the script are forwarded towards your project script.

