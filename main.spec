# Configuracion de PyInstaller para el .exe (§10.3 de requisitos.md).
# Ruta recomendada: --onedir (COLLECT), arranca mas rapido y estable con Qt.
# Uso:  pyinstaller main.spec --noconfirm
from PyInstaller.utils.hooks import collect_all

# psd-tools reparte parsers y recursos que PyInstaller no detecta solo.
psd_bin, psd_data, psd_hidden = collect_all('psd_tools')
# matplotlib: los backends y los archivos de datos tampoco se detectan solos.
# El histograma se renderiza con Agg, asi que hay que forzar ese backend.
mpl_bin, mpl_data, mpl_hidden = collect_all('matplotlib')

a = Analysis(['main.py'],
             pathex=[],
             binaries=psd_bin + mpl_bin,
             datas=[('styles.qss', '.'), ('assets', 'assets')] + psd_data + mpl_data,
             hiddenimports=['core.imagen', 'core.segmentacion', 'core.canales',
                            'core.histograma', 'core.recorte',
                            'ui.tokens', 'ui.widgets', 'ui.helpers',
                            'ui.ventana_principal', 'ui.ventana_canales',
                            'ui.ventana_rgb', 'ui.ventana_ycm',
                            'ui.ventana_histograma', 'ui.ventana_recorte']
                           + psd_hidden
                           + mpl_hidden
                           + ['matplotlib.backends.backend_agg'],
             hookspath=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='Analizador', console=False, icon='assets/icon.ico')
coll = COLLECT(exe, a.binaries, a.datas, name='Analizador')