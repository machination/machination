#!/usr/bin/perl
use strict;
use warnings;
use Test::More 'no_plan';

use Machination::ConfigFile;

my $test_root = "test/tmp";

my $conf = Machination::ConfigFile->new
  ('packaging/default-server-config.xml');
ok(defined $conf,
  "Config object from packaging/default-server-config.xml exists");
$conf->root_path($test_root);
is($conf->root_path, $test_root,
  "root_path is $test_root");
my $doc = $conf->doc;
is(ref($doc), 'XML::LibXML::Document',
  "\$conf->doc is a document");
is($conf->get_dir('dir.SECRETS'),
  "$test_root/etc/machination/server/secrets",
  "dir.SECRETS is $test_root/etc/machination/server/secrets");
is($conf->get_file('file.database.CREDENTIALS'),
  "$test_root/etc/machination/server/secrets/dbcred.xml",
  "file.database.CREDENTIALS is $test_root/etc/machination/server/secrets/dbcred.xml");
