package Apache::DataIterator;

sub valid_info_name {
  my $name = shift;

  return $name=~/^[[:alnum:]+\-_]+$/;
}

1;
