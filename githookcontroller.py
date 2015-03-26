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
from configobj import ConfigObj


# setup logging
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
    def __init__(self,
                 configfile = 'githookcontroller_default.cfg',
                 tempdir = '/tmp/'):
        self.args = None
        self.load_config( configfile )
        self.stdin = []
        descr = 'Parser for git message to hook'
        parser = argparse.ArgumentParser(description= descr)
        self.parser = parser
        self.tempdir = tempdir

    ## Load infos from config file into controller object
    #
    # @param self The object pointer
    def load_config(self, configfile):
        if not os.path.exists( os.path.join( self.root_path, 'hooks'  , configfile )):
            log.error('Config file %s not found' % os.path.join( os.getcwd()  , configfile ) )
        try:
            self.config = ConfigObj( os.path.join( self.root_path, 'hooks'  , configfile ) )
        except:
            log.error( 'Unable to open config file %s' % configfile)
        self.docenv = self.config['general']['docenv']
        self.organisation = self.config['general']['docenv']
        self.vetobranches = list(self.config['general']['vetobranches'])
        #Check if repo name in repos section and add repo specific repos
        if self.remote_root_name in self.config['repos']:
            try:
                self.create_doxy = bool( self.config[self.remote_root_name]['create_doxy'] )
            except KeyError:
                self.create_doxy = False
            # check if doxygen should be enforced
            try:
                self.doxy_enforce = bool( self.config[self.remote_root_name]['doxy_enforce'] )
            except KeyError:
                pass
                self.doxy_enforce = False
    ############################
    ### git helper functions ###
    ############################

    ## Get root name of repo
    #
    # @param self The object pointer
    # @returns string containing the name of the root name
    @property
    def root_name(self):
        cmd = ["git", "rev-parse","--show-toplevel"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout.split('/')[-1]

    ## Get root path of repo
    #
    # @param self The object pointer
    # @returns string containing the name of the root name
    @property
    def root_path(self):
        cmd = ["git", "rev-parse","--show-toplevel"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip()
        return stdout

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
                    return line.split( '/' )[-1].replace( '.git', '' ).replace( '(fetch)', '' ).strip()
                if 'git@github.com' in line:
                    return line.split( '/' )[-1].replace( '.git', '' ).replace( '(fetch)', '' ).strip()
        return 'not_found'

    ## Get root name of doc repo
    #
    # @returns string containing the name of the remote root name
    @property
    def doc_remote_root_name(self):
        # check if DOC folder env variable is set
        if os.getenv( self.docenv ) is not None:
            docdir = os.path.join('', os.getenv( self.docenv ) )
        else:
            log.error( 'Did not find environment variable %s' % self.docenv)
            log.error( 'Skipping creation of new documention')
            sys.exit(1)

        cwd = os.getcwd()
        # change dir into /doc submodule
        os.chdir( docdir )

        cmd = ["git", "remote","-v"]
        cmd = [' '.join(cmd)]
        stdout = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0].rstrip().split('\n')
        # get back to original dir
        os.chdir( cwd )
        for line in stdout:
            if 'fetch' in line:
                if 'https' in line:
                    return line.split( '/' )[-1].replace( '.git', '' ).replace( '(fetch)', '' ).strip()
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
                    url = line.split( '@' )[-1]
                    url = url.replace( '.git', '' )
                    url = url.replace( '(fetch)', '' ).strip()
                    url = url.replace( ':', '/' ).strip()
                    url = "https://" + url

                try:
                    urllib2.urlopen(url)
                    return url
                except urllib2.HTTPError, e:
                    return "HTTPerror url nor found %s" % e.args
                except urllib2.URLError, e:
                    return "URLerror url nor found %s" % e.args
                except :
                    return ""
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

    ## run a git command
    #
    # @param self The object pointer
    # @param command list with commands as needed by subprocess.Popen
    def _call_git(self, cmd):
        cmd.insert( 0, 'git')
        cmd = [' '.join(cmd)]
        proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        stdout, stderr = proc.communicate()

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
        self.stdin = sys.stdin.read()
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
    # @param filepath path to the file where lint check should be performed
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
    #     %branchname% current branch name
    #     %remote_root_name%
    #     %html_header% path to html header file
    #     %html_footer% path to html header file
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
        # check if DOC folder env variable is set
        if os.getenv( self.docenv ) is not None:
            docdir = os.getenv( self.docenv )
        else:
            log.error( 'Did not find environment variable %s' % self.docenv)
            log.error( 'Skipping creation of new documention')
            sys.exit(1)

        cwd = os.getcwd()
        # change dir into doc submodule
        log.info('current dir %s' % os.getcwd() )
        os.chdir( docdir )

        #make sure doc is set to gh-pages branch
        if not self.current_branch == 'gh-pages':
            self.checkout_branch('gh-pages', True)

        #get back to original repo
        log.info('current dir %s' % os.getcwd() )

        os.chdir( cwd )

        ## prepare footer.html and header.html
        template_html = {}
        header_template_path = os.path.join('', '%s/header_template.html' % docdir )
        footer_template_path = os.path.join('', '%s/footer_template.html' % docdir )

        # check if template files exist and read
        if os.path.isfile( header_template_path ):
            header_path = path = os.path.join('', '%s/header.html' % docdir)
            with open( header_template_path, "rU+") as header_template:
                header_html = header_template.read()
                template_html.update({'header' : header_html } )
        else:
            header_path = ''

        if os.path.isfile( footer_template_path ):
            doFooter = True
            footer_path = path = os.path.join('', '%s/footer.html' % docdir)
            with open( footer_template_path , "rU+") as footer_template:
                footer_html = footer_template.read()
                template_html.update( {'footer':footer_html} )
        else:
            footer_path = ''

        # prepare linklines and replacements
        linklines = []
        for branchname in list( set(self.remote_branches) ):
            if branchname in self.vetobranches:
               continue
            #~ print ( self.organisation, self.doc_remote_root_name, branchname , branchname)
            linkline = '<option value="http://%s.github.io/%s/%s/doc_%s/html/index.html">%s</option>' % \
                        ( self.organisation, self.doc_remote_root_name, self.remote_url, branchname, branchname)

            linklines.append( linkline )

        replacements = { '++branchname++' : self.current_branch,
                         '++remote_root_name++' : self.remote_root_name,
                         '++remote_url++' : self.remote_url }

        # replace tokens and write files
        for key in template_html.keys():
            text = template_html[key]
            text = text.replace( '+++optionsline+++', '\n'.join( linklines ) )
            for src, target in replacements.iteritems():
                text = text.replace(src, target)
            path = os.path.join('', '%s/%s.html' % (docdir, key))
            with open(path , "wb" ) as html_file:
                html_file.write( text )
        outputdir = os.path.join(docdir, self.remote_root_name,'doc_%s'% self.current_branch)

        if not os.path.isdir( outputdir ):
            os.makedirs( outputdir)
        ## prepare main config
        replacements = { '%branchname%':self.current_branch,
                         '%remote_root_name%' : self.remote_root_name,
                         '%output_dir%' : outputdir,
                         '%footer_html%' : footer_path,
                         '%header_html%' : header_path }
        path = os.path.join('', '%s/doxy_cfg_template' % docdir  )
        with open( path, "rU+") as template:
            text = template.read()
            for src, target in replacements.iteritems():
                    text = text.replace(src, target)
        path = os.path.join( '', '%s/doxy_cfg' % docdir )
        with open( path, "wb") as config:
            config.write(text)

    ## Checkout all doygen folders in gh-pages branch and commit changes
    #
    def publish_doxygen( self, branchnames ):
        # check if DOC folder env variable is set
        if os.getenv( self.docenv ) is not None:
            docdir = os.path.join('', os.getenv( self.docenv ) )
        else:
            sys.error( 'Did not find environment variable %s' % self.docenv)
            sys.error( 'Skipping creation of new documention')
            sys.exit(1)

        cwd = os.getcwd()
        # change dir into /doc submodule
        os.chdir( docdir )

        #make sure doc is set to gh-pages branch
        if not self.current_branch == 'gh-pages':
            self.checkout_branch('gh-pages', True)
        # commit latests changes
        self._call_git(['add', '.'])
        bname = ' '.join( branchnames )
        msg = '" updated doxygen documentation for branch: %s"' % bname
        self._call_git([ "commit", "-a" ,"--no-verify", "-m" , msg])
        #pull latests repo version
        self._call_git(['pull'])
        self._call_git( [ "push", "--no-verify" ,"origin", "gh-pages"] )


        #get back to original repo
        os.chdir( cwd )
    ## Update the doxygen documentation for this folder repo
    #
    # Based on example in:
    # http://axialcorps.com/2014/06/03/preventing-errant-git-pushes-with-a-pre-push-hook/
    #
    # @param self The object pointer
    # @param configpath Path to the doxygen confi file
    def update_doxygen(self):

        if os.getenv( self.docenv ) is not None:
            docdir = os.path.join('', os.getenv( self.docenv ) )
        else:
            log.error( 'Did not find environment variable %s' % self.docenv)
            log.error( 'Skipping creation of new documention')
            sys.exit(1)

        if self.current_branch in self.vetobranches:
            log.info( 'No doxygen documentation for branch %s' % self.current_branch )
            return None
        log.info( 'updating doxygen documentation' )
        configpath = os.path.join( docdir, 'doxy_cfg')
        stdout, stderr = current_ref = subprocess.Popen(['doxygen', configpath],
                                        stdout=subprocess.PIPE).communicate()
        warnings = self._get_doxygen_warnings()
        nwarnings = len(warnings)
        if nwarnings > 0:
            log.warning('Doxyen produced %d warnings, please check in ./doc/doxy.warn' % nwarnings)
            log.info('Everybody will love you for great documentation !')

            # check if doxgen should be enforced

            if self.doxy_enforce :
                log.warning( 'Working in repo %s, please take special care of documentation and fix all doxgen warnings before commit.' % self.root_name)
                if self.current_branch in 'dev'  or  self.current_branch in 'master' :
                    log.error( 'You are in branch %s. Doxygen documention is enforced here! No commit until doxy.warn is empty' % self.current_branch)
                    log.info( '\n'.join(warnings) )
                    sys.exit(1)
                else:
                    log.warning( 'You are in branch %s. Better fix errors now or merge commits will be rejected to dev/master in the future' )
        # add new doc to branch
        #~ cmd = [ "git", "add", "doc/doc_%s/" % self.current_branch ]
        #~ print cmd
        #~ proc = subprocess.Popen(cmd,stdout=subprocess.PIPE)
        #~ stdout = proc.communicate()[0].rstrip()
        #~ cmd = ["git", "commit", "-a", "--amend", "-C", "HEAD", "--no-verify"]
        #~ proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True)
        #~ stdout = proc.communicate()[0].rstrip()


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


