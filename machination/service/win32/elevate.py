import win32api

# Launch a new process with elevation

# FIXME! Pass in the appropriate command to run
application = "c:\\windows\\notepad.exe"
commandline = None

win32api.ShellExecute(0,
                      'runas',
                      application,
                      commandline,
                      '',
                      1)
