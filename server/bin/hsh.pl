use strict;
use warnings;
use Machination::HAccessor;
use Machination::MPath;
use Machination::HPath;
use Data::Dumper;
use Getopt::Long;
use Text::ParseWords;

$ENV{PERL_RL} = 'Zoid';
eval 'use Term::ReadLine';
die $@ if $@;

Exception::Class::Base->Trace(1) if $ENV{DEBUG};

#my $client_type = "ha";
my $config = "/home/eggy/svn/machination/trunk/test/machination/config.xml";
my $url = "http://localhost/machination/hierarchy/";
my $user = getpwuid($>);
my $ha = Machination::HAccessor->new($config);
my $pwd = "/";
GetOptions(
           "config=s" => \$config,
           );

# set up our list of commands
my @cmds = qw(config pwd cd ls);
my %cmds = map {$_ => \&{"_".$_}, } @cmds;

my $term = Term::ReadLine->new('Machination hsh');
#$term->Attribs->{completion_function} = \&complete;
my $prompt = "hsh: ";
my $OUT = $term->OUT || \*STDOUT;
while ( defined ($_ = $term->readline($prompt)) ) {
  my @words = shellwords($_);
  my $cmd = shift @words;
  if (exists $cmds{$cmd}) {
    my $res = eval { $cmds{$cmd}(@words) };
    warn $@ if $@;
    print $OUT $res, "\n" unless $@;
  } else {
    warn "no such command '$cmd'";
  }
}

sub complete {
  my ($word, $buffer, $start) = @_;

  print "\n$word, $buffer, $start\n";

  return ("a", "b");
}

sub _config {
  return $config unless(@_);
  $ha = Machination::HAccessor->new($_[0]);
  $config = shift;
}

sub _pwd {
  return $pwd;
}

sub _cd {
  $pwd = __extend_path($pwd,$_[0]);
  return $pwd;
}

sub __extend_path {
  my ($base, $ext) = @_;
  unless($ext=~/^\//) {
    $base .= "/" unless($base=~/\/$/);
    $ext = $base . $ext;
  }
  return $ext;
}

sub _ls {

}
