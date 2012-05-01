use strict;
use warnings;
use Machination::HAccessor;
use Machination::MPath;
use Machination::HPath;
use Data::Dumper;
use Getopt::Long;

use HOP::Lexer ':all';
use Machination::Parser ':all';
use Machination::WebClient;
#use HOP::Parser ':all';
use HOP::Stream ':all';

Exception::Class::Base->Trace(1) if $ENV{DEBUG};

my $client_type = "ha";
my $config = "/home/eggy/svn/machination/trunk/test/machination/config.xml";
my $url = "http://localhost/machination/hierarchy/";
my $user = getpwuid($>);
GetOptions(
           "client=s" => \$client_type,
           "config=s" => \$config,
           "url=s" => \$url,
           "user=s" => \$user,
          );
my $client;
if($client_type eq "ha") {
  $client = Machination::HAccessor->new($config);
} elsif($client_type eq "web") {
  die "web client not supported yet";
  $client = Machination::WebClient->new(url=>$url,user=>$user);
}
my $statement_store = {};

my @token_in =
  (
   ['COMMENT',qr/#.*\n/, sub{""}],
   ['STRING',qr/'(?:\\.|[^'])*'|"(?:\\.|[^"])*"/s,
    sub {my (undef,$s) = @_;
         $s =~ s/^.//; $s =~ s/.$//;
         $s=~ s/\\(.)/$1/g;
         return ['STRING',$s]},
   ],
   ['CONTINUATION', qr/\\\n/s, sub {""}],
   ['TERMINATOR', qr/;\n*|\n+/, sub {return ['TERMINATOR',";"]}],
   ['PLUS',qr/\+/],
   ['COMMA', qr/,/],
   ['FUNC', qr/\w+(?=\()/,],
#    sub { my(undef,$f) = @_; $f=~s/^&//; return ['FUNC',$f]}],
   ['LPAREN', qr/[(]/],
   ['RPAREN', qr/[)]/],
   ['OPT', qr/\|/],
   ['EQUALS',qr/=/],
   ['STRING', qr/[^\s+]+/],
   ['SPACE', qr/\s+/, sub {""}],
  );

open (my $f, "<", $ARGV[0]);

my $lex = iterator_to_stream(make_lexer(fh_iterator($f),@token_in));
while (defined (my $token = head($lex))) {
  print Machination::Parser::deref(drop($lex)) . "\n";
}
close $f;

my $funcs =
  {
   echo => \&func_echo,
   print => \&func_print,
   cat => \&func_cat,
   join => \&func_join,
   setvar => \&func_setvar,
   getvar => \&func_getvar,
   exists => \&func_exists,
   notexists => \&func_notexists,
   attached => \&func_attached,
   notattached => \&func_notattached,
   members_exist => \&func_members_exist,
   notmembers_exist => \&func_notmembers_exist,

   type_id => \&func_type_id,
   obj_id => \&func_obj_id,
   os_id=>\&func_os_id,
   channel_id=>\&channel_id,
   last_hpath=>\&func_last_hpath,
  };

my $vars = {};
my $last_hpath;

my ($prog,$statement,$func,$atom,$base,$expression,$option,$keyvalue,$string);
my $Prog = parser { $prog->(@_) };
my $Statement = sub { $statement->(@_) };
my $Expression = sub { $expression->(@_) };
my $Func = sub { $func->(@_) };
my $Atom = sub { $atom->(@_) };
my $Base = sub { $base->(@_) };
my $Option = parser { $option->(@_) };
my $Keyvalue = parser { $keyvalue->(@_) };
my $String = parser { $string->(@_) };

$Machination::Parser::N{$Prog} = 'prog';
$Machination::Parser::N{$Statement} = 'statement';
$Machination::Parser::N{$Expression} = 'expression';
$Machination::Parser::N{$Func} = 'func';
$Machination::Parser::N{$Atom} = 'atom';
$Machination::Parser::N{$Base} = 'base';
$Machination::Parser::N{$Option} = 'option';
$Machination::Parser::N{$Keyvalue} = 'keyvalue';
$Machination::Parser::N{$String} = 'string';

# strings can be made of STRING tokens or the results of functions
$string = alternate(lookfor("STRING"), $Func);

$func = T
  (
   concatenate
   (
    lookfor('FUNC'),
    absorb(lookfor('LPAREN')),
    list_values_of(star($Atom)),
    absorb(lookfor('RPAREN')),
   ),
   sub {
     my $fname = $_[0];
     if(exists $funcs->{$fname}) {
       return $funcs->{$fname}->(arg2str(@{$_[1]}));
     } else {
       die "tried to call unknown function $fname";
     }
   }
  );

