use Machination::HAccessor;
use Data::Dumper;
use Getopt::Long;
use Text::ParseWords;

Exception::Class::Base->Trace(1);

my $config = "/home/eggy/svn/machination/trunk/test/machination/config.xml";
my $objtype = "ha";
my $class;
my @newargs;
#my $argsubs =
#  {
#   "\$ha" => $ha,
#   };
GetOptions
  (
   "config=s" => \$config,
   "class=s" => \$class,
   "objtype=s" => \$objtype,
   "newargs=s{,}" => \@newargs,
  );

my $ha = Machination::HAccessor->new($config);

my $objtypes =
  {
   set => "Machination::HSet",
   hpath => "Machination::HPath",
  };
if(!$class && $objtype) {
  if(! ($class = $objtypes->{$objtype})) {
    $class = "Machination::HObject";
  }
  unshift @newargs, "\$ha";
}

my $method = shift @ARGV;
my @newvars;
foreach my $newarg (@newargs) {
  push @newvars, convert_to_var($newarg);
}
my @args;
foreach my $arg (@ARGV) {
    push @args, convert_to_var($arg);
}
print "creating \$obj = $class->new(" . join(",",@newargs) . ")\n";
print "creating \$obj = $class->new(" . join(",",@newvars) . ")\n";
print "calling \$obj->$method(" . join(",",@ARGV) . ")\n";
print "calling \$obj->$method(" . join(",",@args) . ")\n";

my $obj = $class->new(@newvars);
print Dumper($obj->$method(@args));
$ha->write_dbh->commit;

sub convert_to_var {
  my $arg = shift;
  if($arg=~/^{/ || $arg=~/^\[/ || $arg=~/^\$/) {
    # convert to ref
    return eval "$arg";
  }
  $arg = undef if($arg eq "undef");
  return $arg;
}
