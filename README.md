SublimeYouCompleteMe
====================
A plugin for Sublime Text 2 that acts as a client of an [YCMD server](https://github.com/Valloric/ycmd).
This plugin is heavily based on [YouCompleteMe](https://github.com/Valloric/YouCompleteMe).

YCMD enables powerfull general autocomplete for every language, and more indepth sementic completion for some, e.g.: python, c, c++

SublimeYouCompleteMe is currently in the very early stages of development.
Currently it is only tested on 64bit windows, with 64bit sublime text 2 and 64bit python 2.7.8.

Current features
----------------
* Starts the YCMD server and keeps it alive.
* ycm_goto command (ctrl+t, ctrl+t) - Jump to the declaration/definition of the symbol under the first cursor.
* ycm_goto_history command (ctrl+t, ctrl+b) - Jump to the location before ycm_goto
* ycm_auto_complete command (ctrl+space) - Force semantic autocomplete list to pop up. YCMD can also decide on it's own to use semantic autocomplete. For example when typing "." or "->" in the C-family languages.
* Highlights diagnostics (compiler errors) that YCMD reports when loading or modifying a file. This only works for the C-family of languages.

Installation for 64bit windows
-------------------------
1.  Clone this repository into your sublime text 2 packages folder.

        cd C:\Users\<yourname>\appdata\Roaming\Sublime Text 2\Packages
        git clone https://github.com/ivankoster/SublimeYouCompleteMe

2.  Use git submodule to download some dependencies

        git submodule update --init

3.  Now you need YCMD. YCMD is rather annoying to build on windows, but Haroogan has downloadable binaries that we can use.
4.  Download the x64 package from [vim YCM for windows from Haroogan](https://bitbucket.org/Haroogan/vim-youcompleteme-for-windows).
5.  Copy the third_party/ycmd/ folder in the above package to your <sublime_packages>/SublimeYouCompleteMe/ycmd folder.
6.  Last but not least you need libclang.dll. Again I got it from [llvm - Haroogan](https://bitbucket.org/Haroogan/llvm-for-windows). Make sure to get the x64 version.
7.  Copy the libclang.dll from the above package to <sublime_packages>/SublimeYouCompleteMe/ycmd/libclang.dll.
8.  Make sure you have a 64bit version of python 2.7 installed. The plugin searches first in the default installation path (C:\\python27\\python.exe) if not found it searches in your PATH environment variable.
9.  Start Sublime Text 2. It should now work!
