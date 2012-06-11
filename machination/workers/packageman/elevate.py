import win32api
import sys
from machination import context

# Launch a new process with elevation

def main():
    if len(sys.argv) != 3:
        msg = "Failed to raise privileges: Wrong number of parameters supplied"
        context.emsg(msg)
        return msg

    application = sys.argv[1]
    commandline = sys.argv[2]

    win32api.ShellExecute(0,
                          'runas',
                          application,
                          commandline,
                          '',
                          1)

if __name__ == '__main__':
    main()
