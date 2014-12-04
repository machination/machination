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
my $dbc = $ha->dbc;
my $telt = $dbc->gen_table_elt(
  {
    name=>"hcs",
    pk=>['id'],
    cols=>[["id",'{ID_TYPE}'],
    ['parent','{IDREF_TYPE}'],
    ['name','{OBJECT_NAME_TYPE}',{nullAllowed=>0}],
    ['ordinal','bigint',{nullAllowed=>0}],
    ['is_mp','boolean',{nullAllowed=>0}],
    ["owner",'{OBJECT_NAME_TYPE}']],
    fks=>[{table=>'hcs',cols=>[['parent','id']]}],
    cons=>[{type=>"unique",cols=>['parent','ordinal']}],
    history=>1,
  }
);
foreach my $elt ($dbc->mach_table_to_canonical($telt)) {
  print $elt->toString(1) . "\n";
  is($dbc->dbconfig->validate_table_xml($elt),0,
    "xml for table '" . $elt->getAttribute('name') . "' is valid.");
}
