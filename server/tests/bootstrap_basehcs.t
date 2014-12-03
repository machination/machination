#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';
use Data::Dumper;
use XML::LibXML;

use Machination::HAccessor;
use Machination::HPath;

my %args = @ARGV;

my $test_root = $args{test_root};
$test_root = 'nothin' unless defined $test_root;

my $config_file = "$test_root/etc/machination/server/config.xml";
my $conf = Machination::ConfigFile->new($config_file);
$conf->root_path($test_root);

my $ha = Machination::HAccessor->new($conf);
ok(defined $ha, "new ha from $config_file");

#my $hp = Machination::HPath->new(from=>'/', ha=>$ha);
#print $hp->rep->[0]->branch . "\n";
#print $hp->existing_pos . "\n";
#print $hp->exists . "\n";
#exit 0;

# run the bootstrap
$ha->bootstrap_basehcs;
$ha->write_dbh->commit;

# check to see if they are there
