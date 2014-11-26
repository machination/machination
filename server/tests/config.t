#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';

use Machination::ConfigFile;

my %args = @ARGV;

my $test_root = $args{test_root};
$test_root = 'nothin' unless defined $test_root;

print "config tests\n";
print "  test_root = $test_root\n";

my $config_file = "$test_root/etc/machination/server/config.xml";
my $conf = Machination::ConfigFile->new($config_file);
ok(defined $conf,
  "Config object from $config_file exists");
$conf->root_path($test_root);
is($conf->root_path, $test_root,
  "root_path is $test_root");
my $doc = $conf->doc;
is(ref($doc), 'XML::LibXML::Document',
  "\$conf->doc is a document");
is($conf->get_dir('dir.LOG'),
  "$test_root/var/log/machination/server/file",
  "dir.LOG is $test_root/var/log/machination/server/file");
is($conf->get_dir('dir.SECRETS'),
  "$test_root/etc/machination/server/secrets",
  "dir.SECRETS is $test_root/etc/machination/server/secrets");
is($conf->get_file('file.database.CREDENTIALS'),
  "$test_root/etc/machination/server/secrets/dbcred.xml",
  "file.database.CREDENTIALS is $test_root/etc/machination/server/secrets/dbcred.xml");
