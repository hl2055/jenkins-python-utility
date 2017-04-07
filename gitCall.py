#!/usr/bin/python

from gitOperations import cGitRepo
from gitOperations import cGitArgs

gitArgs = cGitArgs()
gitRepo = cGitRepo(gitArgs.repo,gitArgs.path)
if not gitRepo.action(gitArgs.action,gitArgs.branch,gitArgs.ref1,gitArgs.ref2,gitArgs.start,gitArgs.end,gitArgs.directory,gitArgs.tag,gitArgs.endtag,gitArgs.message,gitArgs.ignore):
    exit(1)
