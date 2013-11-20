#!/usr/bin/perl
use strict;
use warnings;
use Test::More tests=>5;

BEGIN {
  # make sure we use the dev versions of libraries
  use File::Basename;
  my $libdir =  File::Basename::dirname(__FILE__) . "/../lib";
  unshift @INC, $libdir;
}

use Data::Dumper;
use Machination::HAccessor;
my $ha;
eval {$ha = Machination::HAccessor->new("/etc/machination/server/config.xml");};
ok(defined $ha, '$ha = Machination::HAccessor->new($config)');
ok($ha->isa("Machination::HAccessor"), '$ha isa Machination::HAccessor');
ok(defined $ha->read_dbh, "Got read_dbh handle");
ok(defined $ha->read_dbh, "Got write_dbh handle");
my $root_id = $ha->fetch_root_id;
ok(defined $root_id, "Got a root_id ($root_id)");

# clean up
$ha->read_dbh->disconnect;

