# MGC YFC Operations 0.26.0

- Changes Manage / Update Server to open authenticated browser settings instead of launching the separate Remote Manager executable that Windows Application Control blocked on the reported computer.
- Renames Open schedule to Login to Operations in the server window and tray menu. It opens the application sign-in screen, ending an existing session in that browser when necessary.
- Updates the server, tray, console, installer and shortcuts to a YFC rings icon with an office building in front at the right. The desktop title is MGC YFC Operations Server.
- Updates the Start menu management shortcut to browser settings and verifies the desktop button destinations during Windows installer tests.
- Includes all prior settings, journal, appearance, receipt and dispatch changes.

IMPORTANT: Install MGC-YFC-Operations-Setup-v0.26.0.exe on the host computer to refresh desktop executables, shortcuts and icons. The in-app update ZIP updates server/web code only and cannot replace the running desktop launcher. Exit the server from its tray menu before installing; keep the existing installation location and select the Server component. Existing installation identity and data paths are preserved. Reopen MGC YFC Operations Server afterward and refresh browsers.

This change removes the blocked Remote Manager dependency from the management button. It does not change Windows security policy or code-sign the application; a separate Windows policy block on the installer or server itself still requires trusted signing or administrator policy review.
