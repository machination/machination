use Machination::HAccessor;
use Data::Dumper;
use Getopt::Long;
use Text::ParseWords;

Exception::Class::Base->Trace(1);

my $config = "/home/eggy/svn/machination/trunk/test/machination/config.xml";
GetOptions(
    "config=s" => \$config,
    );

my $ha = Machination::HAccessor->new($config);

my $method = shift;


print "calling: $method(" . join(",",@ARGV) . ")\n";
my @args;
foreach my $arg (@ARGV) {
    push @args, convert_to_var($arg);
}
#print "calling: $method(" . join(",",@args) . ")\n";

print Dumper($ha->$method(@args));
$ha->dbc->dbh->commit;

sub convert_to_var {
  my $arg = shift;
  if($arg=~/^{/ || $arg=~/^\[/) {
    # convert to ref
    return eval "$arg";
  }
  if($arg=~s/^string://) {
    # would look like a ref but we want a string
    return $arg;
  }
  $arg = undef if($arg eq "undef");
  return $arg;
}
