import win32security
import win32ts
import win32process
import win32profile
import win32con

#Set the application options
# FIX ME! (use pythonic method for diving path to python and script)
application = None
commandline = "c:\\python27\\python.exe c:\\workspace\\elevate.py"
workingDir = None


# Find the active session
sessionid = win32ts.WTSGetActiveConsoleSessionId()

# Get the user token from that session
token = win32ts.WTSQueryUserToken(sessionid)

# We might want to load user's environment here?
# (win32profile.CreateEnvironmentBlock etc)


win32security.ImpersonateLoggedOnUser(token)

# Setup appropriate desktop and window stuff
si = win32process.STARTUPINFO()
si.lpDesktop = 'Winsta0\\default'

#Launch the user script
win32process.CreateProcessAsUser(
    token,
    application,
    commandline,
    None,
    None,
    False,
    win32con.NORMAL_PRIORITY_CLASS | win32con.CREATE_NEW_CONSOLE,
    env,
    workingDir,
    si
    )
