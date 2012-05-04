#!/usr/bin/perl
use strict;
use warnings;
use Machination::HAccessor;
use Machination::MPath;
use Machination::HPath;
use Data::Dumper;
use Getopt::Long;
use Text::ParseWords;
use Term::ANSIColor;

$ENV{PERL_RL} = 'Zoid';
eval 'use Term::ReadLine';
die $@ if $@;

Exception::Class::Base->Trace(1) if $ENV{DEBUG};

# these work fairly well if you're colour blind (well not completely
# or there would be no point...) and using a black background. Someday
# they should be configurable.
my $colors = {
              container => 'bold bright_blue',
              key => 'yellow',
              value => 'bright_yellow',
              title => 'bold bright_red',
              undef => 'magenta',
           };

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
my @cmds = qw(config pwd cd ls show reload);
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
  $pwd = __abs_path($_[0]);
  return $pwd;
}

sub _reload {
  exec "perl -I$INC[0] $0";
}

sub __abs_path {
  my ($p) = @_;

  my $base = $pwd;
  if(defined $p) {
    if ($p=~/^\//) {
      return $p;
    } else {
      $base .= "/" unless($base=~/\/$/);
    }
    $base = $base . $p;
  }
  return $base;
}

sub _ls {
  my ($path) = @_;
  $path = __abs_path($path);
  my $hp = Machination::HPath->new($ha, $path);
  die "$path does not exist" unless $hp->id;
  my $maxlen = 0;
  my @cont;
  my $sth = $ha->get_contents_handle
    ($hp->id, ['machination:hc', keys %{$ha->all_types_info}]);
  while (my $ent = $sth->fetchrow_hashref) {
    my $name = $ent->{name};
    my $type = $ha->type_name($ent->{type});
    if($ent->{type} eq 'machination:hc') {
      $name .= "/";
      $name = colored([$colors->{container}], $name);
    } else {
      $name = colored([$colors->{key}],"$type:") .
        colored([$colors->{value}],"$name");
    }
    $maxlen = length($name) if(length($name) > $maxlen);
    push @cont, $name;
  }
  return join("\n",@cont);
}

sub _show {
  my ($path) = @_;
  $path = __abs_path($path);
  my $hp = Machination::HPath->new($ha, $path);
  die "$path does not exist" unless $hp->id;
  my $d = Machination::HObject->new($ha, $hp->type_id, $hp->id)
    ->fetch_data;
  my @ret;
#  push @ret, colored([$colors->{title}], $path);
  push @ret, __colorize_path($path);
  foreach my $f (sort keys %$d) {
    my $str = "  " . colored([$colors->{key}],sprintf('%-15s',"$f:"));
    if (defined $d->{$f}) {
      $str .=  colored([$colors->{value}],$d->{$f});
    } else {
      $str .= colored([$colors->{undef}],'undef');
    }
    push @ret, $str;
  }
  return join("\n", @ret);
}

sub __colorize_path {
  my $path = shift;
  my $hp = Machination::HPath->new($ha, $path);
  if ($hp->type eq "machination:hc") {
    return colored([$colors->{container}], $path);
  } else {
    my $str = $hp->parent->to_string;
    $str .= "/" unless ($str =~ /\/$/);
    $str = colored([$colors->{container}], $str);
    $str .= colored([$colors->{key}], $hp->type . ":") .
      colored([$colors->{value}], $hp->name);
    return $str;
  }
}
