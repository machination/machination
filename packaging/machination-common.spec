# Machination Common

%define git_version %(git describe --tags --long | sed 's/-\\([0-9]\\+\\)-.*$/\\.\\1/')

Name: machination-common
Version: %{git_version}
Summary: File common to client and server for Machination
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

buildrequires: python-devel
requires: python-lxml

%description
Machination is a configuration management system. This package
installs the files common to the client and the server.

%prep
cp -a %{SOURCE0} .
%build

%install
rm -rf %{buildroot}
for dir in `find machination/machination -type d -printf %%P\\\\n`
do
    mkdir -p %{buildroot}%{python_sitelib}/machination/$dir
done
for file in `find machination/machination -type f -printf %%P\\\\n`
do
    cp -p machination/machination/$file %{buildroot}%{python_sitelib}/machination/$file
done
mkdir -p %{buildroot}/var/lib/machination
mkdir -p %{buildroot}/var/log/machination
mkdir -p %{buildroot}/etc/machination
cp -p machination/packaging/default-desired-status.xml %{buildroot}/var/lib/machination/desired-status.xml

%files
%{python_sitelib}/*
/var/log/machination/
/etc/machination/
%config(noreplace) /var/lib/machination/desired-status.xml

