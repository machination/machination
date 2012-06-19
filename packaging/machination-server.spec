# Machination Server

Name: machination-server
Version: 2.0alpha1
Summary: Server side of the Machination configuration management system
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

buildrequires: python-devel
requires: config(httpd), machination-common

%description
Machination is a configuration management system. This package
installs the Machination hierarchy (directory/tree) service and
associated utilities.

%global perllib %{_datadir}/perl5
%global srcperllib machination/server/lib

%prep
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

mkdir -p %{buildroot}/etc/machination/server/bootstrap
mkdir -p %{buildroot}/etc/machination/server/bootstrap/functions
for file in `find machination/server/database -type f -printf %%P\\\\n`
do
    cp -p machination/server/database/$file %{buildroot}/etc/machination/server/bootstrap/$file
done

%clean

%files
%{perllib}/*
/var/www/cgi-bin/machination-join.py
%config(noreplace) /etc/httpd/conf.d/machination.conf
/etc/machination/server/
%config(noreplace) /etc/machination/server/config.xml
%config(noreplace) /etc/machination/server/secrets/dbcred.xml

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
