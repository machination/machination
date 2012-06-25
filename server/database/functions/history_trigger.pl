# Initialise
#
# set to some true value to enable debug messages
$debug = 1;
# Load lib functions if not already loaded
unless ($_SHARED{lib}) {
  spi_exec_query("select lib()");
}
my $lib = $_SHARED{lib};
# a place to hold otherwise anonymous subroutines
my $subs = {};
$subs->{insert_history_row} = sub {
  my ($htable,$op,$deletes,$cols,$vals) = @_;
  if ($deletes) {
    $deletes = "'t'";
  } else {
    $deletes = "'f'";
  }
  my @cols = @$cols;
  my $coltypes = $lib->{column_types}($_TD->{table_name});
  my $i = 0;
  my @qvals;
  foreach my $val (@$vals) {
    push @qvals, $lib->{quote}($coltypes->{$cols[$i]}->{category}, $val);
    $i++;
  }
  #    $op = substr($op,0,1);
  unshift @cols, "history_db_op";
  unshift @qvals, "'$op'";
  unshift @cols, "history_timestamp";
  unshift @qvals, "current_timestamp";
  unshift @cols, "history_deletes";
  unshift @qvals, $deletes;
  my $sql = "insert into $htable (" .
    join(",",@cols) .
      ") values (" .
        join(",",@qvals) .
          ")";
  elog(INFO,"executing: $sql") if($debug);
  spi_exec_query($sql);
};

# To hold the return objects from queries
my $ret;

my $htable = "zzh_" . $_TD->{table_name};
elog(INFO,"updating history table $htable") if($debug);

my $ev = $_TD->{event};
elog(INFO,"event: $ev") if($debug);

if ($ev eq "INSERT") {
  my @cols = keys %{$_TD->{new}};
  my @vals = values %{$_TD->{new}};
  $subs->{insert_history_row}($htable,"I",0,\@cols,\@vals);
} elsif ($ev eq "UPDATE") {
  # We model this as a delete and an add,
  # but with db_op "U" so we remember it was really an update.

  # "delete"
  my %old = %{$_TD->{old}};
  $old{rev_id} = $_TD->{new}->{rev_id};
  my @oldcols = keys %old;
  my @oldvals = values %old;
  $subs->{insert_history_row}($htable,"U",1,\@oldcols,\@oldvals);

  # "add"
  my @cols = keys %{$_TD->{new}};
  my @vals = values %{$_TD->{new}};
  $subs->{insert_history_row}($htable,"U",0,\@cols,\@vals);
} elsif ($ev eq "DELETE") {
  # make sure the revision number is the latest one
  my %data = %{$_TD->{old}};
  my $ret = spi_exec_query("select currval('revisions_id_seq')",1);
  $data{rev_id} = $ret->{rows}[0]->{currval};

  my @cols = keys %data;
  my @vals = values %data;
  $subs->{insert_history_row}($htable,"D",1,\@cols,\@vals);
} else {
  elog(ERROR,"cannot use this trigger on event type $ev");
}

return;
