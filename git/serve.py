"""
Enforce git-shell to only serve allowed by access control policy.
directory. The client should refer to them without any extra directory
prefix. Repository names are forced to match ALLOW_RE.
"""

import logging

import sys, os, re
import requests
import json
import time
from gitosis import access
from gitosis import repository
from gitosis import gitweb
from gitosis import gitdaemon
from gitosis import app
from gitosis import util

log = logging.getLogger('gitosis.serve')

ALLOW_RE = re.compile("^'/*(?P<path>[a-zA-Z0-9][a-zA-Z0-9@._-]*(/[a-zA-Z0-9][a-zA-Z0-9@._-]*)*)'$")

COMMANDS_READONLY = [
    'git-upload-pack',
    'git upload-pack',
    'git-upload-archive',
    'git upload-archive',
    ]

COMMANDS_WRITE = [
    'git-receive-pack',
    'git receive-pack',
    ]

class ServingError(Exception):
    """Serving error"""

    def __str__(self):
        return '%s' % self.__doc__

class CommandMayNotContainNewlineError(ServingError):
    """Command may not contain newline"""

class UnknownCommandError(ServingError):
    """Unknown command denied"""

class UnsafeArgumentsError(ServingError):
    """Arguments to command look dangerous"""

class AccessDenied(ServingError):
    """Access denied to repository"""

class WriteAccessDenied(AccessDenied):
    """Repository write access denied"""

class ReadAccessDenied(AccessDenied):
    """Repository read access denied"""

def print_result(header="",status=None,points=None,tim=None):
    out=header
    if status:
        if status=="AC":
            out=out+"\033[92m"+status+"\033[0m"
        elif status=="TLE":
            out=out+"\033[93m"+status+"\033[0m"
        elif status=="WA":
            out=out+"\033[91m"+status+"\033[0m"
        elif status=="RE":
            out=out+"\033[95m"+status+"\033[0m"
        elif status=="CE":
            out=out+"\033[96m"+status+"\033[0m"
        elif status=="pending" or status=="judging":
            status="   "
            out=out+status
        else:
            out=out+"\033[90m"+status+"\033[0m"
    if status and points:
        out=out+","+" "*(4-len(status))+"Points: \033[33m"+points+"\033[0m"
    if status and tim:
        out=out+","+" "*(4-len(status))+"  \033[94m"+tim+"\033[0m s"
    print(out+"\033[K")

def serve(
    cfg,
    user,
    command,
    ):
    if '\n' in command:
        raise CommandMayNotContainNewlineError()
    
    try:
        verb, args = command.split(None, 1)
    except ValueError:
        try:
            print("------------------------------------")
            print "Hi, "+user+"!"
            key_file=open(os.path.join("repositories",user+".git","hooks","key"),"r")
            data={"key":key_file.read(),"gitHash":command}
            key_file.close()
            fin=False
            while not fin:
                fin=True
                r = requests.post("https://ada-judge.csie.ntu.edu.tw/submission/get/gitHash",json=data)
                print("\033[s------------------------------------\033[K")
                line=1
                try:
                    results=json.loads(r.content)
                    for result in results:
                        print(result["problem"]["name"].encode("utf-8")+"\033[K")
                        line+=1
                        print("------------------------------------\033[K")
                        line+=1
                        pad=len(str(result["_id"]))
                        print("Submission #"+str(result["_id"])+":\033[K")
                        line+=1
                        if result["status"] != "finished":
                            print(" Status: \033[96m"+result["status"]+"\033[0m\033[K")
                            line+=1
                            fin=False
                        else:
                            print_result(" "*pad+"Final Result: ",result["result"],"%3d"%(result["points"]))
                            line+=1
                        if "_result" in result and result["_result"] and "subresults" in result["_result"] and result["_result"]["subresults"]:
                            for grp, sb in enumerate(result["_result"]["subresults"]):
                                print_result(" "*pad+" "*(5-len(str(grp)))+"Group #"+str(grp)+": ",sb.get("result") or "   ","%3d"%(sb.get("points") or 0))
                                line+=1
                                if "subresults" in sb and sb["subresults"]:
                                    for sb2 in sb["subresults"]:
                                        print_result(" "*pad+"     Subtask: ",sb2.get("result") or "   ",None,"%7.3f"%(sb2.get("runtime") or 0))
                                        line+=1
                except:
                    print("\033[91m"+r.content+"\033[0m\033[K")
                    line+=1
                    fin=True
                print("------------------------------------\033[K")
                line+=1
                if not fin:
                    sys.stdout.flush()
                    time.sleep(1)
                    print("\033["+str(line+1)+"A")
            sys.exit(0)
        except:
            #pass
            #main_log.error('Need SSH_ORIGINAL_COMMAND in environment.')
            sys.exit(0)
        sys.exit(0)
        # all known "git-foo" commands take one argument; improve
        # if/when needed
        # raise UnknownCommandError()

    if verb == 'git':
        try:
            subverb, args = args.split(None, 1)
        except ValueError:
            # all known "git foo" commands take one argument; improve
            # if/when needed
            raise UnknownCommandError()
        verb = '%s %s' % (verb, subverb)

    if (verb not in COMMANDS_WRITE
        and verb not in COMMANDS_READONLY):
        raise UnknownCommandError()

    match = ALLOW_RE.match(args)
    if match is None:
        raise UnsafeArgumentsError()

    path = match.group('path')

    # write access is always sufficient
    newpath = access.haveAccess(
        config=cfg,
        user=user,
        mode='writable',
        path=path)

    if newpath is None:
        # didn't have write access; try once more with the popular
        # misspelling
        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='writeable',
            path=path)
        if newpath is not None:
            log.warning(
                'Repository %r config has typo "writeable", '
                +'should be "writable"',
                path,
                )

    if newpath is None:
        # didn't have write access

        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='readonly',
            path=path)

        if newpath is None:
            raise ReadAccessDenied()

        if verb in COMMANDS_WRITE:
            # didn't have write access and tried to write
            raise WriteAccessDenied()

    (topdir, relpath) = newpath
    assert not relpath.endswith('.git'), \
           'git extension should have been stripped: %r' % relpath
    repopath = '%s.git' % relpath
    fullpath = os.path.join(topdir, repopath)
    if not os.path.exists(fullpath):
        # it doesn't exist on the filesystem, but the configuration
        # refers to it, we're serving a write request, and the user is
        # authorized to do that: create the repository on the fly

        # create leading directories
        p = topdir
        for segment in repopath.split(os.sep)[:-1]:
            p = os.path.join(p, segment)
            util.mkdir(p, 0750)

        repository.init(path=fullpath)
        gitweb.set_descriptions(
            config=cfg,
            )
        generated = util.getGeneratedFilesDir(config=cfg)
        gitweb.generate_project_list(
            config=cfg,
            path=os.path.join(generated, 'projects.list'),
            )
        gitdaemon.set_export_ok(
            config=cfg,
            )

    # put the verb back together with the new path
    newcmd = "%(verb)s '%(path)s'" % dict(
        verb=verb,
        path=fullpath,
        )
    return newcmd