$keyvalue = T
  (
   concatenate
   (
    $String,
    lookfor("EQUALS"),
    $String
   ),
   sub {
     return ["keyvalue", $_[0], $_[2]];
#     $statement_store->{named_vars}->{$_[0]} = $_[2];
#     return $_[0] . "=" . $_[2];
   }
  );

$option = T
  (
   concatenate
   (
    absorb(lookfor("OPT")),
    $Keyvalue,
   ),
   sub {
     return ["option",$_[0]->[1], $_[0]->[2]];
   }
  );

$atom = alternate($Option,$Keyvalue,$Func,lookfor('STRING'));
$statement = T
  (
   concatenate(star($Atom),lookfor('TERMINATOR')),
   sub {
     debug "found statement " . join(",",map Machination::Parser::deref($_), @{$_[0]}) . "\n";

     return "nothing" unless @_ > 1;
     return "empty" if(join("",@{$_[0]})=~/^\s*$/);

     # determine function to call
     my $f = "func_";
     my $hpath = shift @{$_[0]};
     # look for a negation
     if( $hpath =~ s/^!//) {
       $f .= "not";
     }
     # look for short forms
     if ($hpath =~ s/^E//) {
       $f .= "members_exist";
     } elsif ($hpath =~ s/^@//) {
       $f .= "attached";
     } elsif ($hpath =~ s/^\&//) {
       $f .= "inhc";
     } elsif ($hpath =~ s/^AG//) {
       $f .= "agroup";
     } else {
       $f .= "exists";
     }

#     { no strict 'refs'; $f->($hpath->to_string,@{$_[0]}); };

     # look for references to previous hpath
     if($hpath eq ".") {
       $hpath = $last_hpath;
     } elsif($hpath =~ s/^\.\///) {
       $hpath = $last_hpath->to_string . "/$hpath";
     } elsif(my $nmatch = $hpath =~ s/^((?:\.\.\/)+)//) {
       my @dots = split("/",$1);
       foreach (@dots) {
         $last_hpath = $last_hpath->parent;
       }
       if($last_hpath->to_string eq "/") {
         $hpath = "/$hpath";
       } else {
         $hpath = $last_hpath->to_string . "/$hpath";
       }
     }

     $hpath = Machination::HPath->new($client,$hpath);
     $last_hpath = $hpath;

     # call the function
     { no strict 'refs'; $f->($hpath->to_string,@{$_[0]}); };
     return $hpath->to_string . " $f " . join(",",map Machination::Parser::deref($_), @{$_[0]});
   },
  );

#$prog = sub { debug "prog\n"; my $p = star($Statement)->(@_);  return 5;};
$prog = T
  (
   concatenate(star($Statement), \&End_of_Input),
   sub{return $_[0]}
  );

open (my $fh, "<", $ARGV[0]);
my $stream = iterator_to_stream(make_lexer(fh_iterator($fh),@token_in));
my $parser = $prog;
my @res;

eval { @res=$parser->($stream); };
if(my $e = $@) {
  if(ref $e eq "ARRAY") {
    print "Parser died: " . Dumper($e);
  } else {
    die $e;
  }
}
#@res = $parser->($stream);
print Dumper(\@res);
exit;
while (defined (my $token = $res[1]->())) {
  if (ref $token) {
    my ($label,$value) = @$token;
    print "$label: $value\n"
  } else {
    print "$token\n";
  }
}
exit;

sub fh_iterator {
  my $fh = shift;
  $fh  ? return sub {
    my $l = <$fh>;
    if(defined $l) {
      debug "***** got $l";
    } else {
      debug "***** End of file!!!\n";
    }
    return $l
  } :
    return sub {return <>};
}

sub func_echo {
  return $_[0];
}

sub func_print {
  print "$_[0]\n";
  return "";
}

sub func_token {
  print "token returning $_[0], $_[1]\n";
  return  [$_[0], $_[1]];
}

sub func_cat {
  return join("",@_);
}

sub func_join {
  my $sep = shift;
  return join($sep,@_);
}

sub func_setvar {
  $vars->{$_[0]} = $_[1];
  return "";
}

sub func_getvar {
  return $vars->{$_[0]};
}

