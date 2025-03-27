# Updated git repository instructions
Follow this instructions to update your work
## Download repo to work
Create your workspace, then use this code:
```shell
git init
git clone git@github.com:Lephap129/CyclingAIImplement.git . -b firmware
```
Create your branch to work
```shell
git checkout -b firmware_<workbranch name>
```
## Update your work
First, ensure that your branch can compare with repo:
```shell
git checkout firmware && git pull origin
git checkout firmware_<workbranch name> && git merge firmware
```
Then, commit your branch and push to repo:
```shell
git add .
git commit -m "<your commend commit>"
git push origin firmware_<workbranch name>
```
Then, let's go to github and make pull request to firmware branch:

![Select pull request](imgs/Pull_request%20(6).png)
![Choose create pull request](imgs/Pull_request%20(5).png)
![Ensure select pull request](imgs/Pull_request%20(4).png)
![Confirm pull request](imgs/Pull_request%20(3).png)
![Confirm merge pull request](imgs/Pull_request%20(2).png)
![Result pull request](imgs/Pull_request%20(1).png)

