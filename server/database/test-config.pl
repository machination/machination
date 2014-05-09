use DB::Config;
use DBI;
use Data::Dumper;
use XML::LibXML;
use File::Slurp;

my $dbh = DBI->connect('dbi:Pg:dbname=machination;host=localhost;port=5432',
                      'machination', '!workingyet');
my $dbc = DB::Config->new($dbh);
my $table_str = read_file("test-table.xml");
my $table_elt = XML::LibXML->load_xml(string=>$table_str)->documentElement;
$dbc->schema_path('rng-schemas');
$dbc->validate_xml($table_str);
$dbc->config_table_cols($table_str);
for $celt ($table_elt->findnodes('constraint'), $table_elt->findnodes('primaryKey')) {
#  print $celt->toString . "\n";
#  print $dbc->constraint_name('dbc_test', $celt) . "\n";
}
$dbc->config_table_constraints($table_str);
$dbc->config_table_foreign_keys($table_elt);
$dbc->config_table_triggers($table_elt);