class Main(app.App):
    def create_parser(self):
        parser = super(Main, self).create_parser()
        parser.set_usage('%prog [OPTS] USER')
        parser.set_description(
            'Allow restricted git operations under DIR')
        return parser

    def handle_args(self, parser, cfg, options, args):
        try:
            (user,) = args
        except ValueError:
            parser.error('Missing argument USER.')

        main_log = logging.getLogger('gitosis.serve.main')
        os.umask(0022)
        cmd = os.environ.get('SSH_ORIGINAL_COMMAND', None)
        if cmd is None:
            try:
                print("------------------------------------")
                print "Hi, "+args[0]+"!"
                key_file=open(os.path.join("repositories",args[0]+".git","hooks","key"),"r")
                data={"key":key_file.read()}
                key_file.close()
                
                fin=False
                while not fin:
                    fin=True
                    r = requests.post("https://ada-judge.csie.ntu.edu.tw/submission/get/last",json=data)
                    print("------------------------------------\033[K")
                    line=1
                    try:
                        result=json.loads(r.content)
                        print(result["problem"]["name"].encode("utf-8")+"\033[K")
                        line+=1
                        print("------------------------------------\033[K")
                        line+=1
                        pad=len(str(result["_id"]))
                        print("Submission #"+str(result["_id"])+":"+"\033[K")
                        line+=1
                        if result["status"] != "finished":
                            print(" Status: \033[96m"+result["status"]+"\033[0m\033[K")
                            line+=1
                            fin=False
                        else:
                            print_result(" "*pad+"Final Result: ",result["result"],"%3d"%(result["points"]))
                            line+=1
                        if "_result" in result and result["_result"] and "subresults" in result["_result"] and result["_result"]["subresults"]:
                            for grp, sb in enumerate(result["_result"]["subresults"]):
                                print_result(" "*pad+" "*(5-len(str(grp)))+"Group #"+str(grp)+": ",sb.get("result") or "   ","%3d"%(sb.get("points") or 0))
                                line+=1
                                if "subresults" in sb and sb["subresults"]:
                                    for sb2 in sb["subresults"]:
                                        print_result(" "*pad+"     Subtask: ",sb2.get("result") or "   ",None,"%7.3f"%(sb2.get("runtime") or 0))
                                        line+=1
                    except:
                        print("\033[91m"+r.content+"\033[0m\033[K")
                        line+=1
                        fin=True
                    print("------------------------------------\033[K")
                    line+=1
                    if not fin:
                        sys.stdout.flush()
                        time.sleep(1)
                        print("\033["+str(line+1)+"A")
                sys.exit(0)
            except:
                #pass
                #main_log.error('Need SSH_ORIGINAL_COMMAND in environment.')
                sys.exit(0)

        main_log.debug('Got command %(cmd)r' % dict(
            cmd=cmd,
            ))

        os.chdir(os.path.expanduser('~'))

        try:
            newcmd = serve(
                cfg=cfg,
                user=user,
                command=cmd,
                )
        except ServingError, e:
            main_log.error('%s', e)
            sys.exit(1)

        main_log.debug('Serving %s', newcmd)
        os.environ['GITOSIS_USER'] = user
        os.execvp('git', ['git', 'shell', '-c', newcmd])
        main_log.error('Cannot execute git-shell.')
        sys.exit(1)
