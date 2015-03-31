#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script performs post-commit actions
##

import sys

from githookcontroller import GitHookController

gitController = GitHookController()

# do linting if requested
if gitController.do_lint:
    # list of changed files
    changed_files = gitController.parse_pre_commit()

    # lint each changed files
    allow_commit = True
    for changed_file in changed_files:
        if gitController.lint_file(changed_file[1]) is not 0:
            allow_commit = False

    # if committing is now allowed, exit
    if not allow_commit:
        print "In this repository and branch, one should stay in line with the code style."
        print "Please address the issue(s) before commiting!"
        sys.exit(1)

# doxygen integration
if gitController.create_doxy:
    gitController.prepare_doxygen_cfg()
    gitController.update_doxygen()
