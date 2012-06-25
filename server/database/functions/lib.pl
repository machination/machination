if ($_SHARED{lib}) {
  elog(INFO,"reloading library");
}

$_SHARED{lib} = {} unless($_SHARED{lib});
my $lib = $_SHARED{lib};

$lib->{init_cache} = sub {
  return $lib->{clear_cache}() unless($_SHARED{libcache});
  return $_SHARED{libcache};
};

$lib->{clear_cache} = sub {
  return $_SHARED{libcache} = {};
};

$lib->{hello} = sub {
  elog(INFO,"hello from library function");
};

$lib->{dumper_max_recursion} = 100;
$lib->{dumper} = sub {
  my ($thing,$opts,$level) = @_;
  if ($level > $lib->{dumper_max_recursion}) {
    elog(ERROR,"too much recursion in dumper " .
         "(limit = " . $lib->{dumper_max_recursion});
  }

  my $str;
  my $indent = "  ";
  my $levindent = $indent x $level;
  #    elog(INFO,'ref($thing) = ' . ref($thing));

  #    $str .= $indent;
  if (ref($thing)) {
    if (ref($thing) eq "ARRAY") {
	    $str .= "\[\n";
	    foreach my $newthing (@$thing) {
        $str .= $levindent . $indent .
          $lib->{dumper}($newthing,$opts,$level+1) .
            ",\n";
	    }
	    $str .= "$levindent\]";
    } elsif (ref($thing) eq "HASH") {
	    $str .= "{\n";
	    foreach my $key (keys %$thing) {
        #		elog(INFO,"processing key $key");
        $str .= $levindent . $indent .
          $key . " => " .
            $lib->{dumper}($thing->{$key},$opts,$level+1) .
              ",\n";
	    }
	    $str .= "$levindent}";

    } else {
	    elog(ERROR,"called dumper on a " . ref($thing) .
           " - don't know how to deal with that");
    }
  } else {
    # scalar
    $str = $thing;
  }

  return $str;
};

$lib->{column_types} = sub {
  my ($table_name) = @_;
  my $cache = $lib->{init_cache}();

  # return straight away if we have a cache hit
  if ($cache->{column_types}->{$table_name}) {
    return $cache->{column_types}->{$table_name};
  }

  # need to find the answer
  my $ret = spi_exec_query(
                           "select col.attname, t.typname, t.typcategory from " .
                           "pg_catalog.pg_attribute as col, " .
                           "pg_catalog.pg_class as class, " .
                           "pg_catalog.pg_type as t " .
                           "where col.attrelid=class.oid and " .
                           "class.relname='$table_name' and " .
                           "col.attnum > 0 and " .
                           "col.atttypid=t.oid"
                          );
  foreach my $row (@{$ret->{rows}}) {
    $cache->{column_types}->{$table_name}->{$row->{attname}} =
      {
       name=>$row->{typname},category=>$row->{typcategory}};
  }
  return $cache->{column_types}->{$table_name};
};

$lib->{quote} = sub {
  my ($cat,$value) = @_;

  if (!defined $value) {
    return "NULL";
  }
  if ($cat eq "N") {
    return $value;
  }
  if ($cat eq "S" || $cat eq "B") {
    my $copy = $value;
    $copy =~ s/'/''/g;
    return "'$copy'";
  } else {
    elog(ERROR, "cannot quote values of category \"$cat\" " .
         "- don't know how");
  }
};

elog(INFO,"loaded library");
