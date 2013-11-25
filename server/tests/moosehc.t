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
use Machination::HPath;
use Machination::MooseHC;

my $actor = "person:dev";

my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");
my $root_id = $ha->fetch_root_id;
my $hc = Machination::MooseHC->new(ha=>$ha, id=>$root_id);
ok(defined $hc, sprintf("\$hc from root_id (%d) exists.", $root_id));
my $idpath = $hc->id_path;
cmp_ok(@$idpath, '==', 1, "  id_path has one entry (" . join(",",@$idpath) . ")");

my $sys_hpath = Machination::HPath->new(ha=>$ha, from=>"/system");
my $sys_hc = Machination::MooseHC->new(ha=>$ha, id=>$sys_hpath->id);
ok(defined $sys_hc, sprintf("\$sys_hc from /system exists (%d).", $sys_hc->id));
my $sys_idpath = $sys_hc->id_path;
cmp_ok(@$sys_idpath, '==', 2, "  sys_idpath has two entries (" . join(",",@$sys_idpath) . ")");


# clean up
$ha->read_dbh->disconnect;

