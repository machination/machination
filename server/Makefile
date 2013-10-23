SRC_ROOT=
SRC_PERLLIB=$(SRC_ROOT)server/lib
TGT_ROOT=/
TGT_PERLLIB=$(TGT_ROOT)usr/local/perl5
TGT_CONFIG=$(TGT_ROOT)etc
TGT_CONFIG_APACHE=$(TGT_CONFIG)/apache2
TGT_CONFIG_MACH=$(TGT_CONFIG)/machination
TGT_VAR=$(TGT_ROOT)var
TGT_VAR_MACH=$(TGT_VAR)/lib/machination
TGT_BINDIR=$(TGT_ROOT)usr/bin
TGT_LOGDIR=$(TGT_VAR)/log

MKDIR=mkdir -p
CP=cp -p
LN=ln -s

install-server:
	for dir in `find $(SRC_PERLLIB) -type d -printf %P\\\\n`;\
	do\
	  $(MKDIR) $(TGT_PERLLIB)/$$dir;\
	done
	for file in `find $(SRC_PERLLIB) -type f -not -name "*~" -printf %P\\\\n`;\
	do\
	  $(CP) $(SRC_PERLLIB)/$$file $(TGT_PERLLIB)/$$file;\
	done
	$(CP) packaging/default-mod-perl-machination.conf\
	  $(TGT_CONFIG_APACHE)/conf-available/machination.conf
	(cd $(TGT_CONFIG_APACHE)/conf-enabled && ln -s ../conf-available/machination.conf)
	$(MKDIR) $(TGT_CONFIG_MACH)/server/secrets
	$(CP) packaging/default-server-config.xml $(TGT_CONFIG_MACH)/server/config.xml
	$(CP) packaging/default-dbcred.xml $(TGT_CONFIG_MACH)/server/secrets/dbcred.xml
	$(MKDIR) $(TGT_VAR_MACH)/server/database/functions
	for file in `find server/database -type f -not -name "*~" -printf %P\\\\n`;\
	do\
	  $(CP) server/database/$$file $(TGT_VAR_MACH)/server/database/$$file;\
	done
	$(CP) server/database/bootstrap_hierarchy.hda $(TGT_CONFIG_MACH)/server/bootstrap_hierarchy.hda
	for file in `find server/bin -type f -not -name "*~" -printf %P\\\\n`;\
	do\
	  $(CP) server/bin/$$file $(TGT_BINDIR)/$$file;\
	done
	$(MKDIR) $(TGT_LOGDIR)/machination/server/file
