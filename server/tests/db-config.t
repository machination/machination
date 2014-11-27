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

my  $ha = Machination::HAccessor->new($conf);
ok(defined $ha, "new ha from $config_file");

# Some basic tests
my $dbconf = $ha->dbc->dbconfig;
is($dbconf->schema_path,
  $conf->get_dir('dir.DATABASE') . "/rng-schemas",
  "schema path is " . $conf->get_dir('dir.DATABASE') . "/rng-schemas");
is($dbconf->type_sub('{ID_TYPE}'),'bigserial',
  "ID_TYPE is bigserial");

# Try creating some tables
my $tables_doc = XML::LibXML->load_xml(
  location => $conf->get_dir("dir.DATABASE") . "/test-tables.xml"
);
