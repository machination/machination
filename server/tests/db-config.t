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
$dbconf->verbosity(1);
is($dbconf->schema_path,
  $conf->get_dir('dir.DATABASE') . "/rng-schemas",
  "schema path is " . $conf->get_dir('dir.DATABASE') . "/rng-schemas");
is($dbconf->type_sub('{ID_TYPE}'),'bigserial',
  "ID_TYPE is bigserial");

# Try creating some tables
my $tables_doc = XML::LibXML->load_xml(
  location => $conf->get_dir("dir.DATABASE") . "/test-tables.xml"
);

foreach my $table ($tables_doc->findnodes('/tables/table')) {
  # Checks for all tables
  my $tname = $table->getAttribute("name");
  ok(defined $tname, "checking table $tname");
  is($dbconf->validate_table_xml($table), 0, "  xml valid.");
  $dbconf->config_table_cols($table);
  ok($dbconf->table_exists($tname), "  table exists");
  my $colinfo = $ha->read_dbh->column_info(
    undef,undef,$tname,'%'
    )->fetchall_hashref('COLUMN_NAME');
  foreach my $col_elt ($table->findnodes('column')){
    ok(exists $colinfo->{$col_elt->getAttribute('name')},
      "  column " . $col_elt->getAttribute('name') . " exists.");
  }
  $dbconf->config_table_constraints($table);
  $dbconf->config_table_foreign_keys($table);

  # More specific checks
  if(my ($pkey) = $table->findnodes('primaryKey')) {
    print "**** add some primary key checks\n";
  }
  foreach my $con ($table->findnodes('constraint')) {
    my $con_type = $con->getAttribute('type');
    print "**** constraint tests for $con_type\n";
  }

  $dbconf->config_table_triggers($table);

  # Commit the table to the database
  $ha->write_dbh->commit;
}
