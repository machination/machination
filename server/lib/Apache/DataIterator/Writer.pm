package Apache::DataIterator::Writer;
# Copyright 2011 Colin Higgs
#
# This file is part of Machination.
#
# Machination is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Machination is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Machination.  If not, see <http://www.gnu.org/licenses/>.

use File::Temp;
use Data::Dumper;
use POSIX;
use IO::Select;
use IO::Handle;
use Fcntl;
use File::Path;
use strict;

use Apache::DataIterator;

=pod

=head1 Apache::DataIterator::Writer

=head2 Write data somewhere in chunks to be requested a piece at a
time later

Apache::DataIterator::Writer and Apache::DataIterator::Reader work
together to allow iteration over a large dataset with multiple calls
to a mod_perl request handler. These calls are probably served by
multiple threads, if not multiple processes, and will need a way to
share data.

=head2 Synopsis

The following example assumes a mod_perl handler which dispatches
calls to callable_* subroutines. A set of routines which tie together
to send back directory listings might look like the following:

sub callable_list_dir_iterator {
  my $params = shift;
  my $path = $params->{path};
  my $directory_lister = A::Directory::Listing::Class->new($path);
  # $directory_lister must have certain methods as described below.

  my $itw = Apache::DataIterator::Writer->
    new($directory_lister,{chunk_size=>10});
  $itw->start;

  # How you get the id back to the client will be a matter for your
  # API implmentation. Lets pretend we should print it directly for now,
  # and that appropriate content headers have been printed elsewhere.
  print $itw->id;

  return Apache2::Const::OK;
}

sub callable_fetch_next {
  my $id = shift;
  my $itr = Apache::DataIterator::Reader->new($id);

  # The data is stored serialised (by Data::Dumper by default). You
  # can ask for it back as a data structure again with "next", or if
  # you know you are sending the data back in the same serialisation
  # format as it is stored, you can retrieve the serialised data
  # directly with "next_serialised"
  my $data = $itr->next;
  my $data_str = $itr->next_serialised;

  print to_web_string($data);
  # where &to_web_string puts the data in the right format to be sent
  # back to the remote caller (XML, JSON, etc) and is implemented
  # elsewhere.

  # or
  print $data_str;

  return Apache2::Const::OK;
}

If the dispatching is done by url and CGI style parameter passing, the
remote caller (curl in our example) might have to do something like
the following:

$ curl http://server/base_url/call/list_dir_iterator?path=/tmp

Lets say this returns "123456" as the id and that there are 100 files
in /tmp.

$ curl http://server/base_url/call/fetch_next?id=123456

should show the first 10 (serialised). A further call

$ curl http://server/base_url/call/fetch_next?id=123456

should show the next 10, and so on.

=head2 Apache::DataIterator::Writer

=head3 Methods:

=over

=item B<new>

$itw = Apache::DataIterator::Writer->new($data_fetcher);

=cut

sub new {
  my $this = shift;
  my $class = ref($this) || $this;
  my $self = {};
  bless $self,$class;

  $self->fetcher(shift);
  my %opts = @_;

  # The following attributes are not used during initialisation
  $self->nfetch(10);
  $self->max_iterations(100);
  $self->max_write_ahead(10);
  $self->check_write_ahead_every(10);
  $self->idle_timeout(300);

  # The following attributes are used during initialisation
  $self->dir("/dev/shm/");
  $self->dir($opts{dir}) if exists $opts{dir};
  $self->cleanup_flag(1);
  $self->cleanup_flag($opts{cleanup_flag}) if exists($opts{cleanup_flag});
  $self->template("apache-dataiterator-XXXXXXXX");
  $self->template($opts{template}) if exists $opts{template};


  my $dir = File::Temp->newdir
    ($self->template,
     DIR=>$self->dir,
     CLEANUP=>$self->cleanup_flag);
  $self->_tmp_obj($dir);
  $self->id("$dir");
  mkdir "$dir/data";
  mkdir "$dir/info";
  mkdir "$dir/info/server";
  mkdir "$dir/info/client";
  mkfifo("$dir/rw_coordinate",0600) ||
    die "could not create rw_coordinate $^E";

#  STDOUT->autoflush(1);

  return $self;
}

