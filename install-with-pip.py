#!env python
# coding=utf-8
import sys
reload(sys) 
sys.setdefaultencoding('utf-8')

import pip

def install():
    file = open("requirements.txt", "r")
    argv = ["install", "", "--disable-pip-version-check"] + sys.argv[1:]
    count, failures = 0, []
    for line in file:
        if len(line) <= 2 or line[0] in (';', '#') or line[0:2] == '//':
            continue
        argv[1] = line.strip()
        if "PIL" in argv[1]:
            argv += [
                "--allow-external", "PIL",
                "--allow-unverified", "PIL",
            ]
        count += 1
        if pip.main(argv) != 0:
            failures.append(line.strip())
        if "PIL" in argv[1]:
            argv = argv[:-2]
        print
        print "============================================="
        print

    err = len(failures)
    print "Summary:  %d / %d dependencies has been installed." % (count - err, count)
    if err > 0:
        print "  Failed:", str(failures)[1:-1].replace("'", ""), "."
    return err

if __name__ == '__main__':
    sys.exit(install())