sub func_exists {
  showfn(@_);
  my ($args,$fields,$opts) = getargs(@_);
  my $path = shift @$args;

  # change field values of "<undef>" to undef
  map {
    $fields->{$_} = undef if($fields->{$_} eq "<undef>")
  } keys %$fields;

  if($client_type eq "ha") {
    my $hp = Machination::HPath->new($client,$path);
    if(defined $hp->id) {
      print "  exists\n";
      if(@_) {
        print "  checking fields\n";
        my $obj = Machination::HObject->new($client,$hp->type_id,$hp->id);
        my $dbdata = $obj->fetch_data(keys %$fields);
        my $different;
        foreach my $name (keys %$fields) {
          $different=1
            if(($dbdata->{$name} ne $fields->{$name}) ||
               (defined $dbdata->{$name} && !defined $fields->{$name}) ||
               (!defined $dbdata->{$name} && defined $fields->{$name}));
        }
        if($different) {
          print "  different from what we want: modifying\n";
          $obj->modify_data({actor=>$user},%$fields);
        } else {
          print "  as requested\n";
        }
      }
    } else {
      print "  does not exist\n";
      $client->create_path({actor=>$user},$path,$fields);
    }
  } elsif($client_type eq "web") {
#    $client->
  }
  return "";
}
sub func_notexists {
  showfn(@_);
  my ($args,$named,$opts) = getargs(@_);
  my $path = shift @$args;
  if($client_type eq "ha") {
    my $hp = Machination::HPath->new($client,$path);
    if(defined $hp->id) {
      $client->delete_obj({actor=>$user},$hp->type_id,$hp->id,
                         {'delete_obj:recursive'=>1});
    }
  } elsif($client_type eq "web") {

  }
  return "";
}

sub func_inhc {
  showfn(@_);
  my ($args,$kv,$opts) = getargs(@_);

  # hc should exist
  my $hchp = Machination::HPath->new($client, shift @$args);
  die "hc (" . $hchp->to_string . ") does not exist" unless $hchp->id;

  # object should exist
  my $objhp = Machination::HPath->new($client, shift@$args);
  die "object to link (" . $objhp->to_string . ") does not exist"
    unless $objhp->id;

  if($client->object_in_hc($objhp->type_id, $objhp->id, $hchp->id)) {
    print "  already in hc\n";
  } else {
    print "  not in hc - adding\n";
    $client->add_to_hc({actor=>$user}, $objhp->type_id, $objhp->id, $hchp->id);
  }

  return "";
}
sub func_notinhc {
  showfn(@_);
  my ($args,$kv,$opts) = getargs(@_);
  $opts->{del_orphans} = 0 unless exists $opts->{del_orphans};

  # hc should exist
  my $hchp = Machination::HPath->new($client, shift @$args);
  die "hc (" . $hchp->to_string . ") does not exist" unless $hchp->id;

  my $objhp = Machination::HPath->new($client, shift@$args);
  # trivially true if object doesn't exist
  if (not $objhp->id) {
    print "  " . $objhp->to_string . " doesn't exist\n";
    return "";
  }

  if($client->object_in_hc($objhp->type_id, $objhp->id, $hchp->id)) {
    print "  in hc - removing\n";
    $client->remove_from_hc({actor=>$user},
                            $objhp->type_id, $objhp->id, $hchp->id);
    if($opts->{del_orphans} and not
       $client->fetch_parents($objhp->type_id, $objhp->id)) {
      $client->delete_obj({actor=>$user},$objhp->type_id,$objhp->id);
    }
  } else {
    print "  not in hc\n";
  }

  return "";
}

sub func_members_exist {
  showfn(@_);
  my ($args) = getargs(@_);
  my $path = shift @$args;
  my $hp = Machination::HPath->new($client,$path);

  # $path ought to refer to a set
  die "tried to add members to a non set object $path"
    unless $hp->type eq "set";
  # $path ought to exist
  die "tried to add members to a set that does not exist: $path"
    unless $hp->id;

  my $set = Machination::HSet->new($client,$hp->id);

  # Make sure all the members exist and are of the correct type
  my @members;
  foreach my $memp (@$args) {
    print " queueing member $memp\n";
    if($set->is_internal) {
      my $mhp = Machination::HPath->new($client,$memp);
      die "prospective member $memp does not exist"
        unless $mhp->id;
      die "prospective member $memp is of type " . $mhp->type .
        ". Set contains members of type " . $set->member_type
          unless $set->member_type == $mhp->type_id;
      push @members, $mhp->id;
    } else {
      push @members, $memp;
    }
  }

  # add all members to the set
  $client->add_to_set({actor=>$user}, $set->id, @members);

  return "";
}
sub func_notmembers_exist {
  showfn(@_);
  my ($args) = getargs(@_);
  my $path = shift @$args;
  my $hp = Machination::HPath->new($client,$path);

  # $path ought to refer to a set
  die "tried to remove members from a non set object $path"
    unless $hp->type eq "set";
  # $path ought to exist
  die "tried to remove members from a set that does not exist: $path"
    unless $hp->id;

  my $set = Machination::HSet->new($client,$hp->id);

  # Make sure all the member paths are of the correct type
  my @members;
  foreach my $memp (@$args) {
    print " ensuring no member $memp\n";
    if($set->is_internal) {
      my $mhp = Machination::HPath->new($client,$memp);
      die "removal path $memp is of type " . $mhp->type .
        ". Set contains members of type " . $set->member_type
          unless $set->member_type == $mhp->type_id;
      push @members, $mhp->id;
    } else {
      push @members, $memp;
    }
  }

  # add all members to the set
  $client->remove_from_set({actor=>$user}, $set->id, @members);
  return "";
}

