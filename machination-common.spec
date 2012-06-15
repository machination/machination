# Machination Common

Name: machination-common
Version: 2.0alpha1
Summary: File common to client and server for Machination
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

buildrequires: python-devel

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

%files
%{python_sitelib}/*
