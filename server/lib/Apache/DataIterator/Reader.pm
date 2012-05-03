package Apache::DataIterator::Reader;

use Apache::DataIterator;
use Data::Dumper;

sub next {
  my $dir = shift;

  # find out which is the next data file
  my $next;
  {
    local *N;
    open (N,"<$dir/next");
    $next = <N>;
    close N;
  }
  print "next is $next\n";

  # read the data from it
  my $data;
  {
    local *D;
    open(D,"<$dir/data/$next");
    -f D && sysread(D,$data,-s D);
    close D;
  }
  $data = eval $data;

  # write to the coordinating pipe to say that we have read a data page
  {
    local *C;
    open(C,">$dir/rw_coordinate");
    print C "r";
    close C;
  }

  return $data;
}

sub finish {
  my $dir = shift;

  # write to the coordinating pipe to say that we have finished
  {
    local *C;
    open(C,">$dir/rw_coordinate");
    print C "f";
    close C;
  }

}

sub retrieve_info {
  my $dir = shift;
  my $type = shift;
  my $name = shift;

  die "retrieve_info: argument 1 must be 'server' or 'client'"
    unless($type eq 'server' || $type eq 'client');

  die "retrieve_info: name (argument 2) must contain only characters from " .
    "[:alnum:]+-_" unless(Apache::DataIterator::valid_info_name($name));

  my $data;
  {
    local *INFO_READ;
    open INFO_READ, "<$dir/info/$type/$name";
    -f INFO_READ && sysread(INFO_READ,$data,-s INFO_READ);
    close INFO_READ;
  }
  return $data;
}


1;
