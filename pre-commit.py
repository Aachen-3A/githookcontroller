#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script performs post-commit actions
##

from githookcontroller import GitHookController

gitController = GitHookController()

#list of changen files
changed = gitController.parse_pre_commit()

# doxygen integration
if gitController.create_doxy:
    gitController.prepare_doxygen_cfg() 
    gitController.update_doxygen() 
    
