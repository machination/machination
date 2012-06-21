#!/usr/bin/perl
use strict;
use warnings;

use Machination::HAccessor;

my $bshfile = '/var/lib/machination/server/bootstrap/bootstrap_hierarchy.hda';

# initial hierarchy admin user
open BSH, $bshfile;
my $bline = <BSH>;
print $bline . "\n";
my ($hadmin) = $bline =~ /setvar\(_USER_,(.*)\)$/;
close BSH;
die "Please change the hierarchy admin user in $bshfile before bootstrapping"
  if($hadmin eq 'changeme_to_admin@somewhere.com');

# create the database
qx"create_machination_db.pl";

# bootstrap the hierarchy

my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");
