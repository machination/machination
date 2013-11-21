#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';

BEGIN {
  # make sure we use the dev versions of libraries
  use File::Basename;
  my $libdir =  File::Basename::dirname(__FILE__) . "/../lib";
  unshift @INC, $libdir;
}

use Data::Dumper;
use Machination::HAccessor;
use Machination::MooseHC;

my $actor = "person:dev";

my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");
my $root_id = $ha->fetch_root_id;
my $hc = Machination::MooseHC->new(ha=>$ha, id=>$root_id);
ok(defined $hc, sprintf("\$hc from root_id (%d) exists.", $root_id));
my $idpath = $hc->id_path;
cmp_ok(@$idpath, '==', 1, "  id_path has one entry (" . join(",",@$idpath) . ")");

# clean up
$ha->read_dbh->disconnect;

