#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script performs post-commit actions
##

from githookcontroller import GitHookController

gitController = GitHookController()

# doxygen integration
gitController.prepare_doxygen_cfg() 
gitController.update_doxygen() 
