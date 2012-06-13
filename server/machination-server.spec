# Machination Server

Name: machination-server
Version: 2.0alpha1
Summary: Server side of the Machination configuration management system
Release: 1%{?dist}
License: GPLv3+
URL: https://github.com/machination/machination/
source: machination

buildarch: noarch

%description
Machination is a configuration management system. This package
installs the Machination hierarchy (directory/tree) service and
associated utilities.

%global perllib %{_datadir}/perl5
%global srclib machination/server/lib
%global mlib %{perllib}/Machination
%global smlib %{srclib}/Machination

%prep
cp -a %{source} .

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{mlib}/
cp -p %{smlib}/HAccessor.pm %{buildroot}%{mlib}/

%clean

%files
%{mlib}/HAccessor.pm
