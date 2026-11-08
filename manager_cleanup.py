"""Remove only obsolete standalone-manager files; never run the suite uninstaller."""
import os
from pathlib import Path

def legacy_manager_locations(current):
    """Discover registered legacy locations; never invoke a suite uninstaller."""
    locations={Path(current).resolve()}
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
                try:
                    with winreg.OpenKey(hive,r'Software\Microsoft\Windows\CurrentVersion\Uninstall',0,winreg.KEY_READ|view) as root:
                        for index in range(winreg.QueryInfoKey(root)[0]):
                            try:
                                with winreg.OpenKey(root,winreg.EnumKey(root,index)) as entry:
                                    name=winreg.QueryValueEx(entry,'DisplayName')[0]
                                    if name not in ('MGC YFC Operations','Thrift Mart Dispatch','MGC YFC Operations Remote Manager','Thrift Mart Dispatch Remote Manager'):continue
                                    folder=Path(winreg.QueryValueEx(entry,'InstallLocation')[0])
                                    if folder.is_absolute():locations.add(folder.resolve())
                            except OSError:continue
                except OSError:continue
    except ImportError:pass
    names=('MGC YFC Operations Remote Manager.exe','Thrift Mart Dispatch Remote Manager.exe')
    return sorted((p for p in locations if any((p/n).is_file() for n in names)),key=str)

def remove_standalone_manager(install, shortcut_roots=None):
    install=Path(install).resolve()
    files=[install/name for name in ('MGC YFC Operations Remote Manager.exe','Thrift Mart Dispatch Remote Manager.exe','Remote-Manager-README.txt')]
    if shortcut_roots is None:
        appdata=Path(os.environ['APPDATA'])
        desktop=Path(os.environ['USERPROFILE'])/'Desktop'
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                desktop=Path(os.path.expandvars(winreg.QueryValueEx(key,'Desktop')[0]))
        except (ImportError,OSError):pass
        programs=appdata/'Microsoft/Windows/Start Menu/Programs'
        shortcut_roots=[desktop,programs/'MGC YFC Operations',programs/'Thrift Mart Dispatch']
    targets=[(file,install) for file in files]
    for folder in shortcut_roots:
        folder=Path(folder).resolve()
        for name in ('MGC YFC Operations Remote Manager.lnk','Thrift Mart Dispatch Remote Manager.lnk'):
            targets.append((folder/name,folder))
    # Verify every target before changing anything. No recursive removal or data access.
    for file,parent in targets:
        if file.resolve().parent != parent:raise OSError('Standalone manager path is outside its installation folder.')
    for file,_ in targets:file.unlink(missing_ok=True)
