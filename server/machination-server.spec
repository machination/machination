# Machination Server

Name: machination-server
Version: 2.0alpha1
Summary: Server side of the Machination configuration management system
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

requires: conf(httpd)

%description
Machination is a configuration management system. This package
installs the Machination hierarchy (directory/tree) service and
associated utilities.

%global perllib %{_datadir}/perl5
%global srclib machination/server/lib
%global mlib %{perllib}/Machination
%global smlib %{srclib}/Machination

%prep
cp -a %{SOURCE0} .

%build

%install
rm -rf %{buildroot}
for dir in `find %{srclib} -type d -printf %%P\\\\n`
do
    mkdir -p %{buildroot}%{perllib}/$dir/
done
for file in `find %{srclib} -type f -printf %%P\\\\n`
do
    cp -p %{srclib}/$file %{buildroot}%{perllib}/$file
done

%clean

%files
%{perllib}/*

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