sub fetcher {
  my $self = shift;
  if(@_) {
    my $fetcher = shift;
    $self->{fetcher} = $fetcher;
  }
  return $self->{fetcher};
}

sub dir {
  my $self = shift;
  if(@_) {
    $self->{dir} = shift;
  }
  return $self->{dir};
}

sub _tmp_obj {
  my $self = shift;
  if(@_) {
    $self->{_tmp_obj} = shift;
  }
  return $self->{_tmp_obj};
}

sub cleanup_flag {
  my $self = shift;
  if(@_) {
    $self->{cleanup_flag} = shift;
  }
  return $self->{cleanup_flag};
}

sub id {
  my $self = shift;
  if(@_) {
    $self->{id} = shift;
  }
  return $self->{id};
}

sub idle_timeout {
  my $self = shift;
  if(@_) {
    $self->{idle_timeout} = shift;
  }
  return $self->{idle_timeout};
}

sub template {
  my $self = shift;
  if(@_) {
    $self->{template} = shift;
  }
  return $self->{template};
}

sub nfetch {
  my $self = shift;
  if(@_) {
    $self->{nfetch} = shift;
  }
  return $self->{nfetch};
}

sub max_iterations {
  my $self = shift;
  if(@_) {
    $self->{max_iterations} = shift;
  }
  return $self->{max_iterations};
}

sub max_write_ahead {
  my $self = shift;
  if(@_) {
    $self->{max_write_ahead} = shift;
  }
  return $self->{max_write_ahead};
}

sub check_write_ahead_every {
  my $self = shift;
  if(@_) {
    $self->{check_write_ahead_every} = shift;
  }
  return $self->{check_write_ahead_every};
}

