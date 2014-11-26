#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';
use Data::Dumper;

use Machination::HAccessor;

my %args = @ARGV;

my $test_root = $args{test_root};
$test_root = 'nothin' unless defined $test_root;

my $config_file = "$test_root/etc/machination/server/config.xml";
my $conf = Machination::ConfigFile->new($config_file);
$conf->root_path($test_root);

my  $ha = Machination::HAccessor->new($conf);
ok(defined $ha, "new Machination::HAccessor from $config_file");

# put the functions there
$ha->bootstrap_functions;
$ha->write_dbh->commit;

# check to see if they are there
my $f_file = $conf->get_dir('dir.DATABASE') .
  "/bootstrap_functions.xml";
my $f_doc = XML::LibXML->load_xml(location=>$f_file);
my $db_funcs = $ha->read_dbh->selectall_hashref(
  "select p.proname,n.nspname from pg_proc p left join pg_namespace n on p.pronamespace = n.oid where pg_function_is_visible(p.oid) and n.nspname <> 'pg_catalog' and n.nspname <> 'information_schema'",
  "proname"
);
foreach my $f ($f_doc->findnodes('//function')) {
  ok(exists $db_funcs->{$f->getAttribute('name')},
    "func " . $f->getAttribute('name') . " exists in db");
}


$ha->write_dbh->disconnect;
