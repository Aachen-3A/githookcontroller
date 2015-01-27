#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script performs post-commit actions
##

from githookcontroller import GitHookController

gitController = GitHookController()

changed = gitController.parse_pre_commit()
print changed

# doxygen integration
gitController.prepare_doxygen_cfg() 
gitController.update_doxygen() 
