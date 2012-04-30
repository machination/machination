package Machination::Parser;

use warnings;
use strict;
use base 'Exporter';
use Data::Dumper;
use HOP::Stream qw(drop tail head node is_node);

our @EXPORT_OK =
  qw(
      lookfor
      parser
      concatenate
      alternate
      star
      list_values_of
      absorb
      nothing
      null_list
      End_of_Input
      star2
      T
      debug
   );
our %EXPORT_TAGS = ( 'all' => \@EXPORT_OK );

our %N;
$N{\&End_of_Input} = 'EOI';
$N{\&nothing} = '(nothing)';
$N{\&null_list} = 'null_list';
#$N{$Expression} = 'expression';
#$N{$Term} = 'term';
#$N{$Factor} = 'factor';

sub parser(&);    # Forward declaration - see below
sub debug($);

sub lookfor {
  my $wanted = shift;
  my $value = shift || sub {$_[0][1]};
  my $param = shift;

  $wanted = [$wanted] unless ref $wanted;
#  debug "lookfor " . Dumper($wanted);
  my $id = "[@$wanted]";
  my $parser = parser {
    my $input = shift;
    debug "lookfor $id\n";
    debug "input is " . deref($input) . "\n";
    $input = node(@$input) if ref($input) eq 'ARRAY';
    debug "noded input is " . deref($input) . "\n";
    unless ( defined $input ) {
#      die "no input specified";
      die [ 'TOKEN', $input, $wanted ];
    }

#    my $next = $input->('peek');
    my $next = head($input);
    debug "next is " . deref($next) . " ($next)\n";
    for my $i ( 0 .. $#$wanted ) {
      next unless defined $wanted->[$i];
      no warnings 'uninitialized';
      unless ($wanted->[$i] eq $next->[$i]) {
        debug "failure: lookfor $id\n";
        die [ 'TOKEN', $input, $wanted ];
#        die "lookfor " . join(",",@$wanted) . " failed: found " . join(",",@$next);
      }
    }
    my $wanted_value = $value->( $next, $param );
    
    # the following is unlikely to affect a stream with a promise
    # for a tail as the promise tends to Do The Right Thing.
    #
    # Otherwise, the AoA stream might just return an aref for
    # the tail instead of an AoA.  This breaks things
    my $tail = tail($input);
#    if ( is_node($tail) && !is_node($tail->[0]) ) {
#      $tail = [$tail];
#    }
    debug "success: found $wanted_value\n";
#    sleep 1;
    return ( $wanted_value, $tail);
  };
  $N{$parser} = $id;
#  debug "returning parser: " . Dumper($parser);
  return $parser;
}

sub concatenate {
  shift unless ref $_[0];
  my @parsers = @_;
  return \&nothing   if @parsers == 0;
  return $parsers[0] if @parsers == 1;

  my $id;
  {
    no warnings 'uninitialized';
#    $id = "@N{@parsers}";
    $id = join ( " + ", map $N{$_}, @parsers );
  }

  my $parser = parser {
    my $input = shift;
    debug "cat looking for $id\n";
    my ( $v, @values );
    my ($q, $np) = (0, scalar @parsers);
    for (@parsers) {
      $q++;
      debug "trying $N{$_} ($q/$np)\n";
      unless (( $v, $input ) = $_->($input)) {
        debug "Failed concatenated component $q/$np\n";
        return;
      }
      debug "Matched concatenated component $q/$np with " .
        _textof($v) . "\n";
      push @values, $v if defined $v;   # assumes we wish to discard undef
    }
    debug "Finished matching $id\n";
    return ( \@values, $input );
  };
  $N{$parser} = $id;
  return $parser;
}

sub _textof {
  my $v = shift;
  return "UNDEF" unless defined $v;
  return $v unless ref $v;
  my $d = Data::Dumper->new($v);
#  $d->Terse;
  return "$v = " . $d->Dump;
}

sub alternate {
  my @parsers = @_;
  return parser { return () }
    if @parsers == 0;
  return $parsers[0] if @parsers == 1;

  my $id;
  {
    no warnings 'uninitialized';
    $id = join ( " | ", map $N{$_}, @parsers );
  }

  my $parser = parser {
    my $input = shift;
    my @failures;

    debug "alternate ($id)\n";
    for (@parsers) {
      my ( $v, $newinput ) = eval { $_->($input) };
      if ($@) {
        debug "sub parser $N{$_} died\n";
        die $@ unless ref $@ eq "ARRAY"; # not a parser failure
        push @failures, $@;
      }
      else {
        return ( $v, $newinput );
      }
    }
    die [ 'ALT', $input, \@failures ];
  };
  $N{$parser} = "($id)";

  return $parser;
}

sub star2 {
  my $p = shift;
  my $p_star;
  $p_star = alternate(concatenate($p, parser {$p_star->(@_)}),\&nothing);
}

sub star {
    my $p = shift;
    my ($p_star,$conc,$star_tail);
    $p_star = alternate
      (
       T(
         $conc = concatenate( $p, $star_tail = parser { $p_star->(@_) }),
         sub {
           my ( $first, $rest ) = @_;
           [ $first, @$rest ];
         }
        ),
       \&null_list
      );
    $N{$star_tail} = "star_tail";
    $N{$p_star} = "star($N{$p})";
    $N{$conc} = "$N{$p} + $N{$p_star}";
    debug "$N{$p_star}\n";
    return $p_star;
}

sub list_values_of {
  my ( $element, $separator ) = @_;
  $separator = lookfor('COMMA') unless defined $separator;

  return T(
           concatenate
           (
            $element, star( concatenate( absorb($separator), $element ) )
           ),
           sub {
             my @matches = shift;
             if ( my $tail = shift ) {
               foreach my $match (@$tail) {
                 push @matches, grep defined $_, @$match;
               }
             }
             return \@matches;
           }
          );
}


sub T {
    my ( $parser, $transform ) = @_;
    my $p = parser {
        my $input = shift;
        if ( my ( $value, $newinput ) = $parser->($input) ) {
            local $^W;    # using this to suppress 'uninitialized' warnings
            $value = [$value] if !ref $value;
            $value = $transform->(@$value);
            return ( $value, $newinput );
        }
        else {
            return;
        }
    };
    $N{$p} = $N{$parser};
    return $p;
}

sub absorb {
    my $parser = shift;
    return T( $parser, sub { () } );
}

sub End_of_Input {
    my $input = shift;
    return ( undef, undef ) unless defined($input);
    die [ "End of input", $input ];
}

sub nothing {
    my $input = shift;
    return ( undef, $input );
}

sub null_list {
    my $input = shift;
    return ( [], $input );
}

sub parser (&) { $_[0] }

sub debug ($) {
  return unless $ENV{DEBUG};
  my $msg = shift;
  my $i = 0;
  $i++ while caller($i);
  my $I = " " x ($i-2);
  $I =~ s/../ |/g;
  print $I, $msg;
}

sub deref {
  my $in = shift;
#  return "[@$in]";
#  ref $in || return $in;
  if(! defined $in) {
    return "UNDEF";
  } elsif(ref $in eq "ARRAY" || ref $in eq "HOP::Stream") {
    return substr(ref($in),0,1) . "[" . join(",", map {deref($_)} @$in) . "]";
  } elsif (ref $in eq "CODE") {
    return $N{$in} || $in;
  } else {
    return $in;
  }
}

1;
