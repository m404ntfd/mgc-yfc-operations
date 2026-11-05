THRIFT MART DISPATCH REMOTE MANAGER — 0.5.0

On a SECOND Windows computer on the same trusted staff network:
1. Run the unified MGC YFC Operations installer and choose Remote Manager.
2. Open MGC YFC Operations Remote Manager.exe. Python is not needed.
3. Enter the IP address shown on the server computer, e.g. 192.168.1.50:8080.
   A local computer name also works if your network resolves it.
4. Test connection, then sign in with an administrator account from the server.
   Create the first administrator locally on the server computer first.

Requires MGC YFC Operations Server 0.5.0 or later. Restart requires a full 0.5.0
server installation (new launcher); older launchers can still install server updates.

FEATURES
- Remembers the server address and employee name, never passwords.
- Shows connection status, server version, uptime and record counts.
- Creates a complete backup in the configured server OneDrive folder; no customer database is copied here.
- Restarts the running server and installs GitHub server updates as administrator.
- Opens the shared schedule and settings in your default browser for appointments,
  vehicles and employees. Sign in separately in that browser.
- The Remote Manager downloads button opens GitHub for the latest unified installer.
  Run that installer to update the remote app; the server update button updates
  the SERVER, not this executable.

The app is a native management panel with browser-based schedule editing, not
Windows Remote Desktop. It cannot power on the server PC or start a stopped server.
Closing Remote Manager leaves the server running. Network outages prevent changes.
Use only the trusted staff network: the current server uses unencrypted local HTTP.
This executable is not code-signed. It is a desktop app, not an installed service.
Configuration: %APPDATA%\ThriftMartDispatchRemoteManager\config.json

For source users: with Python + Tk installed, run python remote_manager.py from
this folder with client.py beside it. No extra Python packages are required.

PASSWORD CHANGES
After administrator sign-in, click Change a user's password, select a user, and
enter/confirm a password of 8–256 characters. Their existing sessions are ended.
If changing your own administrator password, sign in again with the new password.
