# Machination server Makefile
#
SRC_PERLLIB=$(SRC_ROOT)lib
TGT_PERLLIB=$(TGT_ROOT)usr/local/perl5
TGT_CONFIG=$(TGT_ROOT)/etc
TGT_CONFIG_APACHE=$(TGT_CONFIG)/apache2
TGT_CONFIG_MACH=$(TGT_CONFIG)/machination
TGT_VAR=$(TGT_ROOT)/var
TGT_VAR_MACH=$(TGT_VAR)/lib/machination
TGT_BINDIR=$(TGT_ROOT)/usr/bin
TGT_LOGDIR=$(TGT_VAR)/log

MKDIR=mkdir -p
CP=install -D
LN=ln -s

.PHONY install install-files config-apache create-cert perms

install: install-files

perms: install-files config-apache create-cert
	packaging/install.pl --tgt_root=TGT_ROOT perms

install-files:
	packaging/install.pl --tgt_root=TGT_ROOT install

config-apache:
	packaging/install.pl --tgt_root=TGT_ROOT configure_apache

create-cert:
	echo "would create cert"