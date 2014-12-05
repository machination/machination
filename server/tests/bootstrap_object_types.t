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

my $ha = Machination::HAccessor->new($conf);
ok(defined $ha, "new ha from $config_file");

# put the object types there
$ha->bootstrap_object_types;
$ha->write_dbh->commit;

# check to see if they are there
my $dir = $conf->get_dir('dir.database.OBJECT_TYPES');
foreach my $file (<"$dir/*.xml">) {
  my $elt = XML::LibXML->load_xml(location=>$file)->documentElement;
  my $tname = $elt->getAttribute('name');
  ok(
    $ha->type_exists_byname($tname,{cache=>0}),
    "type $tname exists."
  );
}
