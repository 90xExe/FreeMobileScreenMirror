# Third-party notices

ClearMirror launches the official **scrcpy** Android mirroring engine and the Android Debug Bridge included with its Windows distribution.

scrcpy is Copyright (C) 2018-2026 Romain Vimont and contributors, licensed under the Apache License 2.0.

- Project: https://github.com/Genymobile/scrcpy
- License: https://github.com/Genymobile/scrcpy/blob/master/LICENSE

Android Debug Bridge is part of Android SDK Platform Tools. This source snapshot excludes the engine binaries. Preserve the notices supplied with the official scrcpy/ADB download when packaging a runtime distribution.

## NAudio

PC microphone routing uses NAudio.Wasapi 2.2.1 and NAudio.Core 2.2.1, licensed under the MIT License.

Project: https://github.com/naudio/NAudio


Copyright 2020 Mark Heath

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Optional gaming overlay dependencies

The Python overlay depends on PyQt5 (`>=5.15.10,<6.0`). PyQt is available under GPLv3 or a Riverbank commercial license; it is not LGPL. Qt libraries have their own license terms. See [Riverbank's PyQt introduction and licensing information](https://riverbankcomputing.com/software/pyqt/intro).

Python and PyInstaller are separately installed build/runtime tools. Their notices and any packaged Qt/plugin notices must accompany distributions as required by their respective licenses. These tools and their binaries are not vendored in this source snapshot.

## ClearMirror source license

No project-wide license has been selected for this snapshot. The third-party notices above describe those components; they do not select a license for ClearMirror's own source.

