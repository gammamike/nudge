PREFIX ?= /usr/local
DESTDIR ?=
BINARY ?= target/release/nudge-rust
NOTICE_DIR ?= target/notices
CARGO ?= cargo

.PHONY: all build notices check install uninstall
all: build notices

build:
	$(CARGO) build --release --locked

notices:
	./scripts/source-notices.sh "$(NOTICE_DIR)"

check:
	$(CARGO) test --locked
	python3 -m unittest discover -s tests -v

# Installation only copies prepared files; it never builds as root or edits homes.
install:
	test -x "$(BINARY)"
	test -f "$(NOTICE_DIR)/THIRD_PARTY_NOTICES.md"
	install -Dm755 "$(BINARY)" "$(DESTDIR)$(PREFIX)/lib/nudge-bash/bin/nudge"
	install -Dm644 nudge.bash "$(DESTDIR)$(PREFIX)/lib/nudge-bash/nudge.bash"
	install -Dm644 packaging/package-managed "$(DESTDIR)$(PREFIX)/lib/nudge-bash/package-managed"
	install -d "$(DESTDIR)$(PREFIX)/bin"
	ln -sfnT ../lib/nudge-bash/bin/nudge "$(DESTDIR)$(PREFIX)/bin/nudge-bash"
	install -Dm644 man/nudge-bash.1 "$(DESTDIR)$(PREFIX)/share/man/man1/nudge-bash.1"
	install -Dm644 completions/nudge-bash "$(DESTDIR)$(PREFIX)/share/bash-completion/completions/nudge-bash"
	install -Dm644 LICENSE "$(DESTDIR)$(PREFIX)/share/licenses/nudge-bash/LICENSE"
	install -m644 "$(NOTICE_DIR)/THIRD_PARTY_NOTICES.md" "$(DESTDIR)$(PREFIX)/share/licenses/nudge-bash/"
	cp -R "$(NOTICE_DIR)/licenses" "$(DESTDIR)$(PREFIX)/share/licenses/nudge-bash/"
	install -d "$(DESTDIR)$(PREFIX)/share/doc/nudge-bash"
	install -m644 docs/SYSTEM_INSTALL.md "$(DESTDIR)$(PREFIX)/share/doc/nudge-bash/README.md"
	install -m644 docs/PROVIDERS.md "$(DESTDIR)$(PREFIX)/share/doc/nudge-bash/"

# For manual Makefile installs only. Distribution packages use their manager.
uninstall:
	test -f "$(DESTDIR)$(PREFIX)/lib/nudge-bash/package-managed"
	rm -f "$(DESTDIR)$(PREFIX)/bin/nudge-bash" "$(DESTDIR)$(PREFIX)/share/man/man1/nudge-bash.1" "$(DESTDIR)$(PREFIX)/share/bash-completion/completions/nudge-bash"
	rm -rf "$(DESTDIR)$(PREFIX)/lib/nudge-bash" "$(DESTDIR)$(PREFIX)/share/licenses/nudge-bash" "$(DESTDIR)$(PREFIX)/share/doc/nudge-bash"
