import win32serviceutil
import win32service
import win32event
import win32file
import time
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
        # Establish a socket listening for 'kicks'
        self.kick_socket()

        while True:
            # Block, waiting for stop event or daemon kick
            event = win32event.WaitForMultipleObjects(
                [self.kick_event, self.stop_event],
                0,
                win32event.INFINITE)

            if event == win32event.WAIT_OBJECT_0:
                self.sock.shutdown(2)
                self.sock.close()
                self.launch_update()

                # Keep the socket closed for 60 secs to prevent DOS
                time.sleep(60)
                self.start_service()
            elif event == win32event.WAIT_OBJECT_1:
                self.SvcStop()

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
        """Code that calls the update command goes here."""

        with open("c:\\workspace\\kick.txt", 'w') as f:
            f.write('kick')


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ServiceLauncher)
