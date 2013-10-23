# Machination Server

%define git_version %(git describe --tags --long | sed 's/-\\([0-9]\\+\\)-.*$/\\.\\1/')

Name: machination-server
#Version: 2.0alpha1
Version: %{git_version}
Summary: Server side of the Machination configuration management system
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

buildrequires: python-devel
requires: config(httpd)

%description
Machination is a configuration management system. This package
installs the Machination hierarchy (directory/tree) service and
associated utilities.

%global perllib %{_datadir}/perl5
%global srcperllib machination/server/lib

%prep
rm -rf ./machination
cp -a %{SOURCE0} .

%build

%install
rm -rf %{buildroot}
for dir in `find %{srcperllib} -type d -printf %%P\\\\n`
do
    mkdir -p %{buildroot}%{perllib}/$dir/
done
for file in `find %{srcperllib} -type f -printf %%P\\\\n`
do
    cp -p %{srcperllib}/$file %{buildroot}%{perllib}/$file
done
mkdir -p %{buildroot}/var/www/cgi-bin
cp -p machination/server/certcgi/machination-join.py %{buildroot}/var/www/cgi-bin/

mkdir -p %{buildroot}/etc/httpd/conf.d
cp -p machination/packaging/default-mod-perl-machination.conf %{buildroot}/etc/httpd/conf.d/machination.conf

mkdir -p %{buildroot}/etc/machination/server/secrets
cp -p machination/packaging/default-server-config.xml %{buildroot}/etc/machination/server/config.xml
cp -p machination/packaging/default-dbcred.xml %{buildroot}/etc/machination/server/secrets/dbcred.xml

mkdir -p %{buildroot}/var/lib/machination/server/database
mkdir -p %{buildroot}/var/lib/machination/server/database/functions
for file in `find machination/server/database -type f -printf %%P\\\\n`
do
    cp -p machination/server/database/$file %{buildroot}/var/lib/machination/server/database/$file
done
cp -p machination/server/database/bootstrap_hierarchy.hda %{buildroot}/etc/machination/server/bootstrap_hierarchy.hda

mkdir -p %{buildroot}%{_bindir}
for file in `find machination/server/bin -type f -printf %%P\\\\n`
do
    cp -p machination/server/bin/$file %{buildroot}%{_bindir}/$file
done

mkdir -p %{buildroot}/var/log/machination/server/file

%clean

%files
%{perllib}/*
%{_bindir}/*
/var/www/cgi-bin/machination-join.py
%config(noreplace) /etc/machination/server
%config(noreplace) /etc/httpd/conf.d/machination.conf
%attr(-,apache,apache) /var/lib/machination/server/
%attr(-,apache,apache) /etc/machination/server/bootstrap_hierarchy.hda
%config(noreplace) /etc/machination/server/config.xml
%attr(0750,apache,apache) /etc/machination/server/secrets
%config(noreplace) %attr(0640,apache,apache) /etc/machination/server/secrets/dbcred.xml
%attr(0750,apache,apache) /var/log/machination/server/

# needs:

# probably installed?

# existing:
# mod_perl
# perl-Apache-DBI
# perl-Exception-Class
# perl-XML-LibXML
# perl-XML-XPath

# need created/found:
# perl-HOP-Stream
# perl-Exception-Class-DBI
