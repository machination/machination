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
use Machination::MooseHObject;
Exception::Class::Base->Trace(1);

my $actor = "person:dev";

my $ha = Machination::HAccessor->new("/etc/machination/server/config.xml");
my $root_id = $ha->fetch_root_id;
my $set_type_id = $ha->type_id("set");
# set 1 should exist
my $o = Machination::MooseHObject->
  new(ha=>$ha, type_id=>$set_type_id, id=>1);
ok(defined $o, "\$o as set 1 exists.");
print "set 1 in paths " . join(",", map {$_->to_string} $o->paths) . "\n";

$ha->create_path({actor=>$actor}, "/dev/tests/moosehobject/path1", {is_mp=>1});
$ha->create_path({actor=>$actor}, "/dev/tests/moosehobject/path2", {is_mp=>1});
my $hp1 = Machination::HPath->
  new(ha=>$ha, from=>"/dev/tests/moosehobject/path1");
ok($hp1->exists, "/dev/tests/moosehobject/path1 exists" );
my $hp2 = Machination::HPath->
  new(ha=>$ha, from=>"/dev/tests/moosehobject/path2");
ok($hp2->exists, "/dev/tests/moosehobject/path2 exists" );

my $hp_set1 = Machination::HPath->
  new(ha=>$ha, from=>"/dev/tests/moosehobject/path1/set:test");
$ha->delete_obj({actor=>$actor}, $hp_set1->type_id, $hp_set1->id)
  if($hp_set1->exists);
my $testset_id = $ha->create_obj
  ({actor=>$actor}, $hp_set1->type_id, $hp_set1->name, $hp1->id,
   {is_internal=>1, member_type=>$set_type_id});
ok($hp_set1->exists, "/dev/tests/moosehobject/path1/set:test exists" );

$ha->add_to_hc({actor=>$actor}, $set_type_id, $testset_id, $hp2->id);
my $hp_set2 = Machination::HPath->
  new(ha=>$ha, from=>"/dev/tests/moosehobject/path2/set:test");
ok($hp_set2->exists, "/dev/tests/moosehobject/path2/set:test exists" );

$hp_set1 = Machination::HPath->
  new(ha=>$ha, from=>"/dev/tests/moosehobject/path1/set:test");
ok($hp_set1->id == $hp_set2->id,
   sprintf("  both paths point to the same object (%d,%d)",$hp_set1->id, $hp_set2->id));

$o = Machination::MooseHObject->
  new(ha=>$ha, type_id=>$set_type_id, id=>$hp_set1->id);
ok(defined $o, sprintf("\$o as set %d exists.",$hp_set1->id));
ok($o->paths == 2,"  in paths " . join(",", map {$_->to_string} $o->paths));

my $o2 = Machination::MooseHObject->
  new(ha=>$ha, from=>"set:" . $o->id);
ok(defined $o2, sprintf("  found set with constructor %s",$o2->from));
ok($o2->paths == 2,"  in paths " . join(",", map {$_->to_string} $o2->paths));

$o2 = Machination::MooseHObject->
  new(ha=>$ha, from=>"#${set_type_id}:" . $o->id);
ok(defined $o2, sprintf("  found set with constructor %s",$o2->from));
ok($o2->paths == 2,"  in paths " . join(",", map {$_->to_string} $o2->paths));

eval { $o2 = Machination::MooseHObject->
         new(ha=>$ha, from=>"${set_type_id}:" . $o->id);
     };
ok($@ =~ /Type with name/, "  creating with type $set_type_id failed.");



# clean up
$ha->read_dbh->disconnect;

