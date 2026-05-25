# TXT to ChordPro Converter PyQt6

Conversor gráfico para transformar canciones en formato TXT común de músicos e iglesias al formato ChordPro válido.

Autor / Desarrollador: **Washington Indacochea Delgado**  
Email: **linuxfrontier@proton.me**  
Web: <https://github.com/wachin/>

## ¿Qué convierte?

Convierte archivos como este:

```text
Vine a Adorarte
Kayros

[Verso I]
   G        D
Tú eres la luz
           Am         C
Qué brillo en las tinieblas
```

A ChordPro válido:

```chordpro
{title: Vine a Adorarte}
{artist: Kayros}

{comment: Verso I}
[G]Tú eres la [D]luz
[Am]Qué brillo en las [C]tinieblas
```

También convierte títulos con tono entre paréntesis:

```text
Este es mi deseo (A)
Claudio Friedson
```

A:

```chordpro
{title: Este es mi deseo}
{artist: Claudio Friedson}
{key: A}
```

## Características

- Interfaz gráfica hecha con PyQt6.
- Botón central para añadir archivos.
- Drag and drop de archivos `.txt`.
- Permite añadir varios archivos al mismo tiempo.
- Muestra cuántos archivos fueron añadidos.
- Todos los archivos quedan marcados para conversión por defecto.
- El usuario puede desmarcar archivos individualmente.
- Botones para seleccionar todo, desmarcar todo y limpiar la lista.
- Exporta a `.cho` o `.chopro`.
- Icono SVG incluido.

## Instalación en Debian 12 / MX Linux 23 / Ubuntu

### Opción recomendada con paquetes del sistema

```bash
sudo apt update
sudo apt install python3-pyqt6 python3-pyqt6.qtsvg qt6-translations-l10n
```

Ejecutar:

```bash
python3 txt_to_chordpro_gui.py
```

### Opción con entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install PyQt6
python txt_to_chordpro_gui.py
```

## Instalación en Windows

Instala Python desde:

<https://www.python.org/downloads/>

Luego abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
py -m venv venv
venv\Scripts\activate
pip install PyQt6
python txt_to_chordpro_gui.py
```

## Instalación en macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install PyQt6
python3 txt_to_chordpro_gui.py
```

## Uso

1. Abre el programa.
2. Arrastra uno o varios `.txt` a la ventana, o usa el botón **Add files**.
3. Revisa la lista de archivos añadidos.
4. Desmarca los que no quieras convertir.
5. Elige `.cho` o `.chopro`.
6. Pulsa **Convert selected files**.

El archivo convertido se guarda junto al archivo original.

## Probar los archivos generados con ChordPro

Si tienes instalado `chordpro`, puedes probar:

```bash
chordpro "examples/Vine a adorarte - Kayros (G).cho"
```

O con cualquier canción convertida:

```bash
chordpro "Mi cancion.cho"
```

## Notas importantes

Este programa no necesita el código fuente de ChordPro. La conversión se hace directamente en Python.

ChordPro usa corchetes `[]` para acordes, por ejemplo:

```chordpro
[G]Vine a [D]adorarte
```

Por eso las secciones de tus archivos, como:

```text
[Verso]
[Coro]
[Intro]
```

se convierten a:

```chordpro
{comment: Verso}
{comment: Coro}
{comment: Intro}
```

## Estructura del proyecto

```text
txt_to_chordpro_pyqt6/
├── txt_to_chordpro_gui.py
├── README.md
├── assets/
│   └── txt-to-chordpro.svg
└── examples/
    ├── Este es mi deseo (A) - Claudio Freidzon.txt
    ├── Perfume a tus pies (A) - Jaz Jacob.txt
    └── Vine a adorarte - Kayros (G).txt
```
