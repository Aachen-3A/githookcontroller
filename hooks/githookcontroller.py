#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## This script contains classes to quickly build own git hooks
## 
## Copyright (c) 2014 Tobias Pook
## 
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
## 
## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.
## 
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
## THE SOFTWARE.

import sys, os
import shutil
from  collections import namedtuple
import parser
import argparse
import subprocess
import logging

log = logging.getLogger( 'githookcontroller' )
log.setLevel( logging.INFO )
ch = logging.StreamHandler( sys.stdout )
ch.setLevel( logging.INFO )
formatter = logging.Formatter( '%(levelname)s (%(name)s): %(message)s' )
ch.setFormatter( formatter )
log.addHandler( ch )

Push = namedtuple('Push', ['commits', 'remote_name', 'remote_url',
                           'current_branch', 'removing_remote', 'forcing'])
Commit = namedtuple('Commit', ['local_ref', 'local_sha1', 'remote_ref', 'remote_sha1',
                               'local_branch', 'remote_branch'])
class GitHookController():
    
    ## The constructor.
    #
    # @param self The object pointer
    # @param tempdir Directory where files are stored temporarily outside the repo default: /tmp/
    def __init__(self, tempdir = '/tmp/'):
        self.args = None
        self.stdin = []
        parser = argparse.ArgumentParser(description='Parser for git message to hook')
        self.parser = parser
        self.stdin = sys.stdin.read()
        self.tempdir = tempdir
        # list of branches where branch specific hooks are ignored
        self.vetobranches = ['gh-pages']
        # list of reponametags (parts of repo root name) where doxygen
        # documentation is enforced
        self.doxy_enforce_repos = ['lib', 'Lib','test']
    
    
    ###########################
    ### git helper functions ###
    ###########################
    
    ## Get currently chosen branch 
    #
    @property
    def current_branch(self):
        cmd = ["git", "branch", "|", "sed -n -e 's/^\\* \\(.*\)/\\1/p'"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout
        
    ## Get currently chosen branch 
    #
    @property
    def root_name(self):
        cmd = ["git", "rev-parse","--show-toplevel"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout.split('/')[-1]
        
    ## Checkout another branch 
    #
    # @param self The object pointer
    # @param branchname name of branch which is checked out 
    # @param forced boolean for forced checkout 
    def checkout_branch(self, branchname, forced = False):
        if forced: flag = '-f'
        else: flag = ''
        cmd = ["git", "checkout", branchname,flag]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
    
    ###########################
    ### functions for hooks ###
    ###########################
    
    ## Parse message from post commit
    #
    # @param self The object pointer
    def post_commit(self):
        pass

    def pre_commit(self):
        if not any(self.current_branch in b for b in self.vetobranches):
            self.prepare_doxygen_cfg()
            self.update_doxygen()
            
    
    ## Parse message from pre-push 
    #
    # Based on example in:
    # http://axialcorps.com/2014/06/03/preventing-errant-git-pushes-with-a-pre-push-hook/
    #
    # @param self The object pointer
    # @returns namedtupe of type Push fields: ['commits', 'remote_name', 'remote_url','current_branch', 'removing_remote', 'forcing']
    def parse_pre_push(self):
        commits = []
        self.parser.add_argument('remote_name')
        self.parser.add_argument('remote_url')
        args = self.parser.parse_args()
        lines = self.stdin.splitlines()
        for line in lines:
            split_line = line.split()
            if len(split_line) != 4:
                self.parser.exit(status=1,
                            message="Could not parse commit from '{}'\n".format(line))
            # local_branch
            local_branch = split_line[0].split('/')[-1] if '/' in split_line[0] else None
            split_line.append(local_branch)
            # remote_branch
            remote_branch = split_line[2].split('/')[-1] if '/' in split_line[2] else None
            split_line.append(remote_branch)
            commits.append(Commit(*split_line))
        current_ref = subprocess.Popen(['git', 'symbolic-ref', 'HEAD'],
                                        stdout=subprocess.PIPE).communicate()[0]
        current_branch = current_ref.split('/')[-1]
        pid = os.getppid()
        push_command = subprocess.Popen(['ps', '-ocommand=', '-p',
                                        str(pid)],
                                        stdout=subprocess.PIPE).communicate()[0]
        forcing = ('--force' in push_command or '-f' in push_command)
        removing_remote = set()
        for commit in commits:
            if commit.local_ref == "(delete)":
                removing_remote.add(commit.remote_branch)
        return Push(commits=commits,
                    remote_name=args.remote_name, remote_url=args.remote_url,
                    current_branch=current_branch, removing_remote=removing_remote,
                    forcing=forcing)
    
    #########################################
    ### functions for doxygen integration ###
    #########################################
    
    ## Prepare doxygen config file from template
    #
    # @param self The object pointer
    def prepare_doxygen_cfg(self):
        if self.current_branch in self.vetobranches:
            return None
        replacements = {'<branchname>':self.current_branch}
        with open('./doc/template_cfg', "rU+") as template:
            text = template.read()
            for src, target in replacements.iteritems():
                    text = text.replace(src, target)
                    
        with open('./doc/doxy_cfg', "wb") as config:
            config.write(text)
    
    ## Copy all doygen folders to gh-pages branch and commit changes
    #
    def publish_doxygen( self, branchnames ):
        branchnames = list(set(branchnames))
        startbranch = self.current_branch
        if len(branchnames) > 0:
            #check if /tmp dir exists
            if not os.path.exists(self.tempdir) and os.path.isdir(self.tempdir):
                log.error('Directory %s not found. Create it or change tempdir of githookcontroller')
                sys.exit(1)
                
            # check if current branch is in branchnames and process it first to
            # avoid uneccessary git checkouts
            if any(self.current_branch in b for b in branchnames):
                branchnames.remove( self.current_branch )
                branchnames.insert( 0, self.current_branch )
            
            # checkout branches and copy docs folder to temp
            copied = []
            for branch in branchnames:
                if 'gh-pages' in branch: continue
                self.checkout_branch( branch , forced = True)
                docdir = './doc/doc_%s' % branch
                # copy doxygen folder if it exists
                if not os.path.isdir( docdir ): continue
                dest = os.path.join( self.tempdir, 'doc_%s' % branch)
                try:
                    shutil.rmtree( dest  ) 
                except:
                    pass
                shutil.copytree( docdir, dest )
                #~ try:
                shutil.rmtree( docdir  ) 
                copied.append( (dest, branch) )
                #~ except:
                    #~ pass
                
                    
            # checkout gh-pages branch, move and add folders
            self.checkout_branch( 'gh-pages' )
            
            for temp in copied:
                (src, branch) = temp
                docfolder = './doc/doc_%s' % branch
                try:
                    shutil.rmtree( docfolder ) 
                except:
                    pass
                shutil.copytree( src , docfolder  )
                cmd = [ "git", "add", docfolder ]
                cmd =  [' '.join(cmd)]
                print cmd
                stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip() 
                shutil.rmtree( src  )       
                
            # commit changes 
            msg = '" updated doxygen documentation for branch: %s"' % ' '.join( [c[1] for c in copied] ) 
            cmd = [ "git", "commit", "-m" , msg]
            cmd =  [' '.join(cmd)]
            print cmd
            stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
            
            # return to start branch
            self.checkout_branch( startbranch )
           
    ## Update the doxygen documentation for this folder repo
    #
    # Based on example in:
    # http://axialcorps.com/2014/06/03/preventing-errant-git-pushes-with-a-pre-push-hook/
    #
    # @param self The object pointer
    # @param configpath Path to the doxygen confi file
    def update_doxygen(self,configpath = './doc/doxy_cfg'):
        if self.current_branch in self.vetobranches:
            return None
        log.info( 'updating doxygen documentation' )
        stdout, stderr = current_ref = subprocess.Popen(['doxygen', configpath],
                                        stdout=subprocess.PIPE).communicate()
        
        warnings = self._get_doxygen_warnings()
        nwarnings = len(warnings)
        if nwarnings > 0:
            log.warning('Doxyen produced %d warnings, please check in ./doc/doxy.warn' % nwarnings)
            log.info('Everybody will love you for great documentation !')
            
            # check if doxgen should be enforced
            
            if any(b in self.root_name for b in self.doxy_enforce_repos) :
                log.warning( 'Working in repo %s, please take special care of documentation and fix all doxgen warnings before commit.' % self.root_name)
                if self.current_branch in 'dev'  or  self.current_branch in 'master' :
                    log.error( 'You are in branch %s. Doxygen documention is enforced here! No commit until doxy.warn is empty' % self.current_branch)
                    log.info( '\n'.join(warnings) )
                    sys.exit(1)
                else:
                    log.warning( 'You are in branch %s. Better fix errors now or merge commits will be rejected to dev/master in the future' )



    ## Get all doxygen warnings
    #
    def _get_doxygen_warnings(self):
        doxy_warn_path = './doc/doxy.warn'
        if os.path.exists(doxy_warn_path):
            with open( doxy_warn_path ) as warnfile:
                warnings = warnfile.readlines()
            return warnings
        else:
            return []
    
#~ for line in fileinput.input("test.txt", inplace=True):
    #~ print "%d: %s" % (fileinput.filelineno(), line),
#~ def 
#~ sed 's/foo/bar/g'
#~ git log --format=%B -n 1 <commit>
def main():
    pass
    #~ print lines
    #~ newpush = assemble_push( args, lines )
    #~ print newpush
    #~ gitController = GitHookController()
    #~ push = gitController.parse_pre_push()
    #~ print push

if __name__=="__main__":
    main()

    
