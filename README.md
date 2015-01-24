# githookcontroller
This repository contains the githookcontroller, a general tool to construct git hooks in TAPAS

The project is work in progress and contains only few features so far.

Currently implemented features:
+ Parse output from pre-commit hooks
+ Create branch specific doxygen documentation on every commit (see hooks/pre-commit)
  Doxygen documentation without warnig can be enfoced based on repo root and branch name
+ Add doxygen documentation for given branches to gh-pages branch (see hooks/pre-push)
