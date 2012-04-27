# Initialise
#
# Load lib functions if not already loaded
unless($_SHARED{lib}) {
    spi_exec_query("select lib()");
}
my $lib = $_SHARED{lib};

$lib->{clear_cache}();
