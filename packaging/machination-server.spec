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
requires: config(httpd)

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

%clean

%files
%{perllib}/*
/var/www/cgi-bin/machination-join.py

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
