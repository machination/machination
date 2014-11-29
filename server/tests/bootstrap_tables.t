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
$ha->bootstrap_tables;
$ha->write_dbh->commit;

# check to see if they are there
my $t_file = $conf->get_dir('dir.DATABASE') .
  "/bootstrap_tables.xml";
my $t_doc = XML::LibXML->load_xml(location=>$t_file);
my @xml_tables = $t_doc->findnodes('/tables/table');
my $db_tables = $ha->read_dbh->
  table_info(undef,undef,'%', 'TABLE')->
  fetchall_hashref('TABLE_NAME');
#print Dumper($db_tables);
foreach my $xt (@xml_tables) {
  ok(exists $db_tables->{$xt->getAttribute('name')},
    "table " . $xt->getAttribute('name') . " exists.");
  if($xt->getAttribute('history')) {
    my $ht_name = 'zzh_' . $xt->getAttribute('name');
    ok(exists $db_tables->{$ht_name},
      "  history table $ht_name exists.");
  }
}
