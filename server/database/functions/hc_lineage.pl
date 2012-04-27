# Initialise
#
# set to some true value to enable debug messages
$debug = 1;
# Load lib functions if not already loaded
unless($_SHARED{lib}) {
    spi_exec_query("select lib()");
}
my $lib = $_SHARED{lib};
# a place to hold otherwise anonymous subroutines
#my $subs = {};

my $hc_id = shift;

foreach (0..$hc_id) {
  return_next($_);
}
return undef;
