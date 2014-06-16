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

my $actor = "person:dev";

my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");
my $hp = Machination::HPath->new(ha=>$ha, from=>"/");
ok(defined $hp, "\$hp from '/' exists.");
is($hp->to_string, "/", "  string rep is '/'");
ok($hp->is_rooted, "  is_rooted");
ok($hp->exists, "  exists in hierarchy");
ok(defined $hp->id, "  id defined (" . $hp->id . ")");

my $p = $hp->parent;
ok($p->isa('Machination::HPath'), "  parent of root is a Machination::HPath");
ok(!$p->is_rooted, "    not rooted");
ok(! $p->leaf_node, "    has no leaf node");
ok(! $p->identifies_object, "    does not identify an object");
ok(! $p->exists, "    does not exist");
ok(! defined $p->name, "    no name");
ok(! defined $p->id, "    no id");
ok(! defined $p->type, "    no type");
ok(! defined $p->type_id, "    no type_id");
is($p->to_string, '', "    string rep is ''");


# Now move on to /dev/tests/hpath
$hp = Machination::HPath->new(ha=>$ha, from=>"/dev/tests/hpath");
is($hp->to_string, "/dev/tests/hpath", "switched to hpath '/dev/tests/hpath'");
# we'd like at least part of the path not to exist to test remainder
if($hp->exists) {
  $ha->delete_obj({"actor"=>"dev"}, $hp->type_id, $hp->id);
  $hp = Machination::HPath->new(ha=>$ha, from=>"/dev/tests/hpath");
}
ok($hp->existing->isa('Machination::HPath'), "  existing isa Machination::HPath (" . $hp->existing->to_string . ")");
ok($hp->remainder->isa('Machination::HPath'), "  remainder isa Machination::HPath (" . $hp->remainder->to_string . ")");

# clean up
$ha->read_dbh->disconnect;

