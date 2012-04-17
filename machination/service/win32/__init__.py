import win32serviceutil
import win32service
import win32event
import win32file
import socket


class ServiceLauncher(win32serviceutil.ServiceFramework):
    _svc_name_ = "machination-service"
    _svc_display_name_ = "Machination Launcher Daemon"
    _svc_description_ = "The Machination 'kick' listening daemon."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Event handler for stop events
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        # Event handler for daemon kicks
        self.kick_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        # Trigger a stop event
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):

        eventlist = [self.stop_event]
        timeout = 0
        while True:
            # Block, waiting for events to fire
            event = win32event.WaitForMultipleObjects(eventlist,
                                                      0,
                                                      timeout)

            if event == win32event.WAIT_TIMEOUT:
                #timeout has expired - handle kicks again
                self.kick_socket()
                eventlist = [self.stop_event, self.kick_event]
                timeout = win32event.INFINITE
            elif event == 0:
                #stop the service
                break
            elif event == 1:
                #kick received - close socket to prevent DOS
                self.sock.close()
                eventlist = [self.stop_event]
                timeout = 10000
                #Launch the update process
                self.launch_update()

    def kick_socket(self):
        """Open a socket waiting for 'kicks' to launch update."""

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #Associate this socket with the event handler for ACCEPT events
        win32file.WSAEventSelect(self.sock.fileno(),
                                 self.kick_event,
                                 win32file.FD_ACCEPT)
        self.sock.bind(('', 1313))
        self.sock.setblocking(0)
        self.sock.listen(0)

    def launch_update(self):
        """Launch the Machination update code."""
        pass


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ServiceLauncher)
