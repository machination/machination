#!/usr/bin/perl

use TAP::Harness;
use DBI;
my $harness = TAP::Harness->new(
  {
    'verbosity' => 1,
    'lib' => ['lib']
  }
);

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
  die "Could not connect to test database. Have you run create-test-db.sh?\n\n$@"
}

$harness->runtests(qw(tests/bootstrap.t));
