#!/usr/bin/make
# An install-only makefile to allow easy running of checkinstall.

PACKAGE = utilities-douglas
prefix = /usr/local
exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin
datarootdir = $(prefix)/share
docdir = $(datarootdir)/doc/$(PACKAGE)
pixmaps = $(datarootdir)/pixmaps/$(PACKAGE)
sysconfdir = /etc
completiondir = $(sysconfdir)/bash_completion.d
DESTDIR = /

executables = display_terminal_colours \
	      generate_password \
	      gnome-screenlock-action \
	      hashcdrom \
	      infoq_correct_album_and_artist \
              make-me-a-sandwich \
	      not \
	      notify-send-failure \
	      notify-send-result \
	      notify-send-success \
	      path \
	      pomodoro \
	      pomodoro_remaining_time \
	      rwhich \
	      solve \
	      terminal-vim \
	      vim_antiword \
	      zoom-update
completionfiles = rwhich_completion
imagefiles = pomodoro.png
docfiles = $(wildcard *.md)

help:
	@echo "An install-only makefile to allow easy running of checkinstall:"
	@echo "   $$ make checkinstall"
	@echo
	@echo "Installs the following executables:"
	@echo -n "   "; echo $(executables) | sed 's# \+#\n   #g'
	@echo
	@echo "And the following additional files:"
	@echo -n "   "; echo $(imagefiles) | sed 's# \+#\n   #g'

install:
	@install -d $(DESTDIR)$(bindir)
	@install -d $(DESTDIR)$(completiondir)
	@install -d $(DESTDIR)$(docdir)
	@install -d $(DESTDIR)$(pixmaps)
	@install -v -m775 $(executables)     $(DESTDIR)$(bindir)
	@install -v -m664 $(completionfiles) $(DESTDIR)$(completiondir)
	@install -v -m664 $(docfiles)        $(DESTDIR)$(docdir)
	@install -v -m664 $(imagefiles)      $(DESTDIR)$(pixmaps)

checkinstall:
	sudo checkinstall --pkgname=$(PACKAGE) --nodoc

