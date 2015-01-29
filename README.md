# githookcontroller
This repository contains the githookcontroller, a general tool to construct git hooks for
gitHub based projects without a central contral server.

## Using githookcontroller in your repo:
### Setup:
The easiest way to implement the githookcontroller to your repo is to add setup script as shown in the setup.sh.example file and run it from the root directory of your repo.
### Adjusting the hooks
Githookcontroller ships with some exampe hook implementations, which you may want to adjust. The standard way to use the githookcontroller is to create a GitHookController class object within a python hook script, parse hook infos if necessary and call member functions of the controller (e.g. update doxygen) to perform hook actions as needed.

### Currently implemented features:
+ Parse output from pre-commit hooks.
+ Parse which files are changed in a commit.
+ Several easy to use controller class properties: current_branch, tracked remote_branches, local and remote root directory name, remote url.
+ Function to checkout different branches in local repo.
+ Create branch specific doxygen documentation on every commit (see hooks/pre-commit).
  Doxygen documentation without warnig can be enfoced based on repo root and branch name.
+ Add doxygen documentation for given branches to gh-pages branch (see hooks/pre-push).
