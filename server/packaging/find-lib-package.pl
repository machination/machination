use Getopt::Long;
use Data::Dumper;

my $libdir = "lib";

GetOptions(
           "libdir=s" => \$libdir,
           );

my $mod = shift;

eval "use lib \"$libdir\"";

$mod =~ s/^$libdir\///;
$mod =~ s/\//::/g;
$mod =~ s/\.pm$//;

print $mod . "\n";

eval "use $mod";
die $@ if $@;

my %found_pkgs;
foreach my $key (keys %INC) {
  my $file = $INC{$key};
  next if($file =~ /^$libdir\//);
  my $pkg = qx"dpkg -S $file";
  chomp $pkg;
  if($?) {
    warn "could not find package for $key\n";
  } else {
    $pkg =~ s/:.*$//;
    $found_pkgs{$pkg} = undef;
  }
}

print join(",", keys %found_pkgs) . "\n";
