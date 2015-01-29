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
import urllib2

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
        self.organisation = 'aachen-3a'
        self.tempdir = tempdir
        # list of branches where branch specific hooks are ignored
        self.vetobranches = ['gh-pages']
        # list of reponametags (parts of repo root name) where doxygen
        # documentation is enforced
        self.doxy_enforce_repos = ['lib', 'Lib','test']
        
    
    ############################
    ### git helper functions ###
    ############################
    
    ## Get root name of repo
    #
    # @returns string containing the name of the root name
    @property
    def root_name(self):
        cmd = ["git", "rev-parse","--show-toplevel"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout.split('/')[-1]
    
    ## Get root name of remote (the original repo name) 
    #
    # @returns string containing the name of the remote root name
    @property
    def remote_root_name(self):
        cmd = ["git", "remote","-v"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip().split('\n')
        #~ print stdout
        for line in stdout:
            if 'fetch' in line:
                if 'https' in line:
                    return line.split( '/' )[-2].replace( '.git', '' ).replace( '(fetch)', '' ).strip()
                if 'git@github.com' in line:
                    return line.split( '/' )[-1].replace( '.git', '' ).replace( '(fetch)', '' ).strip()
        return 'not_found'
        
    ## Get url from remote 
    #
    # @returns string containing the name of the remote root name
    @property
    def remote_url(self):
        cmd = ["git", "remote","-v"]
        cmd = [' '.join(cmd)]
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        stdout = proc.communicate()[0].rstrip().split('\n')
        #~ print stdout
        for line in stdout:
            if 'fetch' in line:

                if 'https' in line:
                    url = line.split()[1].replace( '.git', '' )
                    url = url.replace( '(fetch)', '' ).strip()
                if 'git@' in line:
                    url = "https://" + line.split( '@' )[-1]
                    url = url.replace( '.git', '' ).replace( '(fetch)', '' ).strip()
                try:
                    urllib2.urlopen(url)
                    return url
                except urllib2.HTTPError, e:
                    return "HTTPerror url nor found %s" % e.args
                except urllib2.URLError, e:
                    return "URLerror url nor found %s" % e.args
        return ""
    
    ## Get currently chosen branch 
    #
    @property
    def current_branch(self):
        cmd = ["git", "branch", "|", "sed -n -e 's/^\\* \\(.*\)/\\1/p'"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout
    
    ## Get list of remote branches 
    #
    # @returns A list of strings containing all remot branch names
    @property
    def remote_branches(self):
        cmd = ["git", "branch", "-r"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip().split('\n')
        stdout = [ st.split('/')[-1] for st in stdout]
        branches = list( set(stdout) )
        return stdout
        
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
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        stdout = proc.communicate()[0].rstrip()
    
    ###########################
    ### functions for hooks ###
    ###########################
    
    ## Parse message from post commit
    #
    # @param self The object pointer
    def post_commit(self):
        pass
        
    ## Get list of chagend files in commit
    #
    # @param self The object pointer
    def parse_pre_commit(self):
        cmd = ["git", "diff", "--cached", "--name-status"]            
        cmd = [' '.join(cmd)]
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        files = proc.communicate()[0].rstrip().split('\n')
        try:
            files = [(f.split('\t')[0] , f.split('\t')[1] ) for f in files]
        except:
            files = []
        return files
        
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
                    remote_name=args.remote_name, 
                    remote_url=args.remote_url,
                    current_branch=current_branch,
                    removing_remote=removing_remote,
                    forcing=forcing)
    
    ###########################################
    ### functions for code style enforcment ###
    ###########################################
    
    ## Check if file fullfills cpplint check
    #
    # @param self The object pointer
    def check_cpplint( self, filepath):
        pass
        
    #########################################
    ### functions for doxygen integration ###
    #########################################
    
    ## Prepare doxygen config file from template
    #
    # The function replaces Tokens for files in ./doc/:
    # - template_cfg
    #   available Tokens:
    #     <branchname> current branch name
    #     <remote_root_name>
    #     <html_header> path to html header file
    #     <html_footer> path to html header file
    # - header_template.html
    # - footer_template.html
    #   available Tokens:
    #      +++optionsline+++ a fixed url path 
    #      ++branch_name++ current branch name
    #      ++remote_url++ see object property
    #      ++remote_root_name++ see object property
    # 
    # @param self The object pointer
    def prepare_doxygen_cfg(self):
        if self.current_branch in self.vetobranches:
            return None
            
        ## prepare footer.html and header.html
        template_html = {}
        header_template_path = './doc/header_template.html'
        footer_template_path = './doc/footer_template.html'
        
        # check if template files exist and read
        if os.path.isfile( header_template_path ):
            header_path = './doc/header.html'
            with open( header_path, "rU+") as header_template:
                header_html = header_template.read()
                template_html.update({'header' : header_html } )
        else: 
            header_path = ''
            
        if os.path.isfile( footer_template_path ):
            doFooter = True
            footer_path = './doc/footer.html'
            with open( footer_template_path , "rU+") as footer_template:
                footer_html = footer_template.read()
                template_html.update( {'footer':footer_html} )
        else: 
            footer_path = ''
            
        # prepare linklines and replacements
        linklines = []
        for branchname in self.remote_branches:
            if branchname in self.vetobranches:
               continue 
            linkline = '<option value="http://%s.github.io/'+\
                        '%s/doc/doc_%s/html/index.html">%s</option>' % \
                        ( self.organisation, 
                        self.remote_root_name,
                        branchname , branchname)
            linklines.append( linkline )
        
        
        replacements = { '++branchname++' : self.current_branch,
                         '++remote_root_name++' : self.remote_root_name }      
                         '++remote_url++' : self.remote_root_name }      
        ) )
        
        # replace tokens and write files
        for key in template_html.keys():
            text = template_html[key]   
            text = text.replace( '+++optionsline+++', '\n'.join( linklines ) )   
            for src, target in replacements.iteritems():
                text = text.replace(src, target)
            with open( './doc/%s.html' % key, "wb" ) as html_file:
                html_file.write( text )  
        
        ## prepare main config    
        replacements = { '<branchname>':self.current_branch,
                         '<footer_html>' : footer_path,
                         '<header_html>' : header_path }
        with open('./doc/doxy_cfg_template', "rU+") as template:
            text = template.read()
            for src, target in replacements.iteritems():
                    text = text.replace(src, target)
                    
        with open('./doc/doxy_cfg', "wb") as config:
            config.write(text)
    
    ## Checkout all doygen folders in gh-pages branch and commit changes
    #
    def publish_doxygen( self, branchnames ):
        branchnames = list(set(branchnames))
        startbranch = self.current_branch
        if len(branchnames) > 0:
            # check if current branch is in branchnames and process it first to
            # avoid uneccessary git checkouts
            if any(self.current_branch in b for b in branchnames):
                branchnames.remove( self.current_branch )
                branchnames.insert( 0, self.current_branch )
                
            if not 'gh-pages' in branchnames:
                # checkout gh-pages branch, move and add folders
                self.checkout_branch( 'gh-pages' )
                # make sure gh-pages is up to date
                cmd = [ "git", "pull"]
                proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                stdout = proc.communicate()[0].rstrip()
                
                #checkout doc folders from all branches
                for branchname in branchnames:
                    log.info( 'adding doc for %s to gh-pages' % branchname )
                    cmd = ["git", "checkout", branchname, "./doc/doc_%s" % branchname]
                    cmd = ' '.join(cmd)
                    log.info( cmd )
                    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                    #~ proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
                    stdout = proc.communicate()[0].rstrip()
                    log.info( stdout )
                    
                    # add checked out files
                    cmd = ["git", "add", "./doc/doc_%s" % branchname]
                    cmd = ' '.join( cmd ) 
                    log.info( cmd )
                    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                    #~ proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
                    stdout = proc.communicate()[0].rstrip()
                    log.info( stdout )
                 # commit changes 
                bname = ' '.join( branchnames )
                msg = '" updated doxygen documentation for branch: %s"' % bname
                cmd = [ "git", "commit", "-a" ,"--no-verify", "-m" , msg]
                cmd =  [' '.join(cmd)]
                log.info( cmd )
                #~ print cmd
                proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                stdout = proc.communicate()[0].rstrip()
                log.info( stdout )
                
                # push only gh-branches as it is not included in current push
                cmd = ["git", "push", "--no-verify" ,"origin", "gh-pages"]
                cmd = ' '.join(cmd)
                log.info( cmd )
                log.info( 'pushing in gh-pages')
                #~ proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
                stdout = proc.communicate()[0].rstrip()
                log.info( stdout )
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
        # add new doc to branch
        cmd = [ "git", "add", "doc/doc_%s/" % self.current_branch ]
        print cmd
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
        stdout = proc.communicate()[0].rstrip()
        cmd = ["git", "commit", "-a", "--amend", "-C", "HEAD", "--no-verify"]
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        stdout = proc.communicate()[0].rstrip()


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

    