sub start {
  my $self = shift;

#  $dir = "/dev/shm/apache-dataiterator";
  my $dir = $self->id;
#  print "starting new iterator in $dir\n";

  $self->fetcher->ITERATOR_INIT;

  my $chunk = 0;
  my $last_read = -1;
  my $fetch_n_chunks;
  my $continue = 1;
  my $still_fetching = 1;
  { local *N;
    open(N,">$dir/next");
    print N 0;
    close N;
  }
 AHEAD_LOOP:  while ($continue) {
#    print "starting ahead loop, last_read = $last_read, n = $fetch_n_chunks\n";
    if($still_fetching) {
      # fetch some data and write it to the shared data dir
      $fetch_n_chunks = $self->max_write_ahead + $last_read + 1 - $chunk;
      foreach (1..$fetch_n_chunks) {
        my @data = $self->fetcher->ITERATOR_NEXT($self->nfetch,$self->id);
        if(@data) {
#          print "  fetching new data\n";
          open DATA, "> $dir/data/$chunk";
          print DATA $self->serialise($chunk,@data);
          close DATA;
          $chunk++;
        } else {
          # no more data left - stop fetching
#          print "  no more data\n";
          $still_fetching = 0;
          last;
        }
      }
    }
    # Now have a look to see how far ahead we are. Read from
    # rw_coordinate until we block (if reader is more than
    # max_read_ahead behind), would block (if reader is between 0 and
    # max_read_ahead behind) or have caght up (reader is 0 behind)
    my $behind = $chunk - $last_read - 1;

    my $f;
    my $sel = IO::Select->new;
    my $reopen = 1;

    while($behind) {
#      print "starting behind loop, behind = $behind\n";
      # going to try to read a line from $f, but slightly differently
      # depending on how far ahead we are.
      my $line;
      my $timeout;
      my $on_timeout;

      if($reopen) {
        sysopen($f, "$dir/rw_coordinate",O_RDONLY | O_NONBLOCK);
        $sel->add($f);
        $reopen = 0;
      }

      if($behind >= $self->max_write_ahead) {
#        print "more than limit behind - select for idle_timeout\n";
        # try to read $f, block for idle_timeout, clean up request if timeout
        my @ready = $sel->can_read($self->idle_timeout);
        if(@ready) {
#          print "  ready to read\n";
          if($f->eof) {
#            print "  read eof\n";
            # Getting eof is quite common: each read comes from a different
            # process or thread. We want to ignore them.
            $sel->remove($f);
            $reopen = 1;
          } else {
            $line = $f->getline;
            chomp $line;
#            print "  read $line\n";
          }
        } else {
          # timeout
#          print "timed out waiting for reader\n";
          $self->cleanup($dir);
          $continue = 0;
          last;
        }
      } elsif($self->max_write_ahead > $behind && $behind > 0) {
#        print "$behind is between 0 and max_write_ahead\n";
        # try to read $f, don't block, go around and get more data if
        # would have blocked (i.e. we can fetch more chunks before
        # reaching max_write_ahead).
        my @ready = $sel->can_read(0);
        if(@ready) {
#          print "  ready to read\n";
          if($f->eof) {
#            print "  read eof\n";
            $sel->remove($f);
            $reopen = 1;
          } else {
            $line = $f->getline;
            chomp $line;
#            print "  read $line\n";
          }
        } else {
#          print "  nothing ready\n";
          # would have bocked
          if($still_fetching) {
            # don't wait for reader to catch up - go around again to
            # fetch more chunks.
#            print "  still fetching\n";
            last; # will break out of this loop to the enclosing one
          } else {
            # No more data to fetch - lets really block for idle_timeout
#            print "  not fetching - blocking, behind = $behind\n";
            @ready = $sel->can_read($self->idle_timeout);
            if(@ready) {
              if($f->eof) {
#                print "  read eof\n";
                $sel->remove($f);
                $reopen = 1;
              } else {
                $line = $f->getline;
                chomp $line;
              }
            } else {
              # timeout
#              print "  timed out waiting for reader\n";
              $self->cleanup($dir);
              $continue = 0;
              last;
            }
          }
        }
      }
#      print "  processing $line\n";
      chomp($line);
      if($line eq "r") {
        # $line represents a chunk file read by the reader
        $last_read++;
        # update the "next" file to tell readers which to read next
        { local *N;
          open (N,">$dir/next");
          print N $last_read + 1;
          close N;
        }
#        print "reader read a line: last read now $last_read\n";
        unlink("$dir/data/$last_read");
        $behind = $chunk - $last_read - 1;
#        print "  finishing behind loop with " .
#          "last_read=$last_read, behind=$behind\n";
      } elsif($line eq "f") {
        # reader is signaling that it has finished
        $self->cleanup($dir);
        $continue = 0;
        last;
      }
    }
    if(!$still_fetching) {
      $self->cleanup($dir);
      $continue = 0;
    }
  }
}

sub serialise {
  my $self = shift;
  my $chunk = shift;

#  print "serialising " . join(",",@_) . "\n";

  if ($self->fetcher->can("SERIALISE")) {
    return $self->fetcher->SERIALISE({chunk=>$chunk,data=>\@_});
  } else {
    { local $Data::Dumper::Purity=1;
      local $Data::Dumper::Indent=0;
      return Dumper({chunk=>$chunk,data=>\@_});
    }
  }
}

sub store_info {
  my $self = shift;
  my $type = shift;
  my $name = shift;
  my $data = shift;

  die "store_info: argument 1 must be 'server' or 'client'"
    unless($type eq 'server' || $type eq 'client');

  die "store_info: name (argument 2) must contain only characters from " .
    "[:alnum:]+-_" unless(Apache::DataIterator::valid_info_name($name));

  my $dir = $self->id;
  {
    local *INFO_FILE;
    open INFO_FILE, ">$dir/info/$type/$name";
    print INFO_FILE $data;
    close INFO_FILE;
  }
}

sub cleanup {
  my $self = shift;
  my $dir = shift;

  $self->fetcher->ITERATOR_PRECLEANUP($self->id)
    if($self->fetcher->can("ITERATOR_PRECLEANUP"));
  $self->_tmp_obj(undef);
  $self->fetcher->ITERATOR_POSTCLEANUP($self->id)
    if($self->fetcher->can("ITERATOR_POSTCLEANUP"));
}

1;