sub func_attached {
  showfn(@_);
  my ($args,$kv,$opts) = getargs(@_);
  $kv->{mandatory} = 0 unless exists $kv->{mandatory};
  $kv->{active} = 1 unless exists $kv->{active};
  my $path = shift @$args;
  my $hp = Machination::HPath->new($client,$path);

  # $path ought to refer to an hc
  die "cannot attach to a " . $hp->type
    unless not defined $hp->type or $hp->type eq "machination:hc";
  # $path ought to exist
  die "tried to attach to an hc that does not exist: $path"
    unless $hp->id;

  foreach my $attp (@$args) {
    my $ahp = Machination::HPath->new($client,$attp);
    # make sure it exists
    die "cannot attach non existant item $attp"
      unless $ahp->id;
    # make sure it is attachable
    die "cannot attach $attp, type " . $ahp->type . " is not attachable"
      unless $client->type_info($ahp->type_id)->{is_attachable};
    # see if it is already attached
    if($client->attachment_exists($hp->id, $ahp->type_id, $ahp->id, $kv->{mandatory})) {
      print "  $attp attached\n";
      next;
    }
    # do the attachment
    print "  $attp not attached - attaching\n";
    $client->attach_to_hc({actor=>$user},
                          $ahp->type_id, $ahp->id, $hp->id,
                          $kv->{mandatory}, $kv->{active},
                          $kv->{applies_to});
  }

  return "";
}
sub func_notattached {
  showfn(@_);
  my ($args,$kv) = getargs(@_);
  $kv->{mandatory} = 0 unless exists $kv->{mandatory};
  my $path = shift @$args;
  my $hp = Machination::HPath->new($client,$path);

  # $path ought to refer to an hc
  die "cannot detach from a " . $hp->type
    unless not defined $hp->type or $hp->type eq "machination:hc";
  # $path ought to exist
  die "tried to detach from an hc that does not exist: $path"
    unless $hp->id;

  foreach my $attp (@$args) {
    my $ahp = Machination::HPath->new($client,$attp);
    # see if it is attached
    if($client->attachment_exists($hp->id, $ahp->type_id, $ahp->id)) {
      print "  $attp attached - detaching\n";
      $client->detach_from_hc({actor=>$user},
                              $ahp->type_id, $ahp->id, $hp->id);
      next;
    }
    print "  $attp not attached\n";
  }


  return "";
}

sub func_type_id {
  if($client_type eq "ha") {
    return $client->type_id($_[0]);
  } else {
    return $client->call("TypeId",$_[0]);
  }
}

sub func_obj_id {
  my $hp = Machination::HPath->new($client, $_[0]);
  return $hp->id;
}

sub func_os_id {
  if($client_type eq "ha") {
    return $client->os_id(@_);
  } else {
    return $client->call("OsId",@_);
  }
}

sub channel_id {
  return $client->channel_id(@_);
}

sub func_last_hpath {
  return $last_hpath->to_string;
}

sub showfn {
  print "" . (caller(1))[3] . " " .
    join(",",map Machination::Parser::deref($_), @_) . "\n";
}

sub arg2str {
  my @str;
  foreach my $arg (@_) {
    my $str;
    foreach (@$arg) {
      ref $_ ? $str .= $_->[0] : $str .= $_;
    }
    push @str, $str;
  }
  return @str;
}

sub getcmd {
#  my $cmd = getline();
  my $cmd ;
  my $continue = 1;
  while ($continue) {
    my $line = getline();
    return $cmd unless(defined $line);
    $cmd .= $line;
    if ($cmd =~ /(\\+)$/) {
      if(length($1) % 2) {
        $cmd =~ s/\\$//;
      } else {
        $continue = 0;
      }
    } else {
      $continue = 0;
    }
  }
  return $cmd;
}

sub getline {
  my $line = <>;
#  $line_no++;
  chomp $line;
  $line =~ s/^\s+//;
  return getline() if(defined $line && $line eq "");
  return $line;
}

sub getargs {
  my @vals;
  my $keyvals;
  my $opts;
  foreach my $arg (@_) {
    if(! ref $arg) {
      push @vals, $arg;
    } elsif($arg->[0] eq "keyvalue") {
      $keyvals->{$arg->[1]} = $arg->[2];
    } elsif($arg->[0] eq "option") {
      $opts->{$arg->[1]} = $arg->[2];
    }
  }
  return (\@vals,$keyvals,$opts);
}
