package Machination::HObject;

use Moose;
use namespace::autoclean;
use Machination::HPath;

use Data::Dumper;

has "ha" => (is=>"ro",
             required=>1,
             handles=>[qw(read_dbh write_dbh)]);
has "hpath" => (is=>"ro",
                writer=>"_set_hpath",
                required=>1,
                handles=>[qw(to_string id id_path)]);

sub BUILD {
  my $self = shift;
  my $args = shift;

  if(!ref $self->hpath) {
    $self->_set_hpath(Machination::HPath->new($self->ha,$self->hpath));
  }
}

__PACKAGE__->meta->make_immutable;

1;
