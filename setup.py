from distutils.core import setup
setup(name = 'TermEmulator',
      version = '1.0',
      description = "Emulator for V100 terminal programs",
      author = "Siva Chandran P",
      author_email = "siva.chandran.p@gmail.com",
      url = "http://sourceforge.net/projects/termemulator/",
      py_modules = ['TermEmulator'],
      license = "LGPL",
      long_description = """TermEmulator is a pure python module for emulating 
                            VT100 terminal programs. It handles V100 special 
                            characters and most important escape sequences. 
                            It also handles graphics rendition which specifies
                            text style(i.e. bold, italics), foreground color
                            and background color. The handled escape sequences 
                            are CUU, CUD, CUF, CUB, CHA, CUP, ED, EL, VPA 
                            and SGR.""",
      platforms = [ "any" ],
      data_files = [
                    ("/usr/share/doc/TermEmulator", [ "README", "LICENSE" ]),
                    ("/usr/share/doc/TermEmulator/examples",
                                                    [ "TermEmulatorDemo.py" ])
                   ]
      
      )
