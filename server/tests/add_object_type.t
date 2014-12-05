#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';
use Data::Dumper;
use XML::LibXML;

use Machination::HAccessor;

my %args = @ARGV;

my $test_root = $args{test_root};
$test_root = 'nothin' unless defined $test_root;

my $config_file = "$test_root/etc/machination/server/config.xml";
my $conf = Machination::ConfigFile->new($config_file);
$conf->root_path($test_root);
# Use a test set of objects in their own directory
my $otelt = ($conf->doc->findnodes(
  '//dir[@xml:id="dir.database.OBJECT_TYPES"]'
))[0];
my $newot = XML::LibXML->load_xml(string=><<"EOF")->documentElement;
<dir xml:id="dir.database.OBJECT_TYPES">
  <component ref="dir.DATABASE"/>
  <component value="object-types"/>
  <component value="test"/>
</dir>
EOF
my $parent = $otelt->parentNode;
$otelt->parentNode->replaceChild($newot,$otelt);
print $conf->get_dir('dir.database.OBJECT_TYPES') . "\n";

my $ha = Machination::HAccessor->new($conf);
ok(defined $ha, "new ha from $config_file");

#my $dir = $conf->get_dir('dir.database.OBJECT_TYPES');

my @add_types = qw(test_dependent_type);
foreach my $type_name (@add_types) {
  if(!$ha->type_exists_byname($type_name)) {
    $ha->add_object_type(
      {actor=>"test"},
      $ha->get_object_type_elt($type_name)
    );
  }
}

# check to see if they are there
my @test_types = (@add_types, qw(test_object_type set));
foreach my $type_name (@test_types) {
  ok($ha->type_exists_byname($type_name), "Type '$type_name' exists.");
}
