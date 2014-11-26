#!/usr/bin/perl

use TAP::Harness;
use DBI;
use Getopt::Long;
use Data::Dumper;
use File::Path qw(remove_tree);
use lib 'lib';
use Machination::Manifest;


my $test_root = 'test/tmp';
my $clean;
my @tests;
my @default_tests = qw(config bootstrap_funcs);

GetOptions(
  "test_root=s" => \$test_root,
  "clean" => \$clean,
  "runtest=s@" => \@tests,
);
@tests = split(/,/,join(',',@tests));
@tests = @default_tests unless @tests;
@tests = map {"tests/$_.t"} @tests;
#print "tests: " . Dumper(\@tests);

my $harness = TAP::Harness->new(
  {
    verbosity => 1,
    lib => ['lib'],
    test_args => [test_root=>$test_root],
  }
);

if($clean) {
  print "cleaning\n";
#  open (my $cmd, "./drop-test-db.sh|");
#  while(<$cmd>) {
#    print;
#  }
#  close $cmd;
  qx"./drop-test-db.sh";
  remove_tree($test_root);

  qx"./create-test-db.sh";
}

# Make a test file tree
my $man = Machination::Manifest->new(location=>'manifest.xml');
$man->tgt_root($test_root);
$man->install;
# Alter default config files
my $dbcred_file = "$test_root/etc/machination/server/secrets/dbcred.xml";
my $dbcred_doc = XML::LibXML->load_xml(location=>$dbcred_file);
my ($user_elt) = $dbcred_doc->findnodes('//username');
my ($pass_elt) = $dbcred_doc->findnodes('//password');
$user_elt->removeChildNodes;
$user_elt->appendText('machination_test');
$pass_elt->removeChildNodes;
$pass_elt->appendText('machination_test');
open(my $dbch, ">$dbcred_file");
print $dbch $dbcred_doc->toString;
close $dbch;

my $bsh_file =
  "$test_root/etc/machination/server/bootstrap_hierarchy.hda";
my $bsh_backup = "$bsh_file.orig";
rename($bsh_file, $bsh_backup);
open(my $bshread, $bsh_backup);
open(my $bshwrite, ">$bsh_file");
while(<$bshread>) {
  s/changeme_to_admin_user\@somewhere.com/test_admin/;
  print $bshwrite $_;
}
close $bshwrite;
close $bshread;

# Everything relies on there being a test database set up.
# Try to connect to this database and issue an error if we can't.
my $dbh;
eval {
  $dbh = DBI->connect(
  'dbi:Pg:dbname=machination_tests;host=localhost',
  'machination_tests','machination_tests',
  {RaiseError=>1}
  );
};
if($@) {
  die "Could not connect to test database. Have you run create-test-db.sh?\n\n$@";
}

$harness->runtests(@tests);
