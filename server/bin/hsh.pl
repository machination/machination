#!/usr/bin/perl
use strict;
use warnings;
use Machination::HAccessor;
use Machination::MPath;
use Machination::HPath;
use Data::Dumper;
use Getopt::Long qw(GetOptionsFromArray);
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
              attach => 'blue',
              key => 'yellow',
              value => 'bright_yellow',
              title => 'bold bright_red',
              undef => 'magenta',
           };

my $abbrevs = [
               [qr(^machination:hierarchy$), 'm:h'],
               [qr(^machination:osprofile$), 'm:os'],
               [qr(^machination:userprofile$), 'm:usr'],
              ];

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
  my @types;
  my @atypes;
  my @channels;
  my $contents = 1;
  my $attachments = 0;
  GetOptionsFromArray
    (
     \@_,
     'types=s' => \@types,
     'atypes=s' => \@atypes,
     'channels=s' => \@channels,
     'contents!' => \$contents,
     'attachments!' => \$attachments,
    );
  my @type_ids;
  if(@types) {
    @types = split(/,/,join(",",@types));
    @type_ids = map {$ha->type_id($_)} @types;
  } else {
    @type_ids = ('machination:hc', keys %{$ha->all_types_info});
  }
  my @channel_ids;
  if (@channels) {
    @channels = split(/,/,join(",",@channels));
    @channel_ids = map {$ha->channel_id($_)} @channels;
  } else {
    @channel_ids = map {$_->{id}}
      $ha->fetch('valid_channels',{fields=>['id'],condition=>""});
  }
  if($attachments and not @atypes) {
    # not very databasey, but this lot's probably in memory...
    my $info = $ha->all_types_info;
    foreach my $t (keys %$info) {
      my $name = $info->{$t}->{name};
      $name =~ s/^agroup_//;
      # TODO(colin) deal with sets properly
      next if $name eq "set";
      push @atypes, $name if $info->{$t}->{is_attachable};
    }
  }

  my $path = shift;
  $path = __abs_path($path);
  my $hp = Machination::HPath->new($ha, $path);
  die "$path does not exist" unless $hp->id;
  my $maxlen = 0;

  my @res;
  if($attachments) {
    foreach my $channel (@channel_ids) {
      foreach my $atype (@atypes) {
        my $sth = $ha->get_attachments_handle
          ($channel, [$hp->id] , $atype);
        while (my $att = $sth->fetchrow_hashref) {
          my $indicator;
          my $bold = "";
          if($att->{is_mandatory}) {
            $indicator = "*";
            $bold = "bold ";
          } else {
            $indicator = "";
          }
          my $cname = $ha->fetch
            ('valid_channels',{fields=>['name'],
                               params=>[$channel]})
              ->{name};
          $cname = _abbreviate($cname);
          my $item = colored([$bold . $colors->{attach}],
                             "\@$indicator($cname)$indicator") .
            colored([$colors->{key}],"$atype:") .
            colored([$colors->{value}],$att->{name});
          push @res, $item;
        }
      }
    }
  }
  if($contents) {
    my $sth = $ha->get_contents_handle
      ($hp->id, [@type_ids]);
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
      push @res, $name;
    }
  }
  return join("\n",@res);
}

sub _abbreviate {
  my ($text) = @_;
  foreach my $re (@$abbrevs) {
    return $text if($text =~ s/$re->[0]/$re->[1]/);
  }
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
