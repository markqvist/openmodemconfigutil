# -- mode python ; coding utf-8 --

block_cipher = None

data_list = []
dscan = Tree('.\\public', prefix='public\\')
for tupl in dscan:
    s = tupl[1]
    s = s[0:s.rfind('\\')]
    nt = (tupl[0], s)
    data_list.append(nt)
    print(nt)

a = Analysis(['openmodemconfig.py'],
             pathex=['.'],
             binaries=[],
             datas=data_list,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='OpenModem Configuration',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='openmodemconfig')
