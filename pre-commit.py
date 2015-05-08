#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script performs post-commit actions
##

import sys

from githookcontroller import GitHookController

ghc = GitHookController()

# check if branch is being controlled
if ghc.branch_active:
    # do linting if requested
    if ghc.lint_enable:
        # list of changed files
        changed_files = ghc.parse_pre_commit()

        # lint each changed files
        allow_commit = True
        for changed_file in changed_files:
            if ghc.lint_file(changed_file[1]) is not 0:
                allow_commit = False

        # if committing is now allowed, exit
        if not allow_commit:
            print "In this repository and branch, one should stay in line with the code style."
            print "Please address the issue(s) before commiting!"
            sys.exit(1)

    # doxygen integration
    if ghc.doxy_enable:
        ghc.prepare_doxygen_cfg()
        ghc.update_doxygen()
