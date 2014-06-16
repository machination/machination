#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';

my $actor = "person:dev";

BEGIN {
  # make sure we use the dev versions of libraries
  use File::Basename;
  my $libdir =  File::Basename::dirname(__FILE__) . "/../lib";
  unshift @INC, $libdir;
}

use Data::Dumper;
use Machination::HAccessor;
my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");


# clean up
$ha->read_dbh->disconnect;

