#!/usr/bin/perl
use strict;
use warnings;

use DBI;
use XML::LibXML;

my $crfile = '/etc/machination/server/secrets/dbcred.xml';
my $uxpath = '/cred/username';
my $pxpath = '/cred/password';

my $cred = XML::LibXML->load_xml(location=>$crfile);
my ($uname, $pass);
eval { $uname = ($cred->findnodes($uxpath))[0]->textContent};
die "could not find $uxpath in $crfile" if $@;
eval { $pass = ($cred->findnodes($pxpath))[0]->textContent};
die "could not find $pxpath in $crfile" if $@;

print "$uname\n$pass\n";

my $pg_uid = getpwnam('postgres');
my $pg_gid = getgrnam('postgres');

$) = $pg_gid;
$> = $pg_uid;

my $dbh = DBI->connect("dbi:Pg:dbname=postgres",'postgres','',{RaiseError=>1, AutoCommit=>1});

$uname = "frog with password 'splat'; create user mince ";

$dbh->do("create user $uname with password ?", {}, $pass);

