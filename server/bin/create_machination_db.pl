#!/usr/bin/perl
use strict;
use warnings;

use DBI;
use XML::LibXML;

# Gather some information from various files
my $crfile = '/etc/machination/server/secrets/dbcred.xml';
my $uxpath = '/cred/username';
my $pxpath = '/cred/password';

# Database credentials
my $cred = XML::LibXML->load_xml(location=>$crfile);
my ($uname, $pass);
eval { $uname = ($cred->findnodes($uxpath))[0]->textContent};
die "could not find $uxpath in $crfile" if $@;
eval { $pass = ($cred->findnodes($pxpath))[0]->textContent};
die "could not find $pxpath in $crfile" if $@;
die "Please change the database password in $crfile before bootstrapping"
  if($pass eq "thepassword");

# create the user and database
my $pg_uid = getpwnam('postgres');
my $pg_gid = getgrnam('postgres');


$) = $pg_gid;
$> = $pg_uid;

my $dbh = DBI->connect("dbi:Pg:dbname=postgres",'postgres','',{RaiseError=>1, AutoCommit=>1});

my $quname = $dbh->quote_identifier($uname);

eval {$dbh->do("create user $quname with password ?", {}, $pass);};
if(my $e = $@) {
  if($e =~ /role $quname already exists/) {
    warn "WARNING: user $quname already exists\n";
  } else {
    die $e;
  }
}

eval {$dbh->do("create database machination with owner $quname");};
if(my $e = $@) {
  if($e =~ /database \"machination\" already exists/) {
    warn "WARNING: database \"machination\" already exists\n";
  } else {
    die $e;
  }
}
