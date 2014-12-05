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

# put the tables there
$ha->bootstrap_ops;
$ha->write_dbh->commit;

# check to see if they are there
my $file = $conf->get_dir('dir.DATABASE') .
  "/bootstrap_ops.xml";
my $doc = XML::LibXML->load_xml(location=>$file);
my @xml_ops = $doc->findnodes('/ops/op');
my $db_ops = $ha->read_dbh->
  selectall_hashref('select * from valid_ops', 'name');
foreach my $xo (@xml_ops) {
  ok(exists $db_ops->{$xo->getAttribute('name')},
    "op " . $xo->getAttribute('name') . " exists.");
}
